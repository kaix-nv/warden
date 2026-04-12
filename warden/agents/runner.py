import subprocess
from pathlib import Path


class AgentError(Exception):
    pass


class AgentRunner:
    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd

    def run(self, prompt: str, max_turns: int | None = None, allowed_tools: list[str] | None = None) -> str:
        cmd = ["claude", "-p", prompt, "--output-format", "text"]
        if max_turns is not None:
            cmd.extend(["--max-turns", str(max_turns)])
        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.cwd)
        if result.returncode != 0:
            raise AgentError(result.stderr.strip() or f"claude exited with code {result.returncode}")
        return result.stdout.strip()
