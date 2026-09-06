"""YouTube Extractor Pro - Application Entry Point.

Refatorado com arquitetura modular, princípios SOLID, concorrência otimizada
e proteção contra corrupção de dados e vazamento de chaves de API.
"""

import logging
import os
import sys

# Garante que o diretório raiz do projeto esteja no sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configuração de Logging global
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Exportações para retrocompatibilidade
from src.ui.theme import COLORS
from src.ui.components.toast import ToastNotification
from src.ui.dialogs.calendar_dialog import CalendarModal
from src.ui.dialogs.api_dialog import APIConfigDialog
from src.ui.main_window import MainWindow, MainWindow as YoutubeExtractorApp


def resource_path(relative_path: str) -> str:
    """Retorna caminho absoluto para recursos (compatível com PyInstaller e Dev)."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = BASE_DIR
    return os.path.join(base_path, relative_path)


def main() -> None:
    """Inicia a aplicação YouTube Extractor Pro."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()