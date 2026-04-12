# Implementation Plan: Warden MVP

**Branch**: `001-warden-mvp` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-warden-mvp/spec.md`

## Summary

Warden is a Python CLI that maintains persistent understanding of a codebase and proactively improves code quality. It runs on each commit (via git hook) or on demand, delegating all AI reasoning to Claude Code via the Agent SDK. The MVP delivers three capabilities: understanding (bootstrap + incremental documentation of architecture, decisions, and patterns), reviewing (automated code review with draft PR creation), and answering (natural language Q&A against understanding docs).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer (CLI), Pydantic v2 (config), SQLAlchemy (ORM), GitPython (git ops), claude-agent-sdk (AI agents), PyYAML (config file), Rich (progress/output)
**Storage**: SQLite via SQLAlchemy (state index, gitignored); Markdown files (understanding docs, committed)
**Testing**: pytest + pytest-asyncio (Agent SDK is async)
**Target Platform**: Linux/macOS (developer workstations with git)
**Project Type**: CLI tool
**Performance Goals**: Post-commit hook must not block git operations; background analysis should complete within minutes per commit
**Constraints**: Zero-config installation; no daemon process; no API key management (uses existing Claude Code auth)
**Scale/Scope**: Solo developer, single repository, hundreds to thousands of commits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No project-specific constitution has been defined. The default template is in place with placeholder values. No gates to enforce.

**Pre-Phase 0 status**: PASS (no constitution constraints)
**Post-Phase 1 status**: PASS (no constitution constraints)

## Project Structure

### Documentation (this feature)

```text
specs/001-warden-mvp/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Technology research
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/
│   └── cli.md           # Phase 1: CLI command contracts
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
warden/
├── warden/
│   ├── __init__.py              # Package init, version
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py          # Typer CLI commands (init, analyze, ask, status, config, reset)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Decides what work to do, coordinates agents
│   │   ├── state.py             # SQLite state manager (read/write commit records, reviews)
│   │   └── config.py            # Pydantic config loader + validator
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── runner.py            # Claude Code Agent SDK wrapper (query, options)
│   │   ├── understand.py        # UnderstandAgent prompt construction (bootstrap + incremental)
│   │   ├── review.py            # ReviewAgent prompt construction + PR creation flow
│   │   └── ask.py               # AskAgent prompt construction + response formatting
│   ├── git/
│   │   ├── __init__.py
│   │   ├── hooks.py             # Git hook installation (append to post-commit)
│   │   └── repo.py              # Git operations (history, diff, remote detection, ignore patterns)
│   └── models/
│       ├── __init__.py
│       ├── db.py                # SQLAlchemy models (CommitRecord, Decision, Review)
│       └── config.py            # Pydantic config schema (WardenConfig, sections)
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py       # Config loading, validation, defaults
│   │   ├── test_state.py        # State DB operations
│   │   ├── test_hooks.py        # Hook installation logic
│   │   ├── test_repo.py         # Git operations
│   │   └── test_prompts.py      # Agent prompt construction
│   └── integration/
│       ├── __init__.py
│       ├── test_init.py         # Full init workflow on a test repo
│       ├── test_analyze.py      # Incremental analysis workflow
│       └── test_cli.py          # CLI command invocation
├── pyproject.toml               # Package metadata, dependencies, entry points
└── LICENSE
```

**Structure Decision**: Single-project CLI structure. No frontend, no web service, no separate packages. The `warden/` package is the sole deliverable, installed as a CLI entry point via `pyproject.toml`.

## Implementation Phases

### Phase 1: Foundation (P1 prerequisite infrastructure)

Build the project skeleton and all non-AI components.

1. **Project setup**: `pyproject.toml` with entry point `warden = "warden.cli.commands:app"`, all dependencies declared
2. **Config model** (`models/config.py`): Pydantic schema matching `.warden/config.yml` structure with defaults
3. **Config loader** (`core/config.py`): Load YAML, validate, merge CLI overrides
4. **DB models** (`models/db.py`): SQLAlchemy models for `commits_processed`, `decisions`, `reviews`
5. **State manager** (`core/state.py`): Create DB, query unprocessed commits, mark commits done, track reviews
6. **Git operations** (`git/repo.py`): Commit history iteration, diff extraction, remote URL detection, ignore pattern matching
7. **Git hooks** (`git/hooks.py`): Install/uninstall post-commit hook, detect existing hooks
8. **Agent runner** (`agents/runner.py`): Thin wrapper around `claude-agent-sdk` `query()` — configures options, handles async iteration, collects results

### Phase 2: Understand Capability (User Story 1 + 2)

Implement bootstrap and incremental understanding.

1. **UnderstandAgent prompts** (`agents/understand.py`):
   - Bootstrap prompt: reads repo structure, full commit history, PR discussions → outputs three markdown docs
   - Incremental prompt: reads current docs + new diff + commit message → appends updates
2. **Orchestrator — init flow** (`core/orchestrator.py`): Create `.warden/` directory, write default config, install hook, add state.db to .gitignore, spawn bootstrap UnderstandAgent, index results
3. **Orchestrator — analyze flow**: Find unprocessed commits, for each: spawn incremental UnderstandAgent, update state DB
4. **CLI commands**: `warden init`, `warden analyze` (wire to orchestrator)

### Phase 3: Review Capability (User Story 3)

Add automated code review with draft PR creation.

1. **ReviewAgent prompts** (`agents/review.py`): Reads understanding docs + changed files → identifies issues → for each: creates branch, applies fix, pushes, creates draft PR
2. **Orchestrator — review flow**: After understand step, if review enabled and under max_draft_prs, spawn ReviewAgent
3. **Review state tracking**: Record findings in state DB, link to PR URLs
4. **CLI integration**: Review results shown in `warden analyze` output

### Phase 4: Ask + Status + Config (User Stories 4, 5, 6)

Complete the CLI surface.

1. **AskAgent prompts** (`agents/ask.py`): Loads understanding docs as context, answers with citations
2. **CLI — warden ask**: Pass question to AskAgent, format response
3. **CLI — warden status**: Query state DB, format summary
4. **CLI — warden config**: Show config, validate subcommand
5. **CLI — warden reset**: Clear specified state (understanding, improvements, all)

## Key Design Decisions

### Warden is the orchestrator, not the brain

Warden never reasons about code directly. It decides *what* to analyze (which commits, which files), prepares *context* (understanding docs, diffs, config), and delegates *all reasoning* to Claude Code agents. This keeps the Python codebase simple and testable.

### Understanding docs are the source of truth

The SQLite database is an index for performance (finding unprocessed commits, querying review status). If it's deleted, it can be rebuilt from the markdown docs and git history. Users can edit markdown docs directly; Warden respects those edits.

### One agent invocation per task

Each agent call is stateless and self-contained: one prompt, one response. No multi-turn conversations during analysis. This simplifies error handling (retry the whole call) and makes prompts testable in isolation. The AskAgent is the only potentially multi-turn use case, but MVP keeps it single-turn.

### Background analysis, never blocking

The post-commit hook runs `warden analyze` in the background. If it fails, the developer doesn't notice — they can always run `warden analyze` manually later. Unprocessed commits accumulate and are batch-processed on the next run.

## Risk Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Agent SDK API changes | Pin version in pyproject.toml; thin wrapper in `runner.py` isolates SDK calls |
| Large repo overwhelms bootstrap | `--commit-count` and `--pr-count` flags limit scope; `max_commits_per_run` for incremental |
| False positive reviews erode trust | High-confidence-only instruction in ReviewAgent prompt; `review.enabled` config toggle |
| PR discussion unavailable (no gh CLI, private repo) | Graceful degradation: skip PR data, log warning, continue with commit data only |
| Concurrent analyze runs (hook + manual) | SQLite WAL mode for concurrent reads; state.db lock prevents duplicate processing |
