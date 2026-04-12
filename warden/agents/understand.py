from pathlib import Path
from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner

class UnderstandAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def bootstrap(self, pr_count: int | None = None, commit_count: int | None = None) -> str:
        pr_instruction = f"Read the last {pr_count} merged PRs" if pr_count else "Read ALL merged PRs"
        commit_instruction = f"Read the last {commit_count} commits" if commit_count else "Read ALL commits (use `git log`)"

        prompt = (
            "You are building an initial understanding of this codebase "
            "from its complete history.\n\n"
            f"{pr_instruction} (use `gh pr list --state merged` and "
            "`gh pr view <number>` for details including review comments) and "
            f"{commit_instruction} from the very first commit to now. "
            "Explore the repo structure.\n\n"
            "Produce three documents and save them:\n\n"
            f"1. `{self.understanding_dir}/architecture.md` — Current system architecture. "
            "Components, how they connect, data flow, key dependencies.\n\n"
            f"2. `{self.understanding_dir}/design-decisions.md` — Major decisions that "
            "shaped this codebase. What was decided, why, what was rejected. "
            "Cite specific PRs and commits.\n\n"
            f"3. `{self.understanding_dir}/patterns.md` — Recurring patterns, "
            "conventions, and shared idioms.\n\n"
            "Write as a senior engineer briefing a new hire. "
            "Be concise — facts and structure, not prose."
        )
        return self.runner.run(prompt)

    def incremental(self, commit_info: dict) -> str:
        existing_docs = load_understanding(self.understanding_dir)
        prompt = (
            "You are updating the codebase understanding docs after a new commit.\n\n"
            f"Commit: {commit_info['hash']}\n"
            f"Message: {commit_info['message']}\n\n"
            f"Diff:\n```\n{commit_info['diff']}\n```\n\n"
        )
        if existing_docs:
            prompt += f"Here are the existing understanding docs:\n\n{existing_docs}\n\n"
        prompt += (
            f"Update the understanding docs in `{self.understanding_dir}/`.\n\n"
            "Rules:\n"
            "- Append new information. Do not rewrite or restate what's already there.\n"
            "- If this commit reverses a prior decision, note the reversal explicitly.\n"
            "- If no meaningful design information is in this commit, make no changes.\n"
            "- Write as a senior engineer briefing a new hire."
        )
        return self.runner.run(prompt)
