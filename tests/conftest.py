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
