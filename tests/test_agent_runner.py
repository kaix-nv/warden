from unittest.mock import patch, MagicMock
import subprocess
import pytest
from warden.agents.runner import AgentRunner, AgentError

def test_run_returns_stdout():
    runner = AgentRunner()
    with patch("warden.agents.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Claude's response here", stderr="", returncode=0)
        result = runner.run("Analyze this code")
        assert result == "Claude's response here"
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert "claude" in args[0][0]
        assert "-p" in args[0][0]

def test_run_with_working_directory(tmp_path):
    runner = AgentRunner(cwd=tmp_path)
    with patch("warden.agents.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test")
        assert mock_run.call_args.kwargs["cwd"] == tmp_path

def test_run_raises_on_failure():
    runner = AgentRunner()
    with patch("warden.agents.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="Error: something went wrong", returncode=1)
        with pytest.raises(AgentError, match="something went wrong"):
            runner.run("bad prompt")

def test_run_with_max_turns():
    runner = AgentRunner()
    with patch("warden.agents.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test", max_turns=5)
        cmd = mock_run.call_args[0][0]
        assert "--max-turns" in cmd
        assert "5" in cmd

def test_run_with_allowed_tools():
    runner = AgentRunner()
    with patch("warden.agents.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test", allowed_tools=["Read", "Grep", "Glob"])
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
