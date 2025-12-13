"""
Main window for the GUI application.

This module contains the main application window that provides
the primary interface for anime downloading.
"""

import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QTableWidget,
    QProgressBar,
    QStatusBar,
    QLabel,
    QHeaderView,
    QListWidgetItem,
    QTableWidgetItem,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QFont, QPalette, QColor, QIcon, QPixmap, QAction

from ..utils import constants, config_manager
from ..api import AnimePaheAPI, Downloader
from ..core.signal_handler import setup_signal_handling, register_shutdown_callback
from .workers import EpisodeWorker, DownloadWorker, UpdateCacheWorker, MultiAnimeDownloadWorker
from .dialogs import SettingsDialog


class MainWindow(QMainWindow):
    """
    The main application window.

    This class sets up the UI layout and connects all the signals and slots
    to handle user interaction and background worker threads.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimePahe Downloader")
        self.setGeometry(100, 100, 800, 600)

        # --- Initialize Core Components ---
        # Apply base_url override early (same behavior as CLI)
        app_cfg = config_manager.load_config()
        if app_cfg.get("base_url") and app_cfg.get("base_url") != constants.get_base_url():
            try:
                constants.set_base_url(app_cfg["base_url"])
            except Exception:
                pass  # Fail silently; will surface in cache update if invalid

        # Build API client (forced insecure SSL per user request)
        self.api = AnimePaheAPI(verify_ssl=False)
        self.downloader = Downloader(self.api)
        self.current_anime = None
        self.local_anime_list = []
        self.worker = None  # To hold a reference to the running worker
        self.last_cache_count = None
        
        # Ensure download directory exists
        try:
            download_dir = app_cfg.get("download_directory", "downloads")
            os.makedirs(download_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create download directory: {e}")

        self._setup_ui()
        self._setup_system_tray()
        self._apply_modern_styling()
        self.load_local_anime_list()
        
        # Setup update timer for background monitoring
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.background_update_check)
        
        # Auto-update cache if empty on launch
        if not self.local_anime_list:
            self.start_cache_update()
    def _setup_ui(self):
        """Initializes all UI elements and layouts."""
        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # --- Header with Title ---
        header_layout = QVBoxLayout()
        title_label = QLabel("AnimePahe Downloader")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Download anime episodes with ease")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: palette(mid); font-size: 11pt;")
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # --- Search Area ---
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)
        
        search_label = QLabel("Search:")
        search_label.setMinimumWidth(60)
        search_layout.addWidget(search_label)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter anime list... (Ctrl+F to focus)")
        self.search_bar.textChanged.connect(self.filter_anime_list)
        search_layout.addWidget(self.search_bar, 1)  # Give search bar more space

        self.update_cache_button = QPushButton("🔄 Update Cache")
        self.update_cache_button.clicked.connect(self.start_cache_update)
        self.update_cache_button.setToolTip("Refresh the anime list from server (F5)")
        search_layout.addWidget(self.update_cache_button)

        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setToolTip("Configure download settings")
        search_layout.addWidget(self.settings_button)
        main_layout.addLayout(search_layout)

        # --- Results and Episodes Panels ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Left panel - Anime list
        left_panel = QVBoxLayout()
        anime_label = QLabel("📺 Anime List")
        anime_label.setStyleSheet("font-weight: 600; font-size: 12pt; margin-bottom: 8px;")
        left_panel.addWidget(anime_label)
        
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.results_list.itemClicked.connect(self.on_anime_selected)
        self.results_list.setMinimumWidth(300)
        left_panel.addWidget(self.results_list)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        content_layout.addWidget(left_widget, 1)

        # Right panel - Episodes
        right_panel = QVBoxLayout()
        episodes_label = QLabel("📋 Episodes")
        episodes_label.setStyleSheet("font-weight: 600; font-size: 12pt; margin-bottom: 8px;")
        right_panel.addWidget(episodes_label)
        
        self.episode_table = QTableWidget()
        self.episode_table.setColumnCount(3)
        self.episode_table.setHorizontalHeaderLabels(["Episode", "Status", "Download"])
        header = self.episode_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.episode_table.verticalHeader().setVisible(False)
        right_panel.addWidget(self.episode_table)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        content_layout.addWidget(right_widget, 2)  # Give episodes panel more space
        
        main_layout.addLayout(content_layout)

        # --- Episode Selection Controls ---
        episode_controls_layout = QHBoxLayout()
        episode_controls_layout.setSpacing(12)
        
        controls_label = QLabel("Episode Selection:")
        controls_label.setStyleSheet("font-weight: 500;")
        episode_controls_layout.addWidget(controls_label)
        
        self.select_all_button = QPushButton("✅ Select All Episodes")
        self.select_all_button.clicked.connect(self.select_all_episodes)
        self.select_all_button.setEnabled(False)  # Disabled by default
        self.select_all_button.setToolTip("Select all available episodes (Ctrl+A)")
        episode_controls_layout.addWidget(self.select_all_button)
        
        self.select_none_button = QPushButton("❌ Select None")
        self.select_none_button.clicked.connect(self.select_no_episodes)
        self.select_none_button.setEnabled(False)  # Disabled by default
        self.select_none_button.setToolTip("Deselect all episodes (Ctrl+D)")
        episode_controls_layout.addWidget(self.select_none_button)
        
        episode_controls_layout.addStretch()  # Push buttons to the left
        main_layout.addLayout(episode_controls_layout)

        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.play_button = QPushButton("▶️ Play Selected Episodes")
        self.play_button.setObjectName("playButton")
        self.play_button.clicked.connect(self.start_playback)
        self.play_button.setToolTip("Stream selected episodes directly (Ctrl+P)")
        self.play_button.setEnabled(False)  # Disabled by default
        action_layout.addWidget(self.play_button)
        
        self.download_button = QPushButton("⬇️ Download Selected Episodes")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setToolTip("Start downloading selected episodes (Enter)")
        action_layout.addWidget(self.download_button)
        action_layout.addStretch()
        
        main_layout.addLayout(action_layout)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # --- Keyboard Shortcuts ---
        self.setup_shortcuts()

    def _setup_system_tray(self):
        """Setup system tray icon and menu."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "System Tray",
                "System tray is not available on this system."
            )
            return

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon (you can replace this with a proper icon file)
        icon = self._create_tray_icon()
        self.tray_icon.setIcon(icon)
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show/Hide action
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide_window)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        # Update cache action
        update_action = QAction("Update Cache", self)
        update_action.triggered.connect(self.start_cache_update)
        tray_menu.addAction(update_action)
        
        # Start/Stop monitoring
        self.monitor_action = QAction("Start Monitoring", self)
        self.monitor_action.triggered.connect(self.toggle_monitoring)
        tray_menu.addAction(self.monitor_action)
        
        tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Connect tray icon activation
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()
        
        # Set tooltip
        self.tray_icon.setToolTip("AnimePahe Downloader")
        
        # Show tray message
        self.tray_icon.showMessage(
            "AnimePahe Downloader",
            "Application started and running in system tray",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _create_tray_icon(self):
        """Create a simple tray icon."""
        # Create a simple colored square icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(33, 150, 243))  # Blue color
        return QIcon(pixmap)

    def load_local_anime_list(self):
        """Loads the anime list from the local cache file and populates the list widget."""
        self.local_anime_list = []
        try:
            with open(constants.ANIME_LIST_CACHE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    slug, title = line.strip().split("::::", 1)
                    self.local_anime_list.append({"title": title, "session": slug})
        except FileNotFoundError:
            self.status_bar.showMessage(
                "Anime cache not found. Click 'Update Cache' to download it."
            )

        self.local_anime_list.sort(key=lambda x: x["title"])
        self.filter_anime_list()
        
        # Initially disable episode selection buttons since no anime is selected
        self.select_all_button.setEnabled(False)
        self.select_none_button.setEnabled(False)
        self.play_button.setEnabled(False)

    def filter_anime_list(self):
        """Filters the anime list in the UI based on the search bar text."""
        query = self.search_bar.text().lower()
        self.results_list.clear()
        for anime_data in self.local_anime_list:
            if query in anime_data["title"].lower():
                item = QListWidgetItem(anime_data["title"])
                # Store the full data dict in the item
                item.setData(Qt.ItemDataRole.UserRole, anime_data)
                self.results_list.addItem(item)
    def start_cache_update(self):
        """Start async cache update (UI disabled during run)."""
        if self.worker and self.worker.isRunning():
            return
        self.update_cache_button.setEnabled(False)
        self.status_bar.showMessage("Updating anime list cache from server...")
        self.worker = UpdateCacheWorker(self.api)
        self.worker.finished.connect(self.on_cache_update_finished)
        self.worker.start()

    def on_cache_update_finished(self, count: int):
        """Handle completion of cache update."""
        self.last_cache_count = count
        if count > 0:
            self.status_bar.showMessage(f"Cache updated: {count} entries.", 5000)
            self.load_local_anime_list()
        elif count == 0:
            self.status_bar.showMessage("Cache updated but zero entries parsed.", 7000)
            QMessageBox.warning(
                self,
                "Empty Cache",
                (
                    "The cache update completed but no entries were found.\n"
                    f"Base URL: {constants.get_base_url()}\n"
                    "Possible causes:\n"
                    " - Site layout changed\n - Incorrect base URL\n - Temporary server issue\n\n"
                    "Try updating the base URL in settings (config.json) or retry later."
                ),
            )
        else:  # -1
            self.status_bar.showMessage(
                "Cache update failed (network or write error).", 7000
            )
            QMessageBox.warning(
                self,
                "Cache Update Failed",
                (
                    "Could not download the anime list.\n"
                    f"Base URL: {constants.get_base_url()}\n"
                    "Check your internet connection or adjust the base URL, then retry."
                ),
            )
        self.update_cache_button.setEnabled(True)

    def on_anime_selected(self, item: QListWidgetItem):
        """Fetches the episode list for the selected anime(s) in a background worker."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            return
        
        # For now, show episodes for the first selected anime
        anime_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        if len(selected_items) > 1:
            self.status_bar.showMessage(
                f"Selected {len(selected_items)} anime. Showing episodes for {anime_data['title']}..."
            )
        else:
            self.status_bar.showMessage(f"Fetching episodes for {anime_data['title']}...")
        
        self.worker = EpisodeWorker(self.api, anime_data)
        self.worker.finished.connect(self.on_episodes_fetched)
        self.worker.start()

    def on_episodes_fetched(self, anime):
        """Populates the episode table with data from the fetched anime object."""
        self.current_anime = anime
        self.episode_table.setRowCount(0)
        if not anime or not anime.episodes:
            self.status_bar.showMessage("Could not fetch episode list.", 5000)
            self.select_all_button.setEnabled(False)
            self.select_none_button.setEnabled(False)
            self.play_button.setEnabled(False)
            return

        self.episode_table.setRowCount(len(anime.episodes))
        for i, episode in enumerate(anime.episodes):
            # Column 0: Episode Number
            self.episode_table.setItem(
                i, 0, QTableWidgetItem(f"Episode {episode.number}")
            )

            # Column 1: Download Status
            status = "Downloaded" if episode.is_downloaded else "Not Downloaded"
            status_item = QTableWidgetItem(status)
            if episode.is_downloaded:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.episode_table.setItem(i, 1, status_item)

            # Column 2: Download Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            check_state = (
                Qt.CheckState.Unchecked
                if episode.is_downloaded
                else Qt.CheckState.Checked
            )
            checkbox.setCheckState(check_state)
            if episode.is_downloaded:
                checkbox.setFlags(checkbox.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                checkbox.setBackground(Qt.GlobalColor.lightGray)
            self.episode_table.setItem(i, 2, checkbox)

        downloaded_count = sum(1 for ep in anime.episodes if ep.is_downloaded)
        total_count = len(anime.episodes)
        self.status_bar.showMessage(
            f"Loaded {total_count} episodes for {anime.name} ({downloaded_count} already downloaded)."
        )
        
        self.select_all_button.setEnabled(True)
        self.select_none_button.setEnabled(True)
        self.play_button.setEnabled(True)
    def start_download(self):
        """Starts the download process for all episodes checked in the table."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No anime selected.", 3000)
            return

        # If only one anime is selected, use the current episode table selection
        if len(selected_items) == 1:
            if not self.current_anime:
                return

            selected_episodes = []
            for i in range(self.episode_table.rowCount()):
                if self.episode_table.item(i, 2).checkState() == Qt.CheckState.Checked:
                    episode_number_str = self.episode_table.item(i, 0).text().split(" ")[-1]
                    if episode_number_str.isdigit():
                        episode_number = int(episode_number_str)
                        episode = self.current_anime.get_episode(episode_number)
                        if episode and not episode.is_downloaded:
                            selected_episodes.append(episode)

            if not selected_episodes:
                self.status_bar.showMessage("No new episodes selected for download.", 3000)
                return

            self.download_button.setEnabled(False)
            self.worker = DownloadWorker(
                self.api,
                self.downloader,
                self.current_anime,
                selected_episodes,
                config_manager.load_config(),
            )
            self.worker.progress_update.connect(self.update_progress)
            self.worker.finished.connect(self.on_download_finished)
            self.worker.log.connect(self.log_message)
            self.worker.start()
        else:
            # Multiple anime selected
            reply = QMessageBox.question(
                self,
                "Download Multiple Anime",
                f"You have selected {len(selected_items)} anime.\n"
                "This will download ALL available episodes for each anime.\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.download_button.setEnabled(False)
                self.status_bar.showMessage(f"Preparing to download {len(selected_items)} anime...")
                self.worker = MultiAnimeDownloadWorker(
                    self.api,
                    self.downloader,
                    [item.data(Qt.ItemDataRole.UserRole) for item in selected_items],
                    config_manager.load_config(),
                )
                self.worker.progress_update.connect(self.update_progress)
                self.worker.finished.connect(self.on_download_finished)
                self.worker.log.connect(self.log_message)
                self.worker.start()

    def update_progress(self, current: int, total: int, message: str):
        """Updates the progress bar and status message during downloads."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Downloading... {message}")

    def log_message(self, message: str):
        """Displays a log message in the status bar."""
        self.status_bar.showMessage(message, 4000)

    def on_download_finished(self):
        """Called when the download worker has finished all tasks."""
        self.status_bar.showMessage("All selected downloads finished.", 5000)
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(0)
        if self.current_anime:
            current_item = self.results_list.currentItem()
            if current_item:
                self.on_anime_selected(current_item)

    def start_playback(self):
        """Starts playback of selected episodes using an external media player."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No anime selected.", 3000)
            return

        if not self.current_anime:
            self.status_bar.showMessage("No episodes loaded.", 3000)
            return

        # Get selected episodes
        selected_episodes = []
        for i in range(self.episode_table.rowCount()):
            checkbox = self.episode_table.item(i, 2)
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                episode_num = self.current_anime.episodes[i].number
                episode_session = self.current_anime.episodes[i].session
                selected_episodes.append((episode_num, episode_session))

        if not selected_episodes:
            self.status_bar.showMessage("No episodes selected for playback.", 3000)
            return

        # Import the detect_media_player function from CLI
        from ..cli.commands import detect_media_player
        
        # Detect available media player
        media_player = detect_media_player()
        if not media_player:
            QMessageBox.warning(
                self,
                "No Media Player Found",
                "No compatible media player found.\n\n"
                "Please install one of the following:\n"
                "• mpv (recommended)\n"
                "• VLC\n"
                "• ffplay (part of FFmpeg)\n"
                "• mplayer\n\n"
                "Installation suggestions:\n"
                "• Ubuntu/Debian: sudo apt install mpv\n"
                "• macOS: brew install mpv\n"
                "• Windows: Download from https://mpv.io/"
            )
            return

        # Get quality and audio settings from config
        app_config = config_manager.load_config()
        quality = app_config.get("quality", "best")
        audio = app_config.get("audio", "jpn")

        self.status_bar.showMessage(f"Starting playback of {len(selected_episodes)} episode(s) with {media_player}...")

        # Start playback worker
        from .workers import PlaybackWorker
        self.play_button.setEnabled(False)
        self.worker = PlaybackWorker(
            self.api,
            self.current_anime.name,
            self.current_anime.slug,
            selected_episodes,
            quality,
            audio,
            media_player
        )
        self.worker.finished.connect(self.on_playback_finished)
        self.worker.error.connect(self.on_playback_error)
        self.worker.episode_started.connect(self.on_episode_playback_started)
        self.worker.start()

    def on_playback_finished(self):
        """Called when playback worker finishes."""
        self.status_bar.showMessage("Playback session finished.", 3000)
        self.play_button.setEnabled(True)

    def on_playback_error(self, error_message):
        """Called when playback worker encounters an error."""
        self.status_bar.showMessage(f"Playback error: {error_message}", 5000)
        self.play_button.setEnabled(True)
        QMessageBox.warning(self, "Playback Error", f"Failed to start playback:\n{error_message}")

    def on_episode_playback_started(self, episode_num, anime_name):
        """Called when an episode starts playing."""
        self.status_bar.showMessage(f"Playing {anime_name} Episode {episode_num}...", 0)

    def select_all_episodes(self):
        """Selects all non-downloaded episodes in the episode table."""
        if not self.current_anime:
            return
            
        selected_count = 0
        for i in range(self.episode_table.rowCount()):
            checkbox = self.episode_table.item(i, 2)
            if checkbox and checkbox.flags() & Qt.ItemFlag.ItemIsEnabled:
                checkbox.setCheckState(Qt.CheckState.Checked)
                selected_count += 1
        
        if selected_count > 0:
            self.status_bar.showMessage(f"Selected {selected_count} episodes for download.", 3000)
        else:
            self.status_bar.showMessage("No episodes available for selection.", 3000)
    
    def select_no_episodes(self):
        """Deselects all episodes in the episode table."""
        if not self.current_anime:
            return
            
        deselected_count = 0
        for i in range(self.episode_table.rowCount()):
            checkbox = self.episode_table.item(i, 2)
            if checkbox and checkbox.flags() & Qt.ItemFlag.ItemIsEnabled:
                if checkbox.checkState() == Qt.CheckState.Checked:
                    deselected_count += 1
                checkbox.setCheckState(Qt.CheckState.Unchecked)
        
        if deselected_count > 0:
            self.status_bar.showMessage(f"Deselected {deselected_count} episodes.", 3000)
        else:
            self.status_bar.showMessage("No episodes were selected.", 3000)
    
    def setup_shortcuts(self):
        """Sets up keyboard shortcuts for better usability."""
        # Ctrl+F to focus search bar
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(lambda: self.search_bar.setFocus())
        
        # Ctrl+A to select all episodes
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(lambda: self.select_all_episodes() if self.select_all_button.isEnabled() else None)
        
        # Ctrl+D to deselect all episodes
        select_none_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        select_none_shortcut.activated.connect(lambda: self.select_no_episodes() if self.select_none_button.isEnabled() else None)
        
        # Enter to start download
        download_shortcut = QShortcut(QKeySequence("Return"), self)
        download_shortcut.activated.connect(self.start_download)
        
        # Ctrl+P to start playback
        play_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        play_shortcut.activated.connect(self.start_playback)
        
        # F5 to refresh cache
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.start_cache_update)
    def _apply_modern_styling(self):
        """Applies modern styling and respects system theme."""
        # Set a modern font
        font = QFont()
        if sys.platform == "darwin":  # macOS
            font.setFamily("SF Pro Display")
        elif sys.platform.startswith("linux"):  # Linux
            font.setFamily("Ubuntu, Roboto, sans-serif")
        else:  # Windows
            font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.setFont(font)
        
        # Detect if system is using dark theme
        is_dark_theme = self._detect_dark_theme()
        
        # Define colors based on theme
        if is_dark_theme:
            bg_color = "#1e1e1e"
            surface_color = "#2d2d2d"
            card_color = "#383838"
            border_color = "#404040"
            text_color = "#ffffff"
            secondary_text = "#b3b3b3"
            accent_color = "#0078d4"
            hover_color = "#404040"
            button_color = "#333333"
            success_color = "#4CAF50"
            selected_color = "#0078d4"
            disabled_color = "#666666"
        else:
            bg_color = "#ffffff"
            surface_color = "#f8f9fa"
            card_color = "#ffffff"
            border_color = "#dee2e6"
            text_color = "#212529"
            secondary_text = "#6c757d"
            accent_color = "#0078d4"
            hover_color = "#e9ecef"
            button_color = "#f8f9fa"
            success_color = "#28a745"
            selected_color = "#0078d4"
            disabled_color = "#adb5bd"
        
        # Apply comprehensive dark/light theme stylesheet
        modern_style = f"""
        QMainWindow {{
            background-color: {bg_color};
            color: {text_color};
        }}
        
        QWidget {{
            background-color: {bg_color};
            color: {text_color};
        }}
        
        QLineEdit {{
            padding: 8px 12px;
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: {card_color};
            color: {text_color};
            font-size: 10pt;
            selection-background-color: {selected_color};
        }}
        
        QLineEdit:focus {{
            border-color: {accent_color};
            background-color: {surface_color};
        }}
        
        QPushButton {{
            padding: 8px 16px;
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: {button_color};
            color: {text_color};
            font-size: 10pt;
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {hover_color};
            border-color: {accent_color};
        }}
        
        QPushButton:pressed {{
            background-color: {border_color};
        }}
        
        QPushButton:disabled {{
            background-color: {surface_color};
            color: {disabled_color};
            border-color: {disabled_color};
        }}
        
        QListWidget {{
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: {card_color};
            color: {text_color};
            outline: none;
            padding: 4px;
        }}
        
        QListWidget::item {{
            padding: 10px 12px;
            border: none;
            border-radius: 4px;
            margin: 1px;
        }}
        
        QListWidget::item:selected {{
            background-color: {selected_color};
            color: white;
        }}
        
        QListWidget::item:hover {{
            background-color: {hover_color};
        }}
        
        QTableWidget {{
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: {card_color};
            color: {text_color};
            gridline-color: {border_color};
            outline: none;
        }}
        
        QTableWidget::item {{
            padding: 10px 12px;
            border: none;
        }}
        
        QTableWidget::item:selected {{
            background-color: {selected_color};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {surface_color};
            color: {text_color};
            padding: 10px 12px;
            border: none;
            border-right: 1px solid {border_color};
            border-bottom: 1px solid {border_color};
            font-weight: 600;
        }}
        
        QProgressBar {{
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: {surface_color};
            text-align: center;
            color: {text_color};
            font-weight: 500;
        }}
        
        QProgressBar::chunk {{
            background-color: {accent_color};
            border-radius: 5px;
        }}
        
        QStatusBar {{
            background-color: {surface_color};
            color: {text_color};
            border-top: 1px solid {border_color};
            padding: 4px;
        }}
        
        QLabel {{
            color: {text_color};
            font-size: 10pt;
            background-color: transparent;
        }}
        
        QPushButton#downloadButton {{
            background-color: {success_color};
            color: white;
            font-weight: 600;
            font-size: 12pt;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
        }}
        
        QPushButton#downloadButton:hover {{
            background-color: {'#45a049' if is_dark_theme else '#218838'};
        }}
        
        QPushButton#downloadButton:disabled {{
            background-color: {disabled_color};
            color: {secondary_text};
        }}
        
        QPushButton#playButton {{
            background-color: {'#2196F3' if is_dark_theme else '#1976D2'};
            border: none;
            color: white;
            font-weight: 600;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 11pt;
        }}
        
        QPushButton#playButton:hover {{
            background-color: {'#1976D2' if is_dark_theme else '#1565C0'};
        }}
        
        QPushButton#playButton:disabled {{
            background-color: {disabled_color};
            color: {secondary_text};
        }}
        """
        
        self.setStyleSheet(modern_style)
        self.download_button.setObjectName("downloadButton")
        self.episode_table.setAlternatingRowColors(True)
        self.results_list.setAlternatingRowColors(True)
        
        # Connect to palette change events
        app = QApplication.instance()
        if app:
            app.paletteChanged.connect(self._on_palette_changed)
    def show_window(self):
        """Show the main window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_window(self):
        """Hide the main window to system tray."""
        self.hide()

    def tray_icon_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide_window()
            else:
                self.show_window()

    def toggle_monitoring(self):
        """Toggle background monitoring for new episodes."""
        if self.update_timer.isActive():
            self.update_timer.stop()
            self.monitor_action.setText("Start Monitoring")
            self.tray_icon.showMessage(
                "AnimePahe Downloader",
                "Background monitoring stopped",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self.status_bar.showMessage("Background monitoring stopped", 3000)
        else:
            # Start monitoring every hour (configurable)
            app_config = config_manager.load_config()
            interval_minutes = app_config.get("update_interval_hours", 1) * 60
            self.update_timer.start(interval_minutes * 60 * 1000)  # Convert to milliseconds
            self.monitor_action.setText("Stop Monitoring")
            self.tray_icon.showMessage(
                "AnimePahe Downloader",
                f"Background monitoring started (checking every {interval_minutes} minutes)",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            self.status_bar.showMessage(f"Background monitoring active (every {interval_minutes} min)", 5000)

    def background_update_check(self):
        """Perform background update check for new episodes."""
        if self.worker and self.worker.isRunning():
            return  # Don't start if another operation is running
        
        try:
            # Import notification here to avoid circular imports
            from plyer import notification
            
            # Check for new episodes
            new_episodes = self.api.check_for_updates()
            if new_episodes:
                # Filter for anime in user's list
                try:
                    with open(constants.MY_ANIME_LIST_FILE, "r", encoding="utf-8") as f:
                        my_anime_list = [line.strip() for line in f]
                except FileNotFoundError:
                    my_anime_list = []
                
                relevant_episodes = [
                    ep for ep in new_episodes 
                    if ep["anime_title"] in my_anime_list
                ]
                
                if relevant_episodes:
                    # Show notification
                    notification.notify(
                        title="AnimePahe Downloader",
                        message=f"Found {len(relevant_episodes)} new episodes!",
                        app_name="Animepahe Downloader",
                        timeout=10
                    )
                    
                    # Show tray message
                    self.tray_icon.showMessage(
                        "New Episodes Available",
                        f"Found {len(relevant_episodes)} new episodes in your watchlist",
                        QSystemTrayIcon.MessageIcon.Information,
                        5000
                    )
                    
                    # Update status bar if window is visible
                    if self.isVisible():
                        self.status_bar.showMessage(
                            f"Background check: Found {len(relevant_episodes)} new episodes", 
                            10000
                        )
        except Exception as e:
            logger.warning(f"Background update check failed: {e}")

    def quit_application(self):
        """Quit the application completely."""
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        if self.tray_icon:
            self.tray_icon.hide()
        
        QApplication.quit()

    def closeEvent(self, event):
        """Override close event to minimize to tray instead of quitting."""
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "AnimePahe Downloader",
                "Application minimized to tray. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self.hide()
            event.ignore()
        else:
            event.accept()

    def _detect_dark_theme(self):
        """Detect if the system is using a dark theme."""
        # Method 1: Check Qt palette
        palette = self.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        qt_is_dark = window_color.lightness() < 128
        
        # Method 2: Check environment variables and desktop settings
        env_is_dark = False
        
        try:
            # Check for GNOME/GTK dark theme
            if os.environ.get('XDG_CURRENT_DESKTOP', '').lower() in ['gnome', 'unity', 'gtk']:
                try:
                    result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        theme_name = result.stdout.strip().strip("'\"").lower()
                        env_is_dark = 'dark' in theme_name or 'adwaita-dark' in theme_name
                except:
                    pass
            
            # Check for KDE dark theme
            elif os.environ.get('XDG_CURRENT_DESKTOP', '').lower() in ['kde', 'plasma']:
                try:
                    kde_config = os.path.expanduser('~/.config/kdeglobals')
                    if os.path.exists(kde_config):
                        with open(kde_config, 'r') as f:
                            content = f.read()
                            if 'ColorScheme=Breeze Dark' in content or 'ColorScheme=BreezeDark' in content:
                                env_is_dark = True
                except:
                    pass
            
            # Check for Hyprland and other Wayland compositors
            elif os.environ.get('XDG_CURRENT_DESKTOP', '').lower() in ['hyprland', 'sway', 'river', 'wayfire']:
                try:
                    result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        theme_name = result.stdout.strip().strip("'\"").lower()
                        env_is_dark = 'dark' in theme_name or 'adwaita-dark' in theme_name
                    
                    if not env_is_dark:
                        result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'], 
                                              capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            color_scheme = result.stdout.strip().strip("'\"").lower()
                            env_is_dark = 'dark' in color_scheme or 'prefer-dark' in color_scheme
                except:
                    pass
            
            # Check for general dark theme environment variables
            if not env_is_dark:
                dark_env_vars = ['GTK_THEME', 'QT_STYLE_OVERRIDE']
                for var in dark_env_vars:
                    value = os.environ.get(var, '').lower()
                    if 'dark' in value:
                        env_is_dark = True
                        break
        
        except Exception as e:
            print(f"Warning: Could not detect system theme: {e}")
        
        # Method 3: Force dark mode if user has set environment variable
        force_dark = os.environ.get('ANIMEPAHE_DL_DARK_MODE', '').lower() in ['1', 'true', 'yes']
        force_light = os.environ.get('ANIMEPAHE_DL_LIGHT_MODE', '').lower() in ['1', 'true', 'yes']
        
        if force_dark:
            return True
        elif force_light:
            return False
        
        # Use environment detection if available, otherwise fall back to Qt
        final_result = env_is_dark if env_is_dark else qt_is_dark
        
        print(f"Theme detection: Qt={qt_is_dark}, Env={env_is_dark}, Final={final_result}")
        return final_result
    
    def _on_palette_changed(self):
        """Handle system theme changes."""
        self._apply_modern_styling()

    def open_settings(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()


def run_gui():
    """Initializes and runs the PyQt6 GUI application."""
    # Setup signal handling for graceful shutdown
    signal_handler = setup_signal_handling()
    
    # Set Qt platform plugin for better Wayland support
    if not os.environ.get('QT_QPA_PLATFORM'):
        if os.environ.get('WAYLAND_DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'wayland'
        elif os.environ.get('DISPLAY'):
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("AnimePahe Downloader")
    app.setApplicationVersion("5.4.0")
    app.setOrganizationName("AnimePahe-DL")
    
    window = MainWindow()
    
    # Register GUI shutdown callback
    def gui_shutdown():
        if window.worker and window.worker.isRunning():
            window.worker.terminate()
        app.quit()
    
    register_shutdown_callback(gui_shutdown)
    
    window.show()
    sys.exit(app.exec())