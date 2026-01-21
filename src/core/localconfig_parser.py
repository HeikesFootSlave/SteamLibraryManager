"""
LocalConfig Parser - Uses BackupManager (No Hardcoded Strings)
Speichern als: src/core/localconfig_parser.py
"""
import vdf
from pathlib import Path
from src.utils.i18n import t
from src.core.backup_manager import BackupManager

class LocalConfigParser:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.data = {}

    def load(self) -> bool:
        if not self.config_path or not self.config_path.exists():
            print(t('logs.parser.file_not_found', path=self.config_path))
            return False
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = vdf.load(f)
            
            if 'UserLocalConfigStore' not in self.data:
                pass
            
            print(t('logs.parser.loaded', count=len(self.get_all_app_ids())))
            return True
        except Exception as e:
            print(t('logs.parser.load_error', error=e))
            return False

    def save(self) -> bool:
        try:
            backup = BackupManager.create_rolling_backup(self.config_path)
            if backup:
                print(t('logs.parser.backup_created', path=Path(backup).name))

            with open(self.config_path, 'w', encoding='utf-8') as f:
                vdf.dump(self.data, f, pretty=True)
            print(t('logs.parser.saved'))
            return True
        except Exception as e:
            print(t('logs.parser.save_error', error=e))
            return False

    def get_apps_data(self):
        try:
            return self.data['UserLocalConfigStore']['Software']['Valve']['Steam']['apps']
        except KeyError:
            return {}

    def get_all_app_ids(self):
        apps = self.get_apps_data()
        return list(apps.keys())

    def get_app_categories(self, app_id: str):
        apps = self.get_apps_data()
        if app_id in apps and 'tags' in apps[app_id]:
            tags_dict = apps[app_id]['tags']
            if isinstance(tags_dict, dict):
                return list(tags_dict.values())
        return []

    def add_app_category(self, app_id: str, category: str):
        apps = self.get_apps_data()
        if app_id not in apps:
            apps[app_id] = {}
        
        if 'tags' not in apps[app_id]:
            apps[app_id]['tags'] = {}
        
        tags = apps[app_id]['tags']
        if category not in tags.values():
            idx = 0
            while str(idx) in tags:
                idx += 1
            tags[str(idx)] = category

    def remove_app_category(self, app_id: str, category: str):
        apps = self.get_apps_data()
        if app_id in apps and 'tags' in apps[app_id]:
            tags = apps[app_id]['tags']
            keys_to_remove = [k for k, v in tags.items() if v == category]
            for k in keys_to_remove:
                del tags[k]

    def rename_category(self, old_name: str, new_name: str):
        apps = self.get_apps_data()
        for app_id, data in apps.items():
            if 'tags' in data:
                for k, v in data['tags'].items():
                    if v == old_name:
                        data['tags'][k] = new_name

    def delete_category(self, category_name: str):
        apps = self.get_apps_data()
        for app_id, data in apps.items():
            if 'tags' in data:
                tags = data['tags']
                keys_to_delete = [k for k, v in tags.items() if v == category_name]
                for k in keys_to_delete:
                    del tags[k]
