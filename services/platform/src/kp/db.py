"""Engine, schema, and the complaint_count trigger."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from kp.config import get_settings
from kp.models import Base

_engine = None
_Session: sessionmaker | None = None

COUNT_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION kp_verify_issue_complaint_count() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  iid text;
  expected integer;
  actual integer;
BEGIN
  IF TG_TABLE_NAME = 'issues' THEN
    iid := COALESCE(NEW.id, OLD.id);
  ELSE
    iid := COALESCE(NEW.issue_id, OLD.issue_id);
  END IF;

  SELECT complaint_count INTO expected FROM issues WHERE id = iid;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  SELECT COUNT(*) INTO actual FROM issue_complaints WHERE issue_id = iid;
  IF expected IS DISTINCT FROM actual THEN
    RAISE EXCEPTION 'complaint_count % does not match join count % for issue %', expected, actual, iid;
  END IF;
  RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS issues_complaint_count_check ON issues;
CREATE CONSTRAINT TRIGGER issues_complaint_count_check
AFTER INSERT OR UPDATE OR DELETE ON issues
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kp_verify_issue_complaint_count();

DROP TRIGGER IF EXISTS issue_complaints_count_check ON issue_complaints;
CREATE CONSTRAINT TRIGGER issue_complaints_count_check
AFTER INSERT OR UPDATE OR DELETE ON issue_complaints
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION kp_verify_issue_complaint_count();
"""


def get_engine():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def SessionLocal() -> Session:
    get_engine()
    assert _Session is not None
    return _Session()


def reset_engine() -> None:
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


def ensure_schema() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS skill_ids JSONB NOT NULL DEFAULT '[]'::jsonb"))
        conn.execute(text("ALTER TABLE turns ADD COLUMN IF NOT EXISTS report JSONB"))
        conn.execute(text(COUNT_TRIGGER_SQL))


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
