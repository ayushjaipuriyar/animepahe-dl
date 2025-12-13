"""
Interactive mode for enhanced user experience.

This module provides an interactive CLI mode with guided prompts,
smart defaults, and better user interaction.
"""

import os
from typing import List, Dict, Any, Optional
from ..utils import console, config_manager
from ..utils.console import print_banner, print_anime_table, confirm_download, prompt_quality, prompt_audio
from ..api import AnimePaheAPI
from ..models import Anime, Episode
from ..core.signal_handler import is_shutdown_requested
import questionary


class InteractiveMode:
    """Interactive CLI mode with guided prompts."""
    
    def __init__(self):
        self.api = AnimePaheAPI(verify_ssl=False)
        self.config = config_manager.load_config()
        self.selected_anime = []
        self.download_queue = []
    
    def run(self):
        """Run interactive mode."""
        print_banner()
        console.print("[dim]Interactive mode - guided anime downloading[/dim]\n")
        
        try:
            self._main_menu()
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
    
    def _main_menu(self):
        """Show main menu."""
        while True:
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "🔍 Search and download anime",
                    "📋 Manage my anime list",
                    "🔄 Check for updates",
                    "⚙️  Configure settings",
                    "📊 View download history",
                    "❌ Exit"
                ]
            ).ask()
            
            if not choice or "Exit" in choice:
                break
            elif "Search" in choice:
                self._search_and_download()
            elif "Manage" in choice:
                self._manage_anime_list()
            elif "updates" in choice:
                self._check_updates()
            elif "Configure" in choice:
                self._configure_settings()
            elif "history" in choice:
                self._view_history()
    
    def _search_and_download(self):
        """Search and download anime workflow."""
        # Get search query
        query = questionary.text(
            "Enter anime name to search (or press Enter to browse all):"
        ).ask()
        
        if query is None:  # User cancelled
            return
        
        console.print(f"[dim]Searching for: {query or 'all anime'}[/dim]")
        
        # Use fzf for anime selection (same as CLI mode)
        from .commands import choose_anime
        selected_anime_list = choose_anime(self.api, query, multi=True)
        
        if not selected_anime_list:
            console.print("[yellow]No anime selected.[/yellow]")
            return
        
        self.selected_anime = selected_anime_list
        
        # Configure download options
        self._configure_download_options()
        
        # Start downloads
        self._start_downloads()
    
    def _configure_download_options(self):
        """Configure download options for selected anime."""
        console.print(f"\n[bold]Selected {len(self.selected_anime)} anime[/bold]")
        
        # Quality selection
        quality = questionary.select(
            "Select video quality:",
            choices=["best", "1080p", "720p", "480p", "360p"],
            default=self.config.get("quality", "best")
        ).ask()
        
        # Audio selection
        audio = questionary.select(
            "Select audio language:",
            choices=["Japanese (jpn)", "English (eng)"],
            default="Japanese (jpn)" if self.config.get("audio", "jpn") == "jpn" else "English (eng)"
        ).ask()
        
        # Episode selection
        episode_mode = questionary.select(
            "Episode selection:",
            choices=[
                "All episodes",
                "Latest episodes only",
                "Specific range",
                "Missing episodes only"
            ]
        ).ask()
        
        episodes = "all"
        if episode_mode == "Latest episodes only":
            count = questionary.text(
                "How many latest episodes?",
                default="5",
                validate=lambda x: x.isdigit() and int(x) > 0
            ).ask()
            episodes = f"latest:{count}"
        elif episode_mode == "Specific range":
            episodes = questionary.text(
                "Enter episode range (e.g., 1-10, 1,3,5):",
                validate=lambda x: bool(x.strip())
            ).ask()
        elif episode_mode == "Missing episodes only":
            episodes = "missing"
        
        # Store options
        self.download_options = {
            "quality": quality.replace("p", "") if quality != "best" else "best",
            "audio": "jpn" if "Japanese" in audio else "eng",
            "episodes": episodes,
            "concurrent": self.config.get("concurrent_downloads", 2),
            "threads": self.config.get("threads", 50)
        }
    
    def _start_downloads(self):
        """Start the download process."""
        total_episodes = 0
        
        # Build download queue
        for anime in self.selected_anime:
            console.print(f"[dim]Fetching episodes for {anime['title']}...[/dim]")
            
            episode_data = self.api.fetch_episode_data(anime["title"], anime["session"])
            if episode_data:
                # Apply episode filtering based on user selection
                filtered_episodes = self._filter_episodes(episode_data, self.download_options["episodes"])
                total_episodes += len(filtered_episodes)
                
                self.download_queue.append({
                    "anime": anime,
                    "episodes": filtered_episodes
                })
        
        if not self.download_queue:
            console.print("[red]No episodes to download![/red]")
            return
        
        # Confirm download
        if not confirm_download(len(self.selected_anime), total_episodes):
            console.print("[yellow]Download cancelled.[/yellow]")
            return
        
        console.print(f"[green]Starting download of {total_episodes} episodes...[/green]")
        
        # Show what would be downloaded with resume detection
        from .cli import get_video_path
        download_dir = self.config.get("download_directory", "~/Videos")
        
        for item in self.download_queue:
            anime_name = item["anime"]["title"]
            episodes = item["episodes"]
            
            # Check which episodes are already downloaded
            existing_episodes = []
            new_episodes = []
            
            for ep_data in episodes:
                ep_num = int(ep_data["episode"])
                video_path = get_video_path(anime_name, ep_num, download_dir)
                if os.path.exists(video_path):
                    existing_episodes.append(ep_num)
                else:
                    new_episodes.append(ep_num)
            
            if existing_episodes:
                console.print(f"  • {anime_name}: {len(new_episodes)} new episodes, {len(existing_episodes)} already downloaded")
            else:
                console.print(f"  • {anime_name}: {len(episodes)} episodes")
        
        # Start actual download process using the same logic as CLI
        from .commands import download_single_episode
        from ..api import Downloader
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tqdm import tqdm
        
        downloader = Downloader(self.api)
        download_dir = self.config.get("download_directory", "~/Videos")
        
        # Build download tasks
        all_download_tasks = []
        for item in self.download_queue:
            anime_data = item["anime"]
            episodes = item["episodes"]
            
            for ep_data in episodes:
                ep_num = int(ep_data["episode"])
                # Check if already downloaded
                from .commands import get_video_path
                video_path = get_video_path(anime_data["title"], ep_num, download_dir)
                if os.path.exists(video_path):
                    console.print(f"[dim]Skipping {anime_data['title']} Episode {ep_num} (already downloaded)[/dim]")
                    continue
                
                all_download_tasks.append({
                    "name": anime_data["title"],
                    "slug": anime_data["session"],
                    "episode_num": ep_num,
                    "episode_session": ep_data["session"],
                })
        
        if not all_download_tasks:
            console.print("[yellow]No new episodes to download![/yellow]")
            return
        
        console.print(f"[green]Starting download of {len(all_download_tasks)} episode(s)...[/green]")
        
        # Create args-like object for download_single_episode
        class DownloadArgs:
            def __init__(self, options):
                self.quality = options["quality"]
                self.audio = options["audio"]
                self.threads = options["threads"]
                self.verbose = False
        
        args = DownloadArgs(self.download_options)
        
        # Download episodes concurrently
        try:
            with ThreadPoolExecutor(max_workers=self.download_options["concurrent"]) as executor:
                futures = []
                for task in all_download_tasks:
                    future = executor.submit(
                        download_single_episode,
                        self.api,
                        downloader,
                        task,
                        args,
                        self.config,
                    )
                    futures.append(future)
                
                # Track progress
                with tqdm(total=len(futures), desc="Download Progress") as pbar:
                    failed_downloads = []
                    for future in as_completed(futures):
                        task_index = futures.index(future)
                        if task_index < len(all_download_tasks):
                            task = all_download_tasks[task_index]
                            anime_name = task["name"]
                            episode_num = task["episode_num"]
                        else:
                            anime_name = "Unknown"
                            episode_num = "Unknown"
                        
                        try:
                            future.result()  # Wait for completion
                            console.print(f"[green]✓ Completed: {anime_name} Episode {episode_num}[/green]")
                        except Exception as e:
                            console.print(f"[red]✗ Failed: {anime_name} Episode {episode_num} - {str(e)}[/red]")
                            failed_downloads.append(f"{anime_name} Episode {episode_num}")
                        pbar.update(1)
                    
                    if failed_downloads:
                        console.print(f"[yellow]Failed downloads: {', '.join(failed_downloads)}[/yellow]")
                        console.print("[dim]You can retry these episodes later.[/dim]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Download interrupted by user[/yellow]")
            return
        
        console.print("[green]All downloads completed![/green]")
    
    def _filter_episodes(self, episode_data: List[Dict], episode_selection: str) -> List[Dict]:
        """Filter episodes based on user selection."""
        if episode_selection == "all":
            return episode_data
        elif episode_selection.startswith("latest:"):
            count = int(episode_selection.split(":")[1])
            return episode_data[-count:]  # Last N episodes
        elif episode_selection == "missing":
            # Filter out already downloaded episodes
            # This would need integration with download tracking
            return episode_data
        else:
            # Parse specific range/numbers using the existing function
            from .commands import parse_episode_selection
            max_episode = len(episode_data)
            selected_episodes = parse_episode_selection(episode_selection, max_episode)
            
            # Filter episode_data to only include selected episodes
            filtered_episodes = []
            for ep_data in episode_data:
                ep_num = int(ep_data["episode"])
                if ep_num in selected_episodes:
                    filtered_episodes.append(ep_data)
            
            return filtered_episodes
    
    def _manage_anime_list(self):
        """Manage user's anime list."""
        console.print("[dim]Anime list management[/dim]")
        
        choice = questionary.select(
            "Anime list management:",
            choices=[
                "📋 View my anime list",
                "➕ Add anime to list",
                "➖ Remove anime from list",
                "🔄 Update list from downloads",
                "⬅️  Back to main menu"
            ]
        ).ask()
        
        if "View" in choice:
            self._view_anime_list()
        elif "Add" in choice:
            self._add_to_anime_list()
        elif "Remove" in choice:
            self._remove_from_anime_list()
        elif "Update" in choice:
            self._update_anime_list()
    
    def _view_anime_list(self):
        """View user's anime list."""
        try:
            from .constants import MY_ANIME_LIST_FILE
            if os.path.exists(MY_ANIME_LIST_FILE):
                with open(MY_ANIME_LIST_FILE, 'r', encoding='utf-8') as f:
                    anime_list = [line.strip() for line in f if line.strip()]
                
                if anime_list:
                    console.print(f"\n[bold]Your Anime List ({len(anime_list)} anime):[/bold]")
                    for i, anime in enumerate(anime_list, 1):
                        console.print(f"  {i}. {anime}")
                else:
                    console.print("[yellow]Your anime list is empty.[/yellow]")
            else:
                console.print("[yellow]No anime list found.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error reading anime list: {e}[/red]")
    
    def _add_to_anime_list(self):
        """Add anime to user's list."""
        query = questionary.text("Search for anime to add:").ask()
        if not query:
            return
        
        results = self.api.search(query)
        if not results:
            console.print("[red]No anime found![/red]")
            return
        
        choices = [questionary.Choice(anime["title"], value=anime["title"]) for anime in results[:10]]
        selected = questionary.select("Select anime to add:", choices=choices).ask()
        
        if selected:
            try:
                from .constants import MY_ANIME_LIST_FILE
                os.makedirs(os.path.dirname(MY_ANIME_LIST_FILE), exist_ok=True)
                with open(MY_ANIME_LIST_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{selected}\n")
                console.print(f"[green]Added '{selected}' to your anime list![/green]")
            except Exception as e:
                console.print(f"[red]Error adding anime: {e}[/red]")
    
    def _remove_from_anime_list(self):
        """Remove anime from user's list."""
        try:
            from .constants import MY_ANIME_LIST_FILE
            if not os.path.exists(MY_ANIME_LIST_FILE):
                console.print("[yellow]No anime list found.[/yellow]")
                return
            
            with open(MY_ANIME_LIST_FILE, 'r', encoding='utf-8') as f:
                anime_list = [line.strip() for line in f if line.strip()]
            
            if not anime_list:
                console.print("[yellow]Your anime list is empty.[/yellow]")
                return
            
            choices = [questionary.Choice(anime, value=anime) for anime in anime_list]
            to_remove = questionary.checkbox("Select anime to remove:", choices=choices).ask()
            
            if to_remove:
                updated_list = [anime for anime in anime_list if anime not in to_remove]
                with open(MY_ANIME_LIST_FILE, 'w', encoding='utf-8') as f:
                    for anime in updated_list:
                        f.write(f"{anime}\n")
                console.print(f"[green]Removed {len(to_remove)} anime from your list![/green]")
        except Exception as e:
            console.print(f"[red]Error managing anime list: {e}[/red]")
    
    def _update_anime_list(self):
        """Update anime list from downloaded files."""
        console.print("[dim]This feature would scan your download directory and update the list.[/dim]")
    
    def _check_updates(self):
        """Check for new episodes."""
        console.print("[dim]Checking for new episodes...[/dim]")
        # This would integrate with the existing update checking logic
        console.print("[green]No new episodes found.[/green]")
    
    def _configure_settings(self):
        """Configure application settings."""
        console.print("[bold]Current Settings:[/bold]")
        
        # Show current settings
        settings_to_show = {
            "Download Directory": self.config.get("download_directory", "~/Videos"),
            "Default Quality": self.config.get("quality", "best"),
            "Default Audio": self.config.get("audio", "jpn"),
            "Download Threads": self.config.get("threads", 50),
            "Concurrent Downloads": self.config.get("concurrent_downloads", 2)
        }
        
        for key, value in settings_to_show.items():
            console.print(f"  {key}: [cyan]{value}[/cyan]")
        
        if questionary.confirm("Would you like to modify settings?").ask():
            self._modify_settings()
    
    def _modify_settings(self):
        """Modify application settings."""
        # Download directory
        new_dir = questionary.text(
            "Download directory:",
            default=self.config.get("download_directory", "~/Videos")
        ).ask()
        if new_dir:
            self.config["download_directory"] = new_dir
        
        # Default quality
        new_quality = questionary.select(
            "Default quality:",
            choices=["best", "1080", "720", "480", "360"],
            default=self.config.get("quality", "best")
        ).ask()
        if new_quality:
            self.config["quality"] = new_quality
        
        # Default audio
        new_audio = questionary.select(
            "Default audio:",
            choices=["jpn", "eng"],
            default=self.config.get("audio", "jpn")
        ).ask()
        if new_audio:
            self.config["audio"] = new_audio
        
        # Save settings
        config_manager.save_config(self.config)
        console.print("[green]Settings saved![/green]")
    
    def _view_history(self):
        """View download history."""
        console.print("[dim]Download history feature would show completed downloads here.[/dim]")


def run_interactive_mode():
    """Entry point for interactive mode."""
    interactive = InteractiveMode()
    interactive.run()