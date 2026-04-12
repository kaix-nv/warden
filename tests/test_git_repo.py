from pathlib import Path
import pytest
from warden.git.repo import GitRepo

def test_get_all_commits(tmp_repo):
    repo_path, repo = tmp_repo
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
