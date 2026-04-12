# Warden MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that maintains persistent understanding of a codebase by analyzing commits and PR discussions via Claude Code CLI, and reviews code changes for correctness and consistency.

**Architecture:** Warden is a Python CLI (Typer) that orchestrates when to analyze code. It manages state in SQLite and understanding docs in markdown. For all AI reasoning, it shells out to `claude -p` as a subprocess. Three agent prompts: UnderstandAgent (build/update understanding), ReviewAgent (review code changes), AskAgent (answer questions).

**Tech Stack:** Python 3.12, Typer, Pydantic v2, SQLAlchemy 2.0, SQLite, GitPython, PyYAML, pytest

---

## File Structure

```
warden/
├── warden/
│   ├── __init__.py              # Package version
│   ├── cli.py                   # Typer CLI (init, analyze, ask, status, config, reset)
│   ├── config.py                # Pydantic config model + YAML loading
│   ├── state.py                 # SQLAlchemy models + state manager
│   ├── orchestrator.py          # Workflow logic (init, analyze, ask)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── runner.py            # Subprocess wrapper for `claude -p`
│   │   ├── context.py           # Shared: load understanding docs from markdown
│   │   ├── understand.py        # UnderstandAgent prompt construction
│   │   ├── review.py            # ReviewAgent prompt construction
│   │   └── ask.py               # AskAgent prompt construction
│   └── git/
│       ├── __init__.py
│       ├── hooks.py             # Post-commit hook installation
│       └── repo.py              # Git operations (commits, diffs)
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures (temp git repos, etc.)
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_git_repo.py
│   ├── test_git_hooks.py
│   ├── test_agent_runner.py
│   ├── test_understand.py
│   ├── test_review.py
│   ├── test_ask.py
│   ├── test_orchestrator.py
│   └── test_cli.py
├── pyproject.toml
└── README.md
```

**Key simplifications from the spec:**
- Flattened `core/` and `models/` into top-level modules — no need for nested directories with one file each
- Config model and YAML loading live in one file (`config.py`)
- SQLAlchemy models and state manager live in one file (`state.py`)

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `warden/__init__.py`
- Create: `warden/cli.py`
- Create: `warden/agents/__init__.py`
- Create: `warden/git/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "warden"
version = "0.1.0"
description = "AI Agent for Continuous Codebase Vigilance"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "typer>=0.9.0",
    "pydantic>=2.0",
    "sqlalchemy>=2.0",
    "gitpython>=3.1",
    "pyyaml>=6.0",
]

[project.scripts]
warden = "warden.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package structure**

`warden/__init__.py`:
```python
__version__ = "0.1.0"
```

`warden/cli.py`:
```python
import typer

app = typer.Typer(help="Warden - AI Agent for Continuous Codebase Vigilance")


@app.command()
def init():
    """Initialize Warden in the current repository."""
    typer.echo("warden init - not yet implemented")


@app.command()
def analyze(commit: str | None = None):
    """Analyze new commits since last run."""
    typer.echo("warden analyze - not yet implemented")


@app.command()
def ask(question: str):
    """Ask a question about the codebase."""
    typer.echo("warden ask - not yet implemented")


@app.command()
def status():
    """Show Warden status."""
    typer.echo("warden status - not yet implemented")
```

`warden/agents/__init__.py`:
```python
```

`warden/git/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
import os
import tempfile
from pathlib import Path

import pytest
from git import Repo


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary git repository with one commit."""
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return tmp_path, repo
```

- [ ] **Step 3: Install dependencies and verify**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pip install -e ".[dev]" 2>&1 | tail -3`

If `[dev]` isn't defined yet, run: `pip install -e . && pip install pytest`

- [ ] **Step 4: Verify CLI entry point works**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && python -m warden.cli --help`
Expected: Shows help text with init, analyze, ask, status commands

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml warden/ tests/
git commit -m "feat: project scaffolding with CLI skeleton"
```

---

## Task 2: Config Model

**Files:**
- Create: `warden/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
from pathlib import Path

from warden.config import WardenConfig, load_config


def test_default_config():
    """Default config has sensible values without any YAML file."""
    config = WardenConfig()
    assert config.understanding.bootstrap.pr_count is None  # None means "all"
    assert config.understanding.bootstrap.commit_count is None
    assert config.understanding.incremental.include_pr_comments is True
    assert config.review.enabled is True
    assert config.review.max_draft_prs == 5
    assert config.review.auto_push is True
    assert config.git.ignore_patterns == ["*.lock", "node_modules/**", ".env*", "vendor/**"]
    assert config.git.branch_prefix == "warden/"
    assert config.resources.max_commits_per_run == 20


def test_load_config_from_yaml(tmp_path):
    """Config loads from a YAML file and overrides defaults."""
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "review:\n"
        "  enabled: false\n"
        "  max_draft_prs: 3\n"
        "resources:\n"
        "  max_commits_per_run: 50\n"
    )
    config = load_config(config_path)
    assert config.review.enabled is False
    assert config.review.max_draft_prs == 3
    assert config.resources.max_commits_per_run == 50
    # Defaults still apply for unset values
    assert config.understanding.incremental.include_pr_comments is True


def test_load_config_missing_file(tmp_path):
    """Missing config file returns defaults."""
    config = load_config(tmp_path / "nonexistent.yml")
    assert config == WardenConfig()


def test_generate_default_config():
    """Default config serializes to valid YAML."""
    config = WardenConfig()
    yaml_str = config.to_yaml()
    assert "review:" in yaml_str
    assert "understanding:" in yaml_str
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_config.py -v`
Expected: FAIL with ImportError (config module doesn't exist)

- [ ] **Step 3: Write implementation**

`warden/config.py`:
```python
from pathlib import Path

import yaml
from pydantic import BaseModel


class BootstrapConfig(BaseModel):
    pr_count: int | None = None  # None means "all"
    commit_count: int | None = None


class IncrementalConfig(BaseModel):
    include_pr_comments: bool = True


class UnderstandingConfig(BaseModel):
    bootstrap: BootstrapConfig = BootstrapConfig()
    incremental: IncrementalConfig = IncrementalConfig()


class ReviewConfig(BaseModel):
    enabled: bool = True
    max_draft_prs: int = 5
    auto_push: bool = True


class GitConfig(BaseModel):
    ignore_patterns: list[str] = [
        "*.lock",
        "node_modules/**",
        ".env*",
        "vendor/**",
    ]
    branch_prefix: str = "warden/"


class ResourcesConfig(BaseModel):
    max_commits_per_run: int = 20


class WardenConfig(BaseModel):
    understanding: UnderstandingConfig = UnderstandingConfig()
    review: ReviewConfig = ReviewConfig()
    git: GitConfig = GitConfig()
    resources: ResourcesConfig = ResourcesConfig()

    def to_yaml(self) -> str:
        return yaml.dump(
            self.model_dump(),
            default_flow_style=False,
            sort_keys=False,
        )


def load_config(path: Path) -> WardenConfig:
    if not path.exists():
        return WardenConfig()
    raw = yaml.safe_load(path.read_text()) or {}
    return WardenConfig(**raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/config.py tests/test_config.py
git commit -m "feat: config model with YAML loading and defaults"
```

---

## Task 3: SQLite State Manager

**Files:**
- Create: `warden/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

`tests/test_state.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from warden.state import StateManager


@pytest.fixture
def state_mgr(tmp_path):
    db_path = tmp_path / "state.db"
    mgr = StateManager(db_path)
    mgr.initialize()
    return mgr


def test_initialize_creates_db(tmp_path):
    db_path = tmp_path / "state.db"
    mgr = StateManager(db_path)
    mgr.initialize()
    assert db_path.exists()


def test_record_and_get_commit(state_mgr):
    state_mgr.record_commit(
        hash="abc123",
        timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
        files_changed=["api/orders.py", "api/users.py"],
    )
    commit = state_mgr.get_commit("abc123")
    assert commit is not None
    assert commit["hash"] == "abc123"
    assert commit["files_changed"] == ["api/orders.py", "api/users.py"]
    assert commit["understand_done"] is False
    assert commit["review_done"] is False


def test_mark_commit_understood(state_mgr):
    state_mgr.record_commit("abc123", datetime.now(timezone.utc), ["file.py"])
    state_mgr.mark_commit_understood("abc123")
    commit = state_mgr.get_commit("abc123")
    assert commit["understand_done"] is True


def test_mark_commit_reviewed(state_mgr):
    state_mgr.record_commit("abc123", datetime.now(timezone.utc), ["file.py"])
    state_mgr.mark_commit_reviewed("abc123")
    commit = state_mgr.get_commit("abc123")
    assert commit["review_done"] is True


def test_get_last_processed_commit(state_mgr):
    assert state_mgr.get_last_processed_hash() is None
    state_mgr.record_commit("aaa", datetime(2024, 1, 1, tzinfo=timezone.utc), [])
    state_mgr.record_commit("bbb", datetime(2024, 1, 2, tzinfo=timezone.utc), [])
    assert state_mgr.get_last_processed_hash() == "bbb"


def test_record_review(state_mgr):
    state_mgr.record_review(
        commit_hash="abc123",
        issue_type="correctness",
        description="Off-by-one in loop boundary",
        pr_url="https://github.com/user/repo/pull/1",
    )
    reviews = state_mgr.get_reviews(status="pending")
    assert len(reviews) == 1
    assert reviews[0]["issue_type"] == "correctness"
    assert reviews[0]["status"] == "pending"


def test_update_review_status(state_mgr):
    state_mgr.record_review("abc123", "consistency", "Inconsistent naming", None)
    reviews = state_mgr.get_reviews(status="pending")
    state_mgr.update_review_status(reviews[0]["id"], "accepted")
    updated = state_mgr.get_reviews(status="accepted")
    assert len(updated) == 1


def test_get_stats(state_mgr):
    state_mgr.record_commit("aaa", datetime.now(timezone.utc), ["a.py"])
    state_mgr.record_commit("bbb", datetime.now(timezone.utc), ["b.py"])
    state_mgr.mark_commit_understood("aaa")
    state_mgr.record_review("aaa", "correctness", "Bug", None)
    stats = state_mgr.get_stats()
    assert stats["commits_total"] == 2
    assert stats["commits_understood"] == 1
    assert stats["reviews_pending"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_state.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/state.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class CommitRecord(Base):
    __tablename__ = "commits_processed"

    hash = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    files_changed = Column(Text, nullable=False, default="[]")
    understand_done = Column(Boolean, nullable=False, default=False)
    review_done = Column(Boolean, nullable=False, default=False)


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_hash = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    pr_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class StateManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def initialize(self):
        Base.metadata.create_all(self.engine)

    def record_commit(
        self,
        hash: str,
        timestamp: datetime,
        files_changed: list[str],
    ):
        with Session(self.engine) as session:
            record = CommitRecord(
                hash=hash,
                timestamp=timestamp,
                files_changed=json.dumps(files_changed),
            )
            session.add(record)
            session.commit()

    def get_commit(self, hash: str) -> dict | None:
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            if record is None:
                return None
            return {
                "hash": record.hash,
                "timestamp": record.timestamp,
                "files_changed": json.loads(record.files_changed),
                "understand_done": record.understand_done,
                "review_done": record.review_done,
            }

    def mark_commit_understood(self, hash: str):
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            record.understand_done = True
            session.commit()

    def mark_commit_reviewed(self, hash: str):
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            record.review_done = True
            session.commit()

    def get_last_processed_hash(self) -> str | None:
        with Session(self.engine) as session:
            record = (
                session.query(CommitRecord)
                .order_by(CommitRecord.timestamp.desc())
                .first()
            )
            return record.hash if record else None

    def record_review(
        self,
        commit_hash: str,
        issue_type: str,
        description: str,
        pr_url: str | None,
    ):
        with Session(self.engine) as session:
            record = ReviewRecord(
                commit_hash=commit_hash,
                issue_type=issue_type,
                description=description,
                pr_url=pr_url,
            )
            session.add(record)
            session.commit()

    def get_reviews(self, status: str | None = None) -> list[dict]:
        with Session(self.engine) as session:
            query = session.query(ReviewRecord)
            if status:
                query = query.filter(ReviewRecord.status == status)
            return [
                {
                    "id": r.id,
                    "commit_hash": r.commit_hash,
                    "issue_type": r.issue_type,
                    "description": r.description,
                    "status": r.status,
                    "pr_url": r.pr_url,
                    "created_at": r.created_at,
                }
                for r in query.all()
            ]

    def update_review_status(self, review_id: int, status: str):
        with Session(self.engine) as session:
            record = session.get(ReviewRecord, review_id)
            record.status = status
            session.commit()

    def get_stats(self) -> dict:
        with Session(self.engine) as session:
            total = session.query(CommitRecord).count()
            understood = (
                session.query(CommitRecord)
                .filter(CommitRecord.understand_done == True)
                .count()
            )
            pending = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "pending")
                .count()
            )
            accepted = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "accepted")
                .count()
            )
            declined = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "declined")
                .count()
            )
            return {
                "commits_total": total,
                "commits_understood": understood,
                "reviews_pending": pending,
                "reviews_accepted": accepted,
                "reviews_declined": declined,
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_state.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/state.py tests/test_state.py
git commit -m "feat: SQLite state manager for commits and reviews"
```

---

## Task 4: Git Repository Operations

**Files:**
- Create: `warden/git/repo.py`
- Create: `tests/test_git_repo.py`

- [ ] **Step 1: Write the failing test**

`tests/test_git_repo.py`:
```python
from pathlib import Path

import pytest

from warden.git.repo import GitRepo


def test_get_all_commits(tmp_repo):
    repo_path, repo = tmp_repo

    # Add a second commit
    (repo_path / "file.py").write_text("print('hello')\n")
    repo.index.add(["file.py"])
    repo.index.commit("Add file.py")

    git_repo = GitRepo(repo_path)
    commits = git_repo.get_all_commits()
    assert len(commits) == 2
    assert commits[0]["message"] == "Add file.py"
    assert commits[1]["message"] == "Initial commit"


def test_get_commits_since(tmp_repo):
    repo_path, repo = tmp_repo
    first_hash = repo.head.commit.hexsha

    (repo_path / "a.py").write_text("a\n")
    repo.index.add(["a.py"])
    repo.index.commit("Add a")

    (repo_path / "b.py").write_text("b\n")
    repo.index.add(["b.py"])
    repo.index.commit("Add b")

    git_repo = GitRepo(repo_path)
    commits = git_repo.get_commits_since(first_hash)
    assert len(commits) == 2
    assert commits[0]["message"] == "Add b"
    assert commits[1]["message"] == "Add a"


def test_get_commit_diff(tmp_repo):
    repo_path, repo = tmp_repo

    (repo_path / "file.py").write_text("print('hello')\n")
    repo.index.add(["file.py"])
    commit = repo.index.commit("Add file.py")

    git_repo = GitRepo(repo_path)
    diff = git_repo.get_commit_diff(commit.hexsha)
    assert "file.py" in diff
    assert "hello" in diff


def test_get_commit_files(tmp_repo):
    repo_path, repo = tmp_repo

    (repo_path / "a.py").write_text("a\n")
    (repo_path / "b.py").write_text("b\n")
    repo.index.add(["a.py", "b.py"])
    commit = repo.index.commit("Add files")

    git_repo = GitRepo(repo_path)
    files = git_repo.get_commit_files(commit.hexsha)
    assert set(files) == {"a.py", "b.py"}


def test_get_current_branch(tmp_repo):
    repo_path, repo = tmp_repo
    git_repo = GitRepo(repo_path)
    assert git_repo.get_current_branch() in ("main", "master")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_git_repo.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/git/repo.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

from git import Repo


class GitRepo:
    def __init__(self, path: Path):
        self.path = path
        self.repo = Repo(path)

    def get_all_commits(self) -> list[dict]:
        """Return all commits, newest first."""
        commits = []
        for commit in self.repo.iter_commits():
            commits.append(self._commit_to_dict(commit))
        return commits

    def get_commits_since(self, since_hash: str) -> list[dict]:
        """Return commits after the given hash, newest first."""
        commits = []
        for commit in self.repo.iter_commits():
            if commit.hexsha == since_hash:
                break
            commits.append(self._commit_to_dict(commit))
        return commits

    def get_commit_diff(self, commit_hash: str) -> str:
        """Return the unified diff for a commit."""
        commit = self.repo.commit(commit_hash)
        if commit.parents:
            return commit.parents[0].diff(commit, create_patch=True, unified=3).__str__()
        # First commit — diff against empty tree
        return commit.diff(None, create_patch=True).__str__()

    def get_commit_files(self, commit_hash: str) -> list[str]:
        """Return list of files changed in a commit."""
        commit = self.repo.commit(commit_hash)
        if commit.parents:
            diffs = commit.parents[0].diff(commit)
        else:
            diffs = commit.diff(None)
        return [d.b_path or d.a_path for d in diffs]

    def get_current_branch(self) -> str:
        return self.repo.active_branch.name

    def _commit_to_dict(self, commit) -> dict:
        return {
            "hash": commit.hexsha,
            "message": commit.message.strip(),
            "author": str(commit.author),
            "timestamp": commit.committed_datetime,
            "files": self.get_commit_files(commit.hexsha),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_git_repo.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/git/repo.py tests/test_git_repo.py
git commit -m "feat: git repo wrapper for commits and diffs"
```

---

## Task 5: Agent Runner (Claude Code Subprocess)

**Files:**
- Create: `warden/agents/runner.py`
- Create: `tests/test_agent_runner.py`

- [ ] **Step 1: Write the failing test**

`tests/test_agent_runner.py`:
```python
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from warden.agents.runner import AgentRunner, AgentError


def test_run_returns_stdout():
    """AgentRunner captures claude -p stdout."""
    runner = AgentRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="Claude's response here",
            stderr="",
            returncode=0,
        )
        result = runner.run("Analyze this code")
        assert result == "Claude's response here"
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert "claude" in args[0][0]
        assert "-p" in args[0][0]


def test_run_with_working_directory(tmp_path):
    """AgentRunner passes cwd to subprocess."""
    runner = AgentRunner(cwd=tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test")
        assert mock_run.call_args.kwargs["cwd"] == tmp_path


def test_run_raises_on_failure():
    """AgentRunner raises AgentError on non-zero exit."""
    runner = AgentRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Error: something went wrong",
            returncode=1,
        )
        with pytest.raises(AgentError, match="something went wrong"):
            runner.run("bad prompt")


def test_run_with_max_turns():
    """AgentRunner passes --max-turns flag."""
    runner = AgentRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test", max_turns=5)
        cmd = mock_run.call_args[0][0]
        assert "--max-turns" in cmd
        assert "5" in cmd


def test_run_with_allowed_tools():
    """AgentRunner passes --allowedTools flag."""
    runner = AgentRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        runner.run("test", allowed_tools=["Read", "Grep", "Glob"])
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_agent_runner.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/agents/runner.py`:
```python
import subprocess
from pathlib import Path


class AgentError(Exception):
    pass


class AgentRunner:
    def __init__(self, cwd: Path | None = None):
        self.cwd = cwd

    def run(
        self,
        prompt: str,
        max_turns: int | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        cmd = ["claude", "-p", prompt, "--output-format", "text"]

        if max_turns is not None:
            cmd.extend(["--max-turns", str(max_turns)])

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.cwd,
        )

        if result.returncode != 0:
            raise AgentError(result.stderr.strip() or f"claude exited with code {result.returncode}")

        return result.stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_agent_runner.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/agents/runner.py tests/test_agent_runner.py
git commit -m "feat: agent runner wrapping claude -p subprocess"
```

---

## Task 6: Shared Agent Context

**Files:**
- Create: `warden/agents/context.py`
- Create: `tests/test_agent_context.py`

All three agents need to load understanding docs from `.warden/understanding/`. Extract this into a shared module.

- [ ] **Step 1: Write the failing test**

`tests/test_agent_context.py`:
```python
from pathlib import Path

from warden.agents.context import load_understanding

UNDERSTANDING_DOCS = ["architecture.md", "design-decisions.md", "patterns.md"]


def test_load_understanding_empty_dir(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    result = load_understanding(understanding_dir)
    assert result == ""


def test_load_understanding_with_docs(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "architecture.md").write_text("# Architecture\nMicroservices.\n")
    (understanding_dir / "design-decisions.md").write_text("# Decisions\nUse SQLite.\n")

    result = load_understanding(understanding_dir)
    assert "Microservices" in result
    assert "Use SQLite" in result


def test_load_understanding_skips_empty_files(tmp_path):
    understanding_dir = tmp_path / "understanding"
    understanding_dir.mkdir()
    (understanding_dir / "architecture.md").write_text("")
    (understanding_dir / "patterns.md").write_text("# Patterns\nSome pattern.\n")

    result = load_understanding(understanding_dir)
    assert "architecture" not in result.lower()
    assert "Some pattern" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_agent_context.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/agents/context.py`:
```python
from pathlib import Path

UNDERSTANDING_DOCS = ["architecture.md", "design-decisions.md", "patterns.md"]


def load_understanding(understanding_dir: Path) -> str:
    """Load all understanding docs as a single string for prompt context."""
    parts = []
    for doc_name in UNDERSTANDING_DOCS:
        doc_path = understanding_dir / doc_name
        if doc_path.exists():
            content = doc_path.read_text().strip()
            if content:
                parts.append(f"### {doc_name}\n\n{content}")
    return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_agent_context.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/agents/context.py tests/test_agent_context.py
git commit -m "feat: shared context loader for understanding docs"
```

---

## Task 7: UnderstandAgent

**Files:**
- Create: `warden/agents/understand.py`
- Create: `tests/test_understand.py`

- [ ] **Step 1: Write the failing test**

`tests/test_understand.py`:
```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from warden.agents.understand import UnderstandAgent


@pytest.fixture
def mock_runner():
    return MagicMock()


@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    return tmp_path / ".warden"


def test_bootstrap_prompt_includes_voice(mock_runner, warden_dir):
    """Bootstrap prompt tells the agent to write as a senior engineer."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "senior engineer briefing a new hire" in prompt


def test_bootstrap_prompt_asks_for_three_docs(mock_runner, warden_dir):
    """Bootstrap prompt requests architecture.md, design-decisions.md, patterns.md."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "architecture.md" in prompt
    assert "design-decisions.md" in prompt
    assert "patterns.md" in prompt


def test_bootstrap_reads_full_history(mock_runner, warden_dir):
    """Bootstrap prompt instructs reading ALL commits and merged PRs."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap()
    prompt = mock_runner.run.call_args[0][0]
    assert "ALL" in prompt or "all" in prompt.lower()
    assert "commit" in prompt.lower()
    assert "merged PR" in prompt.lower() or "merged pr" in prompt.lower()


def test_bootstrap_with_pr_limit(mock_runner, warden_dir):
    """Bootstrap respects pr_count limit."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap(pr_count=50)
    prompt = mock_runner.run.call_args[0][0]
    assert "50" in prompt


def test_bootstrap_with_commit_limit(mock_runner, warden_dir):
    """Bootstrap respects commit_count limit."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"
    agent.bootstrap(commit_count=100)
    prompt = mock_runner.run.call_args[0][0]
    assert "100" in prompt


def test_incremental_prompt_includes_diff(mock_runner, warden_dir):
    """Incremental prompt includes commit info."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"

    commit_info = {
        "hash": "abc123",
        "message": "Optimize query",
        "diff": "- old_code\n+ new_code",
    }
    agent.incremental(commit_info)
    prompt = mock_runner.run.call_args[0][0]
    assert "abc123" in prompt
    assert "Optimize query" in prompt


def test_incremental_prompt_includes_existing_docs(mock_runner, warden_dir):
    """Incremental prompt feeds existing understanding docs as context."""
    (warden_dir / "understanding" / "architecture.md").write_text("# Architecture\nUses microservices.\n")
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"

    agent.incremental({"hash": "abc123", "message": "test", "diff": "diff"})
    prompt = mock_runner.run.call_args[0][0]
    assert "Uses microservices" in prompt


def test_incremental_tells_agent_to_append(mock_runner, warden_dir):
    """Incremental prompt says append, don't rewrite."""
    agent = UnderstandAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "done"

    agent.incremental({"hash": "abc123", "message": "test", "diff": "diff"})
    prompt = mock_runner.run.call_args[0][0]
    assert "append" in prompt.lower() or "don't rewrite" in prompt.lower() or "do not rewrite" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_understand.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/agents/understand.py`:
```python
from pathlib import Path

from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class UnderstandAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def bootstrap(
        self,
        pr_count: int | None = None,
        commit_count: int | None = None,
    ) -> str:
        pr_instruction = (
            f"Read the last {pr_count} merged PRs"
            if pr_count
            else "Read ALL merged PRs"
        )
        commit_instruction = (
            f"Read the last {commit_count} commits"
            if commit_count
            else "Read ALL commits (use `git log`)"
        )

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
            prompt += (
                "Here are the existing understanding docs:\n\n"
                f"{existing_docs}\n\n"
            )

        prompt += (
            "Update the understanding docs in "
            f"`{self.understanding_dir}/`.\n\n"
            "Rules:\n"
            "- Append new information. Do not rewrite or restate what's already there.\n"
            "- If this commit reverses a prior decision, note the reversal explicitly.\n"
            "- If no meaningful design information is in this commit, make no changes.\n"
            "- Write as a senior engineer briefing a new hire."
        )

        return self.runner.run(prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_understand.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/agents/understand.py tests/test_understand.py
git commit -m "feat: UnderstandAgent with bootstrap and incremental prompts"
```

---

## Task 8: ReviewAgent

**Files:**
- Create: `warden/agents/review.py`
- Create: `tests/test_review.py`

- [ ] **Step 1: Write the failing test**

`tests/test_review.py`:
```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from warden.agents.review import ReviewAgent


@pytest.fixture
def mock_runner():
    return MagicMock()


@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    (understanding / "design-decisions.md").write_text(
        "# Design Decisions\n\n## Use async for all I/O\n- Rationale: performance\n"
    )
    (understanding / "patterns.md").write_text(
        "# Patterns\n\n## All handlers return Result types\n"
    )
    return tmp_path / ".warden"


def test_review_prompt_includes_understanding_context(mock_runner, warden_dir):
    """Review prompt feeds understanding docs for design context."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."

    agent.review(
        commit_hash="abc123",
        diff="+ sync_call()",
        changed_files=["api/handler.py"],
    )
    prompt = mock_runner.run.call_args[0][0]
    assert "async for all I/O" in prompt
    assert "Result types" in prompt


def test_review_prompt_focuses_on_correctness(mock_runner, warden_dir):
    """Review prompt asks for correctness, consistency, design coherence."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."

    agent.review("abc123", "diff", ["file.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "correctness" in prompt.lower()
    assert "consistency" in prompt.lower() or "consistent" in prompt.lower()
    assert "design" in prompt.lower()


def test_review_prompt_includes_diff(mock_runner, warden_dir):
    """Review prompt includes the actual diff."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."

    agent.review("abc123", "- old_line\n+ new_line", ["file.py"])
    prompt = mock_runner.run.call_args[0][0]
    assert "old_line" in prompt
    assert "new_line" in prompt


def test_review_prompt_tells_agent_to_create_pr(mock_runner, warden_dir):
    """Review prompt instructs creating draft PRs for issues."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "No issues found."

    agent.review("abc123", "diff", ["file.py"], branch_prefix="warden/")
    prompt = mock_runner.run.call_args[0][0]
    assert "draft" in prompt.lower() or "PR" in prompt or "pull request" in prompt.lower()
    assert "warden/" in prompt


def test_review_returns_agent_output(mock_runner, warden_dir):
    """Review returns whatever the agent says."""
    agent = ReviewAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "Found 1 issue: off-by-one in loop"

    result = agent.review("abc123", "diff", ["file.py"])
    assert "off-by-one" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_review.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/agents/review.py`:
```python
from pathlib import Path

from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class ReviewAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def review(
        self,
        commit_hash: str,
        diff: str,
        changed_files: list[str],
        branch_prefix: str = "warden/",
    ) -> str:
        understanding = load_understanding(self.understanding_dir)

        prompt = (
            "You are reviewing a code change as a senior engineer who deeply "
            "understands this codebase's history, design decisions, and patterns.\n\n"
        )

        if understanding:
            prompt += (
                "Here is your accumulated understanding of this codebase:\n\n"
                f"{understanding}\n\n---\n\n"
            )

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
            "2. Apply the fix\n"
            "3. Commit the fix\n"
            "4. Push the branch\n"
            "5. Create a draft pull request explaining the issue and fix\n\n"
            "If no issues found, say so. Only report issues you are confident about. "
            "This is not a linter — focus on what matters."
        )

        return self.runner.run(prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_review.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/agents/review.py tests/test_review.py
git commit -m "feat: ReviewAgent for correctness and consistency checks"
```

---

## Task 9: AskAgent

**Files:**
- Create: `warden/agents/ask.py`
- Create: `tests/test_ask.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ask.py`:
```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from warden.agents.ask import AskAgent


@pytest.fixture
def mock_runner():
    return MagicMock()


@pytest.fixture
def warden_dir(tmp_path):
    understanding = tmp_path / ".warden" / "understanding"
    understanding.mkdir(parents=True)
    (understanding / "design-decisions.md").write_text(
        "# Design Decisions\n\n"
        "## Use SQLite over Redis\n"
        "- Source: PR #142\n"
        "- Rationale: ops overhead not justified\n"
    )
    return tmp_path / ".warden"


def test_ask_includes_question(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "Because of ops overhead."

    agent.ask("Why do we use SQLite?")
    prompt = mock_runner.run.call_args[0][0]
    assert "Why do we use SQLite?" in prompt


def test_ask_includes_understanding_docs(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"

    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "SQLite over Redis" in prompt
    assert "PR #142" in prompt


def test_ask_instructs_citing_sources(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"

    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "cite" in prompt.lower() or "Cite" in prompt


def test_ask_instructs_honesty_when_unknown(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "answer"

    agent.ask("anything")
    prompt = mock_runner.run.call_args[0][0]
    assert "don't know" in prompt.lower() or "do not know" in prompt.lower() or "don't guess" in prompt.lower()


def test_ask_returns_agent_output(mock_runner, warden_dir):
    agent = AskAgent(mock_runner, warden_dir)
    mock_runner.run.return_value = "SQLite was chosen over Redis because ops overhead wasn't justified. See PR #142."

    result = agent.ask("Why SQLite?")
    assert "PR #142" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_ask.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/agents/ask.py`:
```python
from pathlib import Path

from warden.agents.context import load_understanding
from warden.agents.runner import AgentRunner


class AskAgent:
    def __init__(self, runner: AgentRunner, warden_dir: Path):
        self.runner = runner
        self.understanding_dir = warden_dir / "understanding"

    def ask(self, question: str) -> str:
        understanding = load_understanding(self.understanding_dir)

        prompt = (
            "You are answering a question about a codebase using "
            "the understanding docs below.\n\n"
        )

        if understanding:
            prompt += f"{understanding}\n\n---\n\n"
        else:
            prompt += "(No understanding docs available yet.)\n\n---\n\n"

        prompt += (
            f"Question: {question}\n\n"
            "Answer the question based on the understanding docs above. "
            "Cite specific decisions, commits, and PRs where relevant. "
            "If the docs don't contain the answer, say you don't know — "
            "don't guess or make things up."
        )

        return self.runner.run(prompt, allowed_tools=["Read", "Grep", "Glob"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_ask.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/agents/ask.py tests/test_ask.py
git commit -m "feat: AskAgent for natural language codebase queries"
```

---

## Task 10: Git Hooks

**Files:**
- Create: `warden/git/hooks.py`
- Create: `tests/test_git_hooks.py`

- [ ] **Step 1: Write the failing test**

`tests/test_git_hooks.py`:
```python
import os
import stat
from pathlib import Path

import pytest

from warden.git.hooks import install_post_commit_hook, HOOK_MARKER


def test_install_creates_hook(tmp_repo):
    repo_path, repo = tmp_repo
    install_post_commit_hook(repo_path)

    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    content = hook_path.read_text()
    assert "warden analyze" in content
    assert HOOK_MARKER in content


def test_install_makes_hook_executable(tmp_repo):
    repo_path, repo = tmp_repo
    install_post_commit_hook(repo_path)

    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    mode = hook_path.stat().st_mode
    assert mode & stat.S_IXUSR  # Owner execute bit


def test_install_appends_to_existing_hook(tmp_repo):
    repo_path, repo = tmp_repo
    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text("#!/bin/bash\necho 'existing hook'\n")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)

    install_post_commit_hook(repo_path)

    content = hook_path.read_text()
    assert "existing hook" in content
    assert "warden analyze" in content


def test_install_is_idempotent(tmp_repo):
    repo_path, repo = tmp_repo
    install_post_commit_hook(repo_path)
    install_post_commit_hook(repo_path)

    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    content = hook_path.read_text()
    assert content.count("warden analyze") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_git_hooks.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/git/hooks.py`:
```python
import os
import stat
from pathlib import Path

HOOK_MARKER = "# Added by Warden"
HOOK_CONTENT = f"""
{HOOK_MARKER}
warden analyze 2>/dev/null &
"""


def install_post_commit_hook(repo_path: Path):
    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    if hook_path.exists():
        existing = hook_path.read_text()
        if HOOK_MARKER in existing:
            return  # Already installed
        new_content = existing.rstrip() + "\n" + HOOK_CONTENT
    else:
        new_content = "#!/bin/bash\n" + HOOK_CONTENT

    hook_path.write_text(new_content)

    # Make executable
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_git_hooks.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/git/hooks.py tests/test_git_hooks.py
git commit -m "feat: post-commit hook installation"
```

---

## Task 11: Orchestrator

**Files:**
- Create: `warden/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

`tests/test_orchestrator.py`:
```python
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from warden.config import WardenConfig
from warden.orchestrator import Orchestrator


@pytest.fixture
def setup(tmp_repo):
    """Set up orchestrator with a real git repo and mocked agent runner."""
    repo_path, repo = tmp_repo
    warden_dir = repo_path / ".warden"
    config = WardenConfig()

    with patch("warden.orchestrator.AgentRunner") as MockRunner:
        mock_runner = MagicMock()
        MockRunner.return_value = mock_runner
        mock_runner.run.return_value = "Agent completed."

        orchestrator = Orchestrator(repo_path, config)
        yield orchestrator, repo_path, repo, mock_runner


def test_init_creates_warden_directory(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    warden_dir = repo_path / ".warden"
    assert warden_dir.exists()
    assert (warden_dir / "understanding").is_dir()
    assert (warden_dir / "improvements" / "pending").is_dir()
    assert (warden_dir / "improvements" / "history").is_dir()
    assert (warden_dir / "config.yml").exists()


def test_init_creates_default_config(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    config_path = repo_path / ".warden" / "config.yml"
    content = config_path.read_text()
    assert "review:" in content
    assert "understanding:" in content


def test_init_installs_hook(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    assert "warden analyze" in hook_path.read_text()


def test_init_adds_state_db_to_gitignore(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    gitignore = repo_path / ".gitignore"
    assert gitignore.exists()
    assert ".warden/state.db" in gitignore.read_text()


def test_init_runs_bootstrap(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    # UnderstandAgent.bootstrap should have been called
    assert mock_runner.run.called
    prompt = mock_runner.run.call_args[0][0]
    assert "senior engineer" in prompt.lower()


def test_analyze_processes_new_commits(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    mock_runner.run.reset_mock()

    # Make a new commit
    (repo_path / "new_file.py").write_text("print('hi')\n")
    repo.index.add(["new_file.py"])
    repo.index.commit("Add new file")

    orchestrator.analyze()
    assert mock_runner.run.called


def test_analyze_skips_already_processed(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    mock_runner.run.reset_mock()

    # Make a commit and analyze it
    (repo_path / "new_file.py").write_text("print('hi')\n")
    repo.index.add(["new_file.py"])
    repo.index.commit("Add new file")
    orchestrator.analyze()

    call_count = mock_runner.run.call_count
    mock_runner.run.reset_mock()

    # Analyze again — nothing new
    orchestrator.analyze()
    assert mock_runner.run.call_count == 0


def test_ask_returns_answer(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()
    mock_runner.run.return_value = "SQLite was chosen for simplicity."

    answer = orchestrator.ask("Why SQLite?")
    assert "SQLite" in answer


def test_status_returns_stats(setup):
    orchestrator, repo_path, repo, mock_runner = setup
    orchestrator.init()

    status = orchestrator.status()
    assert "commits_total" in status
    assert isinstance(status["commits_total"], int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_orchestrator.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

`warden/orchestrator.py`:
```python
from pathlib import Path

from warden.agents.ask import AskAgent
from warden.agents.review import ReviewAgent
from warden.agents.runner import AgentRunner
from warden.agents.understand import UnderstandAgent
from warden.config import WardenConfig, load_config
from warden.git.hooks import install_post_commit_hook
from warden.git.repo import GitRepo
from warden.state import StateManager

GITIGNORE_ENTRY = ".warden/state.db"


class Orchestrator:
    def __init__(self, repo_path: Path, config: WardenConfig | None = None):
        self.repo_path = repo_path
        self.warden_dir = repo_path / ".warden"
        self.config = config or load_config(self.warden_dir / "config.yml")
        self.git_repo = GitRepo(repo_path)

        runner = AgentRunner(cwd=repo_path)
        self.understand_agent = UnderstandAgent(runner, self.warden_dir)
        self.review_agent = ReviewAgent(runner, self.warden_dir)
        self.ask_agent = AskAgent(runner, self.warden_dir)

        self.state = StateManager(self.warden_dir / "state.db")

    def init(
        self,
        pr_count: int | None = None,
        commit_count: int | None = None,
    ):
        """Initialize Warden in the repo."""
        # Create directory structure
        (self.warden_dir / "understanding").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "pending").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "history").mkdir(parents=True, exist_ok=True)

        # Write default config if none exists
        config_path = self.warden_dir / "config.yml"
        if not config_path.exists():
            config_path.write_text(self.config.to_yaml())

        # Initialize state DB
        self.state.initialize()

        # Install git hook
        install_post_commit_hook(self.repo_path)

        # Add state.db to .gitignore
        self._add_to_gitignore(GITIGNORE_ENTRY)

        # Run bootstrap — CLI flags override config values
        effective_pr_count = pr_count or self.config.understanding.bootstrap.pr_count
        effective_commit_count = commit_count or self.config.understanding.bootstrap.commit_count
        self.understand_agent.bootstrap(
            pr_count=effective_pr_count,
            commit_count=effective_commit_count,
        )

        # Record all existing commits as processed
        for commit in self.git_repo.get_all_commits():
            self.state.record_commit(
                hash=commit["hash"],
                timestamp=commit["timestamp"],
                files_changed=commit["files"],
            )
            self.state.mark_commit_understood(commit["hash"])

    def analyze(self, commit_hash: str | None = None):
        """Analyze new commits since last run."""
        self.state.initialize()

        if commit_hash:
            self._analyze_commit(commit_hash)
            return

        last_hash = self.state.get_last_processed_hash()
        if last_hash:
            commits = self.git_repo.get_commits_since(last_hash)
        else:
            commits = self.git_repo.get_all_commits()

        # Process oldest first
        for commit in reversed(commits):
            self._analyze_commit(commit["hash"])

    def ask(self, question: str) -> str:
        """Ask a question about the codebase."""
        return self.ask_agent.ask(question)

    def status(self) -> dict:
        """Return current status."""
        self.state.initialize()
        stats = self.state.get_stats()

        # Add understanding doc info
        understanding_dir = self.warden_dir / "understanding"
        doc_sizes = {}
        if understanding_dir.exists():
            for doc in understanding_dir.iterdir():
                if doc.suffix == ".md":
                    doc_sizes[doc.name] = doc.stat().st_size

        stats["understanding_docs"] = doc_sizes
        return stats

    def _analyze_commit(self, commit_hash: str):
        existing = self.state.get_commit(commit_hash)
        if existing and existing["understand_done"]:
            return

        diff = self.git_repo.get_commit_diff(commit_hash)
        files = self.git_repo.get_commit_files(commit_hash)
        commit_obj = self.git_repo.repo.commit(commit_hash)
        message = commit_obj.message.strip()

        commit_info = {
            "hash": commit_hash,
            "message": message,
            "diff": diff,
        }

        # Record commit if not already recorded
        if not existing:
            self.state.record_commit(
                hash=commit_hash,
                timestamp=commit_obj.committed_datetime,
                files_changed=files,
            )

        # Run understand
        self.understand_agent.incremental(commit_info)
        self.state.mark_commit_understood(commit_hash)

        # Run review if enabled
        if self.config.review.enabled:
            self.review_agent.review(
                commit_hash=commit_hash,
                diff=diff,
                changed_files=files,
                branch_prefix=self.config.git.branch_prefix,
            )
            self.state.mark_commit_reviewed(commit_hash)

    def _add_to_gitignore(self, entry: str):
        gitignore_path = self.repo_path / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if entry in content:
                return
            gitignore_path.write_text(content.rstrip() + "\n" + entry + "\n")
        else:
            gitignore_path.write_text(entry + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_orchestrator.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrator wiring init, analyze, ask, status workflows"
```

---

## Task 12: CLI Commands

**Files:**
- Modify: `warden/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from warden.cli import app

runner = CliRunner()


@pytest.fixture
def mock_orchestrator():
    with patch("warden.cli.Orchestrator") as MockOrch:
        mock = MagicMock()
        MockOrch.return_value = mock
        yield mock


def test_init_command(mock_orchestrator):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    mock_orchestrator.init.assert_called_once()
    assert "initialized" in result.stdout.lower() or "Warden" in result.stdout


def test_analyze_command(mock_orchestrator):
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 0
    mock_orchestrator.analyze.assert_called_once_with(commit_hash=None)


def test_analyze_with_commit(mock_orchestrator):
    result = runner.invoke(app, ["analyze", "--commit", "abc123"])
    assert result.exit_code == 0
    mock_orchestrator.analyze.assert_called_once_with(commit_hash="abc123")


def test_ask_command(mock_orchestrator):
    mock_orchestrator.ask.return_value = "Because of performance."
    result = runner.invoke(app, ["ask", "Why async?"])
    assert result.exit_code == 0
    mock_orchestrator.ask.assert_called_once_with("Why async?")
    assert "performance" in result.stdout.lower()


def test_status_command(mock_orchestrator):
    mock_orchestrator.status.return_value = {
        "commits_total": 42,
        "commits_understood": 40,
        "reviews_pending": 2,
        "reviews_accepted": 5,
        "reviews_declined": 1,
        "understanding_docs": {
            "architecture.md": 1024,
            "design-decisions.md": 2048,
        },
    }
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "42" in result.stdout


def test_config_command():
    """Config show prints current config."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0


def test_reset_command(mock_orchestrator, tmp_path):
    result = runner.invoke(app, ["reset", "--all"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_cli.py -v`
Expected: FAIL (cli.py exists but doesn't have real commands yet)

- [ ] **Step 3: Write implementation**

`warden/cli.py`:
```python
import shutil
from pathlib import Path

import typer

from warden.config import WardenConfig, load_config
from warden.orchestrator import Orchestrator

app = typer.Typer(help="Warden - AI Agent for Continuous Codebase Vigilance")


def _get_orchestrator(repo_path: Path | None = None) -> Orchestrator:
    path = repo_path or Path.cwd()
    config = load_config(path / ".warden" / "config.yml")
    return Orchestrator(path, config)


@app.command()
def init(
    pr_count: int | None = typer.Option(None, "--pr-count", help="Number of PRs to read (default: all)"),
    commit_count: int | None = typer.Option(None, "--commit-count", help="Number of commits to read (default: all)"),
):
    """Initialize Warden in the current repository."""
    orchestrator = _get_orchestrator()
    orchestrator.init(pr_count=pr_count, commit_count=commit_count)
    typer.echo("Warden initialized. Understanding built from repo history.")


@app.command()
def analyze(
    commit: str | None = typer.Option(None, "--commit", help="Analyze a specific commit"),
):
    """Analyze new commits since last run."""
    orchestrator = _get_orchestrator()
    orchestrator.analyze(commit_hash=commit)
    typer.echo("Analysis complete.")


@app.command()
def ask(question: str = typer.Argument(..., help="Question about the codebase")):
    """Ask a question about the codebase."""
    orchestrator = _get_orchestrator()
    answer = orchestrator.ask(question)
    typer.echo(answer)


@app.command()
def status():
    """Show Warden status."""
    orchestrator = _get_orchestrator()
    stats = orchestrator.status()

    typer.echo("Warden Status")
    typer.echo("=" * 40)
    typer.echo(f"Commits processed:  {stats['commits_total']}")
    typer.echo(f"Commits understood: {stats['commits_understood']}")
    typer.echo(f"Reviews pending:    {stats['reviews_pending']}")
    typer.echo(f"Reviews accepted:   {stats['reviews_accepted']}")
    typer.echo(f"Reviews declined:   {stats['reviews_declined']}")

    docs = stats.get("understanding_docs", {})
    if docs:
        typer.echo("\nUnderstanding docs:")
        for name, size in docs.items():
            typer.echo(f"  {name}: {size} bytes")


@app.command()
def config():
    """Show current configuration."""
    path = Path.cwd() / ".warden" / "config.yml"
    cfg = load_config(path)
    typer.echo(cfg.to_yaml())


@app.command()
def reset(
    understanding: bool = typer.Option(False, "--understanding", help="Clear understanding docs"),
    improvements: bool = typer.Option(False, "--improvements", help="Clear improvement history"),
    all_: bool = typer.Option(False, "--all", help="Clear all Warden state"),
):
    """Reset Warden state."""
    warden_dir = Path.cwd() / ".warden"

    if all_ or understanding:
        understanding_dir = warden_dir / "understanding"
        if understanding_dir.exists():
            shutil.rmtree(understanding_dir)
            understanding_dir.mkdir()
            typer.echo("Understanding docs cleared.")

    if all_ or improvements:
        for subdir in ["pending", "history"]:
            imp_dir = warden_dir / "improvements" / subdir
            if imp_dir.exists():
                shutil.rmtree(imp_dir)
                imp_dir.mkdir()
        typer.echo("Improvement history cleared.")

    if all_:
        db_path = warden_dir / "state.db"
        if db_path.exists():
            db_path.unlink()
            typer.echo("State database cleared.")

    typer.echo("Reset complete.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_cli.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add warden/cli.py tests/test_cli.py
git commit -m "feat: CLI commands for init, analyze, ask, status, config, reset"
```

---

## Task 13: End-to-End Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

`tests/test_integration.py`:
```python
"""
End-to-end integration test using a real git repo
and mocked Claude Code CLI calls.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from warden.orchestrator import Orchestrator
from warden.config import WardenConfig


@pytest.fixture
def project(tmp_repo):
    """Create a small project with multiple commits."""
    repo_path, repo = tmp_repo

    # Commit 2: add a Python file
    (repo_path / "app.py").write_text(
        "def get_user(user_id: int):\n"
        "    return db.query(User).filter(User.id == user_id).first()\n"
    )
    repo.index.add(["app.py"])
    repo.index.commit("feat: add user lookup endpoint")

    # Commit 3: add another file
    (repo_path / "models.py").write_text(
        "class User:\n"
        "    id: int\n"
        "    name: str\n"
    )
    repo.index.add(["models.py"])
    repo.index.commit("feat: add User model")

    return repo_path, repo


def test_full_init_and_analyze_cycle(project):
    """Test the complete lifecycle: init → analyze → ask → status."""
    repo_path, repo = project

    with patch("warden.agents.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(
            stdout="Agent completed successfully.",
            stderr="",
            returncode=0,
        )

        config = WardenConfig()
        orchestrator = Orchestrator(repo_path, config)

        # 1. Init
        orchestrator.init()

        # Verify directory structure
        warden_dir = repo_path / ".warden"
        assert (warden_dir / "understanding").is_dir()
        assert (warden_dir / "config.yml").exists()
        assert (warden_dir / "state.db").exists()
        assert (repo_path / ".git" / "hooks" / "post-commit").exists()
        assert ".warden/state.db" in (repo_path / ".gitignore").read_text()

        # Bootstrap should have been called (first subprocess call)
        assert mock_subprocess.called
        first_prompt = mock_subprocess.call_args_list[0][0][0]
        # The first call should be the bootstrap prompt via claude -p
        assert "claude" in first_prompt[0] or "claude" in str(first_prompt)

        # 2. Status after init
        status = orchestrator.status()
        assert status["commits_total"] == 3  # Initial + 2 feature commits
        assert status["commits_understood"] == 3

        # 3. Make a new commit and analyze
        mock_subprocess.reset_mock()
        (repo_path / "utils.py").write_text("def helper(): pass\n")
        repo.index.add(["utils.py"])
        repo.index.commit("feat: add utility helper")

        orchestrator.analyze()

        # Should have called claude for understand + review
        assert mock_subprocess.called

        # 4. Status after analyze
        status = orchestrator.status()
        assert status["commits_total"] == 4

        # 5. Ask
        mock_subprocess.reset_mock()
        mock_subprocess.return_value = MagicMock(
            stdout="The User model was added in commit xyz.",
            stderr="",
            returncode=0,
        )
        answer = orchestrator.ask("What is the User model?")
        assert "User model" in answer


def test_analyze_is_idempotent(project):
    """Running analyze twice doesn't reprocess commits."""
    repo_path, repo = project

    with patch("warden.agents.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(
            stdout="Done.", stderr="", returncode=0,
        )

        config = WardenConfig()
        orchestrator = Orchestrator(repo_path, config)
        orchestrator.init()

        # Add a commit
        (repo_path / "new.py").write_text("x = 1\n")
        repo.index.add(["new.py"])
        repo.index.commit("add new")

        # First analyze
        mock_subprocess.reset_mock()
        orchestrator.analyze()
        first_count = mock_subprocess.call_count

        # Second analyze — nothing new
        mock_subprocess.reset_mock()
        orchestrator.analyze()
        assert mock_subprocess.call_count == 0
```

- [ ] **Step 2: Run the integration test**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest tests/test_integration.py -v`
Expected: All 2 tests PASS

- [ ] **Step 3: Run the full test suite**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest -v`
Expected: All tests PASS (should be ~50 tests total)

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test for init/analyze/ask lifecycle"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Install and verify CLI works**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pip install -e . && warden --help`
Expected: Shows all commands: init, analyze, ask, status, config, reset

- [ ] **Step 2: Run full test suite one more time**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && pytest -v --tb=short`
Expected: All tests PASS

- [ ] **Step 3: Verify warden init works on this repo**

Run: `cd /home/scratch.kaix_coreai/workspace/harness/warden && warden init`
Expected: Creates `.warden/` directory, installs hook, runs bootstrap via Claude Code

- [ ] **Step 4: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: final polish and verification"
```
