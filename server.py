import os
import threading
from typing import List, Dict

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker, Session

from db import get_engine, Base, AgentModel, Conversation, Message
from lib import (
    simulate_hackathon_turn,
    agents as lib_agents,
    get_conversation_groups,
    get_agents_in_conversation_group,
)

# ------------------------------------------------------------------------------
# Database setup
# ------------------------------------------------------------------------------
engine = get_engine()
SessionLocal = sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False, autocommit=False, future=True
)
Base.metadata.create_all(engine)

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = FastAPI(title="Hackathon Simulation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (expects index.html in this directory if present)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")


# ------------------------------------------------------------------------------
# In-memory state
# ------------------------------------------------------------------------------
state_lock = threading.Lock()

# Map conversation group id -> DB conversation id
group_conversation_ids: Dict[int, int] = {}


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _persist_agents_if_needed(session: Session):
    existing = {a.name for a in session.query(AgentModel).all()}
    to_add = []
    for a in lib_agents:
        if a.name not in existing:
            to_add.append(
                AgentModel(name=a.name, personality=a.personality, idea=a.idea)
            )
    if to_add:
        session.add_all(to_add)
        session.commit()


def _ensure_conversation_for_group(session: Session, group_id: int) -> int:
    conv_id = group_conversation_ids.get(group_id)
    if conv_id is not None:
        return conv_id
    conv = Conversation()
    session.add(conv)
    session.commit()
    session.refresh(conv)
    group_conversation_ids[group_id] = conv.id
    return conv.id


def _get_group_memory_snapshot() -> Dict[int, int]:
    """
    Returns a dict of group_id -> current memory length (assumes
    all agents in a group share the same memory length).
    """
    snapshot: Dict[int, int] = {}
    for gid in get_conversation_groups():
        agents_in_group = get_agents_in_conversation_group(gid)
        if not agents_in_group:
            snapshot[gid] = 0
        else:
            # Memory list is shared semantically; take the length from the first agent
            snapshot[gid] = len(agents_in_group[0].memory)
    return snapshot


def _memory_entries_for_group(group_id: int) -> List[Dict]:
    """
    Returns the in-memory conversation for a group as a list of dicts:
    {turn, speaker, text}
    """
    agents_in_group = get_agents_in_conversation_group(group_id)
    if not agents_in_group:
        return []
    mem = agents_in_group[0].memory
    out = []
    for i, entry in enumerate(mem, start=1):
        out.append({"turn": i, "speaker": entry.speaker, "text": entry.text})
    return out


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.get("/")
def read_root():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "ok", "message": "Hackathon Simulation API"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/agents")
def get_agents():
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
    # Expose agent fields relevant to clients; memory is available via conversation endpoints
    return [
        {
            "name": a.name,
            "personality": a.personality,
            "idea": a.idea,
            "conversation_group": a.conversation_group,
        }
        for a in lib_agents
    ]


@app.get("/groups")
def groups_list():
    groups_info = []
    for gid in sorted(get_conversation_groups()):
        members = get_agents_in_conversation_group(gid)
        groups_info.append(
            {
                "group": gid,
                "members": [
                    {
                        "name": a.name,
                        "personality": a.personality,
                        "idea": a.idea,
                        "conversation_group": a.conversation_group,
                        "memory_length": len(members[0].memory) if members else 0,
                    }
                    for a in members
                ],
            }
        )
    return {"groups": groups_info}


@app.get("/groups/{group_id}/conversation")
def groups_conversation(group_id: int):
    # Prefer DB if we have persisted conversation for this group, else fall back to in-memory
    conv_id = group_conversation_ids.get(group_id)
    if conv_id is None:
        # in-memory fallback
        return {
            "group": group_id,
            "messages": _memory_entries_for_group(group_id),
        }

    with SessionLocal() as session:
        msgs = (
            session.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.turn.asc())
            .all()
        )
        return {
            "group": group_id,
            "conversation_id": conv_id,
            "messages": [
                {
                    "id": m.id,
                    "turn": m.turn,
                    "speaker": m.speaker,
                    "text": m.text,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ],
        }


@app.post("/reset")
def reset():
    # Clear all agent memories and forget conversation-id mappings.
    with state_lock:
        for a in lib_agents:
            a.memory.clear()
        group_conversation_ids.clear()
    # Ensure agents are present in DB
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
    return {"ok": True}


@app.post("/simulate/turn")
def simulate_one_turn():
    """
    Runs one global turn:
      - Each conversation group may produce one new message (via lib.simulate_hackathon_turn)
      - New messages are persisted to the DB under per-group conversations
      - Returns the set of new messages (group, turn, speaker, text)
    """
    with state_lock:
        before_snapshot = _get_group_memory_snapshot()
        # Run one turn across all groups via the library
        simulate_hackathon_turn()
        after_snapshot = _get_group_memory_snapshot()

        # Collate new messages per group (typically 0 or 1 per group per turn)
        new_messages: List[Dict] = []
        for gid in sorted(get_conversation_groups()):
            before_len = before_snapshot.get(gid, 0)
            after_len = after_snapshot.get(gid, 0)
            if after_len <= before_len:
                continue  # no new messages for this group

            # Take new entries from in-memory state
            entries = _memory_entries_for_group(gid)[before_len:after_len]
            # Persist and include in response
            with SessionLocal() as session:
                _persist_agents_if_needed(session)
                conv_id = _ensure_conversation_for_group(session, gid)
                for msg in entries:
                    # msg has turn relative to full history; use that as DB turn
                    db_msg = Message(
                        conversation_id=conv_id,
                        turn=int(msg["turn"]),
                        speaker=str(msg["speaker"]),
                        text=str(msg["text"]),
                    )
                    session.add(db_msg)
                    session.commit()
                    session.refresh(db_msg)
                    new_messages.append(
                        {
                            "group": gid,
                            "conversation_id": conv_id,
                            "id": db_msg.id,
                            "turn": db_msg.turn,
                            "speaker": db_msg.speaker,
                            "text": db_msg.text,
                            "created_at": db_msg.created_at.isoformat(),
                        }
                    )

    return {"ok": True, "messages": new_messages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
