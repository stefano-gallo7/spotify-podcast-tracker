from app.db import engine, SessionLocal, Base
import app.db_models  # noqa: F401 — import so models register with Base
from app.db_models import AppState


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if session.query(AppState).first() is None:
            session.add(AppState(id=1))
            session.commit()
    print("Database tables created at data/podcasts.db")


if __name__ == "__main__":
    main()
