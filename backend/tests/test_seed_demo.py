"""v1.4 first-boot demo seeding.

All offline: the job store, dispatcher, and graph client are monkeypatched, and
the bundled demo repo is parsed with the real (local) tree-sitter parser.
"""
import pytest

from api import seed_demo


class _FakeJobs:
    def __init__(self, recent: list | None = None):
        self.recent = recent or []
        self.created: list[dict] = []

    def list_recent(self, limit: int = 20):
        return self.recent[:limit]

    def create(self, repo_url=None, repo_path=None, user_id=None):
        self.created.append({"repo_url": repo_url, "repo_path": repo_path})
        return "seed-job-1"


class _AliveGraph:
    def is_alive(self):
        return True


class _DeadGraph:
    def is_alive(self):
        return False


@pytest.fixture
def dispatched(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr("api.tasks.dispatch_ingest",
                        lambda job_id, url, path: calls.append((job_id, url, path)))
    return calls


def test_disabled_by_default(monkeypatch, dispatched):
    monkeypatch.delenv("SEED_DEMO_REPO", raising=False)
    assert seed_demo.maybe_seed_demo_repo() is None
    assert dispatched == []


def test_seeds_on_first_boot(monkeypatch, dispatched):
    monkeypatch.setenv("SEED_DEMO_REPO", "true")
    fake = _FakeJobs()
    monkeypatch.setattr("api.jobs.jobs", fake)
    monkeypatch.setattr("graph_db.ArcadeDBClient", _AliveGraph)
    job_id = seed_demo.maybe_seed_demo_repo()
    assert job_id == "seed-job-1"
    assert fake.created[0]["repo_path"] == str(seed_demo.DEMO_REPO_DIR)
    assert dispatched == [("seed-job-1", None, str(seed_demo.DEMO_REPO_DIR))]


def test_skips_when_jobs_already_exist(monkeypatch, dispatched):
    monkeypatch.setenv("SEED_DEMO_REPO", "true")
    fake = _FakeJobs(recent=[{"job_id": "old"}])
    monkeypatch.setattr("api.jobs.jobs", fake)
    monkeypatch.setattr("graph_db.ArcadeDBClient", _AliveGraph)
    assert seed_demo.maybe_seed_demo_repo() is None
    assert fake.created == [] and dispatched == []


def test_skips_when_graph_down(monkeypatch, dispatched):
    monkeypatch.setenv("SEED_DEMO_REPO", "true")
    fake = _FakeJobs()
    monkeypatch.setattr("api.jobs.jobs", fake)
    monkeypatch.setattr("graph_db.ArcadeDBClient", _DeadGraph)
    assert seed_demo.maybe_seed_demo_repo() is None
    assert fake.created == [] and dispatched == []


def test_never_raises(monkeypatch, dispatched):
    monkeypatch.setenv("SEED_DEMO_REPO", "yes")

    class _Boom:
        def list_recent(self, limit=20):
            raise RuntimeError("db exploded")

    monkeypatch.setattr("api.jobs.jobs", _Boom())
    assert seed_demo.maybe_seed_demo_repo() is None  # swallowed, logged


def test_demo_repo_exists_and_parses():
    """The bundled repo must ship with the backend and yield a rich graph:
    classes, inheritance, and cross-file calls for the analysis pages."""
    assert seed_demo.DEMO_REPO_DIR.is_dir()
    from ast_parser import parse_repository

    entities, relationships = parse_repository(str(seed_demo.DEMO_REPO_DIR))
    names = {e.name for e in entities}
    assert {"Catalog", "LoanService", "Book", "process_return"} <= names
    rel_types = {r.type for r in relationships}
    assert "contains" in {t.lower() for t in rel_types}
    assert any(t.lower() == "inherits_from" for t in rel_types)
