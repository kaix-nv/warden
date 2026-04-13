import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from warden.config import WardenConfig
from warden.orchestrator import Orchestrator

@pytest.fixture
def setup(tmp_repo):
    """Set up orchestrator with a real git repo and mocked agent runner."""
    repo_path, repo = tmp_repo
    warden_dir = repo_path / ".warden"
    config = WardenConfig()
    with patch("warden.orchestrator.AgentRunner") as MockRunner:
        mock_runner = MagicMock()
        MockRunner.return_value = mock_runner
        mock_runner.run.return_value = "Agent completed."
        orchestrator = Orchestrator(repo_path, config)
        yield orchestrator, repo_path, repo, mock_runner

def test_init_creates_warden_directory(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    warden_dir = repo_path / ".warden"
    assert warden_dir.exists()
    assert (warden_dir / "understanding").is_dir()
    assert (warden_dir / "improvements" / "pending").is_dir()
    assert (warden_dir / "improvements" / "history").is_dir()
    assert (warden_dir / "config.yml").exists()

def test_init_creates_default_config(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    config_path = repo_path / ".warden" / "config.yml"
    content = config_path.read_text()
    assert "review:" in content
    assert "understanding:" in content

def test_init_installs_hook(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    assert "warden analyze" in hook_path.read_text()

def test_init_adds_state_db_to_gitignore(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    gitignore = repo_path / ".gitignore"
    assert gitignore.exists()
    assert ".warden/state.db" in gitignore.read_text()

def test_init_runs_bootstrap(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    assert mock_runner.run.called
    prompt = mock_runner.run.call_args[0][0]
    assert "senior engineer" in prompt.lower()

def _remove_hook(repo_path):
    """Remove post-commit hook so it doesn't race with the mocked orchestrator."""
    hook = repo_path / ".git" / "hooks" / "post-commit"
    if hook.exists():
        hook.unlink()

def test_analyze_processes_new_commits(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    _remove_hook(repo_path)
    mock_runner.run.reset_mock()
    (repo_path / "new_file.py").write_text("print('hi')\n")
    repo.index.add(["new_file.py"])
    repo.index.commit("Add new file")
    orchestrator.analyze()
    assert mock_runner.run.called

def test_analyze_skips_already_processed(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    _remove_hook(repo_path)
    mock_runner.run.reset_mock()
    (repo_path / "new_file.py").write_text("print('hi')\n")
    repo.index.add(["new_file.py"])
    repo.index.commit("Add new file")
    orchestrator.analyze()
    mock_runner.run.reset_mock()
    orchestrator.analyze()
    assert mock_runner.run.call_count == 0

def test_ask_returns_answer(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    mock_runner.run.return_value = "SQLite was chosen for simplicity."
    answer = orchestrator.ask("Why SQLite?")
    assert "SQLite" in answer

def test_status_returns_stats(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    status = orchestrator.status()
    assert "commits_total" in status
    assert isinstance(status["commits_total"], int)

def test_init_builds_graph(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    (repo_path / "app.py").write_text("import os\n\ndef main(): pass\n")
    repo.index.add(["app.py"])
    repo.index.commit("Add app")
    orchestrator.init()
    nodes = orchestrator.graph_manager.get_all_nodes()
    assert len(nodes) > 0

def test_analyze_updates_graph(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    _remove_hook(repo_path)
    mock_runner.run.reset_mock()
    (repo_path / "new_module.py").write_text("class Foo:\n    pass\n")
    repo.index.add(["new_module.py"])
    repo.index.commit("Add new module")
    orchestrator.analyze()
    nodes = orchestrator.graph_manager.get_all_nodes()
    names = {n["qualified_name"] for n in nodes}
    assert "new_module.Foo" in names
