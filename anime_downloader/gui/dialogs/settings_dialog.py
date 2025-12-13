"""
Settings dialog for the GUI application.

This module contains the settings dialog window that allows users to
configure application settings like download directory, quality, etc.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...utils import constants, config_manager


class SettingsDialog(QDialog):
    """
    A dialog window for configuring user settings.

    This dialog allows the user to set the default download quality, audio language,
    number of download threads, download directory, and base URL.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.config = config_manager.load_config()

        # Apply theme-aware styling to the dialog
        is_dark_theme = self.parent()._detect_dark_theme() if self.parent() else False
        
        if is_dark_theme:
            bg_color = "#1e1e1e"
            surface_color = "#2d2d2d"
            card_color = "#383838"
            border_color = "#404040"
            text_color = "#ffffff"
            accent_color = "#0078d4"
            button_color = "#333333"
            hover_color = "#404040"
        else:
            bg_color = "#ffffff"
            surface_color = "#f8f9fa"
            card_color = "#ffffff"
            border_color = "#dee2e6"
            text_color = "#212529"
            accent_color = "#0078d4"
            button_color = "#f8f9fa"
            hover_color = "#e9ecef"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLabel {{
                font-weight: 500;
                color: {text_color};
                background-color: transparent;
            }}
            QLineEdit, QComboBox, QSpinBox {{
                padding: 8px 12px;
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {card_color};
                color: {text_color};
                font-size: 10pt;
                selection-background-color: {accent_color};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {accent_color};
                background-color: {surface_color};
            }}
            QPushButton {{
                padding: 8px 16px;
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {button_color};
                color: {text_color};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: {accent_color};
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {border_color};
                background-color: {card_color};
                color: {text_color};
                selection-background-color: {accent_color};
            }}
        """)

        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add a title
        title_label = QLabel("⚙️ Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("margin-bottom: 10px;")
        layout.addRow(title_label)

        # --- Base URL Setting ---
        self.base_url_edit = QLineEdit(self.config.get("base_url", constants.BASE_URL))
        self.base_url_edit.setPlaceholderText("https://animepahe.si")
        self.base_url_edit.setToolTip("The base URL for the AnimePahe website")
        layout.addRow("🌐 Base URL:", self.base_url_edit)

        # --- Quality Setting ---
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["best", "1080", "720", "360"])
        self.quality_combo.setCurrentText(self.config.get("quality", "best"))
        self.quality_combo.setToolTip("Default video quality for downloads")
        layout.addRow("🎥 Default Quality:", self.quality_combo)

        # --- Audio Setting ---
        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["jpn", "eng"])
        self.audio_combo.setCurrentText(self.config.get("audio", "jpn"))
        self.audio_combo.setToolTip("Default audio language")
        layout.addRow("🔊 Default Audio:", self.audio_combo)

        # --- Threads Setting ---
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 100)
        self.threads_spinbox.setValue(self.config.get("threads", 50))
        self.threads_spinbox.setSuffix(" threads")
        self.threads_spinbox.setToolTip("Number of parallel download threads for segments")
        layout.addRow("⚡ Download Threads:", self.threads_spinbox)

        # --- Concurrent Downloads Setting ---
        self.concurrent_spinbox = QSpinBox()
        self.concurrent_spinbox.setRange(1, 10)
        self.concurrent_spinbox.setValue(self.config.get("concurrent_downloads", 2))
        self.concurrent_spinbox.setSuffix(" episodes")
        self.concurrent_spinbox.setToolTip("Number of episodes to download simultaneously")
        layout.addRow("📥 Concurrent Downloads:", self.concurrent_spinbox)

        # --- Download Directory Setting ---
        dir_layout = QHBoxLayout()
        self.download_dir_edit = QLineEdit(self.config.get("download_directory"))
        self.download_dir_edit.setToolTip("Directory where downloaded episodes will be saved")
        self.browse_button = QPushButton("📁 Browse...")
        self.browse_button.clicked.connect(self.browse_directory)
        self.browse_button.setToolTip("Select download directory")
        dir_layout.addWidget(self.download_dir_edit)
        dir_layout.addWidget(self.browse_button)
        layout.addRow("💾 Download Directory:", dir_layout)

        # --- Dialog Buttons ---
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def browse_directory(self):
        """Opens a directory browser dialog."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", self.download_dir_edit.text()
        )
        if directory:
            self.download_dir_edit.setText(directory)

    def accept(self):
        """Saves the configuration when the OK button is clicked."""
        self.config["base_url"] = self.base_url_edit.text().strip()
        self.config["quality"] = self.quality_combo.currentText()
        self.config["audio"] = self.audio_combo.currentText()
        self.config["threads"] = self.threads_spinbox.value()
        self.config["concurrent_downloads"] = self.concurrent_spinbox.value()
        self.config["download_directory"] = self.download_dir_edit.text()
        config_manager.save_config(self.config)
        
        # Update the base URL in constants if it changed
        if self.config["base_url"] != constants.get_base_url():
            try:
                constants.set_base_url(self.config["base_url"])
            except Exception as e:
                QMessageBox.warning(self, "URL Update", f"Base URL updated but may be invalid: {e}")
        
        super().accept()