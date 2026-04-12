# Research: Warden MVP

**Date**: 2026-04-12
**Feature**: [spec.md](./spec.md)

## R1: Claude Code Agent SDK — Python Integration

**Decision**: Use `claude-agent-sdk` Python package to spawn Claude Code agents programmatically.

**Rationale**: The SDK exposes the same agent execution engine as Claude Code CLI. It supports both one-off task execution (`query()`) and persistent multi-turn sessions (`ClaudeSDKClient`). Agents automatically have access to file read/write, bash execution, and git operations — exactly what Warden's agents need.

**Key API patterns**:
- `query(prompt, options)` — stateless, async generator yielding messages. Best for UnderstandAgent (single task per commit) and ReviewAgent (single review per commit).
- `ClaudeSDKClient` — stateful, multi-turn. Best for AskAgent (conversational Q&A).
- `ClaudeAgentOptions` — configures `allowed_tools`, `model`, `cwd`, `permission_mode`, `thinking`.
- Subagent support via `AgentDefinition` — but for Warden's orchestrator pattern, direct `query()` calls per agent type are simpler.

**Alternatives considered**:
- Raw Anthropic API (`anthropic` SDK): Lower level, would require reimplementing tool use, file access, and git operations. Rejected — too much infrastructure work.
- Subprocess spawning of `claude` CLI: Fragile, no structured output. Rejected.
- LangChain/LlamaIndex: Unnecessary abstraction layer when the Agent SDK is purpose-built. Rejected.

## R2: Git Operations — GitPython

**Decision**: Use GitPython for all git read operations (history, diffs, metadata). Use `gh` CLI (via agent's Bash tool) for GitHub-specific operations (PR reading, PR creation).

**Rationale**: GitPython provides native Python access to commit iteration, diff generation, and remote URL detection. For GitHub API operations (reading PR discussions, creating draft PRs), the `gh` CLI is already authenticated and available — delegating these to Claude Code agents avoids managing GitHub tokens.

**Key patterns**:
- `repo.iter_commits(rev='HEAD', max_count=N)` — paginated commit history
- `commit.diff(commit.parents[0])` — get diff for a commit
- `repo.remote('origin').url` — detect GitHub remote
- Track last processed commit hash in SQLite; query new commits with `repo.iter_commits(rev=f'{last_hash}..HEAD')`

**Alternatives considered**:
- `subprocess.run(['git', ...])`: Works but requires parsing text output. Rejected for read operations; GitPython is more ergonomic.
- PyGithub: Would require separate GitHub token management. Rejected in favor of `gh` CLI.

## R3: CLI Framework — Typer

**Decision**: Use Typer for CLI interface with Rich for progress display.

**Rationale**: Typer provides type-annotated command definitions, automatic help generation, and native Rich integration. The command structure maps directly: `warden init`, `warden analyze`, `warden ask`, `warden status`, `warden config`, `warden reset`.

**Key patterns**:
- Top-level `app = typer.Typer()` with `@app.command()` decorators
- `typer.Option()` for flags like `--commit HASH`, `--pr-count N`
- `typer.Argument()` for positional args like the question in `warden ask "question"`
- `@app.callback()` for shared setup (loading config, initializing repo)
- Rich `Console` and `Progress` for status output during long operations

**Alternatives considered**:
- Click: Typer is built on Click but adds type annotations and auto-completion. Preferred.
- argparse: Too low-level for 6+ commands with sub-options. Rejected.

## R4: State Management — SQLAlchemy + SQLite

**Decision**: Use SQLAlchemy ORM with SQLite for state tracking. Markdown docs remain the source of truth.

**Rationale**: SQLite is zero-config, file-based, and gitignored. SQLAlchemy provides schema migrations and type-safe queries. The database is an index — it can be rebuilt from markdown docs if the user edits them directly.

**Key patterns**:
- Three tables: `commits_processed`, `decisions`, `reviews`
- `commits_processed.hash` as primary key; boolean flags for `understand_done`, `review_done`
- On startup: check if state.db exists; if not, rebuild from markdown docs
- Use `sessionmaker` with `expire_on_commit=False` for simple transaction management

**Alternatives considered**:
- Plain JSON file: No query capability, concurrency issues. Rejected.
- TinyDB: Lacks schema enforcement. Rejected.
- Direct SQLite (no ORM): More boilerplate for CRUD operations. Rejected.

## R5: Configuration — Pydantic

**Decision**: Use Pydantic v2 for configuration schema with YAML serialization.

**Rationale**: Pydantic provides validation, defaults, and type safety. The config model maps directly to `config.yml` structure. Pydantic's `model_validator` can enforce cross-field constraints (e.g., `max_draft_prs` must be positive).

**Key patterns**:
- `BaseModel` subclasses for each config section (understanding, review, git, resources)
- `model_config = ConfigDict(extra='forbid')` to catch typos in config keys
- Load with `yaml.safe_load()` then `Config(**data)`; save with `model_dump()` then `yaml.dump()`
- CLI flags override config values (Typer option defaults pull from loaded config)

**Alternatives considered**:
- dataclasses + manual validation: More boilerplate, no built-in validation. Rejected.
- dynaconf: Heavier than needed for a single YAML file. Rejected.

## R6: Agent Prompt Design

**Decision**: Each agent type gets a dedicated prompt module that constructs the system prompt and context from understanding docs and commit data.

**Rationale**: Agent quality depends entirely on prompt quality. Separating prompt construction into dedicated modules (`understand.py`, `review.py`, `ask.py`) makes prompts testable and iterable independently.

**Key design**:
- **UnderstandAgent (bootstrap)**: System prompt instructs "senior engineer briefing a new hire." Context includes full repo file tree, sampled commit history, and PR discussions. Output: three markdown documents.
- **UnderstandAgent (incremental)**: Context includes current understanding docs + new commit diff + commit message + PR discussion. Instruction: "Append new information. Note reversals explicitly. Do not restate existing content."
- **ReviewAgent**: Context includes understanding docs + changed files. Focus areas: correctness, consistency, design coherence, broken assumptions. Instruction: "Only report high-confidence issues. For each issue, provide a fix."
- **AskAgent**: Context includes all understanding docs. Instruction: "Answer using only the provided context. Cite specific decisions, commits, and PRs. Say 'I don't know' when context is insufficient."

**Alternatives considered**:
- Single generic agent with different instructions: Harder to tune per task. Rejected.
- Prompt templates with Jinja2: Over-engineering for string concatenation. Rejected.
