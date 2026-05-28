from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.db.config import settings


def _get_engine():
    kwargs = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        **kwargs,
    )


engine = _get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
