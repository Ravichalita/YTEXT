"""Download service wrapping yt-dlp with throttling, cancellation, and format selection."""

import logging
import os
import platform
import subprocess
import threading
import time
from typing import Any, Callable, Optional

try:
    import yt_dlp
except ImportError:
    yt_dlp = None  # type: ignore[assignment]

from src.core.models import DownloadFormat, DownloadProgress

logger = logging.getLogger(__name__)


class DownloadCancelledError(Exception):
    """Exceção levantada quando um download é cancelado pelo usuário."""


class DownloadService:
    """Gerenciador de downloads resiliente com yt-dlp."""

    def __init__(self) -> None:
        self._active_cancel_event: Optional[threading.Event] = None
        self._is_busy = False

    @property
    def is_busy(self) -> bool:
        """Indica se há um processo de download ativo."""
        return self._is_busy

    def create_cancel_token(self) -> threading.Event:
        """Cria e retorna um token de cancelamento."""
        self._active_cancel_event = threading.Event()
        return self._active_cancel_event

    def cancel_active_downloads(self) -> None:
        """Sinaliza o cancelamento dos downloads em andamento."""
        if self._active_cancel_event:
            self._active_cancel_event.set()

    def download_single(
        self,
        url: str,
        output_dir: str,
        fmt: DownloadFormat = DownloadFormat.VIDEO_BEST_720P,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
        cancel_token: Optional[threading.Event] = None,
    ) -> str:
        """Realiza o download de um vídeo individual de forma síncrona (destinado a rodar em thread)."""
        self._is_busy = True
        try:
            return self._execute_download(url, output_dir, fmt, on_progress, cancel_token)
        finally:
            self._is_busy = False

    def download_batch(
        self,
        items: list[tuple[str, str]],  # [(title, url), ...]
        output_dir: str,
        fmt: DownloadFormat = DownloadFormat.VIDEO_BEST_720P,
        on_item_start: Optional[Callable[[int, int, str, str], None]] = None,
        on_item_progress: Optional[Callable[[DownloadProgress], None]] = None,
        on_item_complete: Optional[Callable[[int, str, bool, str], None]] = None,
        cancel_token: Optional[threading.Event] = None,
    ) -> tuple[int, int]:
        """Executa downloads em lote sequenciais com verificação de cancelamento."""
        self._is_busy = True
        total = len(items)
        success_count = 0

        try:
            for idx, (title, url) in enumerate(items):
                if cancel_token and cancel_token.is_set():
                    logger.info("Download em lote interrompido pelo usuário.")
                    break

                if on_item_start:
                    on_item_start(idx, total, title, url)

                filepath = ""
                try:
                    filepath = self._execute_download(
                        url=url,
                        output_dir=output_dir,
                        fmt=fmt,
                        on_progress=on_item_progress,
                        cancel_token=cancel_token,
                    )
                    success_count += 1
                except DownloadCancelledError:
                    logger.info("Download de %s cancelado.", title)
                    if on_item_complete:
                        on_item_complete(idx, title, False, "Cancelado")
                    break
                except Exception as e:
                    logger.error("Erro ao baixar %s: %s", title, e)
                    if on_item_complete:
                        on_item_complete(idx, title, False, str(e))
                else:
                    if on_item_complete:
                        on_item_complete(idx, title, True, filepath)

            return success_count, total
        finally:
            self._is_busy = False

    def _execute_download(
        self,
        url: str,
        output_dir: str,
        fmt: DownloadFormat,
        on_progress: Optional[Callable[[DownloadProgress], None]],
        cancel_token: Optional[threading.Event],
    ) -> str:
        """Executa a operação de download via yt_dlp."""
        if yt_dlp is None:
            raise RuntimeError(
                "A biblioteca 'yt-dlp' não está instalada.\n"
                "Execute: pip install -r requirements.txt"
            )

        last_update_time = 0.0
        title_holder = [""]

        def _hook(d: dict[str, Any]) -> None:
            nonlocal last_update_time

            if cancel_token and cancel_token.is_set():
                raise DownloadCancelledError("Download cancelado pelo usuário.")

            status = d.get("status")
            if status == "downloading":
                now = time.monotonic()
                # Throttle de atualizações para 80ms para poupar a UI
                if now - last_update_time < 0.08:
                    return
                last_update_time = now

                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0

                percentage = (downloaded / total) if total > 0 else 0.0
                percentage = min(1.0, max(0.0, percentage))

                if on_progress:
                    prog = DownloadProgress(
                        url=url,
                        title=title_holder[0] or d.get("filename", ""),
                        percentage=percentage,
                        status="downloading",
                    )
                    on_progress(prog)

            elif status == "finished":
                if on_progress:
                    prog = DownloadProgress(
                        url=url,
                        title=title_holder[0] or d.get("filename", ""),
                        percentage=1.0,
                        status="finished",
                    )
                    on_progress(prog)

        ydl_opts = self._build_ydl_opts(output_dir, fmt, _hook)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrai info antes para obter o título limpo e nome final do arquivo
            info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("Não foi possível obter metadados do vídeo.")

            title_holder[0] = info.get("title", "Vídeo")
            final_filename = ydl.prepare_filename(info)

            # Executa o download
            ydl.download([url])

            # Ajuste de extensão se houve conversão para MP3
            if fmt == DownloadFormat.AUDIO_ONLY_MP3:
                base, _ = os.path.splitext(final_filename)
                final_filename = f"{base}.mp3"

            return final_filename

    def _build_ydl_opts(
        self,
        output_dir: str,
        fmt: DownloadFormat,
        progress_hook: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        """Constrói as opções do yt-dlp conforme formato selecionado."""
        opts: dict[str, Any] = {
            "paths": {"home": output_dir},
            "outtmpl": "%(title)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }

        if fmt == DownloadFormat.AUDIO_ONLY_MP3:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif fmt == DownloadFormat.VIDEO_BEST_1080P:
            opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        else:
            # 720p Padrão
            opts["format"] = "best[ext=mp4][height<=720]/best[height<=720]/best"

        return opts

    @staticmethod
    def open_downloaded_file(filepath: str) -> None:
        """Abre o arquivo baixado no player padrão do sistema operacional."""
        if not filepath or not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo '{filepath}' não existe.")

        current_os = platform.system()
        if current_os == "Windows":
            os.startfile(filepath)
        elif current_os == "Darwin":
            subprocess.run(["open", filepath], check=True)
        else:
            subprocess.run(["xdg-open", filepath], check=True)
