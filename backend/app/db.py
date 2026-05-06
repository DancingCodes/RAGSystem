from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _db_url() -> str:
  url = os.getenv("DATABASE_URL", "").strip()
  if url:
    return url
  base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
  data_dir = os.path.join(base_dir, "data")
  os.makedirs(data_dir, exist_ok=True)
  return f"sqlite:///{os.path.join(data_dir, 'app.db')}"


engine = create_engine(_db_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
  bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
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
