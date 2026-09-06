"""Optimized thumbnail loader with bounded thread pool and LRU in-memory cache."""

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
import io
import logging
import threading
import urllib.request
from typing import Callable, Optional
from PIL import Image

logger = logging.getLogger(__name__)


class ThumbnailLoader:
    """Carrega miniaturas de vídeos com ThreadPoolExecutor e Cache LRU."""

    def __init__(self, max_workers: int = 4, max_cache_size: int = 200) -> None:
        self.max_workers = max_workers
        self.max_cache_size = max_cache_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ThumbLoader")
        self._cache: OrderedDict[str, Image.Image] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._active_futures: list[Future] = []

    def get_cached_image(self, url: str) -> Optional[Image.Image]:
        """Retorna imagem do cache em memória se disponível."""
        with self._cache_lock:
            if url in self._cache:
                self._cache.move_to_end(url)
                return self._cache[url]
        return None

    def _add_to_cache(self, url: str, img: Image.Image) -> None:
        """Adiciona imagem ao cache LRU."""
        with self._cache_lock:
            if url in self._cache:
                self._cache.move_to_end(url)
            else:
                if len(self._cache) >= self.max_cache_size:
                    self._cache.popitem(last=False)
                self._cache[url] = img

    def load_async(
        self,
        url: str,
        target_size: tuple[int, int],
        on_success: Callable[[Image.Image], None],
        on_error: Optional[Callable[[], None]] = None,
    ) -> None:
        """Dispara carregamento assíncrono de miniatura sem travar a interface."""
        if not url:
            if on_error:
                on_error()
            return

        # Verifica cache primeiro (O(1))
        cached = self.get_cached_image(url)
        if cached is not None:
            on_success(cached)
            return

        def _worker() -> None:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=7) as response:
                    raw_data = response.read()

                # Processamento PIL na worker thread para poupar a UI thread
                with Image.open(io.BytesIO(raw_data)) as orig_img:
                    # Copia e converte para RGB/RGBA se necessário
                    img = orig_img.convert("RGBA")
                    resized_img = img.resize(target_size, Image.Resampling.LANCZOS)

                self._add_to_cache(url, resized_img)
                on_success(resized_img)

            except Exception as exc:
                logger.debug("Falha ao baixar thumbnail %s: %s", url, exc)
                if on_error:
                    on_error()

        future = self._executor.submit(_worker)
        self._active_futures.append(future)
        # Limpa referências a futures já concluídos
        self._active_futures = [f for f in self._active_futures if not f.done()]

    def cancel_pending(self) -> None:
        """Cancela tarefas pendentes na fila."""
        for f in self._active_futures:
            if not f.running():
                f.cancel()
        self._active_futures.clear()

    def shutdown(self) -> None:
        """Encerra o executor de threads."""
        self.cancel_pending()
        self._executor.shutdown(wait=False)
