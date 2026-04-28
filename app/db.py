from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Database file lives in the data/ directory
DATABASE_URL = "sqlite:///data/podcasts.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_session():
    """Yield a database session, ensuring it gets closed after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()