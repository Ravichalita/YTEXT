"""Unit tests for ConfigManager."""

import os
import tempfile
from src.core.config_manager import ConfigManager


def test_save_and_load_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = ConfigManager(base_dir=tmpdir)
        assert cm.load_api_key() == ""

        cm.save_api_key("AIzaSyTestKey123")
        assert cm.load_api_key() == "AIzaSyTestKey123"


def test_history_deduplication_and_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = ConfigManager(base_dir=tmpdir)
        assert cm.load_history() == []

        cm.save_history_entry("@channel1", max_entries=3)
        cm.save_history_entry("@channel2", max_entries=3)
        cm.save_history_entry("@channel3", max_entries=3)

        assert cm.load_history() == ["@channel3", "@channel2", "@channel1"]

        # Inserir duplicado move para o topo
        cm.save_history_entry("@channel1", max_entries=3)
        assert cm.load_history() == ["@channel1", "@channel3", "@channel2"]

        # Inserir novo elemento descarta o mais antigo conforme limite
        cm.save_history_entry("@channel4", max_entries=3)
        assert cm.load_history() == ["@channel4", "@channel1", "@channel3"]


def test_corrupted_json_resilience():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = ConfigManager(base_dir=tmpdir)
        # Escreve arquivo JSON corrompido
        with open(cm.config_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true,")

        # Não deve lançar exceção fatal, deve retornar string vazia
        assert cm.load_api_key() == ""
