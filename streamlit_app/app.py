<hackathon-simulation/streamlit_app/app.py>
import streamlit as st
import random
import time

# Constants
NUM_AGENTS = 16
GRID_SIZE = 10

# Initialize agent positions
agents = [{"name": f"Agent {i+1}", "x": random.randint(0, GRID_SIZE-1), "y": random.randint(0, GRID_SIZE-1)} for i in range(NUM_AGENTS)]

# Function to move agents randomly
def move_agents(agents):
    for agent in agents:
        agent["x"] = max(0, min(GRID_SIZE-1, agent["x"] + random.choice([-1, 0, 1])))
        agent["y"] = max(0, min(GRID_SIZE-1, agent["y"] + random.choice([-1, 0, 1])))

# Streamlit app
st.title("Hackathon Simulation: Agent Movement")
st.write("This visualization shows 16 agents moving around a grid.")

# Create a placeholder for the grid
grid_placeholder = st.empty()

# Simulation loop
if st.button("Start Simulation"):
    for _ in range(50):  # Number of simulation steps
        move_agents(agents)

        # Render the grid
        grid = [[" " for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        for agent in agents:
            grid[agent["y"]][agent["x"]] = agent["name"][6:]  # Use agent number for display

        grid_display = "\n".join([" ".join(row) for row in grid])
        grid_placeholder.text(f"```\n{grid_display}\n```")

        time.sleep(0.5)  # Pause for half a second between steps
