Hackathon Simulation
====================

Overview
--------
Simulate a small team of agents discussing their ideas. You can:
- Run simulations in the console via `main.py`
- Visualize groups in Streamlit via `streamlit_app/app.py`
- Serve an API and a simple web UI (`index.html`) via `server.py`
- Persist agents and conversation turns to a database (SQLite by default, MySQL optional)

Requirements
------------
- Python 3.11+
- A Google Generative AI API key if you want live LLM responses: set `GOOGLE_API_KEY`

Install dependencies
--------------------
This project uses `uv` for dependency management.

```bash
cd /Users/nathan.alam/Desktop/hackathon-simulation
uv sync
```

Environment variables
---------------------
- `GOOGLE_API_KEY`: your API key for Gemini.
- `DATABASE_URL` (optional): set to use a different DB, e.g. MySQL via PyMySQL.
  - SQLite default: `sqlite:///hackathon.db`
  - MySQL example: `mysql+pymysql://user:password@localhost:3306/hackathon`

Initialize the database
-----------------------
Creates tables and seeds initial agents.

```bash
cd /Users/nathan.alam/Desktop/hackathon-simulation
python setup.py
```

Run the console simulation
--------------------------
```bash
cd /Users/nathan.alam/Desktop/hackathon-simulation
python main.py
```

Run the Streamlit app (optional)
--------------------------------
```bash
cd /Users/nathan.alam/Desktop/hackathon-simulation
streamlit run streamlit_app/app.py
```

Serve API and Web UI
--------------------
Starts a FastAPI server that serves:
- `GET /` → `index.html`
- `GET /agents` → list of agents
- `GET /conversation` → current conversation messages
- `POST /simulate/turn` → advances the simulation by one turn and persists it
- `POST /reset` → resets the in-memory state

Grouped conversations:
- `GET /groups` → list groups and members
- `POST /groups/regroup` body: `{ "num_groups": number }` → reshuffle agents into N groups
- `GET /groups/{group_id}/conversation` → messages for that group
- `POST /groups/{group_id}/simulate/turn` → advance only that group's conversation one turn

```bash
cd /Users/nathan.alam/Desktop/hackathon-simulation
python server.py
# or
uvicorn server:app --reload --port 8000
```

Open your browser at `http://localhost:8000` to use `index.html`.

Using MySQL instead of SQLite (optional)
----------------------------------------
1. Start a MySQL server and create a database (e.g. `hackathon`).
2. Set `DATABASE_URL`:
   ```bash
   export DATABASE_URL='mysql+pymysql://user:password@localhost:3306/hackathon'
   ```
3. Run `python setup.py` once to create tables and seed agents.
4. Start the server: `python server.py`.

Project structure
-----------------
- `main.py`: core simulation logic and agent definitions
- `db.py`: SQLAlchemy models and engine helper
- `setup.py`: database initialization and agent seeding
- `server.py`: FastAPI app with simulation endpoints and static page
- `index.html`: simple control panel and log viewer
- `streamlit_app/app.py`: Streamlit UI for grouped conversations


