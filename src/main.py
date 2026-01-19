#!/usr/bin/env python3
"""
Steam Library Manager - Main Entry Point (PyQt6 Version)
Speichern als: src/main.py
"""
import sys
from pathlib import Path

# Add project root to path (works from anywhere)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from src.config import config
from src.utils.i18n import init_i18n, t
from src.ui.main_window import MainWindow


def main():
    # 1. Sprache initialisieren (BEVOR wir irgendwas ausgeben)
    init_i18n(config.DEFAULT_LOCALE)

    # 2. Jetzt können wir übersetzte Logs ausgeben
    print("=" * 60)
    print(t('cli.banner'))
    print("=" * 60)

    print(t('cli.initializing'))

    if config.STEAM_PATH:
        print(t('cli.steam_found', path=config.STEAM_PATH))
        user_ids = config.get_all_user_ids()
        if user_ids:
            print(t('cli.users_found', count=len(user_ids)))
            if not config.STEAM_USER_ID and len(user_ids) == 1:
                config.STEAM_USER_ID = user_ids[0]
    else:
        print(t('cli.steam_not_found'))

    print(f"\n{t('cli.starting')}\n")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Steam Library Manager")

        # Qt automatically detects and applies system theme
        print(t('cli.qt_theme'))

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n{t('cli.error', error=e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
