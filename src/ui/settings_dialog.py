"""
Settings Dialog - Corrected JSON Keys (No Hardcoded Strings)
Speichern als: src/ui/settings_dialog.py
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFileDialog, QLineEdit,
                             QTabWidget, QWidget, QSpinBox, QCheckBox, QMessageBox,
                             QFormLayout, QGroupBox)
from PyQt6.QtCore import pyqtSignal, Qt
from src.config import config
from src.utils.i18n import t

class SettingsDialog(QDialog):
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.settings.title'))
        self.resize(500, 450)
        self._create_ui()
        self._load_current_settings()

    def _create_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # --- TAB 1: GENERAL ---
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)
        
        # Language
        lang_group = QGroupBox(t('ui.settings.language'))
        lang_layout = QFormLayout()
        
        # UI Language
        self.combo_ui_lang = QComboBox()
        # FIX: Verwende jetzt Keys aus dem JSON
        self.combo_ui_lang.addItem(t('ui.settings.languages.en'), "en")
        self.combo_ui_lang.addItem(t('ui.settings.languages.de'), "de")
        lang_layout.addRow(t('ui.settings.ui_language_label'), self.combo_ui_lang)
        
        # Tags Language
        self.combo_tags_lang = QComboBox()
        self.combo_tags_lang.addItem(t('ui.settings.languages.en'), "en")
        self.combo_tags_lang.addItem(t('ui.settings.languages.de'), "de")
        lang_layout.addRow(t('ui.settings.tags_language_label'), self.combo_tags_lang)
        
        lang_group.setLayout(lang_layout)
        layout_gen.addWidget(lang_group)

        # Steam Path
        path_group = QGroupBox(t('ui.settings.steam_path'))
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton(t('ui.settings.browse'))
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        path_group.setLayout(path_layout)
        layout_gen.addWidget(path_group)

        # Backups
        backup_group = QGroupBox(t('ui.settings.backup_group'))
        backup_layout = QFormLayout()
        self.spin_backups = QSpinBox()
        self.spin_backups.setRange(0, 50)
        self.spin_backups.setSuffix(" " + t('ui.settings.backup_files'))
        self.spin_backups.setToolTip(t('ui.settings.backup_tooltip'))
        backup_layout.addRow(t('ui.settings.backup_limit'), self.spin_backups)
        backup_group.setLayout(backup_layout)
        layout_gen.addWidget(backup_group)

        layout_gen.addStretch()
        self.tabs.addTab(tab_general, t('ui.settings.general'))

        # --- TAB 2: AUTO-CATEGORIZATION ---
        tab_auto = QWidget()
        layout_auto = QVBoxLayout(tab_auto)
        
        self.spin_tags = QSpinBox()
        self.spin_tags.setRange(1, 20)
        
        self.check_common = QCheckBox(t('ui.settings.ignore_common_tags'))
        
        form_auto = QFormLayout()
        form_auto.addRow(t('ui.settings.tags_per_game'), self.spin_tags)
        form_auto.addRow("", self.check_common)
        
        layout_auto.addLayout(form_auto)
        layout_auto.addWidget(QLabel(t('ui.settings.auto_cat_info')))
        layout_auto.addStretch()
        
        self.tabs.addTab(tab_auto, t('ui.settings.auto_categorization'))
        
        layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(t('ui.settings.save'))
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        index = self.combo_ui_lang.findData(config.UI_LANGUAGE)
        if index >= 0: self.combo_ui_lang.setCurrentIndex(index)
        
        index = self.combo_tags_lang.findData(config.TAGS_LANGUAGE)
        if index >= 0: self.combo_tags_lang.setCurrentIndex(index)
        
        if config.STEAM_PATH:
            self.path_edit.setText(str(config.STEAM_PATH))
            
        self.spin_tags.setValue(config.TAGS_PER_GAME)
        self.check_common.setChecked(config.IGNORE_COMMON_TAGS)
        self.spin_backups.setValue(config.MAX_BACKUPS)

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, t('ui.settings.select_steam_dir'))
        if path:
            self.path_edit.setText(path)

    def get_settings(self):
        return {
            'ui_language': self.combo_ui_lang.currentData(),
            'tags_language': self.combo_tags_lang.currentData(),
            'steam_path': self.path_edit.text(),
            'tags_per_game': self.spin_tags.value(),
            'ignore_common_tags': self.check_common.isChecked(),
            'max_backups': self.spin_backups.value()
        }
    
    def accept(self):
        new_lang = self.combo_ui_lang.currentData()
        if new_lang != config.UI_LANGUAGE:
            self.language_changed.emit(new_lang)
        super().accept()
