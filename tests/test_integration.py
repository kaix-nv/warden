"""
End-to-end integration test using a real git repo
and mocked Claude Code CLI calls.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from warden.orchestrator import Orchestrator
from warden.config import WardenConfig


def _remove_hook(repo_path):
    """Remove post-commit hook so it doesn't race with mocked subprocess."""
    hook = repo_path / ".git" / "hooks" / "post-commit"
    if hook.exists():
        hook.unlink()


@pytest.fixture
def project(tmp_repo):
    """Create a small project with multiple commits."""
    repo_path, repo = tmp_repo

    (repo_path / "app.py").write_text(
        "def get_user(user_id: int):\n"
        "    return db.query(User).filter(User.id == user_id).first()\n"
    )
    repo.index.add(["app.py"])
    repo.index.commit("feat: add user lookup endpoint")

    (repo_path / "models.py").write_text(
        "class User:\n"
        "    id: int\n"
        "    name: str\n"
    )
    repo.index.add(["models.py"])
    repo.index.commit("feat: add User model")

    return repo_path, repo


def test_full_init_and_analyze_cycle(project):
    """Test the complete lifecycle: init -> analyze -> ask -> status."""
    repo_path, repo = project

    with patch("warden.agents.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(
            stdout="Agent completed successfully.",
            stderr="",
            returncode=0,
        )

        config = WardenConfig()
        orchestrator = Orchestrator(repo_path, config)

        # 1. Init
        orchestrator.init()
        _remove_hook(repo_path)

        # Verify directory structure
        warden_dir = repo_path / ".warden"
        assert (warden_dir / "understanding").is_dir()
        assert (warden_dir / "config.yml").exists()
        assert (warden_dir / "state.db").exists()
        assert ".warden/state.db" in (repo_path / ".gitignore").read_text()

        # Bootstrap should have been called
        assert mock_subprocess.called
        first_call = mock_subprocess.call_args_list[0][0][0]
        assert "claude" in str(first_call)

        # 2. Status after init
        status = orchestrator.status()
        assert status["commits_total"] == 3  # Initial + 2 feature commits
        assert status["commits_understood"] == 3

        # 3. Make a new commit and analyze
        mock_subprocess.reset_mock()
        (repo_path / "utils.py").write_text("def helper(): pass\n")
        repo.index.add(["utils.py"])
        repo.index.commit("feat: add utility helper")

        orchestrator.analyze()

        # Should have called claude for understand + review
        assert mock_subprocess.called

        # 4. Status after analyze
        status = orchestrator.status()
        assert status["commits_total"] == 4

        # 5. Ask
        mock_subprocess.reset_mock()
        mock_subprocess.return_value = MagicMock(
            stdout="The User model was added in commit xyz.",
            stderr="",
            returncode=0,
        )
        answer = orchestrator.ask("What is the User model?")
        assert "User model" in answer


def test_analyze_is_idempotent(project):
    """Running analyze twice doesn't reprocess commits."""
    repo_path, repo = project

    with patch("warden.agents.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(
            stdout="Done.", stderr="", returncode=0,
        )

        config = WardenConfig()
        orchestrator = Orchestrator(repo_path, config)
        orchestrator.init()
        _remove_hook(repo_path)

        # Add a commit
        (repo_path / "new.py").write_text("x = 1\n")
        repo.index.add(["new.py"])
        repo.index.commit("add new")

        # First analyze
        mock_subprocess.reset_mock()
        orchestrator.analyze()
        first_count = mock_subprocess.call_count

        # Second analyze — nothing new
        mock_subprocess.reset_mock()
        orchestrator.analyze()
        assert mock_subprocess.call_count == 0
