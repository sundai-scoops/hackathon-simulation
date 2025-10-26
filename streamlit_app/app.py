import streamlit as st
import sys
import os
import random

# Add the parent directory to the Python path to import main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import agents as base_agents, simulate_hackathon

# State init
if "agents" not in st.session_state:
    # copy and add simple positions
    GRID_SIZE = 10
    st.session_state.agents = []
    for a in base_agents:
        st.session_state.agents.append({
            **a,
            "x": random.randint(0, GRID_SIZE - 1),
            "y": random.randint(0, GRID_SIZE - 1),
            "memory": a.get("memory", []),
        })
if "global_history" not in st.session_state:
    st.session_state.global_history = []  # setup entries etc.
if "group_assignments" not in st.session_state:
    st.session_state.group_assignments = []  # list[list[int]]
if "group_histories" not in st.session_state:
    st.session_state.group_histories = []  # list[list[history entries]]
if "group_last_turn" not in st.session_state:
    st.session_state.group_last_turn = []  # list[int]


def ensure_setup():
    if not all(a.get("setup_done", False) for a in st.session_state.agents):
        result = simulate_hackathon(st.session_state.agents, turns=0, callback=None)
        st.session_state.global_history = result.get("history", [])


def regroup_agents(num_groups: int):
    idxs = list(range(len(st.session_state.agents)))
    random.shuffle(idxs)
    groups = [[] for _ in range(max(1, num_groups))]
    for i, idx in enumerate(idxs):
        groups[i % len(groups)].append(idx)
    st.session_state.group_assignments = groups
    st.session_state.group_histories = [[] for _ in groups]
    st.session_state.group_last_turn = [0 for _ in groups]


# Function to render agent states and conversations
def render_agents(agents, conversations):
    for agent in agents:
        st.subheader(f"{agent['name']}")
        st.write(f"Position: ({agent['x']}, {agent['y']})")
        st.write(f"Personality: {agent['personality']}")
        st.write(f"Idea: {agent['idea']}")
        st.write("Recent Memory:")
        for m in agent.get("memory", [])[-5:]:
            st.write(f"- {m['turn']}: {m['speaker']}: {m['text']}")


# Streamlit app
st.title("Hackathon Simulation: Agent Conversations")
st.write("This visualization shows agents grouped into conversations with shared context.")

controls_placeholder = st.empty()
groups_placeholder = st.empty()

# Simulation loop
with controls_placeholder.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        num_groups = st.number_input("Num groups", min_value=1, max_value=len(st.session_state.agents), value=max(1, min(3, len(st.session_state.agents)//5 or 1)))
    with c2:
        turns_per_group = st.number_input("Turns per group", min_value=1, max_value=50, value=5)
    with c3:
        if st.button("Regroup") or not st.session_state.group_assignments:
            regroup_agents(int(num_groups))

    if st.button("Run Simulation"):
        ensure_setup()
        for gi, group in enumerate(st.session_state.group_assignments):
            group_agents = [st.session_state.agents[i] for i in group]
            seed = st.session_state.group_histories[gi] if gi < len(st.session_state.group_histories) else []
            result = simulate_hackathon(group_agents, turns=int(turns_per_group), callback=None, seed_history=seed)
            st.session_state.group_histories[gi] = result.get("history", seed)

with groups_placeholder.container():
    for gi, group in enumerate(st.session_state.group_assignments):
        st.write(f"## Group {gi + 1}")
        group_agents = [st.session_state.agents[i] for i in group]
        render_agents(group_agents, st.session_state.group_histories[gi] if gi < len(st.session_state.group_histories) else [])
        st.write("### Group Conversation Log")
        history = st.session_state.group_histories[gi] if gi < len(st.session_state.group_histories) else []
        for item in history[-50:]:
            st.write(f"Turn {item.get('turn','-')}: {item['speaker']} → {item['text']}")
