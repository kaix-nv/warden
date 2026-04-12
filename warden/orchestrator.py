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

    def init(self, pr_count: int | None = None, commit_count: int | None = None):
        """Initialize Warden in the repo."""
        (self.warden_dir / "understanding").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "pending").mkdir(parents=True, exist_ok=True)
        (self.warden_dir / "improvements" / "history").mkdir(parents=True, exist_ok=True)

        config_path = self.warden_dir / "config.yml"
        if not config_path.exists():
            config_path.write_text(self.config.to_yaml())

        self.state.initialize()
        install_post_commit_hook(self.repo_path)
        self._add_to_gitignore(GITIGNORE_ENTRY)

        effective_pr_count = pr_count or self.config.understanding.bootstrap.pr_count
        effective_commit_count = commit_count or self.config.understanding.bootstrap.commit_count
        self.understand_agent.bootstrap(pr_count=effective_pr_count, commit_count=effective_commit_count)

        for commit in self.git_repo.get_all_commits():
            self.state.record_commit(hash=commit["hash"], timestamp=commit["timestamp"], files_changed=commit["files"])
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
        for commit in reversed(commits):
            self._analyze_commit(commit["hash"])

    def ask(self, question: str) -> str:
        return self.ask_agent.ask(question)

    def status(self) -> dict:
        self.state.initialize()
        stats = self.state.get_stats()
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
        commit_info = {"hash": commit_hash, "message": message, "diff": diff}
        if not existing:
            self.state.record_commit(hash=commit_hash, timestamp=commit_obj.committed_datetime, files_changed=files)
        self.understand_agent.incremental(commit_info)
        self.state.mark_commit_understood(commit_hash)
        if self.config.review.enabled:
            self.review_agent.review(commit_hash=commit_hash, diff=diff, changed_files=files, branch_prefix=self.config.git.branch_prefix)
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
