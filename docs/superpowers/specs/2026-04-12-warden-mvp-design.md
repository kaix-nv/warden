# Warden MVP Design Spec

**AI Agent for Continuous Codebase Vigilance**

**Date:** 2026-04-12
**Status:** Approved Design
**Target:** Solo developers, with architecture supporting future team use

---

## Overview

Warden is a Python CLI that maintains persistent understanding of a codebase and proactively improves code quality. It runs on each commit (via git hook) or on demand, delegating all AI reasoning to Claude Code CLI (`claude -p`) as a subprocess.

Warden is the **scheduler and memory**. Claude Code is the **brain**.

### What Warden Does (MVP)

1. **Understands** — reads every commit (and PR discussions) to build living documentation of design decisions, architecture, and patterns
2. **Reviews** — analyzes changed code using accumulated understanding to catch correctness issues, inconsistencies with established patterns, and contradictions of design decisions. Creates draft PRs with fixes.
3. **Answers** — responds to natural language questions about the codebase using accumulated understanding

### What Warden Does NOT Do (MVP)

- No background daemon (CLI-triggered only, daemon mode comes later)
- No dependency monitoring or CVE scanning
- No feedback/learning loop
- No vector DB or semantic search
- No Slack/email notifications
- No multi-repo support

---

## Target User

Solo developer who wants a "senior engineer" watching over their codebase. Installs in under a minute, provides value after the first `warden init`.

Adoption path: solo dev loves it → brings it to their team → team adopts it.

---

## Architecture

### Three Layers

```
┌─────────────────────────────────────┐
│           Warden CLI                 │
│  (init, analyze, status, ask, config)│
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│         Orchestrator                  │
│  - Determines what work to do         │
│  - Manages state (SQLite index)       │
│  - Reads/writes markdown docs         │
│  - Tracks processed commits           │
└──────────────┬───────────────────────┘
               │ shells out to `claude -p`
┌──────────────▼───────────────────────┐
│     Claude Code CLI                   │
│  - UnderstandAgent prompt             │
│  - ReviewAgent prompt                 │
│  - AskAgent prompt                    │
└───────────────────────────────────────┘
```

### What Warden Builds vs. What Claude Code Provides

| Warden builds | Claude Code provides |
|---------------|---------------------|
| When to analyze | Code understanding |
| What context to feed | Reasoning about code |
| Where to store results | File reading/writing |
| Git hook integration | Git operations |
| State tracking across runs | PR creation |
| User-facing CLI | Natural language Q&A |

---

## Agents

### UnderstandAgent

Builds and maintains the understanding docs. Operates in two modes.

**Bootstrap mode** (`warden init`):

Spawns a single Claude Code agent that reads the complete repo history — all commits and all merged PRs from the very first commit. The agent explores the repo structure, reads PR discussions (titles, descriptions, review comments, inline code comments), and produces three documents.

Prompt voice: "Write as a senior engineer briefing a new hire."

**Incremental mode** (`warden analyze`):

Runs on each new commit. Reads the diff, commit message, and associated PR discussion if one exists. Appends new information to the existing understanding docs. Does not restate what's already there. Notes reversals explicitly when a commit changes a prior decision.

### ReviewAgent

Reviews changed code using the understanding docs as context — like a senior engineer who knows the full history of the codebase. Focuses on:

- **Correctness** — logic errors, edge cases, off-by-ones, race conditions
- **Consistency** — does this change follow the patterns established elsewhere?
- **Design coherence** — does this contradict an established design decision?
- **Assumptions** — does this break assumptions that other parts of the code depend on?

For each issue found: creates a branch, applies the fix, pushes, and creates a draft PR. Only reports issues it is confident about. This is not a linter — Warden catches what linters can't because it understands *why* the code is the way it is.

### AskAgent

Reads all understanding docs and answers a natural language question. Cites specific decisions, commits, and PRs. Says "I don't know" when the docs don't contain the answer.

---

## Data Model & Storage

### Directory Structure

```
.warden/
├── config.yml                    # User configuration (committed)
├── state.db                      # SQLite index (gitignored)
├── understanding/                # Source of truth (committed)
│   ├── architecture.md           # Component map, dependencies, data flow
│   ├── design-decisions.md       # Why things were built the way they are
│   ├── patterns.md               # Recurring patterns and conventions
│   └── changelog.md              # What Warden learned per commit
└── improvements/                 # Improvement tracking
    ├── pending/                  # Draft PRs awaiting review
    └── history/                  # Past suggestions (accepted/declined)
```

### Markdown Docs (Source of Truth)

Understanding docs are human-readable, editable, and directly usable as LLM context. Users can edit them to correct Warden. All agents read from these files.

**design-decisions.md example:**

```markdown
# Design Decisions

## Use SQLite for session storage over Redis
- **Source:** PR #142 (2024-01-20)
- **Decision:** SQLite for session storage
- **Rejected alternative:** Redis — ops overhead not justified at current scale
- **Reviewer concern:** @alice raised cold-start latency; resolved with connection pooling
- **Context:** 12-comment review thread

## Use async/await for all I/O
- **Commit:** abc123 (2024-01-15)
- **Files:** api/orders.py, api/users.py
- **Rationale:** Reduced O(n^2) to O(n log n) for large dataset queries
```

### SQLite Schema (Index Only)

Not the source of truth. Rebuilt from markdown if the user edits docs directly.

```sql
commits_processed (
    hash TEXT PRIMARY KEY,
    timestamp DATETIME,
    files_changed TEXT,
    understand_done BOOLEAN,
    review_done BOOLEAN
)

decisions (
    id INTEGER PRIMARY KEY,
    commit_hash TEXT,
    file_path TEXT,
    summary TEXT,
    category TEXT,            -- architecture | design | pattern
    created_at DATETIME
)

reviews (
    id INTEGER PRIMARY KEY,
    commit_hash TEXT,
    issue_type TEXT,          -- correctness | consistency | design | assumptions
    description TEXT,
    status TEXT,              -- pending | accepted | declined
    pr_url TEXT,
    created_at DATETIME
)
```

---

## CLI Interface

```
warden init [--pr-count N] [--commit-count N]
    Create .warden/ directory, install post-commit hook,
    run bootstrap analysis on full repo history.
    --pr-count: override how many PRs to read (default: all)
    --commit-count: override how many commits to read (default: all)
    CLI flags override config.yml values.

warden analyze [--commit HASH]
    Process new commits since last run.
    Default: all unprocessed commits.
    With --commit: process a specific commit only.

warden ask "<question>"
    Query the understanding docs via natural language.

warden status
    Show commits processed, understanding doc sizes,
    pending draft PRs, improvement history.

warden config [validate]
    Show current config. With 'validate': check for errors.

warden reset [--understanding] [--improvements] [--all]
    Clear specific state for a fresh start.
```

### Git Hook

`warden init` appends to `.git/hooks/post-commit`:

```bash
# Added by Warden
warden analyze 2>/dev/null &
```

Runs in background, never blocks the developer's commit flow.

---

## Core Workflows

### `warden init`

1. Create `.warden/` directory structure
2. Create default `config.yml`
3. Install post-commit hook (appends to existing hook if present)
4. Add `.warden/state.db` to `.gitignore`
5. Spawn UnderstandAgent in bootstrap mode — reads full repo history (all commits + all merged PRs), produces `architecture.md`, `design-decisions.md`, `patterns.md`
6. Index the output into SQLite
7. Print summary

### `warden analyze`

1. Read `state.db` to find last processed commit
2. Get new commits since then
3. For each commit:
   a. Spawn UnderstandAgent in incremental mode:
      - Reads diff, commit message, associated PR discussion if any
      - Updates understanding docs (append, don't rewrite)
   b. Update SQLite index
   c. If review enabled:
      - Spawn ReviewAgent:
        - Reads understanding docs + changed files
        - Reviews for correctness, consistency, design coherence
        - For each issue: create branch, fix, push, draft PR
      - Record reviews in state.db + `.warden/improvements/`
4. Print summary

### `warden ask "<question>"`

1. Load all `.warden/understanding/*.md`
2. Spawn AskAgent with understanding docs as context + user question
3. Print answer

### `warden status`

1. Read `state.db`
2. Print: commits processed, last run date, doc sizes, pending PRs, improvement stats

---

## Configuration

```yaml
# .warden/config.yml

# Understanding settings
understanding:
  bootstrap:
    pr_count: all             # How many merged PRs to process at init
    commit_count: all         # How many commits to process at init
  incremental:
    include_pr_comments: true # Fetch associated PR discussion on each commit

# Code review settings
review:
  enabled: true
  max_draft_prs: 5            # Max open draft PRs at any time
  auto_push: true             # Push branch and create PR automatically

# Git integration
git:
  ignore_patterns:
    - "*.lock"
    - "node_modules/**"
    - ".env*"
    - "vendor/**"
  branch_prefix: "warden/"

# Resource limits
resources:
  max_commits_per_run: 20
```

**Design choices:**
- No API keys in config — environment variables or Claude Code's existing auth
- No LLM model selection — Claude Code handles that
- No notification config — later feature
- Zero-config works — all defaults are sensible

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| CLI | Typer |
| Config | Pydantic |
| Database | SQLAlchemy + SQLite |
| Git | GitPython |
| AI | Claude Code CLI (`claude -p`) |
| GitHub | `gh` CLI (via Claude Code) |

---

## Project Structure

```
warden/
├── warden/
│   ├── __init__.py
│   ├── cli/
│   │   └── commands.py          # Typer CLI commands
│   ├── core/
│   │   ├── orchestrator.py      # Decides what work to do
│   │   ├── state.py             # SQLite state manager
│   │   └── config.py            # Pydantic config model
│   ├── agents/
│   │   ├── runner.py            # Shells out to `claude -p`
│   │   ├── understand.py        # UnderstandAgent prompts + context
│   │   ├── review.py            # ReviewAgent prompts + context
│   │   └── ask.py               # AskAgent prompts + context
│   ├── git/
│   │   ├── hooks.py             # Git hook installation
│   │   └── repo.py              # Git operations (diff, log, etc.)
│   └── models/
│       ├── state.py             # SQLAlchemy models
│       └── config.py            # Pydantic config schema
├── tests/
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## What's NOT in MVP (Future Roadmap)

| Feature | Version |
|---------|---------|
| Daemon mode (`warden start/stop`) | v0.2 |
| Dependency monitoring / CVE alerts | v0.3 |
| Slack/email notifications | v0.3 |
| Vector DB / semantic search | v0.3 |
| Feedback loop / learning | v0.4 |
| Multi-repo support | v1.0 |
| RBAC / team features | v1.0 |
