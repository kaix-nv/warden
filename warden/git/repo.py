from datetime import datetime, timezone
from pathlib import Path
from git import Repo


class GitRepo:
    def __init__(self, path: Path):
        self.path = path
        self.repo = Repo(path)

    def get_all_commits(self) -> list[dict]:
        commits = []
        for commit in self.repo.iter_commits():
            commits.append(self._commit_to_dict(commit))
        return commits

    def get_commits_since(self, since_hash: str) -> list[dict]:
        commits = []
        for commit in self.repo.iter_commits():
            if commit.hexsha == since_hash:
                break
            commits.append(self._commit_to_dict(commit))
        return commits

    def get_commit_diff(self, commit_hash: str) -> str:
        commit = self.repo.commit(commit_hash)
        if commit.parents:
            diffs = commit.parents[0].diff(commit, create_patch=True, unified=3)
        else:
            diffs = commit.diff(None, create_patch=True)
        parts = []
        for d in diffs:
            a = d.a_path or d.b_path
            b = d.b_path or d.a_path
            header = f"--- a/{a}\n+++ b/{b}\n"
            patch = d.diff.decode("utf-8", errors="replace") if isinstance(d.diff, bytes) else d.diff
            parts.append(header + patch)
        return "\n".join(parts)

    def get_commit_files(self, commit_hash: str) -> list[str]:
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
