"""
Settings Dialog - Mit i18n für Sprachen und Flaggen
Speichern als: src/ui/settings_dialog.py
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, 
    QPushButton, QHBoxLayout, QMessageBox, QGroupBox, QLabel
)
from src.config import config
from src.utils.i18n import t

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings.title'))
        self.setMinimumWidth(500)
        self._create_ui()
        self._load_current_settings()

    def _create_ui(self):
        layout = QVBoxLayout(self)

        # --- Allgemein ---
        group_general = QGroupBox(t('ui.settings.general'))
        form_general = QFormLayout(group_general)

        # Sprachauswahl mit Flaggen (Emojis) und i18n
        self.combo_language = QComboBox()
        self.combo_language.addItem(t('ui.settings.languages.de'), "de")
        self.combo_language.addItem(t('ui.settings.languages.en'), "en")        
        form_general.addRow(t('ui.settings.language'), self.combo_language)

        # Theme Auswahl
        self.combo_theme = QComboBox()
        self.combo_theme.addItem(f"🌑 {t('ui.settings.themes.dark')}", "dark")
        self.combo_theme.addItem(f"☀️ {t('ui.settings.themes.light')}", "light")
        form_general.addRow(t('ui.settings.theme'), self.combo_theme)

        layout.addWidget(group_general)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_save = QPushButton(t('ui.settings.save'))
        btn_save.clicked.connect(self._save_settings)
        
        btn_cancel = QPushButton(t('ui.settings.cancel'))
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        """Lädt aktuelle Werte in die GUI"""
        # Sprache setzen
        index = self.combo_language.findData(config.UI_LANGUAGE)
        if index >= 0:
            self.combo_language.setCurrentIndex(index)
            
        # Theme setzen
        index_theme = self.combo_theme.findData(config.THEME)
        if index_theme >= 0:
            self.combo_theme.setCurrentIndex(index_theme)

    def _save_settings(self):
        """Speichert Werte"""
        selected_lang = self.combo_language.currentData()
        selected_theme = self.combo_theme.currentData()
        
        restart_required = False
        if selected_lang != config.UI_LANGUAGE:
            restart_required = True
            
        # Werte in Config übernehmen
        config.UI_LANGUAGE = selected_lang
        config.THEME = selected_theme
        
        # Auf Festplatte speichern
        config.save()
        
        if restart_required:
            QMessageBox.information(
                self, 
                t('ui.dialogs.info'), 
                t('ui.settings.restart_required')
            )
            
        self.accept()        lang_layout.addRow(ui_lang_label)

        self.ui_language_combo = QComboBox()
        for code, (flag, name) in self.LANGUAGES.items():
            self.ui_language_combo.addItem(f"{flag}  {name}", code)
        self.ui_language_combo.currentIndexChanged.connect(self._on_ui_language_changed)
        lang_layout.addRow("", self.ui_language_combo)

        ui_info = QLabel("(Menus, buttons, dialogs)")
        ui_info.setStyleSheet("color: gray; font-size: 10px;")
        lang_layout.addRow("", ui_info)

        # Spacer
        lang_layout.addRow("", QLabel(""))

        # Tags Language
        tags_lang_label = QLabel("<b>Steam Tags Language:</b>")
        lang_layout.addRow(tags_lang_label)

        self.tags_language_combo = QComboBox()
        for code, (flag, name) in self.LANGUAGES.items():
            self.tags_language_combo.addItem(f"{flag}  {name}", code)
        lang_layout.addRow("", self.tags_language_combo)

        tags_info = QLabel("(Auto-Categorize uses this language)")
        tags_info.setStyleSheet("color: gray; font-size: 10px;")
        lang_layout.addRow("", tags_info)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # Steam Path Group
        steam_group = QGroupBox(t('ui.settings.steam_path'))
        steam_layout = QFormLayout()

        path_layout = QHBoxLayout()
        self.steam_path_edit = QLineEdit()
        self.steam_path_edit.setReadOnly(True)
        path_layout.addWidget(self.steam_path_edit)

        browse_btn = QPushButton(t('ui.settings.browse'))
        browse_btn.clicked.connect(self._browse_steam_path)
        path_layout.addWidget(browse_btn)

        steam_layout.addRow("", path_layout)
        steam_group.setLayout(steam_layout)
        layout.addWidget(steam_group)

        # Backup Group
        backup_group = QGroupBox(t('ui.settings.auto_backup'))
        backup_layout = QVBoxLayout()

        self.backup_checkbox = QCheckBox(t('ui.settings.backup_before_changes'))
        self.backup_checkbox.setChecked(True)
        backup_layout.addWidget(self.backup_checkbox)

        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        layout.addStretch()
        return widget

    def _create_auto_cat_tab(self) -> QWidget:
        """Auto-Categorization settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Tags Settings Group
        tags_group = QGroupBox("Steam Tags Settings")
        tags_layout = QFormLayout()

        # Tags per game
        self.tags_per_game_spin = QSpinBox()
        self.tags_per_game_spin.setMinimum(1)
        self.tags_per_game_spin.setMaximum(20)
        self.tags_per_game_spin.setValue(13)
        tags_layout.addRow(t('ui.settings.tags_per_game') + ":", self.tags_per_game_spin)

        # Ignore common tags
        self.ignore_common_checkbox = QCheckBox(t('ui.settings.ignore_common_tags'))
        self.ignore_common_checkbox.setChecked(True)
        tags_layout.addRow("", self.ignore_common_checkbox)

        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        # Info
        info = QLabel(
            "ℹ️ These settings apply when using Auto-Categorize.\n\n"
            "Tags are fetched from Steam Store in the selected Tags Language.\n"
            "Example: UI in English, Tags in German = English menus with German categories!"
        )
        info.setStyleSheet("color: gray; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        return widget

    def _on_ui_language_changed(self, index):
        """UI Language changed - Update dialog LIVE"""
        new_language = self.ui_language_combo.currentData()

        if new_language != self.original_ui_language:
            # Reload i18n
            from src.utils.i18n import init_i18n
            init_i18n(new_language)

            # Update dialog texts
            self._refresh_texts()

            # Emit signal for parent to refresh
            self.language_changed.emit(new_language)

    def _refresh_texts(self):
        """Refresh all translatable texts in dialog"""
        self.setWindowTitle(t('ui.settings.title'))
        # Note: Tab titles und andere Labels würden hier auch aktualisiert
        # Für MVP reicht Window Title

    def _browse_steam_path(self):
        """Browse for Steam path"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Steam Installation Directory",
            str(Path.home())
        )
        if path:
            self.steam_path_edit.setText(path)

    def _load_current_settings(self):
        """Load current settings from config"""
        # UI Language
        ui_lang = config.UI_LANGUAGE if hasattr(config, 'UI_LANGUAGE') else config.DEFAULT_LOCALE
        index = self.ui_language_combo.findData(ui_lang)
        if index >= 0:
            self.ui_language_combo.setCurrentIndex(index)

        # Tags Language
        tags_lang = config.TAGS_LANGUAGE if hasattr(config, 'TAGS_LANGUAGE') else config.DEFAULT_LOCALE
        index = self.tags_language_combo.findData(tags_lang)
        if index >= 0:
            self.tags_language_combo.setCurrentIndex(index)

        # Steam Path
        if config.STEAM_PATH:
            self.steam_path_edit.setText(str(config.STEAM_PATH))

        # Tags settings
        self.tags_per_game_spin.setValue(config.TAGS_PER_GAME)
        self.ignore_common_checkbox.setChecked(config.IGNORE_COMMON_TAGS)

    def _save(self):
        """Save settings"""
        self.result_settings = {
            'ui_language': self.ui_language_combo.currentData(),
            'tags_language': self.tags_language_combo.currentData(),
            'steam_path': self.steam_path_edit.text() if self.steam_path_edit.text() else None,
            'backup_enabled': self.backup_checkbox.isChecked(),
            'tags_per_game': self.tags_per_game_spin.value(),
            'ignore_common_tags': self.ignore_common_checkbox.isChecked()
        }

        self.accept()

    def get_settings(self) -> Optional[Dict]:
        """Get saved settings (None if canceled)"""
        return self.result_settings
