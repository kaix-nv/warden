# Data Model: Warden MVP

**Date**: 2026-04-12
**Feature**: [spec.md](./spec.md)

## Entities

### CommitRecord

Tracks processing state for each commit analyzed by Warden.

| Field | Type | Description |
| ----- | ---- | ----------- |
| hash | string (PK) | Git commit SHA |
| timestamp | datetime | Commit timestamp |
| files_changed | string (JSON list) | Paths of files changed in this commit |
| understand_done | boolean | Whether UnderstandAgent has processed this commit |
| review_done | boolean | Whether ReviewAgent has processed this commit |

**Constraints**:
- `hash` is unique and immutable
- `understand_done` defaults to false; set to true after UnderstandAgent completes
- `review_done` defaults to false; set to true after ReviewAgent completes (or if review is disabled)

**State transitions**: `(false, false)` -> `(true, false)` -> `(true, true)`

---

### Decision

Index entry for a design decision extracted from understanding docs. Used for quick lookups; the markdown doc is the source of truth.

| Field | Type | Description |
| ----- | ---- | ----------- |
| id | integer (PK) | Auto-increment |
| commit_hash | string (FK -> CommitRecord) | Commit where this decision was identified |
| file_path | string (nullable) | File most relevant to this decision |
| summary | string | One-line summary of the decision |
| category | enum | One of: architecture, design, pattern |
| created_at | datetime | When this index entry was created |

**Constraints**:
- `category` is restricted to `architecture`, `design`, `pattern`
- `summary` is non-empty
- `commit_hash` references a valid CommitRecord

---

### Review

Tracks code review findings and their lifecycle.

| Field | Type | Description |
| ----- | ---- | ----------- |
| id | integer (PK) | Auto-increment |
| commit_hash | string (FK -> CommitRecord) | Commit that triggered this review finding |
| issue_type | enum | One of: correctness, consistency, design, assumptions |
| description | string | Human-readable description of the issue |
| status | enum | One of: pending, accepted, declined |
| pr_url | string (nullable) | URL of the draft PR if one was created |
| branch_name | string (nullable) | Name of the fix branch |
| created_at | datetime | When this finding was created |

**Constraints**:
- `issue_type` is restricted to the four categories
- `status` defaults to `pending`
- `pr_url` is null until a draft PR is successfully created
- `description` is non-empty

**State transitions**: `pending` -> `accepted` | `declined`

---

### Configuration (file-based, not in DB)

Stored as `.warden/config.yml`. Validated on load.

| Section | Field | Type | Default | Description |
| ------- | ----- | ---- | ------- | ----------- |
| understanding.bootstrap | pr_count | string or int | "all" | How many merged PRs to process at init |
| understanding.bootstrap | commit_count | string or int | "all" | How many commits to process at init |
| understanding.incremental | include_pr_comments | boolean | true | Fetch PR discussion for each commit |
| review | enabled | boolean | true | Whether to run ReviewAgent |
| review | max_draft_prs | integer | 5 | Max concurrent open draft PRs |
| review | auto_push | boolean | true | Push branch and create PR automatically |
| git | ignore_patterns | list of strings | ["*.lock", "node_modules/**", ".env*", "vendor/**"] | File patterns to skip |
| git | branch_prefix | string | "warden/" | Prefix for fix branches |
| resources | max_commits_per_run | integer | 20 | Max commits to process in one run |

**Validation rules**:
- `max_draft_prs` must be > 0
- `max_commits_per_run` must be > 0
- `pr_count` and `commit_count` must be "all" or a positive integer
- `ignore_patterns` must be valid glob patterns
- Unknown keys are rejected (catch typos)

---

### Understanding Documents (file-based, source of truth)

Three markdown files in `.warden/understanding/`:

| Document | Purpose | Updated by |
| -------- | ------- | ---------- |
| architecture.md | Component map, dependencies, data flow | UnderstandAgent |
| design-decisions.md | Why things were built the way they are | UnderstandAgent |
| patterns.md | Recurring patterns and conventions | UnderstandAgent |

**Constraints**:
- Human-editable; agents must respect manual edits
- Incremental updates append; they do not rewrite
- Decision reversals are noted explicitly with before/after context

---

## Entity Relationships

```
CommitRecord 1--* Decision    (a commit may surface multiple decisions)
CommitRecord 1--* Review      (a commit may have multiple review findings)
Configuration --reads--> all agents
Understanding Docs --context--> ReviewAgent, AskAgent
CommitRecord --input--> UnderstandAgent (diff + message)
```

## Changelog Document

In addition to the three understanding docs, a `changelog.md` in `.warden/understanding/` tracks what Warden learned per commit:

| Field | Description |
| ----- | ----------- |
| commit_hash | SHA of the processed commit |
| date | Commit date |
| summary | What Warden learned from this commit |
| docs_updated | Which understanding docs were modified |
