from pathlib import Path
from unittest.mock import MagicMock
import pytest
from warden.agents.review import ReviewAgent

@pytest.fixture
def mock_runner():
    return MagicMock()

@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    (understanding / "design-decisions.md").write_text("# Design Decisions\n\n## Use async for all I/O\n- Rationale: performance\n")
    (understanding / "patterns.md").write_text("# Patterns\n\n## All handlers return Result types\n")
    return tmp_path / ".warden"

def test_review_prompt_includes_understanding_context(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    agent.review(commit_hash="abc123", diff="+ sync_call()", changed_files=["api/handler.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "async for all I/O" in prompt
    assert "Result types" in prompt

def test_review_prompt_focuses_on_correctness(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    agent.review("abc123", "diff", ["file.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "correctness" in prompt.lower()
    assert "consistency" in prompt.lower() or "consistent" in prompt.lower()
    assert "design" in prompt.lower()

def test_review_prompt_includes_diff(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    agent.review("abc123", "- old_line\n+ new_line", ["file.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "old_line" in prompt
    assert "new_line" in prompt

def test_review_prompt_tells_agent_to_create_pr(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."
    agent.review("abc123", "diff", ["file.py"], branch_prefix="warden/")
    prompt = mock_runner.run.call_args[0][0]
    assert "draft" in prompt.lower() or "PR" in prompt or "pull request" in prompt.lower()
    assert "warden/" in prompt

def test_review_returns_agent_output(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "Found 1 issue: off-by-one in loop"
    result = agent.review("abc123", "diff", ["file.py"])
    assert "off-by-one" in result


def test_review_pr_includes_pr_number(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "PR looks good."
    agent.review_pr(1234)
    prompt = mock_runner.run.call_args[0][0]
    assert "1234" in prompt
    assert "gh pr view" in prompt or "gh pr diff" in prompt


def test_review_pr_includes_understanding_context(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "PR looks good."
    agent.review_pr(42)
    prompt = mock_runner.run.call_args[0][0]
    assert "async for all I/O" in prompt
    assert "Result types" in prompt


def test_review_pr_asks_to_reference_decisions(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "PR looks good."
    agent.review_pr(42)
    prompt = mock_runner.run.call_args[0][0]
    assert "design decision" in prompt.lower() or "design coherence" in prompt.lower()
    assert "correctness" in prompt.lower()
    assert "consistency" in prompt.lower() or "consistent" in prompt.lower()


def test_review_pr_returns_agent_output(mock_runner, warden_dir):
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "This PR contradicts decision #3 about config format."
    result = agent.review_pr(99)
    assert "contradicts" in result
