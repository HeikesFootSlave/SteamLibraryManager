"""
Main Window - Steam Login & Secure Settings
Speichern als: src/ui/main_window.py
"""
# ... (Imports wie gehabt)
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu, QMessageBox, QInputDialog,
    QSplitter, QCheckBox, QProgressDialog, QApplication)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from typing import Optional, List, Dict
from pathlib import Path

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.appinfo_manager import AppInfoManager
from src.core.steam_auth import SteamAuthManager # NEU
from src.integrations.steam_store import SteamStoreScraper, FranchiseDetector
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import MetadataEditDialog, BulkMetadataEditDialog, MetadataRestoreDialog
from src.utils.i18n import t, init_i18n
from src.ui.settings_dialog import SettingsDialog
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.components.category_tree import GameTreeWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('ui.main.title'))
        self.resize(1400, 800)

        # Managers
        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None
        self.auth_manager = SteamAuthManager() # NEU
        
        # Signals verbinden
        self.auth_manager.auth_success.connect(self._on_steam_login_success)
        self.auth_manager.auth_error.connect(self._on_steam_login_error)

        self.selected_game: Optional[Game] = None
        self.selected_games: List[Game] = []

        self._create_ui()
        self._load_data()

    # ... _create_ui (Bleibt fast gleich, nur Login Button checken) ...
    def _create_ui(self):
        # ... (Menü Code wie vorher) ...
        menubar = self.menuBar()
        
        # ... (File, Edit Menus ...)
        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(QAction(t('ui.menu.refresh'), self, triggered=self.refresh_data))
        file_menu.addAction(QAction(t('ui.menu.save'), self, triggered=self.force_save))
        file_menu.addSeparator()
        file_menu.addAction(QAction(t('ui.menu.exit'), self, triggered=self.close))
        
        edit_menu = menubar.addMenu(t('ui.menu.edit'))
        edit_menu.addAction(QAction(t('ui.menu.bulk_edit'), self, triggered=self.bulk_edit_metadata))
        edit_menu.addAction(QAction(t('ui.toolbar.auto_categorize'), self, triggered=self.auto_categorize))
        
        settings_menu = menubar.addMenu(t('ui.toolbar.settings'))
        settings_menu.addAction(QAction(t('ui.menu.settings'), self, triggered=self.show_settings))
        settings_menu.addSeparator()
        settings_menu.addAction(QAction(t('ui.menu.restore'), self, triggered=self.restore_metadata_changes))

        help_menu = menubar.addMenu(t('ui.menu.help'))
        github_action = QAction(t('ui.menu.github'), self)
        github_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/")))
        help_menu.addAction(github_action)
        help_menu.addAction(QAction(t('ui.menu.about'), self, triggered=self.show_about))

        # Login Action in Toolbar
        self.login_action = QAction(t('ui.toolbar.login'), self)
        self.login_action.triggered.connect(self._start_steam_login)

        self.user_label = QLabel(t('ui.status.not_logged_in'))
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)

        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self._refresh_toolbar()
        
        # ... (Rest der UI wie Splitter, Tree, Details etc. bleibt gleich) ...
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        left_layout.addLayout(search_layout)
        
        self.tree = GameTreeWidget()
        self.tree.game_clicked.connect(self.on_game_selected)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left_widget)
        
        # Right
        self.details_widget = GameDetailsWidget()
        self.details_widget.category_changed.connect(self._on_category_changed_from_details)
        self.details_widget.edit_metadata.connect(self.edit_game_metadata)
        splitter.addWidget(self.details_widget)
        
        layout.addWidget(splitter)
        self.statusbar = self.statusBar()

    def _refresh_toolbar(self):
        self.toolbar.clear()
        self.toolbar.addAction(t('ui.toolbar.refresh'), self.refresh_data)
        self.toolbar.addAction(t('ui.toolbar.auto_categorize'), self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(t('ui.toolbar.settings'), self.show_settings)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.login_action) # LOGIN BUTTON

    # --- OAUTH LOGIC ---
    def _start_steam_login(self):
        # Zeige Info Dialog
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.info'))
        # Starte Auth
        self.auth_manager.start_login()
        self.set_status(t('ui.login.status_waiting'))

    def _on_steam_login_success(self, code: str):
        # Hier würden wir jetzt den Code gegen ein Token tauschen
        # Da wir noch keine Backend-Logik für den Token-Swap haben (Client Secret),
        # speichern wir erstmal den Code oder simulieren den Erfolg.
        print(f"Auth Code received: {code}")
        self.set_status(t('ui.login.status_success'))
        QMessageBox.information(self, t('ui.login.title'), t('ui.login.status_success'))
        
        # TODO: Implementiere Token Exchange mit requests
        # response = requests.post(...)
        # config.STEAM_API_KEY = response.json()['access_token']
        # self.refresh_data()

    def _on_steam_login_error(self, error: str):
        self.set_status(t('ui.login.status_failed'))
        QMessageBox.critical(self, t('ui.dialogs.error'), error)

    # ... (Rest der Methoden wie _load_data, show_settings, etc. bleiben gleich)
    # Nur _apply_settings muss den API Key speichern:
    
    def _apply_settings(self, settings: dict):
        config.UI_LANGUAGE = settings['ui_language']
        config.TAGS_LANGUAGE = settings['tags_language']
        config.TAGS_PER_GAME = settings['tags_per_game']
        config.IGNORE_COMMON_TAGS = settings['ignore_common_tags']
        config.STEAMGRIDDB_API_KEY = settings['steamgriddb_api_key'] # NEU: Speichern im RAM
        
        if settings['steam_path']:
            config.STEAM_PATH = Path(settings['steam_path'])
            
        self._save_settings(settings) # Speichern auf Disk
        QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.success'))

    def _save_settings(self, settings: dict):
        import json
        settings_file = config.DATA_DIR / 'settings.json'
        # Wir speichern ALLES (auch API Keys der User) in der JSON
        # .env wird nicht überschrieben
        data = {
            'ui_language': settings['ui_language'],
            'tags_language': settings['tags_language'],
            'tags_per_game': settings['tags_per_game'],
            'ignore_common_tags': settings['ignore_common_tags'],
            'steamgriddb_api_key': settings['steamgriddb_api_key'], # User Key
            'max_backups': settings['max_backups']
        }
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)
