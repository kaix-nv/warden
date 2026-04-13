"""Skill templates installed by `warden init`."""

from pathlib import Path

SKILLS = {
    "warden-review-pr": {
        "filename": "SKILL.md",
        "content": """\
---
name: warden-review-pr
description: >
  Review a pull request using Warden's accumulated codebase understanding,
  design decisions, and dependency graph. Use when reviewing PRs or when
  the user mentions reviewing a PR number.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(gh *) Bash(git *)
---

# Warden PR Review

Review a pull request using accumulated codebase understanding.

## Steps

1. **Get the PR number** from the user's message or $ARGUMENTS.

2. **Get changed files:**
   ```bash
   gh pr view <PR_NUMBER> --json files -q '.files[].path'
   ```

3. **Get dependency impact and relevant design context:**
   ```bash
   warden impact <changed-files-space-separated>
   ```
   This returns the dependency graph impact (what depends on these files)
   and the relevant sections from the codebase understanding docs.

4. **Get the PR diff and description:**
   ```bash
   gh pr view <PR_NUMBER>
   gh pr diff <PR_NUMBER>
   ```

5. **Review the PR** using all the context above. Focus on:
   - **Correctness** -- logic errors, edge cases, off-by-ones, race conditions
   - **Consistency** -- does this follow the patterns established in this codebase?
   - **Design coherence** -- does this contradict an established design decision?
   - **Assumptions** -- does this break assumptions other code depends on?

   Reference specific design decisions and patterns from the Warden context
   when they are relevant to your review.

6. **Present findings** as structured feedback. For each issue:
   - File and line range
   - What the issue is
   - Why it matters (cite the relevant design decision or pattern)
   - Suggested fix

   If the PR looks good, say so and explain why it aligns well with
   the codebase's design.

7. **Offer to fix:** If issues were found, ask the user:
   "Want me to fix any of these issues?"
   If yes, create a branch, edit the files, commit, push, and update the PR.
""",
    },
    "warden-review": {
        "filename": "SKILL.md",
        "content": """\
---
name: warden-review
description: >
  Review current uncommitted or staged changes using Warden's codebase
  understanding and dependency graph. Use when reviewing local changes
  before committing.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(git *)
---

# Warden Code Review

Review current changes using accumulated codebase understanding.

## Steps

1. **Get changed files:**
   ```bash
   git diff --name-only
   git diff --staged --name-only
   ```
   Combine both lists (unstaged + staged changes).

2. **Get dependency impact and relevant design context:**
   ```bash
   warden impact <changed-files-space-separated>
   ```

3. **Get the full diff:**
   ```bash
   git diff
   git diff --staged
   ```

4. **Review the changes** using the Warden context. Focus on:
   - **Correctness** -- logic errors, edge cases, off-by-ones, race conditions
   - **Consistency** -- does this follow the patterns established in this codebase?
   - **Design coherence** -- does this contradict an established design decision?
   - **Assumptions** -- does this break assumptions other code depends on?

5. **Present findings** with specific file and line references.

6. **Offer to fix:** If issues were found, offer to edit the files directly.
   Apply fixes with the user's approval.
""",
    },
    "warden-ask": {
        "filename": "SKILL.md",
        "content": """\
---
name: warden-ask
description: >
  Answer questions about the codebase using Warden's accumulated understanding
  of architecture, design decisions, relationships, and patterns. Use when
  the user asks why code is designed a certain way, what components depend
  on each other, or how to extend the codebase.
user-invocable: true
allowed-tools: Read Grep Glob Bash(warden *) Bash(git *)
---

# Warden Codebase Q&A

Answer questions using accumulated codebase understanding.

## Steps

1. **Read the understanding docs:**
   - Read `.warden/understanding/architecture.md`
   - Read `.warden/understanding/relationships.md`
   - Read `.warden/understanding/design-decisions.md`
   - Read `.warden/understanding/patterns.md`

2. **If the question mentions specific files or components**, also run:
   ```bash
   warden impact <mentioned-files>
   ```
   to get structural context from the dependency graph.

3. **Answer the question** based on the understanding docs.
   - Cite specific design decisions, commits, and PRs where relevant
   - If the docs don't contain the answer, say so -- don't guess
   - If the answer involves code, read the actual source files to verify

4. **Follow-up** is natural -- the user can ask clarifying questions
   and you retain the full context from the understanding docs.
""",
    },
}


def install_skills(repo_path: Path):
    """Create .claude/skills/warden-*/ directories with SKILL.md files."""
    skills_dir = repo_path / ".claude" / "skills"
    for skill_name, skill_data in SKILLS.items():
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / skill_data["filename"]
        skill_file.write_text(skill_data["content"])
