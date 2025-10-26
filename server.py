import os
import threading
import copy
from typing import List, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker, Session

from main import agents as base_agents, simulate_hackathon
from db import get_engine, Base, AgentModel, Conversation, Message


# Database engine and session
engine = get_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False, future=True)


# Ensure tables exist
Base.metadata.create_all(engine)


# Application
app = FastAPI(title="Hackathon Simulation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Serve index.html from project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")


@app.get("/")
def read_root():
    index_path = os.path.join(BASE_DIR, "index.html")
    return FileResponse(index_path)


# In-memory state for current conversation
state_lock = threading.Lock()
state_agents: List[Dict] = [copy.deepcopy(a) for a in base_agents]
state_history: List[Dict] = []
current_conversation_id: Optional[int] = None

# Group state
group_assignments: List[List[int]] = []  # list of lists of agent indices
group_histories: List[List[Dict]] = []   # parallel list of message dicts
group_conversation_ids: Dict[int, int] = {}  # group index -> conversation id


def _ensure_conversation(session: Session) -> int:
    global current_conversation_id
    if current_conversation_id is not None:
        return current_conversation_id
    conv = Conversation()
    session.add(conv)
    session.commit()
    session.refresh(conv)
    current_conversation_id = conv.id
    return current_conversation_id


def _persist_agents_if_needed(session: Session):
    existing = {a.name for a in session.query(AgentModel).all()}
    to_add = []
    for a in state_agents:
        if a["name"] not in existing:
            to_add.append(AgentModel(name=a["name"], personality=a["personality"], idea=a["idea"]))
    if to_add:
        session.add_all(to_add)
        session.commit()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/agents")
def get_agents():
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
    return [{"name": a["name"], "personality": a["personality"], "idea": a["idea"]} for a in state_agents]


@app.get("/conversation")
def get_conversation():
    with SessionLocal() as session:
        if current_conversation_id is None:
            return {"conversation_id": None, "messages": state_history}
        msgs = (
            session.query(Message)
            .filter(Message.conversation_id == current_conversation_id)
            .order_by(Message.turn.asc())
            .all()
        )
        return {
            "conversation_id": current_conversation_id,
            "messages": [
                {"id": m.id, "turn": m.turn, "speaker": m.speaker, "text": m.text, "created_at": m.created_at.isoformat()}
                for m in msgs
            ],
        }


@app.post("/reset")
def reset():
    global state_agents, state_history, current_conversation_id, group_assignments, group_histories, group_conversation_ids
    with state_lock:
        state_agents = [copy.deepcopy(a) for a in base_agents]
        state_history = []
        current_conversation_id = None
        group_assignments = []
        group_histories = []
        group_conversation_ids = {}
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
    return {"ok": True}


@app.post("/simulate/turn")
def simulate_one_turn():
    global state_history
    with state_lock:
        seed = list(state_history)
        result = simulate_hackathon(state_agents, turns=1, callback=None, seed_history=seed)
        # result.history includes the full history; append only the last entry
        if not result.get("history"):
            return {"ok": False, "error": "no history returned"}
        last_entry = result["history"][-1]
        state_history.append(last_entry)

    # Persist to DB
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
        conv_id = _ensure_conversation(session)
        # Determine next turn number for DB based on count
        next_turn = last_entry.get("turn")
        msg = Message(
            conversation_id=conv_id,
            turn=int(next_turn),
            speaker=last_entry.get("speaker", ""),
            text=last_entry.get("text", ""),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

    return {"ok": True, "message": last_entry}


# -------- Grouped conversation endpoints --------
def _ensure_groups(num_groups: int):
    """Ensure we have group structures; if not, create with num_groups groups."""
    global group_assignments, group_histories
    if group_assignments:
        return
    n = max(1, int(num_groups))
    idxs = list(range(len(state_agents)))
    import random as _random
    _random.shuffle(idxs)
    groups = [[] for _ in range(n)]
    for i, idx in enumerate(idxs):
        groups[i % n].append(idx)
    group_assignments = groups
    group_histories = [[] for _ in groups]


@app.post("/groups/regroup")
def groups_regroup(payload: Dict):
    """Shuffle agents into N groups and reset group histories (does not reset per-agent memories)."""
    global group_assignments, group_histories, group_conversation_ids
    num_groups = int(payload.get("num_groups", 1))
    if num_groups < 1:
        num_groups = 1
    with state_lock:
        idxs = list(range(len(state_agents)))
        import random as _random
        _random.shuffle(idxs)
        groups = [[] for _ in range(num_groups)]
        for i, idx in enumerate(idxs):
            groups[i % num_groups].append(idx)
        group_assignments = groups
        group_histories = [[] for _ in groups]
        group_conversation_ids = {}
    return groups_list()


@app.get("/groups")
def groups_list():
    if not group_assignments:
        _ensure_groups(1)
    groups = []
    for gi, group in enumerate(group_assignments):
        members = [
            {"index": idx, "name": state_agents[idx]["name"], "personality": state_agents[idx]["personality"], "idea": state_agents[idx]["idea"]}
            for idx in group
        ]
        groups.append({"group": gi, "members": members})
    return {"groups": groups}


@app.get("/groups/{group_id}/conversation")
def groups_conversation(group_id: int):
    if not group_assignments:
        _ensure_groups(1)
    if group_id < 0 or group_id >= len(group_assignments):
        return {"group": group_id, "messages": []}
    with SessionLocal() as session:
        conv_id = group_conversation_ids.get(group_id)
        if conv_id is None:
            # fall back to in-memory
            return {"group": group_id, "messages": list(group_histories[group_id])}
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
                {"id": m.id, "turn": m.turn, "speaker": m.speaker, "text": m.text, "created_at": m.created_at.isoformat()}
                for m in msgs
            ],
        }


@app.post("/groups/{group_id}/simulate/turn")
def groups_simulate_one_turn(group_id: int):
    if not group_assignments:
        _ensure_groups(1)
    if group_id < 0 or group_id >= len(group_assignments):
        return {"ok": False, "error": "invalid group"}

    with state_lock:
        indices = group_assignments[group_id]
        group_agents = [state_agents[i] for i in indices]
        seed = list(group_histories[group_id])
        result = simulate_hackathon(group_agents, turns=1, callback=None, seed_history=seed)
        if not result.get("history"):
            return {"ok": False, "error": "no history returned"}
        last_entry = result["history"][-1]
        group_histories[group_id].append(last_entry)

    # Persist to DB under a unique conversation per group
    with SessionLocal() as session:
        _persist_agents_if_needed(session)
        conv_id = group_conversation_ids.get(group_id)
        if conv_id is None:
            conv = Conversation()
            session.add(conv)
            session.commit()
            session.refresh(conv)
            conv_id = conv.id
            group_conversation_ids[group_id] = conv_id
        msg = Message(
            conversation_id=conv_id,
            turn=int(last_entry.get("turn")),
            speaker=last_entry.get("speaker", ""),
            text=last_entry.get("text", ""),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
    return {"ok": True, "message": last_entry}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)


