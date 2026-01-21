"""
Backup Manager - Handles Rolling Backups (No Hardcoded Strings)
Speichern als: src/core/backup_manager.py
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from src.config import config
from src.utils.i18n import t

class BackupManager:
    
    @staticmethod
    def create_rolling_backup(source_file: Path) -> str:
        if not source_file.exists():
            return ""

        max_backups = config.MAX_BACKUPS
        if max_backups <= 0: return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_file.name}.{timestamp}.bak"
        backup_path = source_file.parent / backup_name

        try:
            shutil.copy2(source_file, backup_path)
            BackupManager._rotate_backups(source_file, max_backups)
            return str(backup_path)
        except Exception as e:
            # Fehler, die beim Backup passieren, loggen wir direkt
            print(f"Backup Error: {e}")
            return ""

    @staticmethod
    def _rotate_backups(source_file: Path, limit: int):
        directory = source_file.parent
        backups = []
        for file in directory.glob(f"{source_file.name}.*.bak"):
            backups.append(file)
            
        backups.sort(key=os.path.getmtime, reverse=True)
        
        if len(backups) > limit:
            to_delete = backups[limit:]
            for old_backup in to_delete:
                try:
                    os.remove(old_backup)
                    print(t('logs.backup.rotated', name=old_backup.name))
                except OSError as e:
                    print(t('logs.backup.delete_error', name=old_backup.name, error=e))
