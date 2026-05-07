import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


def _db_url() -> str:
    dsn = os.getenv("DB_DSN", "").strip()
    if dsn:
        if "://" not in dsn:
            raise ValueError("DB_DSN格式错误")
        return dsn
    raise ValueError("DB_DSN不能为空")


db_url = _db_url()
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
