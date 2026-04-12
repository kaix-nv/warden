from pathlib import Path
from unittest.mock import MagicMock
import pytest
from warden.agents.ask import AskAgent

@pytest.fixture
def mock_runner():
    return MagicMock()

@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    (understanding / "design-decisions.md").write_text("# Design Decisions\n\n## Use SQLite over Redis\n- Source: PR #142\n- Rationale: ops overhead not justified\n")
    return tmp_path / ".warden"

def test_ask_includes_question(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "Because of ops overhead."
    agent.ask("Why do we use SQLite?")
    prompt = mock_runner.run.call_args[0][0]
    assert "Why do we use SQLite?" in prompt

def test_ask_includes_understanding_docs(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"
    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "SQLite over Redis" in prompt
    assert "PR #142" in prompt

def test_ask_instructs_citing_sources(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"
    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "cite" in prompt.lower() or "Cite" in prompt

def test_ask_instructs_honesty_when_unknown(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"
    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "don't know" in prompt.lower() or "do not know" in prompt.lower() or "don't guess" in prompt.lower()

def test_ask_returns_agent_output(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "SQLite was chosen over Redis because ops overhead wasn't justified. See PR #142."
    result = agent.ask("Why SQLite?")
    assert "PR #142" in result
