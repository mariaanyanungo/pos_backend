import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

load_dotenv()


def get_database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise ValueError("DATABASE_URL is missing. Add it to your .env file.")
    return url


def build_engine(url: str) -> Engine:
    kwargs: dict = {"echo": False}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
    return create_engine(url, **kwargs)


DATABASE_URL = get_database_url()

engine = build_engine(DATABASE_URL)


SessionLocal = sessionmaker(autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()