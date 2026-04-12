from pathlib import Path
from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class AskAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def ask(self, question: str) -> str:
        understanding = load_understanding(self.understanding_dir)
        prompt = "You are answering a question about a codebase using the understanding docs below.\n\n"
        if understanding:
            prompt += f"{understanding}\n\n---\n\n"
        else:
            prompt += "(No understanding docs available yet.)\n\n---\n\n"
        prompt += (
            f"Question: {question}\n\n"
            "Answer the question based on the understanding docs above. "
            "Cite specific decisions, commits, and PRs where relevant. "
            "If the docs don't contain the answer, say you don't know — "
            "don't guess or make things up."
        )
        return self.runner.run(prompt, allowed_tools=["Read", "Grep", "Glob"])
