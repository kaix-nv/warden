import shutil
from pathlib import Path
from typing import List

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
def impact(files: List[str] = typer.Argument(..., help="Files to analyze for dependency impact")):
    """Show dependency impact and relevant design context for given files."""
    orchestrator = _get_orchestrator()
    result = orchestrator.impact(files)
    typer.echo(result)


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
    graph_nodes = stats.get("graph_nodes", 0)
    if graph_nodes:
        typer.echo(f"\nGraph nodes: {graph_nodes}")


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
