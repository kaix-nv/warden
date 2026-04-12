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
