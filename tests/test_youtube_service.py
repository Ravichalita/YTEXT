"""Unit tests for YouTubeService URL parsing."""

from src.core.youtube_service import YouTubeService


def test_extract_video_id():
    service = YouTubeService()

    # URL padrão com watch?v=
    assert service.extract_video_id("https://www.youtube.com/watch?v=mCX7c1iJN8o") == "mCX7c1iJN8o"
    assert service.extract_video_id("https://youtube.com/watch?v=mCX7c1iJN8o&t=10s") == "mCX7c1iJN8o"

    # URL encurtada youtu.be
    assert service.extract_video_id("https://youtu.be/mCX7c1iJN8o") == "mCX7c1iJN8o"
    assert service.extract_video_id("https://youtu.be/mCX7c1iJN8o?t=5") == "mCX7c1iJN8o"

    # Shorts
    assert service.extract_video_id("https://www.youtube.com/shorts/mCX7c1iJN8o") == "mCX7c1iJN8o"

    # Embed
    assert service.extract_video_id("https://www.youtube.com/embed/mCX7c1iJN8o") == "mCX7c1iJN8o"

    # ID direto
    assert service.extract_video_id("mCX7c1iJN8o") == "mCX7c1iJN8o"

    # Não é ID de vídeo
    assert service.extract_video_id("@lucrodigital") is None
    assert service.extract_video_id("https://www.youtube.com/@MrBeast") is None
