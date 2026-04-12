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
    assert mode & stat.S_IXUSR

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
