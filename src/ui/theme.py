"""Visual design tokens, theme palette, and styling constants."""

import customtkinter as ctk

# Cores Modernas
COLORS = {
    "primary": "#6366f1",         # Indigo vibrante
    "primary_hover": "#4f46e5",   # Indigo escuro
    "primary_gradient": "#8b5cf6", # Roxo para gradiente
    "secondary": "#10b981",       # Verde emerald
    "secondary_hover": "#059669",
    "accent": "#f59e0b",          # Amber destaque
    "bg_main": "#0f0f23",         # Fundo principal
    "bg_card": "#1a1a2e",         # Cards
    "bg_card_hover": "#252542",   # Cards hover
    "bg_header": "#16213e",       # Header
    "bg_input": "#1e1e3f",        # Inputs
    "text_primary": "#f8fafc",    # Texto principal
    "text_muted": "#94a3b8",      # Texto secundário
    "text_accent": "#a5b4fc",     # Texto accent
    "danger": "#ef4444",          # Vermelho erro
    "danger_hover": "#dc2626",
    "success": "#22c55e",         # Verde sucesso
    "warning": "#f59e0b",         # Amarelo aviso
    "border": "#334155",          # Bordas
    "separator": "#1e293b",       # Separadores
    "thumb_placeholder": "#2b2b40",
}


def apply_global_theme() -> None:
    """Aplica o modo de aparência padrão do CustomTkinter."""
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
