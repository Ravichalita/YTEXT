"""Test runner script for executing all unit tests."""

import sys
import os

# Força UTF-8 na saída do console do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona raiz do projeto ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tests.test_models import (
    test_video_item_csv_row,
    test_search_filter_defaults,
    test_download_formats,
)
from tests.test_config_manager import (
    test_save_and_load_api_key,
    test_history_deduplication_and_limit,
    test_corrupted_json_resilience,
)
from tests.test_youtube_service import test_extract_video_id
from tests.test_image_loader import test_thumbnail_loader_cache_and_eviction


def run_tests():
    tests = [
        ("test_video_item_csv_row", test_video_item_csv_row),
        ("test_search_filter_defaults", test_search_filter_defaults),
        ("test_download_formats", test_download_formats),
        ("test_save_and_load_api_key", test_save_and_load_api_key),
        ("test_history_deduplication_and_limit", test_history_deduplication_and_limit),
        ("test_corrupted_json_resilience", test_corrupted_json_resilience),
        ("test_extract_video_id", test_extract_video_id),
        ("test_thumbnail_loader_cache_and_eviction", test_thumbnail_loader_cache_and_eviction),
    ]

    passed = 0
    failed = 0
    print("=" * 60)
    print("EXECUTANDO TESTES UNITARIOS DO YTEXT (CORE SERVICES)")
    print("=" * 60)

    for name, func in tests:
        try:
            func()
            print(f"  [OK] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Total: {len(tests)} | Passaram: {passed} | Falharam: {failed}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
