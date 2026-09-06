"""Domain models and data structures for YouTube Extractor Pro."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DownloadFormat(str, Enum):
    """Opções de formato de download suportados."""
    VIDEO_BEST_720P = "720p (MP4)"
    VIDEO_BEST_1080P = "1080p (MP4/MKV)"
    AUDIO_ONLY_MP3 = "Áudio (MP3)"


@dataclass(slots=True)
class VideoItem:
    """Representa um item de vídeo extraído."""
    video_id: str
    title: str
    url: str
    published_date: str
    thumbnail_url: str = ""
    is_selected: bool = False

    def to_csv_row(self) -> list[str]:
        """Retorna representação em formato de linha para CSV."""
        return [self.published_date, self.title, self.url]


@dataclass(slots=True)
class SearchFilter:
    """Filtros para busca de vídeos."""
    mode: str = "quantity"  # "quantity" ou "date"
    quantity: int = 10
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass(slots=True)
class DownloadProgress:
    """Representa o progresso de um download ativo."""
    url: str
    title: str
    percentage: float = 0.0
    status: str = "queued"  # "queued", "downloading", "finished", "error", "cancelled"
    error_message: str = ""
    output_filepath: str = ""
