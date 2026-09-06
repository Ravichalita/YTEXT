"""Unit tests for domain models."""

from src.core.models import VideoItem, DownloadFormat, SearchFilter


def test_video_item_csv_row():
    item = VideoItem(
        video_id="abc12345678",
        title="Vídeo de Teste com Acentuação",
        url="https://www.youtube.com/watch?v=abc12345678",
        published_date="2026-09-06",
    )
    row = item.to_csv_row()
    assert row == ["2026-09-06", "Vídeo de Teste com Acentuação", "https://www.youtube.com/watch?v=abc12345678"]


def test_search_filter_defaults():
    sf = SearchFilter()
    assert sf.mode == "quantity"
    assert sf.quantity == 10
    assert sf.start_date is None


def test_download_formats():
    assert DownloadFormat.VIDEO_BEST_720P.value == "720p (MP4)"
    assert DownloadFormat.AUDIO_ONLY_MP3.value == "Áudio (MP3)"
