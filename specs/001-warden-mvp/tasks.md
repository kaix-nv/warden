# Tasks: Warden MVP — AI Agent for Continuous Codebase Vigilance

**Input**: Design documents from `/specs/001-warden-mvp/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `warden/` package at repository root, `tests/` alongside
- All source paths are relative to repository root: `warden/warden/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure: `warden/warden/` with subdirectories `cli/`, `core/`, `agents/`, `git/`, `models/`, each containing `__init__.py`; create `warden/tests/unit/` and `warden/tests/integration/` with `__init__.py` files
- [ ] T002 Create `warden/pyproject.toml` with package metadata, entry point `warden = "warden.cli.commands:app"`, and all dependencies: typer, pydantic>=2.0, sqlalchemy, gitpython, claude-agent-sdk, pyyaml, rich; dev dependencies: pytest, pytest-asyncio
- [ ] T003 Create `warden/warden/__init__.py` with package version string

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Implement Pydantic config schema in `warden/warden/models/config.py` — define `BootstrapConfig`, `IncrementalConfig`, `UnderstandingConfig`, `ReviewConfig`, `GitConfig`, `ResourcesConfig`, `WardenConfig` with all defaults from data-model.md; use `model_config = ConfigDict(extra='forbid')` to reject unknown keys
- [ ] T005 [P] Implement config loader in `warden/warden/core/config.py` — load YAML from `.warden/config.yml`, validate via Pydantic model, merge CLI overrides, write default config on init; handle missing file gracefully
- [ ] T006 [P] Implement SQLAlchemy models in `warden/warden/models/db.py` — define `CommitRecord` (hash PK, timestamp, files_changed JSON, understand_done bool, review_done bool), `Decision` (id PK, commit_hash FK, file_path, summary, category enum, created_at), `Review` (id PK, commit_hash FK, issue_type enum, description, status enum, pr_url nullable, branch_name nullable, created_at); use declarative base with SQLite dialect
- [ ] T007 [P] Implement git operations in `warden/warden/git/repo.py` — functions: `get_repo(path)` returning Repo, `iter_commits(repo, since_hash=None, max_count=None)` yielding commit objects, `get_diff(commit)` returning diff text, `get_commit_metadata(commit)` returning dict, `detect_github_remote(repo)` returning owner/repo or None, `matches_ignore_pattern(path, patterns)` returning bool
- [ ] T008 [P] Implement git hook management in `warden/warden/git/hooks.py` — functions: `install_post_commit_hook(repo_path)` that appends Warden trigger to existing hook or creates new one, `uninstall_post_commit_hook(repo_path)` that removes Warden lines, `is_hook_installed(repo_path)` returning bool; preserve existing hook content
- [ ] T009 Implement state manager in `warden/warden/core/state.py` — functions: `init_db(db_path)` creating SQLite with WAL mode, `get_unprocessed_commits(session)` returning list, `mark_commit_understood(session, hash)`, `mark_commit_reviewed(session, hash)`, `add_review(session, review_data)`, `get_status_summary(session)` returning dict with counts/dates, `add_to_gitignore(repo_path, entry)` appending if not present; depends on T006
- [ ] T010 Implement agent runner in `warden/warden/agents/runner.py` — async function `run_agent(prompt, cwd, allowed_tools=None, model=None)` that wraps `claude-agent-sdk` `query()`, configures `ClaudeAgentOptions` with sensible defaults (Read, Write, Edit, Bash, Grep, Glob tools), iterates async response, returns collected result text; handle SDK errors with clear messages

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Initialize Warden on an Existing Repository (Priority: P1) MVP

**Goal**: Developer runs `warden init` and gets understanding documents generated from full repo history with a git hook installed for future commits.

**Independent Test**: Run `warden init` on any git repository with history. Verify `.warden/` directory is created with `config.yml`, `understanding/architecture.md`, `understanding/design-decisions.md`, `understanding/patterns.md`, `state.db`, and post-commit hook.

### Implementation for User Story 1

- [ ] T011 [US1] Implement UnderstandAgent bootstrap prompt in `warden/warden/agents/understand.py` — function `build_bootstrap_prompt(repo_path, commit_count, pr_count)` that constructs a system prompt instructing the agent to "write as a senior engineer briefing a new hire", includes repo file tree, commit history summary, and PR discussion data; returns prompt string and list of context items
- [ ] T012 [US1] Implement PR discussion fetcher in `warden/warden/git/repo.py` — function `fetch_pr_discussions(owner, repo, count=None)` that uses `gh` CLI subprocess to list merged PRs and their comments; returns list of PR data dicts; gracefully returns empty list if `gh` is unavailable or remote is not GitHub
- [ ] T013 [US1] Implement orchestrator init flow in `warden/warden/core/orchestrator.py` — async function `run_init(repo_path, pr_count=None, commit_count=None)` that: creates `.warden/` directory structure, writes default config.yml, initializes state.db, adds state.db to .gitignore, collects repo history and PR data, spawns bootstrap UnderstandAgent via runner, writes output to understanding docs, indexes decisions into state DB, installs post-commit hook, returns summary dict
- [ ] T014 [US1] Implement CLI `init` command in `warden/warden/cli/commands.py` — create Typer app, add `init` command with `--pr-count` and `--commit-count` options (both default to config or "all"); show Rich progress during bootstrap; print summary on completion; handle already-initialized repo error
- [ ] T015 [US1] Handle edge case: `warden init` on already-initialized repository — check for existing `.warden/` in orchestrator, raise clear error suggesting `warden reset --all` first

**Checkpoint**: User Story 1 complete — `warden init` generates understanding docs and installs hook

---

## Phase 4: User Story 2 — Incremental Commit Analysis (Priority: P1) MVP

**Goal**: After init, each new commit is automatically analyzed in the background via post-commit hook, updating understanding documents incrementally.

**Independent Test**: After `warden init`, make a new commit, then run `warden analyze`. Verify understanding docs are updated with information from the new commit.

### Implementation for User Story 2

- [ ] T016 [US2] Implement UnderstandAgent incremental prompt in `warden/warden/agents/understand.py` — function `build_incremental_prompt(diff_text, commit_message, pr_discussion, current_docs)` that instructs the agent to append new information to existing docs, note decision reversals explicitly, and not restate existing content; returns prompt string
- [ ] T017 [US2] Implement orchestrator analyze flow in `warden/warden/core/orchestrator.py` — async function `run_analyze(repo_path, specific_commit=None)` that: reads state.db for unprocessed commits (or uses specific_commit), respects max_commits_per_run config, for each commit: gets diff, checks ignore patterns, fetches PR discussion if configured, spawns incremental UnderstandAgent, updates understanding docs, marks commit as understood in state DB; returns summary dict
- [ ] T018 [US2] Implement ignore pattern filtering in `warden/warden/core/orchestrator.py` — before spawning UnderstandAgent, filter changed files through `matches_ignore_pattern()`; if all files match ignore patterns, mark commit as processed without agent invocation
- [ ] T019 [US2] Implement CLI `analyze` command in `warden/warden/cli/commands.py` — add `analyze` command with `--commit` option for specific hash; show progress for batch processing; print summary of commits processed and docs updated; handle "no new commits" case gracefully
- [ ] T020 [US2] Implement changelog tracking in `warden/warden/core/orchestrator.py` — after each incremental analysis, append entry to `.warden/understanding/changelog.md` with commit hash, date, summary of what was learned, and which docs were updated

**Checkpoint**: User Stories 1 and 2 complete — full understand pipeline works (bootstrap + incremental)

---

## Phase 5: User Story 3 — Code Review with Automated Fix PRs (Priority: P2)

**Goal**: During commit analysis, Warden also reviews code for issues and creates draft PRs with fixes.

**Independent Test**: Introduce a known bug (e.g., off-by-one, pattern violation) in a commit. Run `warden analyze`. Verify a draft PR is created with the correct fix.

**Dependencies**: Requires US1 + US2 (understanding docs must exist for context)

### Implementation for User Story 3

- [ ] T021 [US3] Implement ReviewAgent prompt in `warden/warden/agents/review.py` — function `build_review_prompt(diff_text, changed_files, understanding_docs)` that instructs the agent to review for correctness, consistency, design coherence, and broken assumptions; only report high-confidence issues; for each issue: create a branch with `warden/` prefix, apply fix, push, create draft PR via `gh`; returns prompt string
- [ ] T022 [US3] Implement orchestrator review flow in `warden/warden/core/orchestrator.py` — extend `run_analyze()`: after understand step, if `config.review.enabled` is true, check open draft PR count against `config.review.max_draft_prs`, spawn ReviewAgent with understanding docs + changed files as context, parse agent output for created PRs, record reviews in state DB
- [ ] T023 [US3] Implement draft PR count check in `warden/warden/core/orchestrator.py` — function `count_open_draft_prs(owner, repo, branch_prefix)` using `gh pr list --draft --json` subprocess; skip review if at max_draft_prs limit
- [ ] T024 [US3] Implement review state recording in `warden/warden/core/state.py` — function `record_review_finding(session, commit_hash, issue_type, description, pr_url, branch_name)` and `get_pending_reviews(session)` returning list of unresolved findings
- [ ] T025 [US3] Update CLI `analyze` output in `warden/warden/cli/commands.py` — display review findings and draft PR URLs in the analyze summary; distinguish between "no issues found" and "review skipped (disabled or at PR limit)"

**Checkpoint**: User Story 3 complete — Warden reviews code and creates draft PRs

---

## Phase 6: User Story 4 — Ask Questions About the Codebase (Priority: P2)

**Goal**: Developer asks Warden a natural language question and gets an answer with citations.

**Independent Test**: After init, run `warden ask "Why was [known decision] made?"`. Verify the answer cites the correct commit or PR.

**Dependencies**: Requires US1 (understanding docs must exist)

### Implementation for User Story 4

- [ ] T026 [P] [US4] Implement AskAgent prompt in `warden/warden/agents/ask.py` — function `build_ask_prompt(question, understanding_docs)` that loads all `.warden/understanding/*.md` files as context, instructs the agent to answer using only provided context, cite specific decisions/commits/PRs, and say "I don't know" when context is insufficient; returns prompt string
- [ ] T027 [US4] Implement CLI `ask` command in `warden/warden/cli/commands.py` — add `ask` command with positional `question` argument; load understanding docs, spawn AskAgent via runner, format and print response; handle missing understanding docs with clear error

**Checkpoint**: User Story 4 complete — developer can query codebase knowledge

---

## Phase 7: User Story 5 — View Status and Manage State (Priority: P3)

**Goal**: Developer can check Warden's state and reset specific parts.

**Independent Test**: After init and several analyze runs, run `warden status`. Verify accurate counts. Run `warden reset --understanding` and verify only understanding docs are cleared.

### Implementation for User Story 5

- [ ] T028 [P] [US5] Implement CLI `status` command in `warden/warden/cli/commands.py` — query state DB via `get_status_summary()`, read understanding doc file sizes, count pending draft PRs, format as Rich table showing: commits processed (count + last hash), last run date, doc sizes (lines/words), pending PRs (count + URLs), improvement history (accepted/declined counts)
- [ ] T029 [P] [US5] Implement orchestrator reset flow in `warden/warden/core/orchestrator.py` — function `run_reset(repo_path, understanding=False, improvements=False, all_state=False)` that: clears `.warden/understanding/` if understanding or all, clears `.warden/improvements/` if improvements or all, resets state.db tables if all, preserves `config.yml` always; returns summary of what was cleared
- [ ] T030 [US5] Implement CLI `reset` command in `warden/warden/cli/commands.py` — add `reset` command with `--understanding`, `--improvements`, `--all` flags (at least one required); confirm action before proceeding; print summary of cleared state

**Checkpoint**: User Story 5 complete — developer can inspect and reset Warden state

---

## Phase 8: User Story 6 — Configure Warden Behavior (Priority: P3)

**Goal**: Developer can view and validate Warden configuration.

**Independent Test**: Edit `config.yml` with an invalid value. Run `warden config validate`. Verify clear error message.

### Implementation for User Story 6

- [ ] T031 [P] [US6] Implement CLI `config` command in `warden/warden/cli/commands.py` — add `config` command that displays current config as formatted YAML; add `validate` subcommand that loads config through Pydantic validation and reports errors with field names and expected types
- [ ] T032 [US6] Implement config validation error formatting in `warden/warden/core/config.py` — function `validate_config_file(config_path)` that catches Pydantic `ValidationError`, formats each error with field path, value, and expected constraint; returns list of error strings or empty list on success

**Checkpoint**: User Story 6 complete — developer can manage configuration

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T033 [P] Handle edge case: `warden init` on repo with zero commits in `warden/warden/core/orchestrator.py` — skip bootstrap analysis, create empty understanding docs with placeholder content, still install hook
- [ ] T034 [P] Handle edge case: large commits (hundreds of files) in `warden/warden/core/orchestrator.py` — truncate diff context if it exceeds a reasonable size limit before passing to agent; log warning about truncation
- [ ] T035 [P] Handle edge case: concurrent analyze runs in `warden/warden/core/state.py` — use SQLite file locking to prevent duplicate processing; if lock is held, exit gracefully with message "Analysis already in progress"
- [ ] T036 [P] Handle edge case: state.db deleted but understanding docs remain in `warden/warden/core/state.py` — on startup, if state.db missing but understanding dir exists, rebuild state from git log (mark all commits as understood based on changelog.md entries)
- [ ] T037 [P] Handle edge case: already-initialized repo re-init in `warden/warden/core/orchestrator.py` — detect existing `.warden/` and show error: "Warden is already initialized. Use 'warden reset --all' to start fresh."
- [ ] T038 [P] Implement error output formatting in `warden/warden/cli/commands.py` — all errors to stderr with `Error: <message>` format; support `WARDEN_DEBUG=1` env var for verbose logging to `.warden/debug.log`
- [ ] T039 Run quickstart.md validation — install package via `pip install -e .`, execute each quickstart step on a test repo, verify all commands work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Foundational
  - US2 (Phase 4): Depends on US1 (needs init + bootstrap docs to test incremental)
  - US3 (Phase 5): Depends on US1 + US2 (needs understanding docs for review context)
  - US4 (Phase 6): Depends on US1 (needs understanding docs for Q&A context)
  - US5 (Phase 7): Can start after Foundational (only needs state DB)
  - US6 (Phase 8): Can start after Foundational (only needs config module)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
Phase 2 (Foundational)
    │
    ├── US1 (Init/Bootstrap) ──┬── US2 (Incremental) ── US3 (Review)
    │                          │
    │                          └── US4 (Ask)
    │
    ├── US5 (Status/Reset) [independent]
    │
    └── US6 (Config) [independent]
         │
Phase 9 (Polish) ← all stories complete
```

### Within Each User Story

- Models before services
- Prompt construction before orchestrator flow
- Orchestrator flow before CLI command
- Core implementation before edge case handling

### Parallel Opportunities

- **Phase 2**: T004, T005, T006, T007, T008 can all run in parallel (different files); T009 depends on T006; T010 is independent
- **Phase 3-4**: US1 and US2 are sequential (US2 needs bootstrap docs)
- **Phase 5-6**: US5 and US6 can run in parallel with US1/US2 (different files, independent concerns)
- **Phase 5-6**: US4, US5, US6 can start in parallel after US1 completes
- **Within US5**: T028 and T029 can run in parallel (different functions/files)
- **Within US6**: T031 depends on T032

---

## Parallel Example: Foundational Phase

```bash
# These 5 tasks touch different files and can run simultaneously:
Task T004: "Pydantic config schema in warden/warden/models/config.py"
Task T005: "Config loader in warden/warden/core/config.py"
Task T006: "SQLAlchemy models in warden/warden/models/db.py"
Task T007: "Git operations in warden/warden/git/repo.py"
Task T008: "Git hooks in warden/warden/git/hooks.py"

# Then sequentially (depends on T006):
Task T009: "State manager in warden/warden/core/state.py"

# Independent (no file dependencies):
Task T010: "Agent runner in warden/warden/agents/runner.py"
```

## Parallel Example: After US1 Completes

```bash
# These stories can proceed in parallel (different concerns and files):
Story US2: "Incremental analysis — warden/warden/agents/understand.py (incremental), orchestrator analyze flow"
Story US4: "Ask agent — warden/warden/agents/ask.py, CLI ask command"
Story US5: "Status/reset — CLI status + reset commands, orchestrator reset flow"
Story US6: "Config — CLI config command, config validation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Init/Bootstrap)
4. **STOP and VALIDATE**: Run `warden init` on a real repo, inspect generated docs
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test `warden init` → MVP!
3. Add User Story 2 → Test `warden analyze` → Core loop complete
4. Add User Story 4 → Test `warden ask` → Knowledge accessible
5. Add User Story 3 → Test code review + draft PRs → Full automation
6. Add User Stories 5 + 6 → Test status/config/reset → Complete CLI
7. Polish → Edge cases, error handling, quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 → US2 → US3 (understand + review pipeline)
   - Developer B: US4 + US5 + US6 (ask + operations)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The `warden/warden/cli/commands.py` file is touched by multiple stories — work sequentially on CLI additions to avoid conflicts
