from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)


@event.listens_for(engine, "connect")
def _set_search_path(dbapi_connection, _connection_record):
    with dbapi_connection.cursor() as cur:
        cur.execute(f'SET search_path TO "{settings.db_schema}", public')


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
