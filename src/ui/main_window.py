"""Main Window - NEUES DESIGN mit Spielen in Kategorien!"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, List
from datetime import datetime
from src.utils.i18n import t
from src.config import config
from src.ui.components.category_tree import CategoryTreeWithGames
from src.ui.auto_categorize_dialog import AutoCategorizeDialog
from src.integrations.steam_store import SteamStoreScraper, FranchiseDetector
from src.core.localconfig_parser import LocalConfigParser
from src.core.localconfig_parser import LocalConfigParser
from src.core.game_manager import GameManager, Game


class ResizablePane(ctk.CTkFrame):
    """Resizable Pane - kann mit Maus links/rechts gezogen werden"""
    
    def __init__(self, parent, initial_width=400, min_width=250, max_width=800):
        super().__init__(parent, width=initial_width, fg_color="transparent")
        self.pack_propagate(False)
        
        self.min_width = min_width
        self.max_width = max_width
        self.current_width = initial_width
        
        # Resize handle (rechter Rand)
        self.handle = ctk.CTkFrame(self, width=5, cursor="sb_h_double_arrow",
                                   fg_color=("gray70", "gray30"))
        self.handle.pack(side="right", fill="y")
        
        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)
        
        # Bind resize
        self.handle.bind("<Button-1>", self.start_resize)
        self.handle.bind("<B1-Motion>", self.do_resize)
        
        self.resize_start_x = 0
        self.resize_start_width = 0
    
    def start_resize(self, event):
        """Start resizing"""
        self.resize_start_x = event.x_root
        self.resize_start_width = self.current_width
    
    def do_resize(self, event):
        """Resize while dragging"""
        delta = event.x_root - self.resize_start_x
        new_width = self.resize_start_width + delta
        
        # Clamp to min/max
        new_width = max(self.min_width, min(self.max_width, new_width))
        
        self.current_width = new_width
        self.configure(width=new_width)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(t('ui.main.title'))
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        ctk.set_appearance_mode(config.THEME)
        
        # Data
        self.game_manager: Optional[GameManager] = None
        self.vdf_parser: Optional[LocalConfigParser] = None
        self.selected_game: Optional[Game] = None
        self.steam_scraper: Optional[SteamStoreScraper] = None
        
        self._create_ui()
        self._load_data()
    
    def _create_ui(self):
        """Erstelle UI"""
        # Menubar
        menu = ctk.CTkFrame(self, height=30, fg_color=("gray85", "gray20"))
        menu.pack(fill="x", side="top")
        
        ctk.CTkButton(menu, text=t('ui.menu.file'), width=60,
                     fg_color="transparent", hover_color=("gray75", "gray30")).pack(side="left", padx=2)
        
        self.user_label = ctk.CTkLabel(menu, text=t('ui.status.not_logged_in'),
                                       font=ctk.CTkFont(size=11))
        self.user_label.pack(side="right", padx=10)
        
        # Toolbar
        toolbar = ctk.CTkFrame(self, height=40, fg_color=("gray90", "gray15"))
        toolbar.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(toolbar, text="🔄 Refresh", width=100,
                     command=self.refresh_data).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="🏷️ Auto-Categorize", width=150,
                     command=self.auto_categorize).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="⚙️ Settings", width=100,
                     command=self.show_settings).pack(side="right", padx=2)
        
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=5, pady=5)
        
        # === LEFT: Resizable pane with categories + games ===
        self.left_pane = ResizablePane(main, initial_width=450, min_width=300, max_width=800)
        self.left_pane.pack(side="left", fill="both", pady=0)
        
        # Search in left pane
        search_frame = ctk.CTkFrame(self.left_pane.content, fg_color="transparent", height=35)
        search_frame.pack(fill="x", padx=5, pady=(0, 5))
        search_frame.pack_propagate(False)
        
        ctk.CTkLabel(search_frame, text="🔍", width=30).pack(side="left")
        self.search_entry = ctk.CTkEntry(search_frame,
                                         placeholder_text=t('ui.main.search_placeholder'))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        ctk.CTkButton(search_frame, text="×", width=30,
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=self.clear_search).pack(side="left")
        
        # Category tree with games
        self.cat_tree = CategoryTreeWithGames(self.left_pane.content, 
                                             on_game_click=self.on_game_selected,
                                             on_game_right_click=self.on_game_right_click,
                                             on_category_right_click=self.on_category_right_click)
        self.cat_tree.pack(fill="both", expand=True, padx=5)
        
        # Loading label
        self.loading_label = ctk.CTkLabel(self.cat_tree,
                                         text="Loading...",
                                         font=ctk.CTkFont(size=16))
        self.loading_label.pack(pady=50)
        
        # === RIGHT: Details ===
        right = ctk.CTkFrame(main, fg_color=("gray90", "gray15"))
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        self.details_title = ctk.CTkLabel(right, text=t('ui.game_details.title'),
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.details_title.pack(pady=10)
        
        self.details_content = ctk.CTkScrollableFrame(right)
        self.details_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.details_placeholder = ctk.CTkLabel(
            self.details_content,
            text="Select a game to view details",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray50")
        )
        self.details_placeholder.pack(pady=50)
        
        # Statusbar
        self.statusbar = ctk.CTkFrame(self, height=25, fg_color=("gray85", "gray20"))
        self.statusbar.pack(fill="x", side="bottom")
        self.status_label = ctk.CTkLabel(self.statusbar, text=t('ui.status.ready'),
                                        font=ctk.CTkFont(size=10))
        self.status_label.pack(side="left", padx=10)
    
    def _load_data(self):
        """Lade Daten"""
        self.set_status("Loading data...")
        
        if not config.STEAM_PATH:
            self.loading_label.configure(text="❌ Steam not found!")
            return
        
        user_ids = config.get_all_user_ids()
        if not user_ids:
            self.loading_label.configure(text="❌ No users found!")
            return
        
        account_id = user_ids[0]
        steam_id64 = config.STEAM_USER_ID if config.STEAM_USER_ID else account_id
        
        self.user_label.configure(text=f"User: {account_id}")
        
        # Load localconfig
        config_path = config.get_localconfig_path(account_id)
        if not config_path:
            self.loading_label.configure(text="❌ localconfig.vdf not found!")
            return
        
        self.vdf_parser = LocalConfigParser(config_path)
        if not self.vdf_parser.load():
            self.loading_label.configure(text="❌ Error loading localconfig.vdf")
            return
        
        # Load from Steam API
        if not config.STEAM_API_KEY:
            self.loading_label.configure(text="❌ No Steam API key\nSet in .env")
            return
        
        self.game_manager = GameManager(config.STEAM_API_KEY, config.CACHE_DIR)
        
        self.loading_label.configure(text="Loading from Steam API...")
        self.update()
        
        if not self.game_manager.load_from_steam_api(steam_id64):
            self.loading_label.configure(text="❌ Error loading from Steam API")
            return
        
        self.game_manager.merge_with_localconfig(self.vdf_parser)
        
        # Initialize scraper
        self.steam_scraper = SteamStoreScraper(config.CACHE_DIR)
        
        # Populate categories
        self.loading_label.destroy()
        self._populate_categories()
        self.set_status(f"Loaded {len(self.game_manager.games)} games")
    
    def _populate_categories(self):
        """Fülle Kategorien mit Spielen"""
        if not self.game_manager:
            return
        
        # Clear
        self.cat_tree.clear()
        
        # All games
        all_games = sorted(self.game_manager.get_all_games(), key=lambda g: g.name.lower())
        self.cat_tree.add_category("All Games", "📁", all_games)
        
        # Favorites
        favorites = sorted(self.game_manager.get_favorites(), key=lambda g: g.name.lower())
        if favorites:
            self.cat_tree.add_category("Favorites", "⭐", favorites)
        
        # Uncategorized
        uncat = sorted(self.game_manager.get_uncategorized_games(), key=lambda g: g.name.lower())
        if uncat:
            self.cat_tree.add_category("Uncategorized", "📦", uncat)
        
        # User categories
        categories = self.game_manager.get_all_categories()
        for cat_name in sorted(categories.keys()):
            if cat_name != 'favorite':
                cat_games = sorted(self.game_manager.get_games_by_category(cat_name),
                                  key=lambda g: g.name.lower())
                self.cat_tree.add_category(cat_name, "📂", cat_games)
    
    def on_game_selected(self, game: Game):
        """Spiel wurde ausgewählt"""
        self.selected_game = game
        self._show_game_details(game)
        self.set_status(f"Selected: {game.name}")
    
    def on_game_right_click(self, game: Game, event):
        """Rechtsklick auf Spiel"""
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color=("gray90", "gray15"))
        
        # Menu items
        ctk.CTkButton(menu, text="📋 View Details", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.on_game_selected(game), menu.destroy()]).pack(fill="x")
        
        ctk.CTkButton(menu, text="⭐ Toggle Favorite", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.toggle_favorite(game), menu.destroy()]).pack(fill="x")
        
        ctk.CTkButton(menu, text="🌐 Open in Steam Store", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.open_in_store(game), menu.destroy()]).pack(fill="x")
        
        # Close on click outside
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()
    
    def on_category_right_click(self, category: str, event):
        """Rechtsklick auf Kategorie"""
        # Ignore special categories
        if category in ["All Games", "Favorites", "Uncategorized"]:
            return
        
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color=("gray90", "gray15"))
        
        # Menu items
        ctk.CTkButton(menu, text="✏️ Rename", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.rename_category(category), menu.destroy()]).pack(fill="x")
        
        ctk.CTkButton(menu, text="🗑️ Delete", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.delete_category(category), menu.destroy()]).pack(fill="x")
        
        # Auto-categorize THIS category
        ctk.CTkButton(menu, text="🏷️ Auto-Categorize", anchor="w",
                     fg_color="transparent", hover_color=("gray80", "gray25"),
                     command=lambda: [self.auto_categorize_category(category), menu.destroy()]).pack(fill="x")
        
        # Close on click outside
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()
    
    def _show_game_details(self, game: Game):
        """Zeige Spiel-Details"""
        self.details_placeholder.pack_forget()
        
        for widget in self.details_content.winfo_children():
            widget.destroy()
        
        self.details_title.configure(text=game.name)
        
        # Info
        self._add_detail("App ID:", game.app_id)
        self._add_detail("Playtime:", f"{game.playtime_hours} hours")
        if game.developer:
            self._add_detail("Developer:", game.developer)
        if game.publisher:
            self._add_detail("Publisher:", game.publisher)
        
        # Categories
        ctk.CTkLabel(self.details_content, text="Categories:",
                    font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(15, 5))
        
        all_categories = sorted(self.game_manager.get_all_categories().keys())
        for cat in all_categories:
            if cat != 'favorite':
                var = ctk.BooleanVar(value=game.has_category(cat))
                cb = ctk.CTkCheckBox(self.details_content, text=cat, variable=var,
                                    command=lambda c=cat, v=var: self.toggle_category(game, c, v))
                cb.pack(anchor="w", pady=2)
    
    def _add_detail(self, label: str, value: str):
        """Detail-Feld"""
        frame = ctk.CTkFrame(self.details_content, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(frame, text=label, width=100, anchor="w",
                    font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(frame, text=value, anchor="w").pack(side="left")
    
    def toggle_category(self, game: Game, category: str, var: ctk.BooleanVar):
        """Toggle Kategorie"""
        if var.get():
            if category not in game.categories:
                game.categories.append(category)
                self.vdf_parser.add_app_category(game.app_id, category)
        else:
            if category in game.categories:
                game.categories.remove(category)
                self.vdf_parser.remove_app_category(game.app_id, category)
        
        self.vdf_parser.save()
        self._populate_categories()
        self.set_status(f"Updated: {game.name}")
    
    def on_search(self, event):
        """Suche in Echtzeit"""
        query = self.search_entry.get().strip().lower()
        
        if not query:
            # Zeige alle Kategorien
            self._populate_categories()
            return
        
        if not self.game_manager:
            return
        
        # Suche Spiele
        results = [g for g in self.game_manager.get_all_games() 
                   if query in g.name.lower()]
        
        # Clear und zeige nur Suchergebnisse
        self.cat_tree.clear()
        
        if results:
            sorted_results = sorted(results, key=lambda g: g.name.lower())
            self.cat_tree.add_category(f"Search Results ({len(results)})", "🔍", sorted_results)
            # Auto-expand search results
            if "Search Results" in self.cat_tree.categories:
                self.cat_tree.categories[f"Search Results ({len(results)})"].expand()
            self.set_status(f"Found {len(results)} games")
        else:
            # No results
            no_results = ctk.CTkLabel(self.cat_tree, 
                                     text=f"No games found for '{query}'",
                                     font=ctk.CTkFont(size=13),
                                     text_color=("gray50", "gray50"))
            no_results.pack(pady=50)
            self.set_status("No results")
    
    def clear_search(self):
        """Clear search"""
        self.search_entry.delete(0, "end")
        self._populate_categories()
        self.set_status("Ready")
    
    def refresh_data(self):
        """Refresh"""
        self._load_data()
    
    def toggle_favorite(self, game: Game):
        """Toggle Favorite"""
        if game.is_favorite():
            game.categories.remove('favorite')
            self.vdf_parser.remove_app_category(game.app_id, 'favorite')
        else:
            game.categories.append('favorite')
            self.vdf_parser.add_app_category(game.app_id, 'favorite')
        
        self.vdf_parser.save()
        self._populate_categories()
        self.set_status(f"Toggled favorite: {game.name}")
    
    def open_in_store(self, game: Game):
        """Öffne im Steam Store"""
        import webbrowser
        webbrowser.open(f"https://store.steampowered.com/app/{game.app_id}")
        self.set_status(f"Opened {game.name} in browser")
    
    def rename_category(self, old_name: str):
        """Kategorie umbenennen"""
        dialog = ctk.CTkInputDialog(text=f"Rename '{old_name}' to:", title="Rename Category")
        new_name = dialog.get_input()
        
        if new_name and new_name != old_name:
            self.vdf_parser.rename_category(old_name, new_name)
            self.vdf_parser.save()
            self._populate_categories()
            self.set_status(f"Renamed: {old_name} → {new_name}")
    
    def delete_category(self, category: str):
        """Kategorie löschen"""
        result = messagebox.askyesno("Delete Category", 
                                     f"Delete category '{category}'?\n\nGames will not be deleted.")
        if result:
            self.vdf_parser.delete_category(category)
            self.vdf_parser.save()
            self._populate_categories()
            self.set_status(f"Deleted category: {category}")
    
    def auto_categorize(self):
        """Auto-categorize (Toolbar button)"""
        uncat = self.game_manager.get_uncategorized_games()
        self._show_auto_categorize_dialog(uncat, None)
    
    def auto_categorize_category(self, category: str):
        """Auto-categorize specific category"""
        games = self.game_manager.get_games_by_category(category)
        self._show_auto_categorize_dialog(games, category)
    
    def _show_auto_categorize_dialog(self, games: List[Game], category_name: Optional[str]):
        """Show auto-categorize dialog"""
        dialog = AutoCategorizeDialog(
            self, games, len(self.game_manager.games),
            self._do_auto_categorize, category_name
        )
        dialog.wait_window()
    
    def _do_auto_categorize(self, settings: dict):
        """Execute auto-categorization"""
        if not settings:
            return
        
        # Create backup
        backup_path = config.STEAM_PATH / 'userdata' / config.STEAM_USER_ID / 'config' / \
                     f'localconfig_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.vdf'
        
        import shutil
        shutil.copy2(self.vdf_parser.config_path, backup_path)
        self.set_status(f"Backup created: {backup_path.name}")
        
        # Get games to process
        if settings['scope'] == 'all':
            games = self.game_manager.get_all_games()
        else:
            games = self.selected_games if hasattr(self, 'selected_games') else \
                   self.game_manager.get_uncategorized_games()
        
        method = settings['method']
        
        # Progress dialog
        progress = ctk.CTkToplevel(self)
        progress.title("Auto-Categorizing...")
        progress.geometry("400x150")
        progress.resizable(False, False)
        
        progress_label = ctk.CTkLabel(progress, text="Starting...",
                                     font=ctk.CTkFont(size=13))
        progress_label.pack(pady=20)
        
        progress_bar = ctk.CTkProgressBar(progress, width=350)
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        
        status_label = ctk.CTkLabel(progress, text="", 
                                   text_color=("gray50", "gray50"))
        status_label.pack(pady=5)
        
        self.update()
        
        # Execute based on method
        if method == 'tags':
            self._categorize_by_tags(games, settings, progress_label, 
                                    progress_bar, status_label)
        elif method == 'publisher':
            self._categorize_by_publisher(games, progress_label)
        elif method == 'franchise':
            self._categorize_by_franchise(games, progress_label)
        elif method == 'genre':
            self._categorize_by_genre(games, progress_label)
        
        # Save and refresh
        self.vdf_parser.save()
        progress.destroy()
        self._populate_categories()
        
        messagebox.showinfo("Success", 
                          f"Auto-categorization complete!\n\n"
                          f"Backup saved: {backup_path.name}")
    
    def _categorize_by_tags(self, games: List[Game], settings: dict,
                           label, pbar, status):
        """Categorize by Steam tags"""
        from datetime import datetime
        
        total = len(games)
        
        for i, game in enumerate(games):
            label.configure(text=f"Processing {i+1}/{total}")
            pbar.set((i+1) / total)
            status.configure(text=game.name[:40] + "..." if len(game.name) > 40 else game.name)
            self.update()
            
            # Get tags
            tags = self.steam_scraper.get_game_tags(
                game.app_id, 
                settings['tags_count'],
                settings['ignore_common']
            )
            
            # Add to categories
            for tag in tags:
                self.vdf_parser.add_app_category(game.app_id, tag)
                if tag not in game.categories:
                    game.categories.append(tag)
    
    def _categorize_by_publisher(self, games: List[Game], label):
        """Categorize by publisher"""
        label.configure(text="Categorizing by publisher...")
        self.update()
        
        for game in games:
            if game.publisher:
                category = f"Publisher: {game.publisher}"
                self.vdf_parser.add_app_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
    
    def _categorize_by_franchise(self, games: List[Game], label):
        """Categorize by franchise"""
        label.configure(text="Detecting franchises...")
        self.update()
        
        for game in games:
            franchise = FranchiseDetector.detect_franchise(game.name)
            if franchise:
                category = f"Franchise: {franchise}"
                self.vdf_parser.add_app_category(game.app_id, category)
                if category not in game.categories:
                    game.categories.append(category)
    
    def _categorize_by_genre(self, games: List[Game], label):
        """Categorize by genre"""
        label.configure(text="Categorizing by genre...")
        self.update()
        
        for game in games:
            if game.genres:
                for genre in game.genres:
                    self.vdf_parser.add_app_category(game.app_id, genre)
                    if genre not in game.categories:
                        game.categories.append(genre)
    
    def show_settings(self):
        """Settings"""
        messagebox.showinfo("TODO", "Coming soon!")
    
    def set_status(self, text: str):
        """Status"""
        self.status_label.configure(text=text)


def main():
    from src.utils.i18n import init_i18n
    init_i18n(config.DEFAULT_LOCALE)
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
