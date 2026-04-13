from pathlib import Path
from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class ReviewAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def review(self, commit_hash: str, diff: str, changed_files: list[str], branch_prefix: str = "warden/", impact_summary: str = "") -> str:
        understanding = load_understanding(self.understanding_dir)
        prompt = (
            "You are reviewing a code change as a senior engineer who deeply "
            "understands this codebase's history, design decisions, and patterns.\n\n"
        )
        if understanding:
            prompt += f"Here is your accumulated understanding of this codebase:\n\n{understanding}\n\n---\n\n"
        if impact_summary:
            prompt += f"{impact_summary}\n\n---\n\n"
        prompt += (
            f"Commit: {commit_hash}\n"
            f"Changed files: {', '.join(changed_files)}\n\n"
            f"Diff:\n```\n{diff}\n```\n\n"
            "Review this change for:\n"
            "- **Correctness** — logic errors, edge cases, off-by-ones, race conditions\n"
            "- **Consistency** — does this follow the patterns established elsewhere?\n"
            "- **Design coherence** — does this contradict an established design decision?\n"
            "- **Assumptions** — does this break assumptions other code depends on?\n\n"
            "If you find issues you are confident about:\n"
            f"1. Create a new branch with prefix `{branch_prefix}`\n"
            "2. Apply the fix\n3. Commit the fix\n4. Push the branch\n"
            "5. Create a draft pull request explaining the issue and fix\n\n"
            "If no issues found, say so. Only report issues you are confident about. "
            "This is not a linter — focus on what matters."
        )
        return self.runner.run(prompt)

    def review_pr(self, pr_number: int, impact_summary: str = "") -> str:
        understanding = load_understanding(self.understanding_dir)

        prompt = (
            "You are reviewing a pull request as a senior engineer who deeply "
            "understands this codebase's history, design decisions, and patterns.\n\n"
        )

        if understanding:
            prompt += (
                "Here is your accumulated understanding of this codebase:\n\n"
                f"{understanding}\n\n---\n\n"
            )

        if impact_summary:
            prompt += f"{impact_summary}\n\n---\n\n"

        prompt += (
            f"Fetch PR #{pr_number} using `gh pr view {pr_number}` and "
            f"`gh pr diff {pr_number}` to get the full description, review "
            "comments, and diff.\n\n"
            "Review this PR for:\n"
            "- **Correctness** — logic errors, edge cases, off-by-ones, race conditions\n"
            "- **Consistency** — does this follow the patterns established in this codebase?\n"
            "- **Design coherence** — does this contradict an established design decision?\n"
            "- **Assumptions** — does this break assumptions other code depends on?\n\n"
            "Reference specific design decisions, architecture choices, or patterns "
            "from the understanding docs when they are relevant to your review.\n\n"
            "Provide your review as structured feedback. For each issue:\n"
            "- File and line range\n"
            "- What the issue is\n"
            "- Why it matters (cite the relevant design decision or pattern)\n"
            "- Suggested fix\n\n"
            "If the PR looks good, say so and explain why it aligns well with "
            "the codebase's design. Only flag issues you are confident about."
        )

        return self.runner.run(prompt)
