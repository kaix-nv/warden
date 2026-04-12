import stat
import subprocess
from pathlib import Path

HOOK_MARKER = "# Added by Warden"
HOOK_CONTENT = f"""
{HOOK_MARKER}
warden analyze 2>/dev/null &
"""


def _get_git_dir(repo_path: Path) -> Path:
    """Resolve the actual .git directory, handling worktrees."""
    dot_git = repo_path / ".git"
    if dot_git.is_file():
        # Worktree: .git is a file like "gitdir: /path/to/actual/.git/worktrees/name"
        content = dot_git.read_text().strip()
        if content.startswith("gitdir:"):
            return Path(content.split(":", 1)[1].strip())
    return dot_git


def install_post_commit_hook(repo_path: Path):
    git_dir = _get_git_dir(repo_path)
    hook_path = git_dir / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    if hook_path.exists():
        existing = hook_path.read_text()
        if HOOK_MARKER in existing:
            return
        new_content = existing.rstrip() + "\n" + HOOK_CONTENT
    else:
        new_content = "#!/bin/bash\n" + HOOK_CONTENT
    hook_path.write_text(new_content)
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
