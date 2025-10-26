import os
from sqlalchemy.orm import sessionmaker

from db import get_engine, Base, AgentModel
from main import agents as base_agents


def main():
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///hackathon.db"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False, future=True)
    with SessionLocal() as session:
        existing = {a.name for a in session.query(AgentModel).all()}
        to_add = []
        for a in base_agents:
            if a["name"] not in existing:
                to_add.append(AgentModel(name=a["name"], personality=a["personality"], idea=a["idea"]))
        if to_add:
            session.add_all(to_add)
            session.commit()
    print(f"Database initialized at {database_url} and agents seeded.")


if __name__ == "__main__":
    main()


