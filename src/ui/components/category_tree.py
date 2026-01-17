"""Category Tree - MIT Spielen drin! Virtualisiert für Performance"""
import customtkinter as ctk
from typing import Optional, Callable, List, Dict
from src.utils.i18n import t


class GameItem(ctk.CTkFrame):
    """Ein Spiel-Item (lightweight)"""
    
    def __init__(self, parent, game, on_click: Optional[Callable] = None,
                 on_right_click: Optional[Callable] = None):
        super().__init__(parent, fg_color="transparent", height=25)
        self.pack_propagate(False)
        self.game = game
        
        # Name
        name_label = ctk.CTkLabel(
            self, text=f"  • {game.name}", 
            anchor="w", width=250
        )
        name_label.pack(side="left", padx=5)
        
        # Playtime
        playtime = f"{game.playtime_hours}h" if game.playtime_hours > 0 else ""
        if playtime:
            time_label = ctk.CTkLabel(self, text=playtime, width=50)
            time_label.pack(side="left", padx=5)
        
        # Favorite indicator
        if game.is_favorite():
            fav_label = ctk.CTkLabel(self, text="⭐", width=20)
            fav_label.pack(side="left")
        
        # Click
        self.bind("<Button-1>", lambda e: on_click(game) if on_click else None)
        name_label.bind("<Button-1>", lambda e: on_click(game) if on_click else None)
        
        # Right-click
        self.bind("<Button-3>", lambda e: on_right_click(game, e) if on_right_click else None)
        name_label.bind("<Button-3>", lambda e: on_right_click(game, e) if on_right_click else None)
        
        # Hover
        self.bind("<Enter>", lambda e: self.configure(fg_color=("gray85", "gray20")))
        self.bind("<Leave>", lambda e: self.configure(fg_color="transparent"))


class CategoryItem(ctk.CTkFrame):
    """Kategorie mit ausklappbaren Spielen"""
    
    def __init__(self, parent, name: str, icon: str, games: List,
                 on_game_click: Optional[Callable] = None,
                 on_game_right_click: Optional[Callable] = None,
                 on_category_right_click: Optional[Callable] = None):
        super().__init__(parent, fg_color="transparent")
        
        self.name = name
        self.games = games
        self.on_game_click = on_game_click
        self.on_game_right_click = on_game_right_click
        self.on_category_right_click = on_category_right_click
        self.is_expanded = False
        self.game_widgets: List[GameItem] = []
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        
        # Expand button
        self.expand_btn = ctk.CTkButton(
            self.header, text="▶", width=25, height=25,
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=self.toggle
        )
        self.expand_btn.pack(side="left", padx=2)
        
        # Label
        label_text = f"{icon} {name} ({len(games)})"
        self.label = ctk.CTkLabel(
            self.header, text=label_text, 
            anchor="w", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.label.pack(side="left", fill="x", expand=True, padx=5)
        
        # Right-click on category
        self.header.bind("<Button-3>", lambda e: self._on_right_click(e))
        self.label.bind("<Button-3>", lambda e: self._on_right_click(e))
        
        # Games container (hidden initially)
        self.games_container = ctk.CTkFrame(self, fg_color="transparent")
    
    def _on_right_click(self, event):
        """Handle right-click on category"""
        if self.on_category_right_click:
            self.on_category_right_click(self.name, event)
    
    def toggle(self):
        """Toggle expand/collapse"""
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        """Klappe Spiele aus"""
        if self.is_expanded:
            return
        
        self.is_expanded = True
        self.expand_btn.configure(text="▼")
        
        # Show container
        self.games_container.pack(fill="x", padx=(20, 0))
        
        # Add games (virtualized - nur erste 100)
        display_games = self.games[:100]  # Limit für Performance
        
        for game in display_games:
            item = GameItem(self.games_container, game, self.on_game_click, 
                          self.on_game_right_click)
            item.pack(fill="x", pady=1)
            self.game_widgets.append(item)
        
        # Show "... and X more" wenn mehr als 100
        if len(self.games) > 100:
            more_label = ctk.CTkLabel(
                self.games_container,
                text=f"  ... and {len(self.games) - 100} more games",
                text_color=("gray50", "gray50"),
                font=ctk.CTkFont(size=10, slant="italic")
            )
            more_label.pack(pady=5)
    
    def collapse(self):
        """Klappe Spiele ein"""
        if not self.is_expanded:
            return
        
        self.is_expanded = False
        self.expand_btn.configure(text="▶")
        
        # Remove all game widgets
        for widget in self.game_widgets:
            widget.destroy()
        self.game_widgets.clear()
        
        # Hide container
        self.games_container.pack_forget()


class CategoryTreeWithGames(ctk.CTkScrollableFrame):
    """Category Tree mit Spielen - Neue Version!"""
    
    def __init__(self, parent, on_game_click: Optional[Callable] = None,
                 on_game_right_click: Optional[Callable] = None,
                 on_category_right_click: Optional[Callable] = None):
        super().__init__(parent, fg_color=("gray90", "gray15"))
        
        self.on_game_click = on_game_click
        self.on_game_right_click = on_game_right_click
        self.on_category_right_click = on_category_right_click
        self.categories: Dict[str, CategoryItem] = {}
        
        # Header mit +/- Buttons
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)
        
        title = ctk.CTkLabel(
            header, 
            text=t('ui.categories.title') + " (ALL)",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        title.pack(side="left")
        
        # Expand/Collapse All buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        expand_all_btn = ctk.CTkButton(
            btn_frame, text="[+]", width=30, height=24,
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=self.expand_all
        )
        expand_all_btn.pack(side="left", padx=2)
        
        collapse_all_btn = ctk.CTkButton(
            btn_frame, text="[−]", width=30, height=24,
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            command=self.collapse_all
        )
        collapse_all_btn.pack(side="left", padx=2)
        
        # Separator
        sep = ctk.CTkFrame(self, height=2, fg_color=("gray70", "gray30"))
        sep.pack(fill="x", padx=5, pady=(0, 5))
    
    def add_category(self, name: str, icon: str, games: List):
        """
        Füge Kategorie mit Spielen hinzu
        
        Args:
            name: Kategorie-Name
            icon: Icon (Emoji)
            games: Liste von Game-Objekten
        """
        item = CategoryItem(self, name, icon, games, self.on_game_click,
                          self.on_game_right_click, self.on_category_right_click)
        item.pack(fill="x", pady=2, padx=5)
        self.categories[name] = item
    
    def expand_all(self):
        """Klappe alle Kategorien aus"""
        for cat in self.categories.values():
            if not cat.is_expanded:
                cat.expand()
    
    def collapse_all(self):
        """Klappe alle Kategorien ein"""
        for cat in self.categories.values():
            if cat.is_expanded:
                cat.collapse()
    
    def clear(self):
        """Lösche alle Kategorien"""
        for cat in self.categories.values():
            cat.destroy()
        self.categories.clear()
    
    def filter_games(self, query: str):
        """
        Filtere Spiele nach Suchbegriff
        TODO: Implementieren
        """
        pass
