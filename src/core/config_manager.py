"""Config and History manager with atomic file I/O operations."""

import json
import logging
import os
import sys
import tempfile
import threading
from typing import Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerencia leitura e persistência segura de configurações e histórico."""

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir:
            self.base_dir = base_dir
        elif getattr(sys, "frozen", False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Diretório raiz do projeto
            self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        self.config_path = os.path.join(self.base_dir, "config.json")
        self.history_path = os.path.join(self.base_dir, "history.json")
        self._lock = threading.Lock()

    def _atomic_write_json(self, file_path: str, data: Any) -> None:
        """Escreve dados em JSON de forma atômica para evitar corrupção."""
        dir_name = os.path.dirname(file_path)
        os.makedirs(dir_name, exist_ok=True)

        with self._lock:
            # Cria arquivo temporário no mesmo diretório para garantir que os.replace seja atômico no mesmo filesystem
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                temp_name = tf.name
                json.dump(data, tf, indent=2, ensure_ascii=False)
                tf.flush()
                os.fsync(tf.fileno())

            # Substituição atômica
            os.replace(temp_name, file_path)

    def load_api_key(self) -> str:
        """Carrega a API Key do YouTube salva."""
        if not os.path.exists(self.config_path):
            return ""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return str(data.get("api_key", "")).strip()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Falha ao ler config.json: %s", e)
            return ""

    def save_api_key(self, api_key: str) -> None:
        """Salva a API Key no arquivo de configuração de forma atômica."""
        cleaned_key = api_key.strip()
        self._atomic_write_json(self.config_path, {"api_key": cleaned_key})

    def load_history(self) -> list[str]:
        """Carrega o histórico de canais e buscas recentes."""
        if not os.path.exists(self.history_path):
            return []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(item) for item in data if item]
                return []
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Falha ao ler history.json: %s", e)
            return []

    def save_history_entry(self, entry: str, max_entries: int = 20) -> None:
        """Adiciona uma entrada ao histórico com deduplicação e limite máximo."""
        cleaned_entry = entry.strip()
        if not cleaned_entry:
            return

        history = self.load_history()
        # Remove duplicatas anteriores
        if cleaned_entry in history:
            history.remove(cleaned_entry)

        # Insere no topo
        history.insert(0, cleaned_entry)

        # Limita tamanho
        if len(history) > max_entries:
            history = history[:max_entries]

        try:
            self._atomic_write_json(self.history_path, history)
        except OSError as e:
            logger.error("Erro ao salvar history.json: %s", e)
