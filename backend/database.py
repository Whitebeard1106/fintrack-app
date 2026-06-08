import os

from sqlmodel import create_engine, Session, SQLModel

_url = os.getenv("DATABASE_URL", "sqlite:///./fintrack.db")

if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)

if _url.startswith("sqlite"):
    engine = create_engine(_url, echo=False, connect_args={"check_same_thread": False})
else:
    engine = create_engine(_url, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
