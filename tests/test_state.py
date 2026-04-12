from datetime import datetime, timezone
from pathlib import Path
import pytest
from warden.state import StateManager

@pytest.fixture
def state_mgr(tmp_path):
    db_path = tmp_path / "state.db"
    mgr = StateManager(db_path)
    mgr.initialize()
    return mgr

def test_initialize_creates_db(tmp_path):
    db_path = tmp_path / "state.db"
    mgr = StateManager(db_path)
    mgr.initialize()
    assert db_path.exists()

def test_record_and_get_commit(state_mgr):
    state_mgr.record_commit(hash="abc123", timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc), files_changed=["api/orders.py", "api/users.py"])
    commit = state_mgr.get_commit("abc123")
    assert commit is not None
    assert commit["hash"] == "abc123"
    assert commit["files_changed"] == ["api/orders.py", "api/users.py"]
    assert commit["understand_done"] is False
    assert commit["review_done"] is False

def test_mark_commit_understood(state_mgr):
    state_mgr.record_commit("abc123", datetime.now(timezone.utc), ["file.py"])
    state_mgr.mark_commit_understood("abc123")
    commit = state_mgr.get_commit("abc123")
    assert commit["understand_done"] is True

def test_mark_commit_reviewed(state_mgr):
    state_mgr.record_commit("abc123", datetime.now(timezone.utc), ["file.py"])
    state_mgr.mark_commit_reviewed("abc123")
    commit = state_mgr.get_commit("abc123")
    assert commit["review_done"] is True

def test_get_last_processed_commit(state_mgr):
    assert state_mgr.get_last_processed_hash() is None
    state_mgr.record_commit("aaa", datetime(2024, 1, 1, tzinfo=timezone.utc), [])
    state_mgr.record_commit("bbb", datetime(2024, 1, 2, tzinfo=timezone.utc), [])
    assert state_mgr.get_last_processed_hash() == "bbb"

def test_record_review(state_mgr):
    state_mgr.record_review(commit_hash="abc123", issue_type="correctness", description="Off-by-one in loop boundary", pr_url="https://github.com/user/repo/pull/1")
    reviews = state_mgr.get_reviews(status="pending")
    assert len(reviews) == 1
    assert reviews[0]["issue_type"] == "correctness"
    assert reviews[0]["status"] == "pending"

def test_update_review_status(state_mgr):
    state_mgr.record_review("abc123", "consistency", "Inconsistent naming", None)
    reviews = state_mgr.get_reviews(status="pending")
    state_mgr.update_review_status(reviews[0]["id"], "accepted")
    updated = state_mgr.get_reviews(status="accepted")
    assert len(updated) == 1

def test_get_stats(state_mgr):
    state_mgr.record_commit("aaa", datetime.now(timezone.utc), ["a.py"])
    state_mgr.record_commit("bbb", datetime.now(timezone.utc), ["b.py"])
    state_mgr.mark_commit_understood("aaa")
    state_mgr.record_review("aaa", "correctness", "Bug", None)
    stats = state_mgr.get_stats()
    assert stats["commits_total"] == 2
    assert stats["commits_understood"] == 1
    assert stats["reviews_pending"] == 1
