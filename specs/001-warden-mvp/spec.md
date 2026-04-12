# Feature Specification: Warden MVP — AI Agent for Continuous Codebase Vigilance

**Feature Branch**: `001-warden-mvp`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: User description: "Create a warden AI Agent for Continuous Codebase Vigilance based on the design spec"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize Warden on an Existing Repository (Priority: P1)

A solo developer discovers Warden and wants to quickly set it up on their existing project. They run a single initialization command in their repository root. Warden scans the full repository history — every commit and every merged pull request — and produces a set of living documentation files that capture the project's architecture, design decisions, and recurring patterns. The developer can immediately read these documents to verify Warden understands their codebase. Warden also installs a git hook so that future commits are automatically analyzed.

**Why this priority**: This is the entry point for every user. Without initialization, no other functionality is accessible. The bootstrap analysis is what delivers the "aha moment" — the developer sees that Warden already understands their codebase after a single command.

**Independent Test**: Can be fully tested by running the initialization command on any git repository with history and verifying that understanding documents are generated, a git hook is installed, and state tracking is set up.

**Acceptance Scenarios**:

1. **Given** a git repository with commit history, **When** the developer runs the initialization command, **Then** a `.warden/` directory is created with configuration, understanding documents (`architecture.md`, `design-decisions.md`, `patterns.md`), and a state database.
2. **Given** a git repository with merged pull requests on a GitHub remote, **When** the developer runs the initialization command, **Then** PR titles, descriptions, review comments, and inline code comments are incorporated into the understanding documents.
3. **Given** initialization has completed, **When** the developer inspects `.git/hooks/post-commit`, **Then** the hook contains a Warden analyze trigger that runs in the background without blocking commits.
4. **Given** a repository with no prior Warden setup, **When** the developer runs initialization, **Then** `.warden/state.db` is automatically added to `.gitignore`.
5. **Given** a repository with an existing post-commit hook, **When** the developer runs initialization, **Then** the Warden trigger is appended to the existing hook rather than overwriting it.

---

### User Story 2 - Incremental Commit Analysis (Priority: P1)

After initialization, the developer continues working normally. Each time they commit, Warden automatically analyzes the new commit in the background. It reads the diff, commit message, and any associated PR discussion, then updates the understanding documents with new information — appending rather than rewriting. If a commit reverses or changes a prior design decision, Warden notes the reversal explicitly. The developer never has to remember to run Warden; it stays up to date automatically.

**Why this priority**: This is the core ongoing value proposition. Without incremental analysis, the understanding documents become stale after the first initialization, and Warden provides no continuous value.

**Independent Test**: Can be tested by making a commit after initialization and verifying that understanding documents are updated with information from the new commit.

**Acceptance Scenarios**:

1. **Given** an initialized repository with processed commits, **When** the developer makes a new commit, **Then** the post-commit hook triggers background analysis without blocking the developer's workflow.
2. **Given** a new commit that changes an established pattern, **When** Warden processes that commit, **Then** the understanding documents note the change explicitly, including what was reversed and why (if discernible from the commit message or PR discussion).
3. **Given** multiple unprocessed commits exist, **When** the developer manually triggers analysis, **Then** all unprocessed commits are analyzed sequentially and the understanding documents reflect all changes.
4. **Given** a commit associated with a GitHub pull request, **When** Warden processes that commit, **Then** PR discussion (title, description, review comments) is incorporated into the understanding.
5. **Given** a commit that only modifies files matching ignore patterns (e.g., lock files, vendor directories), **When** Warden processes that commit, **Then** the commit is marked as processed but understanding documents are not updated with noise.

---

### User Story 3 - Code Review with Automated Fix PRs (Priority: P2)

When Warden processes a commit, it also reviews the changed code using the accumulated understanding as context. It looks for correctness issues (logic errors, edge cases, race conditions), inconsistencies with established patterns, contradictions of design decisions, and broken assumptions. For each issue it finds with high confidence, Warden creates a separate branch, applies the fix, pushes it, and opens a draft pull request. The developer reviews these draft PRs at their convenience — Warden never merges anything automatically.

**Why this priority**: Code review is a major differentiator from simple documentation tools. However, it depends on having understanding documents in place first (Stories 1 and 2), and incorrectly flagged issues erode trust quickly. Getting the understanding layer right first is essential.

**Independent Test**: Can be tested by introducing a known issue (e.g., an off-by-one error, a pattern inconsistency) in a commit and verifying that Warden creates a draft PR with the correct fix.

**Acceptance Scenarios**:

1. **Given** an initialized repository with understanding documents, **When** a commit introduces a logic error that contradicts established patterns, **Then** Warden creates a branch, applies a fix, and opens a draft PR describing the issue and rationale.
2. **Given** review is enabled and a commit has no issues, **When** Warden processes that commit, **Then** no draft PR is created and no false positives are reported.
3. **Given** the maximum number of open draft PRs has been reached, **When** Warden detects a new issue, **Then** it skips PR creation and logs the issue for later processing.
4. **Given** a draft PR exists from Warden, **When** the developer reviews it, **Then** the PR description clearly explains what issue was found, why it matters (citing the relevant design decision or pattern), and what was changed.
5. **Given** review is disabled in configuration, **When** Warden processes a commit, **Then** no review analysis is performed.

---

### User Story 4 - Ask Questions About the Codebase (Priority: P2)

The developer has a question about why certain code exists or how a design decision was made. Instead of digging through git history or old PR threads, they ask Warden directly using natural language. Warden reads the understanding documents and provides an answer that cites specific decisions, commits, and PRs. If the understanding documents don't contain the answer, Warden says so rather than guessing.

**Why this priority**: This completes the value loop — Warden not only watches the codebase but makes its knowledge accessible on demand. It's a high-value feature but depends on quality understanding documents from Stories 1 and 2.

**Independent Test**: Can be tested by asking a question about a known design decision and verifying the answer cites the correct source.

**Acceptance Scenarios**:

1. **Given** an initialized repository with understanding documents, **When** the developer asks "Why do we use SQLite for sessions?", **Then** Warden responds with the relevant design decision, citing the source PR or commit.
2. **Given** a question about something not covered in the understanding documents, **When** the developer asks that question, **Then** Warden responds with "I don't know" or equivalent rather than fabricating an answer.
3. **Given** a question about a recently reversed decision, **When** the developer asks about it, **Then** Warden's answer reflects the current state and notes the reversal history.

---

### User Story 5 - View Warden Status and Manage State (Priority: P3)

The developer wants to check how up-to-date Warden is — how many commits have been processed, when the last analysis ran, how large the understanding documents are, and whether there are pending draft PRs. They can also reset specific parts of Warden's state (understanding docs, improvements, or everything) to start fresh if needed.

**Why this priority**: This is an operational necessity for trust and debugging but doesn't deliver direct analytical value.

**Independent Test**: Can be tested by running the status command and verifying it displays accurate counts and dates, and by running reset commands and verifying the correct state is cleared.

**Acceptance Scenarios**:

1. **Given** an initialized repository, **When** the developer runs the status command, **Then** they see total commits processed, last run date, understanding document sizes, pending draft PRs, and improvement history.
2. **Given** an initialized repository, **When** the developer runs reset for understanding documents only, **Then** only the understanding directory is cleared while improvements and configuration are preserved.
3. **Given** an initialized repository, **When** the developer runs a full reset, **Then** all state, understanding documents, and improvement records are cleared, but configuration is preserved.

---

### User Story 6 - Configure Warden Behavior (Priority: P3)

The developer wants to customize Warden's behavior — for example, disabling automated reviews, limiting the number of open draft PRs, adjusting which files to ignore, or limiting how many commits are processed per run. They edit a configuration file or run a validation command to check their configuration for errors.

**Why this priority**: Configuration is important for adoption but sensible defaults mean most developers never need to touch it. This is a "nice to have" for power users.

**Independent Test**: Can be tested by modifying the configuration file and verifying Warden respects the changes.

**Acceptance Scenarios**:

1. **Given** a default configuration, **When** the developer runs Warden without changes, **Then** all features work with sensible defaults (reviews enabled, all PRs and commits processed at init, 5 max draft PRs, standard ignore patterns).
2. **Given** the developer sets `review.enabled` to false, **When** Warden processes a commit, **Then** no review analysis is performed.
3. **Given** the developer runs configuration validation, **When** the configuration has an error (e.g., invalid value), **Then** a clear error message identifies the problem.

---

### Edge Cases

- What happens when initialization is run on a repository with zero commits?
- How does Warden handle a commit that modifies hundreds of files (e.g., a large refactor or dependency update)?
- What happens if the GitHub remote is inaccessible when trying to read PR discussions?
- How does Warden handle running analysis while a previous analysis is still in progress?
- What happens if the developer manually edits the understanding documents — does the next analysis respect or overwrite those edits?
- What happens if `.warden/state.db` is deleted but understanding documents remain?
- How does Warden handle merge commits vs. regular commits?
- What happens when `warden init` is run on an already-initialized repository?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a `.warden/` directory structure on initialization containing configuration, understanding documents, and state tracking
- **FR-002**: System MUST read all commits in repository history during bootstrap initialization and produce three understanding documents: architecture overview, design decisions, and patterns/conventions
- **FR-003**: System MUST read merged PR discussions (titles, descriptions, review comments, inline code comments) during bootstrap initialization when a GitHub remote is accessible
- **FR-004**: System MUST install a post-commit git hook that triggers background analysis without blocking the developer's commit flow
- **FR-005**: System MUST append the hook to existing post-commit hooks rather than overwriting them
- **FR-006**: System MUST add the state database file to `.gitignore` during initialization
- **FR-007**: System MUST process new commits incrementally by reading the diff, commit message, and associated PR discussion (if any), then appending new information to existing understanding documents
- **FR-008**: System MUST note decision reversals explicitly when a commit changes a prior design decision
- **FR-009**: System MUST track which commits have been processed to avoid duplicate analysis
- **FR-010**: System MUST skip analysis of files matching configured ignore patterns (lock files, vendor directories, environment files)
- **FR-011**: System MUST review changed code for correctness, consistency with established patterns, design coherence, and broken assumptions when review is enabled
- **FR-012**: System MUST create a separate branch and draft PR for each issue found during review, including a description of the issue, its rationale, and the fix applied
- **FR-013**: System MUST respect a configurable maximum number of concurrent open draft PRs
- **FR-014**: System MUST only report issues with high confidence — no speculative or low-certainty findings
- **FR-015**: System MUST answer natural language questions using the understanding documents as context, citing specific decisions, commits, and PRs
- **FR-016**: System MUST respond with "I don't know" when the understanding documents do not contain enough information to answer a question
- **FR-017**: System MUST display status information including commits processed, last run date, document sizes, pending draft PRs, and improvement history
- **FR-018**: System MUST support selective reset of understanding documents, improvements, or all state
- **FR-019**: System MUST support user-editable configuration with sensible defaults that require zero configuration for basic usage
- **FR-020**: System MUST validate configuration and report clear error messages for invalid values
- **FR-021**: System MUST support limiting the number of commits and PRs processed during bootstrap via configuration or command-line flags (CLI flags override configuration)
- **FR-022**: System MUST support a maximum commits per run limit for incremental analysis
- **FR-023**: Understanding documents MUST be human-readable, editable, and committed to version control as the source of truth

### Key Entities

- **Understanding Document**: A human-readable markdown file capturing a specific dimension of codebase knowledge (architecture, design decisions, or patterns). Editable by the developer. Serves as context for all agent reasoning.
- **Commit Record**: A tracked unit of work representing a single processed commit, with metadata about which analysis phases (understand, review) have been completed.
- **Review Finding**: An issue detected during code review, associated with a specific commit, categorized by type (correctness, consistency, design, assumptions), and linked to a draft PR if one was created.
- **Configuration**: User-specified settings controlling Warden's behavior, with defaults that enable zero-config usage.
- **Improvement**: A tracked suggestion from Warden, with lifecycle states (pending, accepted, declined) and an optional link to a draft PR.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can set up Warden on an existing repository and have understanding documents generated in a single command, with no additional configuration required
- **SC-002**: Understanding documents produced during initialization accurately reflect the repository's architecture, key design decisions, and recurring patterns as validated by the developer
- **SC-003**: After each commit, understanding documents are updated within a reasonable time without requiring any manual action from the developer
- **SC-004**: Code review findings are high-confidence — at least 80% of draft PRs created by Warden address genuine issues as judged by the developer
- **SC-005**: Answers to natural language questions cite specific decisions, commits, or PRs, and the developer can verify the citations against the actual history
- **SC-006**: Warden never blocks or slows down the developer's commit flow — git operations complete at normal speed regardless of Warden's analysis state
- **SC-007**: A developer new to Warden can install and run their first initialization in under one minute
- **SC-008**: Understanding documents remain accurate over time — after 50+ incremental updates, the documents are still coherent, non-redundant, and correctly reflect the current state of the codebase
- **SC-009**: When a decision is reversed, the developer can query Warden and get both the current state and the reversal history

## Assumptions

- The target user is a solo developer working on a single repository with git version control
- The repository is hosted on GitHub when PR discussion features are used; PR reading gracefully degrades if no GitHub remote is available
- The developer has an existing authentication setup for the AI service (no API key management is in scope)
- The `gh` CLI is available on the developer's system for GitHub operations (PR reading, PR creation)
- Understanding documents are intended to be committed to version control and are the source of truth — the state database is an index that can be rebuilt
- The post-commit hook runs analysis in the background; if the system is interrupted, unprocessed commits will be picked up on the next manual or automatic run
- Mobile and web interfaces are out of scope — this is a CLI-only tool
- Multi-repository support is out of scope for this version
- Notification integrations (Slack, email) are out of scope for this version
- Background daemon mode is out of scope — analysis is triggered by git hooks or manual CLI invocation
- The developer may manually edit understanding documents to correct Warden; subsequent analyses should respect and build upon those edits rather than overwriting them
