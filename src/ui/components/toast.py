"""Auto-dismissing toast notification widget."""

import customtkinter as ctk
from src.ui.theme import COLORS


class ToastNotification(ctk.CTkFrame):
    """Notificação toast que aparece suavemente e desaparece após um tempo configurável."""

    def __init__(self, parent: ctk.CTkBaseClass, message: str, toast_type: str = "info", duration_ms: int = 3000) -> None:
        super().__init__(parent, corner_radius=10)

        icons_map = {
            "success": (COLORS["success"], "✓"),
            "error": (COLORS["danger"], "✕"),
            "warning": (COLORS["warning"], "⚠"),
            "info": (COLORS["primary"], "ℹ"),
        }

        color, icon = icons_map.get(toast_type, icons_map["info"])
        self.configure(fg_color=color)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(padx=16, pady=10)

        ctk.CTkLabel(
            content,
            text=f"{icon}  {message}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
        ).pack()

        self.after(duration_ms, self._safe_destroy)

    def _safe_destroy(self) -> None:
        """Destroi o widget com segurança verificando se ele ainda existe."""
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass
