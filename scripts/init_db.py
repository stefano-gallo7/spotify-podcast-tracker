from app.db import engine, Base
import app.db_models  # noqa: F401 — import so models register with Base

def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables created at data/podcasts.db")

if __name__ == "__main__":
    main()