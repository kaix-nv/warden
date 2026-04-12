from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from warden.cli import app

runner = CliRunner()

@pytest.fixture
def mock_orchestrator():
    with patch("warden.cli.Orchestrator") as MockOrch:
        mock = MagicMock()
        MockOrch.return_value = mock
        yield mock

def test_init_command(mock_orchestrator):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    mock_orchestrator.init.assert_called_once()
    assert "initialized" in result.stdout.lower() or "Warden" in result.stdout

def test_analyze_command(mock_orchestrator):
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    mock_orchestrator.analyze.assert_called_once_with(commit_hash=None)

def test_analyze_with_commit(mock_orchestrator):
    result = runner.invoke(app, ["analyze", "--commit", "abc123"])
    assert result.exit_code == 0
    mock_orchestrator.analyze.assert_called_once_with(commit_hash="abc123")

def test_ask_command(mock_orchestrator):
    mock_orchestrator.ask.return_value = "Because of performance."
    result = runner.invoke(app, ["ask", "Why async?"])
    assert result.exit_code == 0
    mock_orchestrator.ask.assert_called_once_with("Why async?")
    assert "performance" in result.stdout.lower()

def test_status_command(mock_orchestrator):
    mock_orchestrator.status.return_value = {
        "commits_total": 42, "commits_understood": 40,
        "reviews_pending": 2, "reviews_accepted": 5, "reviews_declined": 1,
        "understanding_docs": {"architecture.md": 1024, "design-decisions.md": 2048},
    }
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "42" in result.stdout

def test_review_pr_command(mock_orchestrator):
    mock_orchestrator.review_pr.return_value = "PR looks good. Aligns with design decision #3."
    result = runner.invoke(app, ["review-pr", "1234"])
    assert result.exit_code == 0
    mock_orchestrator.review_pr.assert_called_once_with(1234)
    assert "design decision" in result.stdout.lower()


def test_config_command():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0

def test_reset_command(mock_orchestrator, tmp_path):
    result = runner.invoke(app, ["reset", "--all"])
    assert result.exit_code == 0
