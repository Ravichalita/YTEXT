"""Channel search history modal dialog."""

from typing import Callable
import customtkinter as ctk

from src.core.config_manager import ConfigManager
from src.ui.theme import COLORS


class HistoryDialog(ctk.CTkToplevel):
    """Janela flutuante exibindo o histórico de canais e buscas recentes."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        config_manager: ConfigManager,
        on_item_selected: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.on_item_selected = on_item_selected

        self.title("📋 Histórico de Busca")
        self.geometry("380x480")
        self.configure(fg_color=COLORS["bg_main"])
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="📺 Canais e Buscas Recentes",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(pady=15)

        history = self.config_manager.load_history()
        if not history:
            ctk.CTkLabel(
                self,
                text="Nenhum histórico disponível.",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_muted"],
            ).pack(expand=True)
            return

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"],
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        for item in history:
            display_text = item[:40] + "..." if len(item) > 40 else item
            btn = ctk.CTkButton(
                scroll,
                text=display_text,
                fg_color="transparent",
                hover_color=COLORS["bg_card_hover"],
                border_width=0,
                text_color=COLORS["text_primary"],
                anchor="w",
                height=40,
                corner_radius=6,
                font=ctk.CTkFont(size=13),
            )
            btn.pack(fill="x", pady=2, padx=10)
            btn.configure(command=lambda entry=item: self._select_entry(entry))

    def _select_entry(self, entry: str) -> None:
        """Seleciona a entrada e fecha a janela."""
        self.on_item_selected(entry)
        self.destroy()
