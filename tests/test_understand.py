from pathlib import Path
from unittest.mock import MagicMock
import pytest
from warden.agents.understand import UnderstandAgent

@pytest.fixture
def mock_runner():
    return MagicMock()

@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    return tmp_path / ".warden"

def test_bootstrap_prompt_includes_voice(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "senior engineer briefing a new hire" in prompt

def test_bootstrap_prompt_asks_for_four_docs(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "architecture.md" in prompt
    assert "relationships.md" in prompt
    assert "design-decisions.md" in prompt
    assert "patterns.md" in prompt

def test_bootstrap_reads_full_history(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "ALL" in prompt or "all" in prompt.lower()
    assert "commit" in prompt.lower()
    assert "merged PR" in prompt.lower() or "merged pr" in prompt.lower()

def test_bootstrap_with_pr_limit(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap(pr_count=50)
    prompt = mock_runner.run.call_args[0][0]
    assert "50" in prompt

def test_bootstrap_with_commit_limit(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap(commit_count=100)
    prompt = mock_runner.run.call_args[0][0]
    assert "100" in prompt

def test_incremental_prompt_includes_diff(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    commit_info = {"hash": "abc123", "message": "Optimize query", "diff": "- old_code\n+ new_code"}
    agent.incremental(commit_info)
    prompt = mock_runner.run.call_args[0][0]
    assert "abc123" in prompt
    assert "Optimize query" in prompt

def test_incremental_prompt_includes_existing_docs(mock_runner, warden_dir):
    (warden_dir / "understanding" / "architecture.md").write_text("# Architecture\nUses microservices.\n")
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.incremental({"hash": "abc123", "message": "test", "diff": "diff"})
    prompt = mock_runner.run.call_args[0][0]
    assert "Uses microservices" in prompt

def test_incremental_tells_agent_to_append(mock_runner, warden_dir):
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.incremental({"hash": "abc123", "message": "test", "diff": "diff"})
    prompt = mock_runner.run.call_args[0][0]
    assert "append" in prompt.lower() or "don't rewrite" in prompt.lower() or "do not rewrite" in prompt.lower()


def test_bootstrap_captures_relationships(mock_runner, warden_dir):
    """Bootstrap prompt asks for component relationships and extension points."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "extension point" in prompt.lower()
    assert "dependency" in prompt.lower() or "dependencies" in prompt.lower()


def test_bootstrap_captures_tech_debt_and_lessons(mock_runner, warden_dir):
    """Bootstrap prompt asks for tech debt, mistakes, and lessons learned."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "tech debt" in prompt.lower()
    assert "mistake" in prompt.lower() or "lesson" in prompt.lower()


def test_bootstrap_captures_evolution_philosophy(mock_runner, warden_dir):
    """Bootstrap prompt explains the relational and evolutionary assumptions."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "relational" in prompt.lower() or "relationship" in prompt.lower()
    assert "evolution" in prompt.lower() or "evolutionary" in prompt.lower()
