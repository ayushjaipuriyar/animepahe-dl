"""
Graphical User Interface for the AnimePahe Downloader.

This module contains the main application window and all related GUI components
built with PyQt6. It uses worker threads to keep the UI responsive during
network operations and downloads.
"""

import sys
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
    QDialog,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QListWidgetItem,
    QTableWidgetItem,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from . import config
from . import config_manager
from .api import AnimePaheAPI
from .downloader import Downloader
from .workers import EpisodeWorker, DownloadWorker, UpdateCacheWorker


class SettingsDialog(QDialog):
    """
    A dialog window for configuring user settings.

    This dialog allows the user to set the default download quality, audio language,
    number of download threads, and the download directory.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(300)
        self.config = config_manager.load_config()

        layout = QFormLayout(self)

        # --- Quality Setting ---
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["best", "1080", "720", "360"])
        self.quality_combo.setCurrentText(self.config.get("quality", "best"))
        layout.addRow("Default Quality:", self.quality_combo)

        # --- Audio Setting ---
        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["jpn", "eng"])
        self.audio_combo.setCurrentText(self.config.get("audio", "jpn"))
        layout.addRow("Default Audio:", self.audio_combo)

        # --- Threads Setting ---
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 100)
        self.threads_spinbox.setValue(self.config.get("threads", 50))
        layout.addRow("Download Threads:", self.threads_spinbox)

        # --- Download Directory Setting ---
        self.download_dir_edit = QLineEdit(self.config.get("download_directory"))
        layout.addRow("Download Directory:", self.download_dir_edit)

        # --- Dialog Buttons ---
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def accept(self):
        """Saves the configuration when the OK button is clicked."""
        self.config["quality"] = self.quality_combo.currentText()
        self.config["audio"] = self.audio_combo.currentText()
        self.config["threads"] = self.threads_spinbox.value()
        self.config["download_directory"] = self.download_dir_edit.text()
        config_manager.save_config(self.config)
        super().accept()


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
        if app_cfg.get("base_url") and app_cfg.get("base_url") != config.BASE_URL:
            try:
                config.set_base_url(app_cfg["base_url"])
            except Exception:
                pass  # Fail silently; will surface in cache update if invalid

        # Build API client (forced insecure SSL per user request)
        self.api = AnimePaheAPI(verify_ssl=False)
        self.downloader = Downloader(self.api)
        self.current_anime = None
        self.local_anime_list = []
        self.worker = None  # To hold a reference to the running worker
        self.last_cache_count = None

        self._setup_ui()
        self.load_local_anime_list()
        # Auto-update cache if empty on launch
        if not self.local_anime_list:
            self.start_cache_update()

    def _setup_ui(self):
        """Initializes all UI elements and layouts."""
        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Search Area ---
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter anime list...")
        self.search_bar.textChanged.connect(self.filter_anime_list)
        search_layout.addWidget(self.search_bar)

        self.update_cache_button = QPushButton("Update Cache")
        self.update_cache_button.clicked.connect(self.start_cache_update)
        search_layout.addWidget(self.update_cache_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        search_layout.addWidget(self.settings_button)
        main_layout.addLayout(search_layout)

        # --- Results and Episodes Panels ---
        content_layout = QHBoxLayout()
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_anime_selected)
        content_layout.addWidget(self.results_list)

        self.episode_table = QTableWidget()
        self.episode_table.setColumnCount(3)
        self.episode_table.setHorizontalHeaderLabels(["Episode", "Status", "Download"])
        header = self.episode_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.episode_table.verticalHeader().setVisible(False)
        content_layout.addWidget(self.episode_table)
        main_layout.addLayout(content_layout)

        # --- Download Button ---
        self.download_button = QPushButton("Download Selected")
        self.download_button.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_button)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)

    def load_local_anime_list(self):
        """Loads the anime list from the local cache file and populates the list widget."""
        self.local_anime_list = []
        try:
            with open(config.ANIME_LIST_CACHE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    slug, title = line.strip().split("::::", 1)
                    self.local_anime_list.append({"title": title, "session": slug})
        except FileNotFoundError:
            self.status_bar.showMessage(
                "Anime cache not found. Click 'Update Cache' to download it."
            )

        self.local_anime_list.sort(key=lambda x: x["title"])
        self.filter_anime_list()

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
        """Handle completion of cache update.

        Args:
            count: Entry count (>0 success, 0 empty parse, -1 failure)
        """
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
                    f"Base URL: {config.BASE_URL}\n"
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
                    f"Base URL: {config.BASE_URL}\n"
                    "Check your internet connection or adjust the base URL, then retry."
                ),
            )
        self.update_cache_button.setEnabled(True)

    def on_anime_selected(self, item: QListWidgetItem):
        """
        Fetches the episode list for the selected anime in a background worker.

        Args:
            item: The QListWidgetItem that was clicked.
        """
        if not item:
            return
        anime_data = item.data(Qt.ItemDataRole.UserRole)
        self.status_bar.showMessage(f"Fetching episodes for {anime_data['title']}...")
        self.worker = EpisodeWorker(self.api, anime_data)
        self.worker.finished.connect(self.on_episodes_fetched)
        self.worker.start()

    def on_episodes_fetched(self, anime):
        """
        Populates the episode table with data from the fetched anime object.

        Args:
            anime: The Anime object containing the episode list.
        """
        self.current_anime = anime
        self.episode_table.setRowCount(0)
        if not anime or not anime.episodes:
            self.status_bar.showMessage("Could not fetch episode list.", 5000)
            return

        self.episode_table.setRowCount(len(anime.episodes))
        for i, episode in enumerate(anime.episodes):
            # Column 0: Episode Number
            self.episode_table.setItem(
                i, 0, QTableWidgetItem(f"Episode {episode.number}")
            )

            # Column 1: Download Status
            status = "Downloaded" if episode.is_downloaded else "Not Downloaded"
            self.episode_table.setItem(i, 1, QTableWidgetItem(status))

            # Column 2: Download Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            # Uncheck downloaded episodes by default
            check_state = (
                Qt.CheckState.Unchecked
                if episode.is_downloaded
                else Qt.CheckState.Unchecked
            )
            checkbox.setCheckState(check_state)
            # Disable checkbox for already downloaded episodes
            if episode.is_downloaded:
                checkbox.setFlags(checkbox.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.episode_table.setItem(i, 2, checkbox)

        self.status_bar.showMessage(
            f"Loaded {len(anime.episodes)} episodes for {anime.name}."
        )

    def start_download(self):
        """
        Starts the download process for all episodes checked in the table.
        """
        if not self.current_anime:
            return

        selected_episodes = []
        for i in range(self.episode_table.rowCount()):
            if self.episode_table.item(i, 2).checkState() == Qt.CheckState.Checked:
                episode_number_str = self.episode_table.item(i, 0).text().split(" ")[-1]
                if episode_number_str.isdigit():
                    episode_number = int(episode_number_str)
                    episode = self.current_anime.get_episode(episode_number)
                    # Add to queue only if it exists and is not already downloaded
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

    def update_progress(self, current: int, total: int, message: str):
        """
        Updates the progress bar and status message during downloads.

        Args:
            current: The current progress value.
            total: The maximum progress value.
            message: The status message to display.
        """
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
        # Refresh the episode list to show the new "Downloaded" status
        if self.current_anime:
            current_item = self.results_list.currentItem()
            if current_item:
                self.on_anime_selected(current_item)

    def open_settings(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()


def run_gui():
    """Initializes and runs the PyQt6 GUI application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
