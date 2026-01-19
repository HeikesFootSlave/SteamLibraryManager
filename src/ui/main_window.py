"""
Main Window - Clean & i18n-ready
Speichern als: src/ui/main_window.py
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QToolBar, QMenu,
    QMessageBox, QInputDialog, QSplitter, QCheckBox,
    QFrame, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime

from src.config import config
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser
from src.core.appinfo_manager import AppInfoManager
from src.integrations.steam_store import SteamStoreScraper, FranchiseDetector
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.ui.metadata_dialogs import (
    MetadataEditDialog,
    BulkMetadataEditDialog,
    MetadataRestoreDialog
)
from src.utils.i18n import t, init_i18n
from src.ui.settings_dialog import SettingsDialog
from src.ui.game_details_widget import GameDetailsWidget
from src.ui.steam_login_dialog import SteamLoginDialog
from src.ui.components.category_tree import GameTreeWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('ui.main.title'))
        self.resize(1400, 800)

        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.selected_game: Optional[Game] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None
        self.appinfo_data: Optional[Dict] = None
        self.selected_games: List[Game] = []
        self.dialog_games: List[Game] = []

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        # === MENÜBAR ===
        menubar = self.menuBar()

        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(QAction(t('ui.menu.refresh'), self, triggered=self.refresh_data))
        file_menu.addSeparator()
        file_menu.addAction(QAction(t('ui.menu.exit'), self, triggered=self.close))

        tools_menu = menubar.addMenu(t('ui.menu.metadata'))
        tools_menu.addAction(QAction(t('ui.menu.bulk_edit'), self, triggered=self.bulk_edit_metadata))
        tools_menu.addAction(QAction(t('ui.menu.restore'), self, triggered=self.restore_metadata_changes))

        help_menu = menubar.addMenu(t('ui.menu.help'))
        help_menu.addAction(QAction(t('ui.menu.settings'), self, triggered=self.show_settings))

        self.user_label = QLabel(t('ui.status.not_logged_in'))
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)

        # === TOOLBAR ===
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self._refresh_toolbar()

        # === MAIN CONTENT ===
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Categories
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(t('ui.main.search_icon')))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        clear_btn = QPushButton("×")
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        self.tree = GameTreeWidget()
        self.tree.game_clicked.connect(self.on_game_selected)
        self.tree.game_right_clicked.connect(self.on_game_right_click)
        self.tree.category_right_clicked.connect(self.on_category_right_click)
        self.tree.selection_changed.connect(self._on_games_selected)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        # RIGHT: Details
        self.details_widget = GameDetailsWidget()
        self.details_widget.category_changed.connect(self._on_category_changed_from_details)
        self.details_widget.edit_metadata.connect(self.edit_game_metadata)
        splitter.addWidget(self.details_widget)
        splitter.setSizes([450, 950])
        layout.addWidget(splitter)

        self.statusbar = self.statusBar()
        self.set_status(t('ui.status.ready'))

    def _refresh_toolbar(self):
        self.toolbar.clear()
        self.toolbar.addAction(t('ui.toolbar.refresh'), self.refresh_data)
        self.toolbar.addAction(t('ui.toolbar.auto_categorize'), self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(t('ui.toolbar.settings'), self.show_settings)

    def _load_data(self):
        self.set_status(t('ui.status.loading'))

        if not config.STEAM_PATH:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('errors.steam_not_found'))
            return

        user_ids = config.get_all_user_ids()
        if not user_ids:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_users'))
            return

        account_id = user_ids[0]
        steam_id64 = config.STEAM_USER_ID if config.STEAM_USER_ID else account_id
        self.user_label.setText(t('ui.main.user_label', user_id=account_id))

        config_path = config.get_localconfig_path(account_id)
        if not config_path:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.localconfig_not_found'))
            return

        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.localconfig_load_error'))
            return

        if not config.STEAM_API_KEY:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_api_key'))
            return

        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)
        if not self.game_manager.load_from_steam_api(steam_id64):
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.api_load_error'))
            return

        self.game_manager.merge_with_localconfig(self.vdf_parser)
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)

        if config.STEAM_PATH:
            try:
                self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
                self.appinfo_data = self.appinfo_manager.load_appinfo()
            except Exception as e:
                print(f"Error loading AppInfo: {e}")

        self._populate_categories()
        self.set_status(t('ui.status.loaded', count=len(self.game_manager.games)))

    def _populate_categories(self):
        if not self.game_manager: return
        
        categories_data = {}
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.name.lower())
        categories_data[t('ui.categories.all_games')] = all_games

        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.name.lower())
        if favorites:
            categories_data[t('ui.categories.favorites')] = favorites

        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.name.lower())
        if uncat:
            categories_data[t('ui.categories.uncategorized')] = uncat

        cats = self.game_manager.get_all_categories()
        for cat_name in sorted(cats.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name), key=lambda g: g.name.lower())
                categories_data[cat_name] = cat_games

        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]):
        self.selected_games = games
        if len(games) > 1:
            self.set_status(t('ui.status.selected_multiple', count=len(games)))
        elif len(games) == 1:
            self.set_status(t('ui.status.selected', name=games[0].name))

    def on_game_selected(self, game: Game):
        self.selected_game = game
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool):
        game = self.game_manager.get_game(app_id)
        if not game: return

        if checked:
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(app_id, category)

        self.vdf_parser.save()
        self._populate_categories()
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)

    def on_game_right_click(self, game: Game, pos):
        menu = QMenu(self)
        menu.addAction(t('ui.context_menu.view_details'), lambda: self.on_game_selected(game))
        menu.addAction(t('ui.context_menu.toggle_favorite'), lambda: self.toggle_favorite(game))
        menu.addAction(t('ui.context_menu.open_store'), lambda: self.open_in_store(game))
        menu.addSeparator()

        if len(self.selected_games) > 1:
            menu.addAction(t('ui.context_menu.auto_categorize_selected'), self.auto_categorize_selected)
            menu.addSeparator()

        menu.addAction(t('ui.context_menu.edit_metadata'), lambda: self.edit_game_metadata(game))
        menu.exec(pos)

    def on_category_right_click(self, category: str, pos):
        special = [t('ui.categories.all_games'), t('ui.categories.favorites'), t('ui.categories.uncategorized')]
        if category in special: return
        
        menu = QMenu(self)
        menu.addAction(t('ui.context_menu.rename'), lambda: self.rename_category(category))
        menu.addAction(t('ui.context_menu.delete'), lambda: self.delete_category(category))
        menu.addSeparator()
        menu.addAction(t('ui.context_menu.auto_categorize'), lambda: self.auto_categorize_category(category))
        menu.exec(pos)

    def on_search(self, query):
        if not query:
            self._populate_categories()
            return
        if not self.game_manager: return
        
        results = [g for g in self.game_manager.get_all_games() if query.lower() in g.name.lower()]
        if results:
            sorted_results = sorted(results, key=lambda g: g.name.lower())
            self.tree.populate_categories({t('ui.status.found_results', count=len(results)): sorted_results})
            self.tree.expandAll()
            self.set_status(t('ui.status.found_results', count=len(results)))
        else:
            self.tree.clear()
            self.set_status(t('ui.status.no_results'))

    def clear_search(self):
        self.search_entry.clear()
        self._populate_categories()

    def toggle_favorite(self, game: Game):
        if game.is_favorite():
            game.categories.remove('favorite')
            self.vdf_parser.remove_app_category(game.app_id, 'favorite')
        else:
            game.categories.append('favorite')
            self.vdf_parser.add_app_category(game.app_id, 'favorite')
        self.vdf_parser.save()
        self._populate_categories()

    def open_in_store(self, game: Game):
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def rename_category(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, t('ui.context_menu.rename'), t('ui.dialogs.rename_category', old=old_name))
        if ok and new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()

    def delete_category(self, category: str):
        reply = QMessageBox.question(self, t('ui.dialogs.confirm_delete_category', name=category),
                                     t('ui.dialogs.confirm_delete_category_msg'))
        if reply == QMessageBox.StandardButton.Yes:
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    def auto_categorize(self):
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)
        else:
            uncat = self.game_manager.get_uncategorized_games()
            self._show_auto_categorize_dialog(uncat, None)

    def auto_categorize_selected(self):
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)

    def auto_categorize_category(self, category: str):
        games = self.game_manager.get_games_by_category(category)
        self._show_auto_categorize_dialog(games, category)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]):
        self.dialog_games = games
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games),
                                      self._do_auto_categorize, category_name)
        dialog.exec()

    def _do_auto_categorize(self, settings: dict):
        if not settings: return

        backup_dir = self.vdf_parser.config_path.parent
        backup_filename = f'localconfig_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.vdf'
        backup_path = backup_dir / backup_filename
        import shutil
        shutil.copy2(self.vdf_parser.config_path, backup_path)
        self.set_status(t('ui.status.backup_created', name=backup_path.name))

        if settings['scope'] == 'all':
            games = self.game_manager.get_all_games()
        else:
            games = self.dialog_games if self.dialog_games else self.game_manager.get_uncategorized_games()

        methods = settings['methods']
        progress = QProgressDialog(t('ui.auto_categorize.processing', current=0, total=len(games)),
                                   t('ui.auto_categorize.cancel'), 0, len(methods) * len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        step = 0
        for method in methods:
            if method == 'tags':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    progress.setLabelText(t('ui.auto_categorize.fetching', game=game.name[:50]))
                    QApplication.processEvents()
                    tags = self.steam_scraper.get_game_tags(game.app_id, settings['tags_count'], settings['ignore_common'])
                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories: game.categories.append(tag)
                step += len(games)
            elif method == 'publisher':
                for game in games:
                    if game.publisher:
                        cat = f"Publisher: {game.publisher}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
            elif method == 'franchise':
                for game in games:
                    franchise = FranchiseDetector.detect_franchise(game.name)
                    if franchise:
                        cat = f"Franchise: {franchise}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
            elif method == 'genre':
                for game in games:
                    if game.genres:
                        for genre in game.genres:
                            self.vdf_parser.add_app_category(game.app_id, genre)
                            if genre not in game.categories: game.categories.append(genre)

        self.vdf_parser.save()
        progress.close()
        self._populate_categories()
        QMessageBox.information(self, t('ui.dialogs.success'),
                              t('ui.dialogs.categorize_complete', methods=len(methods), backup=backup_path.name))

    def edit_game_metadata(self, game: Game):
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
        if not meta:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.dialogs.metadata_load_error', name=game.name))
            return
        dialog = MetadataEditDialog(self, game.name, meta)
        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta and self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, new_meta):
                if self.appinfo_manager.save_appinfo(self.appinfo_data):
                    QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.metadata_success', name=game.name))

    def bulk_edit_metadata(self):
        if not self.selected_games:
            QMessageBox.warning(self, t('ui.dialogs.no_selection'), t('ui.dialogs.no_games_selected'))
            return
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict):
        progress = QProgressDialog(t('ui.status.applying_changes'), t('ui.dialogs.cancel'), 0, len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        success_count = 0
        for i, game in enumerate(games):
            if progress.wasCanceled(): break
            progress.setValue(i)
            progress.setLabelText(f"{game.name[:50]}...")
            QApplication.processEvents()
            meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
            if not meta: continue
            modified_meta = meta.copy()
            if 'developer' in settings and settings['developer']: modified_meta['developer'] = settings['developer']
            if 'publisher' in settings and settings['publisher']: modified_meta['publisher'] = settings['publisher']
            if 'release_date' in settings and settings['release_date']: modified_meta['release_date'] = settings['release_date']
            if 'name_modifications' in settings:
                name_mods = settings['name_modifications']
                name = meta.get('name', '')
                if 'remove' in name_mods and name_mods['remove']: name = name.replace(name_mods['remove'], '')
                if 'prefix' in name_mods and name_mods['prefix']: name = name_mods['prefix'] + name
                if 'suffix' in name_mods and name_mods['suffix']: name = name + name_mods['suffix']
                modified_meta['name'] = name.strip()
            if self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, modified_meta): success_count += 1
        progress.setValue(len(games))
        if success_count > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
            QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.bulk_success', count=success_count))

    def restore_metadata_changes(self):
        if not self.appinfo_manager:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            QMessageBox.information(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_tracked_changes'))
            return
        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            restored = self.appinfo_manager.restore_modifications(self.appinfo_data)
            if restored > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
                QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.restore_success', count=restored))

    def refresh_data(self):
        self._load_data()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.language_changed.connect(self._on_ui_language_changed_live)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self._apply_settings(settings)

    def _on_ui_language_changed_live(self, new_language: str):
        config.UI_LANGUAGE = new_language
        init_i18n(new_language)
        self._refresh_menubar()
        self._refresh_toolbar()
        self.setWindowTitle(t('ui.main.title'))
        self.set_status(t('ui.status.ready'))

    def _refresh_menubar(self):
        menubar = self.menuBar()
        menubar.clear()
        
        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(QAction(t('ui.menu.refresh'), self, triggered=self.refresh_data))
        file_menu.addSeparator()
        file_menu.addAction(QAction(t('ui.menu.exit'), self, triggered=self.close))

        tools_menu = menubar.addMenu(t('ui.menu.metadata'))
        tools_menu.addAction(QAction(t('ui.menu.bulk_edit'), self, triggered=self.bulk_edit_metadata))
        tools_menu.addAction(QAction(t('ui.menu.restore'), self, triggered=self.restore_metadata_changes))

        help_menu = menubar.addMenu(t('ui.menu.help'))
        help_menu.addAction(QAction(t('ui.menu.settings'), self, triggered=self.show_settings))

    def _apply_settings(self, settings: dict):
        config.UI_LANGUAGE = settings['ui_language']
        config.TAGS_LANGUAGE = settings['tags_language']
        config.TAGS_PER_GAME = settings['tags_per_game']
        config.IGNORE_COMMON_TAGS = settings['ignore_common_tags']

        if settings['steam_path']:
            config.STEAM_PATH = Path(settings['steam_path'])

        if self.steam_scraper:
            self.steam_scraper.set_language(config.TAGS_LANGUAGE)

        self._save_settings(settings)
        QMessageBox.information(
            self,
            t('ui.dialogs.success'),
            t('ui.settings.saved_message', ui=settings['ui_language'], tags=settings['tags_language'])
        )

    def _save_settings(self, settings: dict):
        import json
        settings_file = config.DATA_DIR / 'settings.json'
        data = {
            'ui_language': settings['ui_language'],
            'tags_language': settings['tags_language'],
            'tags_per_game': settings['tags_per_game'],
            'ignore_common_tags': settings['ignore_common_tags']
        }
        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_status(self, text: str):
        self.statusbar.showMessage(text)        self.addToolBar(toolbar)
        
        act_tb_login = QAction(t('ui.toolbar.login'), self)
        act_tb_login.triggered.connect(self.on_login_clicked)
        toolbar.addAction(act_tb_login)

        toolbar.addSeparator()
        
        act_tb_refresh = QAction(t('ui.toolbar.refresh'), self)
        act_tb_refresh.triggered.connect(self.refresh_data)
        toolbar.addAction(act_tb_refresh)
        
        act_tb_cat = QAction(t('ui.toolbar.auto_categorize'), self)
        act_tb_cat.triggered.connect(self.auto_categorize)
        toolbar.addAction(act_tb_cat)
        
        toolbar.addSeparator()
        
        act_tb_sett = QAction(t('ui.toolbar.settings'), self)
        act_tb_sett.triggered.connect(self.show_settings)
        toolbar.addAction(act_tb_sett)

        # === MAIN CONTENT ===
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT: Categories + Games ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Search
        search_layout = QHBoxLayout()
        # Auch das Icon kommt jetzt aus der JSON!
        search_layout.addWidget(QLabel(t('ui.main.search_icon')))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        clear_btn = QPushButton("×")
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        # Tree
        self.tree = GameTreeWidget()
        self.tree.game_clicked.connect(self.on_game_selected)
        self.tree.game_right_clicked.connect(self.on_game_right_click)
        self.tree.category_right_clicked.connect(self.on_category_right_click)
        self.tree.selection_changed.connect(self._on_games_selected)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        # === RIGHT: Game Details ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)

        self.details_title = QLabel(t('ui.game_details.title'))
        self.details_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        right_layout.addWidget(self.details_title)

        self.details_scroll = QScrollArea()
        self.details_scroll.setWidgetResizable(True)
        self.details_content = QWidget()
        self.details_layout = QVBoxLayout(self.details_content)
        self.details_scroll.setWidget(self.details_content)
        right_layout.addWidget(self.details_scroll)

        self.details_placeholder = QLabel(t('ui.game_details.select_placeholder'))
        self.details_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details_layout.addWidget(self.details_placeholder)

        splitter.addWidget(right_widget)
        splitter.setSizes([450, 950])
        layout.addWidget(splitter)

        # === STATUSBAR ===
        self.statusbar = self.statusBar()
        self.set_status(t('ui.status.ready'))

    # ... (Rest der Methoden wie on_login_clicked, _load_data, etc. bleiben unverändert) ...
    # Nur die Kontext-Menüs müssen wir noch checken:

    def on_game_right_click(self, game: Game, pos):
        """Rechtsklick auf Spiel"""
        menu = QMenu(self)
        
        # Alle Icons kommen jetzt aus t(...)
        act_details = QAction(t('ui.game_list.context_menu.view_details'), self)
        act_details.triggered.connect(lambda: self.on_game_selected(game))
        menu.addAction(act_details)
        
        act_fav = QAction(t('ui.game_list.context_menu.add_to_favorites'), self)
        act_fav.triggered.connect(lambda: self.toggle_favorite(game))
        menu.addAction(act_fav)
        
        act_store = QAction(t('ui.game_list.context_menu.view_store'), self)
        act_store.triggered.connect(lambda: self.open_in_store(game))
        menu.addAction(act_store)
        
        menu.addSeparator()
        
        act_meta = QAction(t('ui.game_list.context_menu.edit_metadata'), self)
        act_meta.triggered.connect(lambda: self.edit_game_metadata(game))
        menu.addAction(act_meta)

        act_auto = QAction(t('ui.game_list.context_menu.auto_categorize'), self)
        act_auto.triggered.connect(lambda: self.auto_categorize_games([game]))
        menu.addAction(act_auto)

        menu.exec(pos)

    def on_category_right_click(self, category: str, pos):
        """Rechtsklick auf Kategorie"""
        special = [t('ui.categories.all_games'), t('ui.categories.favorites'), t('ui.categories.uncategorized')]
        if category in special:
            return
        menu = QMenu(self)
        
        act_rename = QAction(t('ui.categories.rename'), self)
        act_rename.triggered.connect(lambda: self.rename_category(category))
        menu.addAction(act_rename)
        
        act_del = QAction(t('ui.categories.delete'), self)
        act_del.triggered.connect(lambda: self.delete_category(category))
        menu.addAction(act_del)
        
        act_auto = QAction(t('ui.game_list.context_menu.auto_categorize'), self)
        act_auto.triggered.connect(lambda: self.auto_categorize_category(category))
        menu.addAction(act_auto)
        
        menu.exec(pos)

    # --- Rest der Klasse (Login, Load, Save...) einfach von der vorherigen Version übernehmen ---
    # Da hat sich nichts am Code geändert, nur an den t('') Aufrufen oben.
    
    # Der Vollständigkeit halber hier die wichtigsten Methoden nochmal (Login & Rest):
    def on_login_clicked(self):
        dialog = SteamLoginDialog(self)
        if dialog.exec():
            steam_id = dialog.get_steam_id()
            if steam_id:
                config.STEAM_USER_ID = steam_id
                config.save()
                QMessageBox.information(self, t('ui.dialogs.success'), 
                                      t('ui.login.success', username=steam_id))
                self.refresh_data()
            else:
                QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.login.status_failed'))

    def _load_data(self):
        self.set_status(t('ui.status.loading'))
        if not config.STEAM_PATH:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.steam_not_found'))
            return
        if config.STEAM_USER_ID:
             account_id = config.STEAM_USER_ID
             self.user_label.setText(t('ui.main.user_label', user_id=account_id))
             self.user_label.setStyleSheet("padding: 5px 10px; color: #4CAF50; font-weight: bold;")
        else:
            user_ids = config.get_all_user_ids()
            if user_ids:
                account_id = user_ids[0]
                self.user_label.setText(t('ui.main.user_auto', user_id=account_id))
            else:
                QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.errors.no_users'))
                return
        config_path = config.get_localconfig_path(account_id)
        if not config_path:
            self.set_status(t('ui.status.localconfig_not_found'))
            return
        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            self.set_status(t('ui.errors.localconfig_load_error'))
            return
        if not config.STEAM_API_KEY:
            print(t('ui.status.api_warning'))
        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)
        if not self.game_manager.load_from_steam_api(account_id):
            self.set_status(t('ui.status.api_error'))
        self.game_manager.merge_with_localconfig(self.vdf_parser)
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR)
        if config.STEAM_PATH:
            try:
                self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
                self.appinfo_data = self.appinfo_manager.load_appinfo()
            except Exception as e:
                print(f"Error loading AppInfo: {e}")
        self._populate_categories()
        self.set_status(t('ui.status.loaded', count=len(self.game_manager.games)))

    def _populate_categories(self):
        if not self.game_manager: return
        categories_data = {}
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.name.lower())
        categories_data[t('ui.categories.all_games')] = all_games
        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.name.lower())
        if favorites:
            categories_data[t('ui.categories.favorites')] = favorites
        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.name.lower())
        if uncat:
            categories_data[t('ui.categories.uncategorized')] = uncat
        cats = self.game_manager.get_all_categories()
        for cat_name in sorted(cats.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name), key=lambda g: g.name.lower())
                categories_data[cat_name] = cat_games
        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]):
        self.selected_games = games
        if len(games) > 1:
            self.set_status(t('ui.status.selected_multiple', count=len(games)))
        elif len(games) == 1:
            self.set_status(t('ui.status.selected', name=games[0].name))

    def on_game_selected(self, game: Game):
        self.selected_game = game
        self._show_game_details(game)

    def _show_game_details(self, game: Game):
        self.details_placeholder.hide()
        for i in reversed(range(self.details_layout.count())):
            widget = self.details_layout.itemAt(i).widget()
            if widget and widget != self.details_placeholder:
                widget.deleteLater()
        self.details_title.setText(game.name)
        self._add_detail(t('ui.game_details.name'), game.app_id)
        self._add_detail(t('ui.game_details.playtime'), t('ui.game_details.hours', hours=game.playtime_hours))
        if game.developer:
            self._add_detail(t('ui.game_details.developer'), game.developer)
        if game.publisher:
            self._add_detail(t('ui.game_details.publisher'), game.publisher)
        label = QLabel(t('ui.game_details.categories_label'))
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.details_layout.addWidget(label)
        all_categories = sorted(self.game_manager.get_all_categories().keys())
        for cat in all_categories:
            if cat != 'favorite':
                cb = QCheckBox(cat)
                cb.setChecked(game.has_category(cat))
                cb.stateChanged.connect(lambda state, c=cat, g=game: self.toggle_category(g, c, state))
                self.details_layout.addWidget(cb)
        self.details_layout.addStretch()

    def _add_detail(self, label: str, value: str):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(label)
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl.setMinimumWidth(100)
        layout.addWidget(lbl)
        val = QLabel(str(value))
        layout.addWidget(val)
        layout.addStretch()
        self.details_layout.addWidget(frame)

    def toggle_category(self, game: Game, category: str, state):
        if state == Qt.CheckState.Checked.value:
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(game.app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(game.app_id, category)
        self.vdf_parser.save()
        self._populate_categories()
        self.set_status(t('ui.status.updated', name=game.name))

    def open_in_store(self, game: Game):
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def rename_category(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, t('ui.categories.rename'),
                                           t('ui.dialogs.rename_category', old=old_name))
        if ok and new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()

    def delete_category(self, category: str):
        reply = QMessageBox.question(self, t('ui.dialogs.confirm_delete', name=category),
                                     t('ui.dialogs.confirm_delete_msg'))
        if reply == QMessageBox.StandardButton.Yes:
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    def auto_categorize(self):
        uncat = self.game_manager.get_uncategorized_games()
        self._show_auto_categorize_dialog(uncat, None)

    def auto_categorize_category(self, category: str):
        games = self.game_manager.get_games_by_category(category)
        self._show_auto_categorize_dialog(games, category)

    def auto_categorize_games(self, games: List[Game]):
        self._show_auto_categorize_dialog(games, None)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]):
        self._pending_auto_cat_games = games
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games),
                                     self._do_auto_categorize, category_name)
        dialog.exec()

    def _do_auto_categorize(self, settings: dict):
        if not settings: return
        backup_dir = self.vdf_parser.config_path.parent
        backup_filename = f'localconfig_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.vdf'
        backup_path = backup_dir / backup_filename
        import shutil
        shutil.copy2(self.vdf_parser.config_path, backup_path)
        self.set_status(t('ui.status.backup_created', name=backup_path.name))
        if settings['scope'] == 'all':
            games = self.game_manager.get_all_games()
        else:
            games = self._pending_auto_cat_games if self._pending_auto_cat_games else \
                   (self.selected_games if self.selected_games else self.game_manager.get_uncategorized_games())
        methods = settings['methods']
        progress = QProgressDialog(t('ui.auto_categorize.processing', current=0, total=len(games)),
                                   t('ui.auto_categorize.cancel'), 0, len(methods) * len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        step = 0
        for method in methods:
            if method == 'tags':
                for i, game in enumerate(games):
                    if progress.wasCanceled(): break
                    progress.setValue(step + i)
                    progress.setLabelText(t('ui.auto_categorize.fetching', game=game.name[:50]))
                    QApplication.processEvents()
                    tags = self.steam_scraper.get_game_tags(game.app_id, settings['tags_count'], settings['ignore_common'])
                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories: game.categories.append(tag)
                step += len(games)
            elif method == 'publisher':
                for game in games:
                    if game.publisher:
                        cat = f"Publisher: {game.publisher}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
            elif method == 'franchise':
                for game in games:
                    franchise = FranchiseDetector.detect_franchise(game.name)
                    if franchise:
                        cat = f"Franchise: {franchise}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories: game.categories.append(cat)
            elif method == 'genre':
                for game in games:
                    if game.genres:
                        for genre in game.genres:
                            self.vdf_parser.add_app_category(game.app_id, genre)
                            if genre not in game.categories: game.categories.append(genre)
        self.vdf_parser.save()
        progress.close()
        self._populate_categories()
        QMessageBox.information(self, t('ui.dialogs.success'),
                              t('ui.dialogs.categorize_complete', methods=len(methods), backup=backup_path.name))

    def edit_game_metadata(self, game: Game):
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
        if not meta:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.dialogs.metadata_load_error', name=game.name))
            return
        dialog = MetadataEditDialog(self, game.name, meta)
        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta and self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, new_meta):
                if self.appinfo_manager.save_appinfo(self.appinfo_data):
                    QMessageBox.information(self, t('ui.dialogs.success'),
                                          t('ui.dialogs.metadata_success', name=game.name))

    def bulk_edit_metadata(self):
        if not self.selected_games:
            QMessageBox.warning(self, t('ui.dialogs.no_selection'), t('ui.errors.no_games_selected'))
            return
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict):
        progress = QProgressDialog(t('ui.status.applying_changes'), t('ui.dialogs.cancel'), 0, len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        success_count = 0
        for i, game in enumerate(games):
            if progress.wasCanceled(): break
            progress.setValue(i)
            progress.setLabelText(f"{game.name[:50]}...")
            QApplication.processEvents()
            meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
            if not meta: continue
            modified_meta = meta.copy()
            if 'developer' in settings and settings['developer']: modified_meta['developer'] = settings['developer']
            if 'publisher' in settings and settings['publisher']: modified_meta['publisher'] = settings['publisher']
            if 'release_date' in settings and settings['release_date']: modified_meta['release_date'] = settings['release_date']
            if 'name_modifications' in settings:
                name_mods = settings['name_modifications']
                name = meta.get('name', '')
                if 'remove' in name_mods and name_mods['remove']: name = name.replace(name_mods['remove'], '')
                if 'prefix' in name_mods and name_mods['prefix']: name = name_mods['prefix'] + name
                if 'suffix' in name_mods and name_mods['suffix']: name = name + name_mods['suffix']
                modified_meta['name'] = name.strip()
            if self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, modified_meta): success_count += 1
        progress.setValue(len(games))
        if success_count > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
            QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.bulk_success', count=success_count))

    def restore_metadata_changes(self):
        if not self.appinfo_manager:
            QMessageBox.warning(self, t('ui.dialogs.not_available'), t('ui.dialogs.metadata_not_available'))
            return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            QMessageBox.information(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_tracked_changes'))
            return
        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            restored = self.appinfo_manager.restore_modifications(self.appinfo_data)
            if restored > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
                QMessageBox.information(self, t('ui.dialogs.success'), t('ui.dialogs.restore_success', count=restored))

    def refresh_data(self):
        self._load_data()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def set_status(self, text: str):
        self.statusbar.showMessage(text)                more_item = QTreeWidgetItem(category_item, [f"  ... and {len(games) - 100} more"])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t('ui.main.title'))
        self.resize(1400, 800)

        # Data
        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.selected_game: Optional[Game] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        self.appinfo_manager: Optional[AppInfoManager] = None
        self.appinfo_data: Optional[Dict] = None
        self.selected_games: List[Game] = []
        self.current_ui_language = config.UI_LANGUAGE
        self.dialog_games: List[Game] = []  # Für Auto-Categorize Dialog

        # ✨ NEW: Track games passed to dialog
        self.dialog_games: List[Game] = []

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        """Erstelle UI mit Menü"""
        # === MENÜBAR ===
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(QAction(t('ui.menu.refresh'), self, triggered=self.refresh_data))
        file_menu.addSeparator()
        file_menu.addAction(QAction(t('ui.menu.exit'), self, triggered=self.close))

        # Tools Menu
        tools_menu = menubar.addMenu(t('ui.menu.metadata'))
        tools_menu.addAction(QAction(f"✏️ {t('ui.toolbar.bulk_edit')}", self, triggered=self.bulk_edit_metadata))
        tools_menu.addAction(QAction(f"🔄 {t('ui.toolbar.restore_changes')}", self, triggered=self.restore_metadata_changes))

        # Help Menu
        help_menu = menubar.addMenu(t('ui.menu.help'))
        help_menu.addAction(QAction(t('ui.menu.settings'), self, triggered=self.show_settings))

        # User Label in Menübar (rechts)
        self.user_label = QLabel(t('ui.status.not_logged_in'))
        self.user_label.setStyleSheet("padding: 5px 10px;")
        menubar.setCornerWidget(self.user_label, Qt.Corner.TopRightCorner)

        # === TOOLBAR ===
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self.toolbar.addAction(f"🔄 {t('ui.toolbar.refresh')}", self.refresh_data)
        self.toolbar.addAction(f"🏷️ {t('ui.toolbar.auto_categorize')}", self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(f"⚙️ {t('ui.toolbar.settings')}", self.show_settings)

        # === MAIN CONTENT ===
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT: Categories + Games ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(t('ui.main.search_placeholder'))
        self.search_entry.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_entry)
        clear_btn = QPushButton("×")
        clear_btn.clicked.connect(self.clear_search)
        clear_btn.setMaximumWidth(30)
        search_layout.addWidget(clear_btn)
        left_layout.addLayout(search_layout)

        # Tree
        self.tree = GameTreeWidget()
        self.tree.game_clicked.connect(self.on_game_selected)
        self.tree.game_right_clicked.connect(self.on_game_right_click)
        self.tree.category_right_clicked.connect(self.on_category_right_click)
        self.tree.selection_changed.connect(self._on_games_selected)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        # === RIGHT: Game Details Widget ===
        self.details_widget = GameDetailsWidget()
        self.details_widget.category_changed.connect(self._on_category_changed_from_details)
        self.details_widget.edit_metadata.connect(self.edit_game_metadata)
        splitter.addWidget(self.details_widget)
        splitter.setSizes([450, 950])
        layout.addWidget(splitter)

        # === STATUSBAR ===
        self.statusbar = self.statusBar()
        self.set_status(t('ui.status.ready'))

    def _load_data(self):
        """Lade Daten"""
        self.set_status(t('ui.status.loading'))

        if not config.STEAM_PATH:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('errors.steam_not_found'))
            return

        user_ids = config.get_all_user_ids()
        if not user_ids:
            QMessageBox.warning(self, t('ui.dialogs.error'), "No Steam users found")
            return

        account_id = user_ids[0]
        steam_id64 = config.STEAM_USER_ID if config.STEAM_USER_ID else account_id
        self.user_label.setText(f"User: {account_id}")

        config_path = config.get_localconfig_path(account_id)
        if not config_path:
            QMessageBox.warning(self, t('ui.dialogs.error'), "localconfig.vdf not found")
            return

        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            QMessageBox.warning(self, t('ui.dialogs.error'), "Failed to load localconfig.vdf")
            return

        if not config.STEAM_API_KEY:
            QMessageBox.warning(self, t('ui.dialogs.error'), "Steam API Key not configured in .env")
            return

        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)
        if not self.game_manager.load_from_steam_api(steam_id64):
            QMessageBox.warning(self, t('ui.dialogs.error'), "Failed to load games from Steam API")
            return

        self.game_manager.merge_with_localconfig(self.vdf_parser)
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR, config.TAGS_LANGUAGE)

        # Load metadata
        if config.STEAM_PATH:
            try:
                self.appinfo_manager = AppInfoManager(config.STEAM_PATH)
                self.appinfo_data = self.appinfo_manager.load_appinfo()
                if self.appinfo_data:
                    mod_count = self.appinfo_manager.get_modification_count()
                    if mod_count > 0:
                        print(f"✓ Found {mod_count} metadata modifications")
            except Exception as e:
                print(f"Error loading AppInfo: {e}")
                self.appinfo_manager = None
                self.appinfo_data = None

        self._populate_categories()
        self.set_status(f"Loaded {len(self.game_manager.games)} games")

    def _populate_categories(self):
        """Fülle Kategorien"""
        if not self.game_manager:
            return

        categories_data = {}
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.name.lower())
        categories_data[t('ui.categories.all_games')] = all_games

        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.name.lower())
        if favorites:
            categories_data[t('ui.categories.favorites')] = favorites

        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.name.lower())
        if uncat:
            categories_data[t('ui.categories.uncategorized')] = uncat

        cats = self.game_manager.get_all_categories()
        for cat_name in sorted(cats.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name), key=lambda g: g.name.lower())
                categories_data[cat_name] = cat_games

        self.tree.populate_categories(categories_data)

    def _on_games_selected(self, games: List[Game]):
        """Spiele wurden ausgewählt"""
        self.selected_games = games
        if len(games) > 1:
            self.set_status(f"Selected {len(games)} games")
        elif len(games) == 1:
            self.set_status(f"Selected: {games[0].name}")

    def on_game_selected(self, game: Game):
        """Spiel wurde geklickt"""
        self.selected_game = game
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)

    def _add_detail(self, label: str, value: str):
        """Detail-Zeile hinzufügen"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(label)
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl.setMinimumWidth(100)
        layout.addWidget(lbl)
        val = QLabel(str(value))
        layout.addWidget(val)
        layout.addStretch()
        self.details_layout.addWidget(frame)

    def toggle_category(self, game: Game, category: str, state):
        """Toggle Kategorie"""
        if state == Qt.CheckState.Checked.value:
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(game.app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(game.app_id, category)

        self.vdf_parser.save()
        self._populate_categories()
        self.set_status(f"Updated {game.name}")

    def _on_category_changed_from_details(self, app_id: str, category: str, checked: bool):
        """Category toggled in details widget"""
        game = self.game_manager.get_game(app_id)
        if not game:
            return

        if checked:
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(app_id, category)

        self.vdf_parser.save()
        self._populate_categories()

        # Update details widget
        all_categories = list(self.game_manager.get_all_categories().keys())
        self.details_widget.set_game(game, all_categories)

    def on_game_right_click(self, game: Game, pos):
        """Rechtsklick auf Spiel"""
        menu = QMenu(self)
        menu.addAction(f"📋 {t('ui.context_menu.view_details')}", lambda: self.on_game_selected(game))
        menu.addAction(f"⭐ {t('ui.context_menu.toggle_favorite')}", lambda: self.toggle_favorite(game))
        menu.addAction(f"🌐 {t('ui.context_menu.open_store')}", lambda: self.open_in_store(game))
        menu.addSeparator()

        # ✨ NEW: Auto-categorize für ausgewählte Spiele
        if len(self.selected_games) > 1:
            menu.addAction(f"🏷️ {t('ui.context_menu.auto_categorize_selected')}",
                          lambda: self.auto_categorize_selected())
            menu.addSeparator()

        menu.addAction(f"✏️ {t('ui.context_menu.edit_metadata')}", lambda: self.edit_game_metadata(game))
        menu.exec(pos)

    def on_category_right_click(self, category: str, pos):
        """Rechtsklick auf Kategorie"""
        special = [t('ui.categories.all_games'), t('ui.categories.favorites'), t('ui.categories.uncategorized')]
        if category in special:
            return
        menu = QMenu(self)
        menu.addAction(f"✏️ {t('ui.context_menu.rename')}", lambda: self.rename_category(category))
        menu.addAction(f"🗑️ {t('ui.context_menu.delete')}", lambda: self.delete_category(category))
        menu.addSeparator()
        menu.addAction(f"🏷️ {t('ui.context_menu.auto_categorize')}", lambda: self.auto_categorize_category(category))
        menu.exec(pos)

    def on_search(self, query):
        """Suche"""
        if not query:
            self._populate_categories()
            return
        if not self.game_manager:
            return
        results = [g for g in self.game_manager.get_all_games() if query.lower() in g.name.lower()]
        if results:
            sorted_results = sorted(results, key=lambda g: g.name.lower())
            self.tree.populate_categories({f"Search Results ({len(results)})": sorted_results})
            self.tree.expandAll()
            self.set_status(f"Found {len(results)} games")
        else:
            self.tree.clear()
            self.set_status("No results")

    def clear_search(self):
        self.search_entry.clear()
        self._populate_categories()

    def toggle_favorite(self, game: Game):
        if game.is_favorite():
            game.categories.remove('favorite')
            self.vdf_parser.remove_app_category(game.app_id, 'favorite')
        else:
            game.categories.append('favorite')
            self.vdf_parser.add_app_category(game.app_id, 'favorite')
        self.vdf_parser.save()
        self._populate_categories()

    def open_in_store(self, game: Game):
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")

    def rename_category(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, t('ui.context_menu.rename'),
                                           f"Rename '{old_name}' to:")
        if ok and new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()

    def delete_category(self, category: str):
        reply = QMessageBox.question(self, f"Delete '{category}'?",
                                     "This will remove the category but keep the games.")
        if reply == QMessageBox.StandardButton.Yes:
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()

    # ✅ FIX 1: Auto-categorize Toolbar Button
    def auto_categorize(self):
        """Toolbar Button: kategorisiert uncategorized oder selected games"""
        if self.selected_games:
            # Wenn Spiele ausgewählt sind → die nutzen
            self._show_auto_categorize_dialog(self.selected_games, None)
        else:
            # Sonst uncategorized games
            uncat = self.game_manager.get_uncategorized_games()
            self._show_auto_categorize_dialog(uncat, None)

    # ✅ FIX 2: Auto-categorize Selected Games (Context Menu)
    def auto_categorize_selected(self):
        """Context menu: kategorisiert ausgewählte Spiele"""
        if self.selected_games:
            self._show_auto_categorize_dialog(self.selected_games, None)

    # ✅ FIX 3: Auto-categorize Category
    def auto_categorize_category(self, category: str):
        """Rechtsklick auf Kategorie: kategorisiert Spiele in der Kategorie"""
        games = self.game_manager.get_games_by_category(category)
        self._show_auto_categorize_dialog(games, category)

    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]):
        self.dialog_games = games  # Speichern für _do_auto_categorize
        dialog = AutoCategorizeDialog(self, games, len(self.game_manager.games),
                                      self._do_auto_categorize, category_name)
        dialog.exec()

    # ✅ FIX 4: _do_auto_categorize nutzt JETZT die richtigen Games!
    def _do_auto_categorize(self, settings: dict):
        if not settings:
            return

        backup_dir = self.vdf_parser.config_path.parent
        backup_filename = f'localconfig_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.vdf'
        backup_path = backup_dir / backup_filename
        import shutil
        shutil.copy2(self.vdf_parser.config_path, backup_path)
        self.set_status(f"Backup: {backup_path.name}")

        # ✅ KORRIGIERT: Nutze die richtigen Games!
        if settings['scope'] == 'all':
            # ✅ FIX: Nutze dialog_games statt selected_games!
            if settings['scope'] == 'all':
                games = self.game_manager.get_all_games()
            elif self.dialog_games:
                games = self.dialog_games
            elif self.selected_games:
                games = self.selected_games
            else:
                games = self.game_manager.get_uncategorized_games()
        else:
            # Nutze die Games, die dem Dialog übergeben wurden!
            games = self.dialog_games if self.dialog_games else self.game_manager.get_uncategorized_games()

        methods = settings['methods']
        progress = QProgressDialog(f"Processing 0/{len(games)} games",
                                   "Cancel", 0, len(methods) * len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        step = 0
        for method in methods:
            if method == 'tags':
                for i, game in enumerate(games):
                    if progress.wasCanceled():
                        break
                    progress.setValue(step + i)
                    progress.setLabelText(f"Processing {i+1}/{len(games)}: {game.name[:50]}")
                    QApplication.processEvents()
                    tags = self.steam_scraper.get_game_tags(game.app_id, settings['tags_count'], settings['ignore_common'])
                    for tag in tags:
                        self.vdf_parser.add_app_category(game.app_id, tag)
                        if tag not in game.categories:
                            game.categories.append(tag)
                step += len(games)
            elif method == 'publisher':
                for game in games:
                    if game.publisher:
                        cat = f"Publisher: {game.publisher}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories:
                            game.categories.append(cat)
            elif method == 'franchise':
                for game in games:
                    franchise = FranchiseDetector.detect_franchise(game.name)
                    if franchise:
                        cat = f"Franchise: {franchise}"
                        self.vdf_parser.add_app_category(game.app_id, cat)
                        if cat not in game.categories:
                            game.categories.append(cat)
            elif method == 'genre':
                for game in games:
                    if game.genres:
                        for genre in game.genres:
                            self.vdf_parser.add_app_category(game.app_id, genre)
                            if genre not in game.categories:
                                game.categories.append(genre)

        self.vdf_parser.save()
        progress.close()
        self._populate_categories()
        QMessageBox.information(self, "Success",
                              f"Categorized {len(games)} games using {len(methods)} method(s)\nBackup: {backup_path.name}")

    def edit_game_metadata(self, game: Game):
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, "Not Available", "Metadata editing not available")
            return
        meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
        if not meta:
            QMessageBox.warning(self, "Error", f"Could not load metadata for {game.name}")
            return
        dialog = MetadataEditDialog(self, game.name, meta)
        if dialog.exec():
            new_meta = dialog.get_metadata()
            if new_meta and self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, new_meta):
                if self.appinfo_manager.save_appinfo(self.appinfo_data):
                    QMessageBox.information(self, "Success",
                                          f"Metadata saved for {game.name}")

    def bulk_edit_metadata(self):
        if not self.selected_games:
            QMessageBox.warning(self, "No Selection", "Please select games first")
            return
        if not self.appinfo_manager or not self.appinfo_data:
            QMessageBox.warning(self, "Not Available", "Metadata editing not available")
            return
        game_names = [g.name for g in self.selected_games]
        dialog = BulkMetadataEditDialog(self, len(self.selected_games), game_names)
        if dialog.exec():
            settings = dialog.get_metadata()
            if settings:
                self._do_bulk_metadata_edit(self.selected_games, settings)

    def _do_bulk_metadata_edit(self, games: List[Game], settings: Dict):
        progress = QProgressDialog("Applying changes...", "Cancel", 0, len(games), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        success_count = 0
        for i, game in enumerate(games):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"{game.name[:50]}...")
            QApplication.processEvents()
            meta = self.appinfo_manager.get_app_metadata(game.app_id, self.appinfo_data)
            if not meta:
                continue
            modified_meta = meta.copy()
            if 'developer' in settings and settings['developer']:
                modified_meta['developer'] = settings['developer']
            if 'publisher' in settings and settings['publisher']:
                modified_meta['publisher'] = settings['publisher']
            if 'release_date' in settings and settings['release_date']:
                modified_meta['release_date'] = settings['release_date']
            if 'name_modifications' in settings:
                name_mods = settings['name_modifications']
                name = meta.get('name', '')
                if 'remove' in name_mods and name_mods['remove']:
                    name = name.replace(name_mods['remove'], '')
                if 'prefix' in name_mods and name_mods['prefix']:
                    name = name_mods['prefix'] + name
                if 'suffix' in name_mods and name_mods['suffix']:
                    name = name + name_mods['suffix']
                modified_meta['name'] = name.strip()
            if self.appinfo_manager.set_app_metadata(game.app_id, self.appinfo_data, modified_meta):
                success_count += 1
        progress.setValue(len(games))
        if success_count > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
            QMessageBox.information(self, "Success",
                                  f"Modified {success_count} games")

    def restore_metadata_changes(self):
        if not self.appinfo_manager:
            QMessageBox.warning(self, "Not Available", "Metadata editing not available")
            return
        mod_count = self.appinfo_manager.get_modification_count()
        if mod_count == 0:
            QMessageBox.information(self, "No Changes", "No tracked modifications found")
            return
        dialog = MetadataRestoreDialog(self, mod_count)
        if dialog.exec() and dialog.should_restore():
            restored = self.appinfo_manager.restore_modifications(self.appinfo_data)
            if restored > 0 and self.appinfo_manager.save_appinfo(self.appinfo_data):
                QMessageBox.information(self, "Success",
                                      f"Restored {restored} modifications")

    def refresh_data(self):
        self._load_data()

    def show_settings(self):
        """Settings Dialog öffnen"""
        dialog = SettingsDialog(self)

        # Connect language changed signal for LIVE update
        dialog.language_changed.connect(self._on_ui_language_changed_live)

        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self._apply_settings(settings)

    def _on_ui_language_changed_live(self, new_language: str):
        """UI Language changed in Settings - refresh UI LIVE"""
        config.UI_LANGUAGE = new_language

        # Reload i18n
        init_i18n(new_language)

        # Refresh UI
        self._refresh_menubar()
        self._refresh_toolbar()
        self.set_status(t('ui.status.ready'))

    def _refresh_menubar(self):
        """Refresh menu bar texts"""
        menubar = self.menuBar()
        menubar.clear()

        # File Menu
        file_menu = menubar.addMenu(t('ui.menu.file'))
        file_menu.addAction(t('ui.menu.refresh'), self.refresh_data)
        file_menu.addSeparator()
        file_menu.addAction(t('ui.menu.exit'), self.close)

        # Tools Menu
        tools_menu = menubar.addMenu(t('ui.toolbar.metadata'))
        tools_menu.addAction(f"✏️ {t('ui.toolbar.bulk_edit')}", self.bulk_edit_metadata)
        tools_menu.addAction(f"🔄 {t('ui.toolbar.restore_changes')}", self.restore_metadata_changes)

        # Help Menu
        help_menu = menubar.addMenu(t('ui.menu.help'))
        help_menu.addAction(t('ui.menu.settings'), self.show_settings)

        # User label
        self.user_label.setText(t('ui.status.not_logged_in'))

    def _refresh_toolbar(self):
        """Refresh toolbar texts"""
        # Clear
        self.toolbar.clear()

        # Rebuild
        self.toolbar.addAction(f"🔄 {t('ui.toolbar.refresh')}", self.refresh_data)
        self.toolbar.addAction(f"🏷️ {t('ui.toolbar.auto_categorize')}", self.auto_categorize)
        self.toolbar.addSeparator()
        self.toolbar.addAction(f"⚙️ {t('ui.toolbar.settings')}", self.show_settings)

    def _apply_settings(self, settings: dict):
        """Apply settings"""
        # Update config
        config.UI_LANGUAGE = settings['ui_language']
        config.TAGS_LANGUAGE = settings['tags_language']
        config.TAGS_PER_GAME = settings['tags_per_game']
        config.IGNORE_COMMON_TAGS = settings['ignore_common_tags']

        if settings['steam_path']:
            config.STEAM_PATH = Path(settings['steam_path'])

        # Update Steam Scraper language
        if self.steam_scraper:
            self.steam_scraper.set_language(config.TAGS_LANGUAGE)

        # Save to data file (not .env!)
        self._save_settings(settings)

        QMessageBox.information(
            self,
            t('ui.dialogs.success'),
            f"Settings saved!\n\n"
            f"UI Language: {settings['ui_language']}\n"
            f"Tags Language: {settings['tags_language']}"
        )

    def _save_settings(self, settings: dict):
        """Save settings to data file"""
        import json
        settings_file = config.DATA_DIR / 'settings.json'

        data = {
            'ui_language': settings['ui_language'],
            'tags_language': settings['tags_language'],
            'tags_per_game': settings['tags_per_game'],
            'ignore_common_tags': settings['ignore_common_tags']
        }

        with open(settings_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_status(self, text: str):
        self.statusbar.showMessage(text)
