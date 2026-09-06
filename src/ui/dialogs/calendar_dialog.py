"""Calendar selection modal dialog."""

from datetime import date
from tkinter import Toplevel, messagebox
from typing import Callable
import customtkinter as ctk

from src.ui.theme import COLORS


class CalendarModal(Toplevel):
    """Janela flutuante para seleção de data com estilo moderno."""

    def __init__(self, parent: ctk.CTkBaseClass, callback: Callable[[str], None]) -> None:
        super().__init__(parent)
        self.callback = callback
        self.title("📅 Selecione a Data")
        self.geometry("320x290")
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()

        try:
            from tkcalendar import Calendar  # Lazy import para resiliência
        except ImportError:
            messagebox.showerror(
                "Módulo Ausente",
                "A biblioteca 'tkcalendar' não está instalada.\nExecute: pip install tkcalendar",
            )
            self.destroy()
            return

        today = date.today()
        self.cal = Calendar(
            self,
            selectmode="day",
            year=today.year,
            month=today.month,
            day=today.day,
            date_pattern="y-mm-dd",
            background=COLORS["bg_card"],
            foreground=COLORS["text_primary"],
            headersbackground=COLORS["primary"],
            headersforeground="white",
            selectbackground=COLORS["primary"],
            selectforeground="white",
            normalbackground=COLORS["bg_main"],
            normalforeground=COLORS["text_primary"],
            weekendbackground=COLORS["bg_main"],
            weekendforeground=COLORS["text_accent"],
        )
        self.cal.pack(fill="both", expand=True, padx=15, pady=15)

        btn = ctk.CTkButton(
            self,
            text="✓ Confirmar",
            command=self.on_confirm,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        btn.pack(pady=(0, 15))

    def on_confirm(self) -> None:
        """Confirma a data escolhida e fecha o diálogo."""
        selected_date = self.cal.get_date()
        self.callback(selected_date)
        self.destroy()
