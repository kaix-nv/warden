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

        ud = self.understanding_dir
        prompt = (
            "You are building a deep understanding of this codebase from its "
            "complete history. Your goal is to become the experienced guide that "
            "a new contributor needs — someone who knows not just where things are, "
            "but how to navigate them, what paths are dangerous, and where to "
            "build next.\n\n"
            "Two key assumptions:\n"
            "1. Code is relational — components have contracts, dependencies, and "
            "shared infrastructure. New code must plug into what exists.\n"
            "2. Code is evolutionary — the current structure is the result of "
            "decisions, mistakes, and lessons. Understanding the evolution is "
            "essential to making good decisions going forward.\n\n"
            f"{pr_instruction} (use `gh pr list --state merged` and "
            "`gh pr view <number>` for details including review comments) and "
            f"{commit_instruction} from the very first commit to now. "
            "Explore the repo structure.\n\n"
            "Produce four documents and save them:\n\n"
            f"1. `{ud}/architecture.md` — Current system architecture. "
            "Components, their responsibilities, dependency graph, contracts "
            "between modules, data flow. Not just what exists — how the pieces "
            "fit together and what each component expects from its neighbors.\n\n"
            f"2. `{ud}/relationships.md` — How components interact. Shared "
            "infrastructure and reusable abstractions. Extension points: "
            "\"to add a new algorithm, inherit from X, register via Y, "
            "plug into pipeline Z.\" Dependency chains: what breaks if you "
            "change a given module.\n\n"
            f"3. `{ud}/design-decisions.md` — Major decisions that shaped this "
            "codebase. What was decided, why, what was rejected. Also: "
            "mistakes made and lessons learned, known tech debt and workarounds, "
            "things that were tried and failed. Cite specific PRs and commits.\n\n"
            f"4. `{ud}/patterns.md` — Recurring patterns, conventions, and "
            "shared idioms. Include anti-patterns: things the codebase has "
            "moved away from and why. For each pattern, explain when to use it "
            "and when not to.\n\n"
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
            "The docs are: architecture.md, relationships.md, design-decisions.md, "
            "patterns.md.\n\n"
            "Rules:\n"
            "- Append new information. Do not rewrite or restate what's already there.\n"
            "- If this commit reverses a prior decision, note the reversal explicitly.\n"
            "- If this commit introduces new relationships between components, "
            "update relationships.md.\n"
            "- If this commit reveals tech debt or a lesson learned, add it to "
            "design-decisions.md.\n"
            "- If this commit adds or changes extension points, update relationships.md.\n"
            "- If no meaningful design information is in this commit, make no changes.\n"
            "- Write as a senior engineer briefing a new hire."
        )
        return self.runner.run(prompt)
