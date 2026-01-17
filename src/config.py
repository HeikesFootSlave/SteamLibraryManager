"""Configuration - Aktualisiert"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    
    STEAM_API_KEY: str = os.getenv('STEAM_API_KEY', '')
    STEAMGRIDDB_API_KEY: str = os.getenv('STEAMGRIDDB_API_KEY', '')
    
    STEAM_PATH: Optional[Path] = None
    STEAM_USER_ID: Optional[str] = os.getenv('STEAM_USER_ID', None)
    
    DEFAULT_LOCALE: str = 'en'
    THEME: str = 'dark'
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 800
    
    TAGS_PER_GAME: int = 13
    IGNORE_COMMON_TAGS: bool = True
    
    def __post_init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        (self.CACHE_DIR / 'game_tags').mkdir(exist_ok=True)
        (self.CACHE_DIR / 'store_data').mkdir(exist_ok=True)
        
        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()
    
    def _find_steam_path(self) -> Optional[Path]:
        """Finde Steam Installation auf Linux"""
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
                return p
        return None
    
    def get_localconfig_path(self, user_id: Optional[str] = None) -> Optional[Path]:
        """
        Pfad zur localconfig.vdf für einen User
        
        Args:
            user_id: Steam User ID (optional, nutzt gespeicherte ID falls None)
            
        Returns:
            Path zur localconfig.vdf oder None
        """
        if user_id is None:
            user_id = self.STEAM_USER_ID
        
        if self.STEAM_PATH and user_id:
            config_path = self.STEAM_PATH / 'userdata' / user_id / 'config' / 'localconfig.vdf'
            if config_path.exists():
                return config_path
        
        return None
    
    def get_all_user_ids(self) -> list:
        """Finde alle Steam User IDs im userdata Ordner"""
        if not self.STEAM_PATH:
            return []
        
        userdata = self.STEAM_PATH / 'userdata'
        if not userdata.exists():
            return []
        
        ids = []
        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / 'config' / 'localconfig.vdf').exists():
                    ids.append(item.name)
        return ids

config = Config()
