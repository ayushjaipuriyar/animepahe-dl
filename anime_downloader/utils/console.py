"""
Rich console output for better CLI experience.

This module provides enhanced console output with colors, progress bars,
and formatted tables using the Rich library.
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.tree import Tree
from typing import List, Dict, Any, Optional
import time

# Global console instance
console = Console()


class RichProgress:
    """Enhanced progress display using Rich."""
    
    def __init__(self):
        self.progress = None
        self.tasks = {}
    
    def start(self):
        """Start the progress display."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False
        )
        self.progress.start()
    
    def add_task(self, description: str, total: int = 100) -> int:
        """Add a new progress task."""
        if self.progress:
            task_id = self.progress.add_task(description, total=total)
            self.tasks[description] = task_id
            return task_id
        return 0
    
    def update(self, task_id: int, advance: int = 1, description: str = None):
        """Update progress for a task."""
        if self.progress:
            self.progress.update(task_id, advance=advance, description=description)
    
    def stop(self):
        """Stop the progress display."""
        if self.progress:
            self.progress.stop()
            self.progress = None


def print_banner():
    """Print application banner."""
    banner = Text("AnimePahe Downloader", style="bold blue")
    banner.append(" v5.4.0", style="dim")
    console.print(Panel(banner, expand=False))


def print_anime_table(anime_list: List[Dict[str, Any]]):
    """Print anime list in a formatted table."""
    if not anime_list:
        console.print("[yellow]No anime found.[/yellow]")
        return
    
    table = Table(title="Search Results")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Status", style="green")
    
    for i, anime in enumerate(anime_list[:20], 1):  # Limit to 20 results
        title = anime.get("title", "Unknown")
        status = anime.get("status", "Unknown")
        table.add_row(str(i), title, status)
    
    console.print(table)


def print_episode_info(anime_name: str, episodes: List[int], total_episodes: int):
    """Print episode download information."""
    info = f"[bold]{anime_name}[/bold]\n"
    info += f"Episodes to download: [cyan]{len(episodes)}[/cyan] of [cyan]{total_episodes}[/cyan]\n"
    info += f"Episode range: [yellow]{min(episodes)}-{max(episodes)}[/yellow]"
    
    console.print(Panel(info, title="Download Info", expand=False))


def print_download_summary(completed: int, failed: int, total: int):
    """Print download completion summary."""
    if failed == 0:
        status = "[green]✓ All downloads completed successfully![/green]"
    else:
        status = f"[yellow]⚠ {completed} completed, {failed} failed[/yellow]"
    
    summary = f"""
Downloads: [cyan]{completed}[/cyan] / [cyan]{total}[/cyan]
Status: {status}
"""
    console.print(Panel(summary.strip(), title="Download Summary", expand=False))


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗ Error:[/red] {message}")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_info(message: str):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def confirm_download(anime_count: int, episode_count: int) -> bool:
    """Confirm download with user."""
    message = f"Download [cyan]{episode_count}[/cyan] episodes from [cyan]{anime_count}[/cyan] anime?"
    return Confirm.ask(message, default=True)


def prompt_quality() -> str:
    """Prompt user for quality selection."""
    return Prompt.ask(
        "Select quality",
        choices=["best", "1080", "720", "480", "360"],
        default="best"
    )


def prompt_audio() -> str:
    """Prompt user for audio selection."""
    return Prompt.ask(
        "Select audio language",
        choices=["jpn", "eng"],
        default="jpn"
    )


def show_anime_tree(anime_list: List[Dict[str, Any]]):
    """Show anime in a tree structure."""
    tree = Tree("🎌 Available Anime")
    
    for anime in anime_list[:10]:  # Limit to 10 for tree view
        title = anime.get("title", "Unknown")
        status = anime.get("status", "Unknown")
        branch = tree.add(f"[bold]{title}[/bold]")
        branch.add(f"Status: [green]{status}[/green]")
        if "year" in anime:
            branch.add(f"Year: [cyan]{anime['year']}[/cyan]")
        if "episodes" in anime:
            branch.add(f"Episodes: [yellow]{anime['episodes']}[/yellow]")
    
    console.print(tree)


def print_config_info(config: Dict[str, Any]):
    """Print current configuration."""
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    
    for key, value in config.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print(table)


# Global progress instance
progress = RichProgress()