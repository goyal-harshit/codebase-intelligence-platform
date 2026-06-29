"""Relational store smoke tests (offline, SQLite temp file)."""
import pytest
from sqlalchemy import inspect, select


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    import db as dbpkg

    dbpkg.reset_engine_cache()
    dbpkg.init_db()
    yield dbpkg
    dbpkg.reset_engine_cache()


def test_init_db_creates_all_tables(db):
    tables = set(inspect(db.get_engine()).get_table_names())
    assert {"users", "api_keys", "jobs", "repos", "audit_log"} <= tables


def test_user_and_api_key_roundtrip(db):
    Session = db.get_sessionmaker()
    with Session() as s:
        user = db.User(email="a@b.com", hashed_password="x", full_name="A")
        s.add(user)
        s.flush()
        s.add(db.ApiKey(user_id=user.id, key_hash="hash1", name="ci"))
        s.commit()
        uid = user.id

    with Session() as s:
        got = s.scalar(select(db.User).where(db.User.email == "a@b.com"))
        assert got is not None and got.id == uid
        assert len(got.api_keys) == 1 and got.api_keys[0].key_hash == "hash1"


def test_job_json_fields_persist(db):
    Session = db.get_sessionmaker()
    with Session() as s:
        s.add(db.Job(id="job1", status="complete_with_warnings",
                     warnings=["embedding: boom"], result={"files": 3}))
        s.commit()
    with Session() as s:
        job = s.get(db.Job, "job1")
        assert job.status == "complete_with_warnings"
        assert job.warnings == ["embedding: boom"]
        assert job.result == {"files": 3}


def test_email_unique_constraint(db):
    from sqlalchemy.exc import IntegrityError

    Session = db.get_sessionmaker()
    with Session() as s:
        s.add(db.User(email="dup@b.com", hashed_password="x"))
        s.commit()
    with Session() as s:
        s.add(db.User(email="dup@b.com", hashed_password="y"))
        with pytest.raises(IntegrityError):
            s.commit()
