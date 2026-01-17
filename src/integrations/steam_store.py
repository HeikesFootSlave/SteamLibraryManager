"""
Steam Store Integration - Holt Tags und Details von Spielen
"""

import requests
import time
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from pathlib import Path
import json
from datetime import datetime, timedelta


class SteamStoreScraper:
    """Holt Tags und Details von Steam Store"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / 'store_tags'
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.5  # Sekunden zwischen Requests
        
        # Tag blacklist
        self.tag_blacklist = {
            'Singleplayer', 'Multiplayer', 'Co-op', 'Online Co-Op',
            'Local Co-Op', 'Shared/Split Screen', 'Cross-Platform Multiplayer',
            'Controller Support', 'Full controller support', 'Partial Controller Support',
            'Great Soundtrack', 'Atmospheric', 'Story Rich',
            'VR Support', 'VR Only', 'Tracked Controller Support',
            'Steam Achievements', 'Steam Cloud', 'Steam Trading Cards',
            'Steam Workshop', 'In-App Purchases', 'Includes level editor'
        }
    
    def get_game_tags(self, app_id: str, max_tags: int = 13, 
                     ignore_common: bool = True) -> List[str]:
        """
        Hole Tags für ein Spiel
        
        Args:
            app_id: Steam App ID
            max_tags: Maximale Anzahl Tags
            ignore_common: Ignoriere häufige/nutzlose Tags
            
        Returns:
            Liste von Tags
        """
        # Check cache
        cache_file = self.cache_dir / f'{app_id}.json'
        
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(days=30):
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    tags = cached_data.get('tags', [])
                    return self._filter_tags(tags, max_tags, ignore_common)
        
        # Fetch from Steam Store
        tags = self._fetch_tags_from_store(app_id)
        
        if tags:
            # Cache
            with open(cache_file, 'w') as f:
                json.dump({'tags': tags, 'fetched_at': datetime.now().isoformat()}, f)
        
        return self._filter_tags(tags, max_tags, ignore_common)
    
    def _fetch_tags_from_store(self, app_id: str) -> List[str]:
        """Fetch tags from Steam Store page"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        try:
            url = f'https://store.steampowered.com/app/{app_id}'
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            self.last_request_time = time.time()
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find tags
            tags = []
            tag_elements = soup.find_all('a', class_='app_tag')
            
            for tag_elem in tag_elements:
                tag_text = tag_elem.text.strip()
                if tag_text:
                    tags.append(tag_text)
            
            return tags
            
        except Exception as e:
            print(f"Error fetching tags for {app_id}: {e}")
            return []
    
    def _filter_tags(self, tags: List[str], max_tags: int, 
                    ignore_common: bool) -> List[str]:
        """Filter und limitiere Tags"""
        filtered = []
        
        for tag in tags:
            # Skip blacklist
            if ignore_common and tag in self.tag_blacklist:
                continue
            
            filtered.append(tag)
            
            # Limit
            if len(filtered) >= max_tags:
                break
        
        return filtered
    
    def fetch_multiple_games(self, app_ids: List[str], max_tags: int = 13,
                            ignore_common: bool = True,
                            progress_callback = None) -> Dict[str, List[str]]:
        """
        Hole Tags für mehrere Spiele
        
        Args:
            app_ids: Liste von App IDs
            max_tags: Max Tags pro Spiel
            ignore_common: Ignoriere häufige Tags
            progress_callback: Callback(current, total, game_name)
            
        Returns:
            Dict: {app_id: [tags]}
        """
        results = {}
        total = len(app_ids)
        
        for i, app_id in enumerate(app_ids):
            if progress_callback:
                progress_callback(i + 1, total, app_id)
            
            tags = self.get_game_tags(app_id, max_tags, ignore_common)
            results[app_id] = tags
        
        return results


class FranchiseDetector:
    """Erkennt Franchises anhand von Spielnamen"""
    
    # Bekannte Franchises
    FRANCHISES = {
        'LEGO': ['lego'],
        'Assassin\'s Creed': ['assassin\'s creed', 'assassins creed'],
        'Dark Souls': ['dark souls'],
        'The Elder Scrolls': ['elder scrolls', 'skyrim', 'oblivion', 'morrowind'],
        'Fallout': ['fallout'],
        'Far Cry': ['far cry'],
        'Call of Duty': ['call of duty'],
        'Tomb Raider': ['tomb raider', 'lara croft'],
        'Grand Theft Auto': ['grand theft auto', 'gta'],
        'The Witcher': ['witcher'],
        'Batman Arkham': ['batman arkham', 'batman: arkham'],
        'Borderlands': ['borderlands'],
        'BioShock': ['bioshock'],
        'Metro': ['metro 2033', 'metro last light', 'metro exodus'],
        'Dishonored': ['dishonored'],
        'Deus Ex': ['deus ex'],
        'Mass Effect': ['mass effect'],
        'Dragon Age': ['dragon age'],
        'Resident Evil': ['resident evil'],
        'Total War': ['total war'],
        'Civilization': ['civilization', 'sid meier\'s civilization'],
        'DOOM': ['doom'],
        'Wolfenstein': ['wolfenstein'],
        'Hitman': ['hitman'],
    }
    
    @classmethod
    def detect_franchise(cls, game_name: str) -> Optional[str]:
        """
        Erkenne Franchise
        
        Args:
            game_name: Spielname
            
        Returns:
            Franchise-Name oder None
        """
        name_lower = game_name.lower()
        
        for franchise, patterns in cls.FRANCHISES.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return franchise
        
        return None
