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
