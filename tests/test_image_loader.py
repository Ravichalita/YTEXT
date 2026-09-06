"""Unit tests for ThumbnailLoader."""

from PIL import Image
from src.core.image_loader import ThumbnailLoader


def test_thumbnail_loader_cache_and_eviction():
    loader = ThumbnailLoader(max_workers=2, max_cache_size=3)

    img1 = Image.new("RGBA", (100, 56), color="red")
    img2 = Image.new("RGBA", (100, 56), color="green")
    img3 = Image.new("RGBA", (100, 56), color="blue")
    img4 = Image.new("RGBA", (100, 56), color="yellow")

    loader._add_to_cache("url1", img1)
    loader._add_to_cache("url2", img2)
    loader._add_to_cache("url3", img3)

    # Acessa url1 para torná-lo recentemente usado
    assert loader.get_cached_image("url1") is not None

    # Adicionar 4º elemento deve expulsar o menos recentemente usado (url2)
    loader._add_to_cache("url4", img4)

    assert loader.get_cached_image("url4") is not None
    assert loader.get_cached_image("url1") is not None
    assert loader.get_cached_image("url3") is not None
    assert loader.get_cached_image("url2") is None  # Expulso pelo LRU

    loader.shutdown()
