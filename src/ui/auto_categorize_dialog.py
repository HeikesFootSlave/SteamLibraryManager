"""
Auto-Categorize Dialog - MIT CHECKBOXEN für mehrere Methoden!
"""

import customtkinter as ctk
from typing import List, Callable, Optional
from src.core.game_manager import Game


class AutoCategorizeDialog(ctk.CTkToplevel):
    """Dialog für Auto-Kategorisierung"""
    
    def __init__(self, parent, games: List[Game], 
                 all_games_count: int,
                 on_start: Callable,
                 category_name: Optional[str] = None):
        super().__init__(parent)
        
        self.games = games
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        
        # Window setup
        self.title("Auto-Categorize")
        self.geometry("500x600")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.result = None
        self._create_ui()
    
    def _create_ui(self):
        """Create UI"""
        # Title
        title = ctk.CTkLabel(self, text="Auto-Categorize Games",
                            font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=15)
        
        # Content frame
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Method selection - ✅ CHECKBOXEN statt Radio-Buttons!
        method_label = ctk.CTkLabel(content, text="Methods (select multiple):",
                                    font=ctk.CTkFont(size=13, weight="bold"))
        method_label.pack(anchor="w", pady=(15, 5), padx=15)
        
        # ✅ CHECKBOXEN für jede Methode
        self.method_tags = ctk.BooleanVar(value=True)
        self.method_publisher = ctk.BooleanVar(value=False)
        self.method_franchise = ctk.BooleanVar(value=False)
        self.method_genre = ctk.BooleanVar(value=False)
        
        methods = [
            (self.method_tags, "By Steam Tags (Recommended)"),
            (self.method_publisher, "By Publisher"),
            (self.method_franchise, "By Franchise (LEGO, AC, etc.)"),
            (self.method_genre, "By Genre"),
        ]
        
        for var, text in methods:
            cb = ctk.CTkCheckBox(content, text=text, variable=var,
                                command=self._update_ui)
            cb.pack(anchor="w", padx=30, pady=2)
        
        # Separator
        sep1 = ctk.CTkFrame(content, height=2, fg_color=("gray70", "gray30"))
        sep1.pack(fill="x", padx=15, pady=15)
        
        # Tags settings (only visible when tags is checked)
        self.tags_frame = ctk.CTkFrame(content, fg_color="transparent")
        
        tags_label = ctk.CTkLabel(self.tags_frame, text="Tags per game:",
                                 font=ctk.CTkFont(size=12))
        tags_label.pack(anchor="w", padx=15)
        
        tags_input_frame = ctk.CTkFrame(self.tags_frame, fg_color="transparent")
        tags_input_frame.pack(anchor="w", padx=15, pady=5)
        
        self.tags_count = ctk.IntVar(value=13)
        
        # Entry
        self.tags_entry = ctk.CTkEntry(tags_input_frame, width=60,
                                       textvariable=self.tags_count)
        self.tags_entry.pack(side="left", padx=(0, 5))
        
        # Spinbox buttons
        spin_frame = ctk.CTkFrame(tags_input_frame, fg_color="transparent")
        spin_frame.pack(side="left")
        
        up_btn = ctk.CTkButton(spin_frame, text="▲", width=25, height=15,
                              command=lambda: self._change_tags(1))
        up_btn.pack()
        
        down_btn = ctk.CTkButton(spin_frame, text="▼", width=25, height=15,
                                command=lambda: self._change_tags(-1))
        down_btn.pack()
        
        ctk.CTkLabel(tags_input_frame, text="(1-20)",
                    text_color=("gray50", "gray50")).pack(side="left", padx=5)
        
        # Ignore common tags
        self.ignore_common = ctk.BooleanVar(value=True)
        ignore_cb = ctk.CTkCheckBox(self.tags_frame, text="Ignore common tags",
                                    variable=self.ignore_common)
        ignore_cb.pack(anchor="w", padx=30, pady=5)
        
        ctk.CTkLabel(self.tags_frame, 
                    text="(Singleplayer, Multiplayer, Controller, etc.)",
                    text_color=("gray50", "gray50"),
                    font=ctk.CTkFont(size=10)).pack(anchor="w", padx=45)
        
        self.tags_frame.pack(fill="x", pady=(0, 10))
        
        # Separator
        sep2 = ctk.CTkFrame(content, height=2, fg_color=("gray70", "gray30"))
        sep2.pack(fill="x", padx=15, pady=15)
        
        # Apply to
        apply_label = ctk.CTkLabel(content, text="Apply to:",
                                   font=ctk.CTkFont(size=13, weight="bold"))
        apply_label.pack(anchor="w", pady=(0, 5), padx=15)
        
        self.scope_var = ctk.StringVar(value="selected")
        
        if self.category_name:
            # Specific category
            scope_text = f"Selected category: {self.category_name} ({len(self.games)} games)"
            ctk.CTkRadioButton(content, text=scope_text, variable=self.scope_var,
                              value="selected").pack(anchor="w", padx=30, pady=2)
        else:
            # Uncategorized
            ctk.CTkRadioButton(content, text=f"Uncategorized games only ({len(self.games)} games)",
                              variable=self.scope_var, value="selected").pack(anchor="w", padx=30, pady=2)
        
        ctk.CTkRadioButton(content, text=f"All games ({self.all_games_count} games)",
                          variable=self.scope_var, value="all").pack(anchor="w", padx=30, pady=2)
        
        # Separator
        sep3 = ctk.CTkFrame(content, height=2, fg_color=("gray70", "gray30"))
        sep3.pack(fill="x", padx=15, pady=15)
        
        # Estimate
        self.estimate_label = ctk.CTkLabel(content, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color=("gray50", "gray50"))
        self.estimate_label.pack(pady=10)
        
        # Warning
        warning = ctk.CTkLabel(content,
                              text="⚠️ A backup will be created automatically",
                              font=ctk.CTkFont(size=11),
                              text_color=("orange", "orange"))
        warning.pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=15)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=120,
                                   command=self.cancel)
        cancel_btn.pack(side="left", padx=5)
        
        start_btn = ctk.CTkButton(btn_frame, text="Start", width=120,
                                 command=self.start)
        start_btn.pack(side="left", padx=5)
        
        self._update_ui()
    
    def _change_tags(self, delta: int):
        """Change tag count"""
        current = self.tags_count.get()
        new_value = max(1, min(20, current + delta))
        self.tags_count.set(new_value)
        self._update_ui()
    
    def _update_ui(self):
        """Update UI based on selections"""
        # Show/hide tags settings (nur wenn Tags-Checkbox aktiviert)
        if self.method_tags.get():
            self.tags_frame.pack(fill="x", pady=(0, 10))
        else:
            self.tags_frame.pack_forget()
        
        # Update estimate
        scope = self.scope_var.get()
        game_count = self.all_games_count if scope == "all" else len(self.games)
        
        # ✅ Count selected methods
        selected_methods = []
        if self.method_tags.get():
            selected_methods.append('tags')
        if self.method_publisher.get():
            selected_methods.append('publisher')
        if self.method_franchise.get():
            selected_methods.append('franchise')
        if self.method_genre.get():
            selected_methods.append('genre')
        
        # Estimate time (1.5s per game for tags, instant for others)
        if 'tags' in selected_methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = f"~{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_str = f"~{seconds} seconds"
        else:
            time_str = "< 1 second"
        
        methods_text = f"{len(selected_methods)} method(s) selected" if selected_methods else "No methods selected"
        
        self.estimate_label.configure(
            text=f"Estimated time: {time_str}\n({game_count} games, {methods_text})"
        )
    
    def start(self):
        """Start auto-categorization"""
        # ✅ Get ALL selected methods
        selected_methods = []
        if self.method_tags.get():
            selected_methods.append('tags')
        if self.method_publisher.get():
            selected_methods.append('publisher')
        if self.method_franchise.get():
            selected_methods.append('franchise')
        if self.method_genre.get():
            selected_methods.append('genre')
        
        # Validation
        if not selected_methods:
            from tkinter import messagebox
            messagebox.showwarning("No Method Selected", 
                                  "Please select at least one categorization method!")
            return
        
        self.result = {
            'methods': selected_methods,  # ✅ Liste von Methoden statt nur eine
            'scope': self.scope_var.get(),
            'tags_count': self.tags_count.get(),
            'ignore_common': self.ignore_common.get()
        }
        
        self.destroy()
        
        if self.on_start:
            self.on_start(self.result)
    
    def cancel(self):
        """Cancel"""
        self.result = None
        self.destroy()
