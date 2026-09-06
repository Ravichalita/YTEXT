"""YouTube Data API v3 service with caching, quota optimization, and resilient channel resolution."""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Callable, Optional

try:
    from googleapiclient.discovery import Resource, build
    from googleapiclient.errors import HttpError
except ImportError:
    Resource = Any  # type: ignore[misc, assignment]
    build = None  # type: ignore[assignment]
    HttpError = Exception  # type: ignore[misc, assignment]

from src.core.models import SearchFilter, VideoItem

logger = logging.getLogger(__name__)


class YouTubeService:
    """Serviço de comunicação com a YouTube Data API v3."""

    def __init__(self) -> None:
        self._cached_api_key: str = ""
        self._client: Optional[Any] = None

    def get_client(self, api_key: str) -> Any:
        """Obtém ou reutiliza a instância do cliente da API."""
        if build is None:
            raise RuntimeError(
                "A biblioteca 'google-api-python-client' não está instalada.\n"
                "Execute: pip install -r requirements.txt"
            )

        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValueError("API Key não fornecida.")

        if self._client is None or self._cached_api_key != cleaned_key:
            self._client = build("youtube", "v3", developerKey=cleaned_key, cache_discovery=False)
            self._cached_api_key = cleaned_key

        return self._client

    @staticmethod
    def extract_video_id(input_str: str) -> Optional[str]:
        """Extrai o ID de 11 caracteres de URLs de vídeo ou shorts do YouTube."""
        patterns = [
            r"(?:v=|\/embed\/|\/shorts\/|\/v\/)([0-9A-Za-z_-]{11})(?:[?&]|$)",
            r"youtu\.be\/([0-9A-Za-z_-]{11})(?:[?&]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, input_str)
            if match:
                return match.group(1)

        # Verifica se o próprio input já é um ID de vídeo válido
        if re.fullmatch(r"[0-9A-Za-z_-]{11}", input_str.strip()):
            return input_str.strip()

        return None

    def fetch_single_video(self, api_key: str, video_id: str) -> Optional[VideoItem]:
        """Busca os metadados de um único vídeo pelo seu ID."""
        youtube = self.get_client(api_key)
        try:
            resp = youtube.videos().list(part="snippet", id=video_id).execute()
            items = resp.get("items", [])
            if not items:
                return None

            item = items[0]
            snippet = item["snippet"]
            title = snippet.get("title", "Sem título")
            pub_at = snippet.get("publishedAt", "")
            
            try:
                p_date = datetime.strptime(pub_at, "%Y-%m-%dT%H:%M:%SZ")
                date_str = p_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                date_str = ""

            thumbs = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("medium", {}).get("url")
                or thumbs.get("default", {}).get("url")
                or ""
            )

            return VideoItem(
                video_id=video_id,
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_date=date_str,
                thumbnail_url=thumb_url,
            )
        except HttpError as e:
            logger.error("Erro HTTP ao buscar vídeo único: %s", e)
            raise self._format_http_error(e) from e

    def resolve_uploads_playlist_id(self, api_key: str, channel_input: str) -> str:
        """Resolve o uploads playlist ID de um canal a partir de URLs, @handles ou IDs."""
        youtube = self.get_client(api_key)
        cleaned = channel_input.strip()

        # 1. URL com /channel/UC...
        if "/channel/" in cleaned:
            cid = cleaned.split("/channel/")[1].split("/")[0].split("?")[0]
            return self._get_uploads_from_channel_id(youtube, cid)

        # 2. URL com /@handle ou @handle direto
        handle = None
        if "/@" in cleaned:
            handle = "@" + cleaned.split("/@")[1].split("/")[0].split("?")[0]
        elif cleaned.startswith("@"):
            handle = cleaned.split("/")[0].split("?")[0]

        if handle:
            resp = youtube.channels().list(part="contentDetails", forHandle=handle).execute()
            items = resp.get("items", [])
            if items:
                return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 3. ID de canal direto (começa com UC)
        if cleaned.startswith("UC") and len(cleaned) >= 20:
            return self._get_uploads_from_channel_id(youtube, cleaned)

        # 4. Busca por id ou forUsername
        resp = youtube.channels().list(part="contentDetails", id=cleaned).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 5. Fallback por nome/custom URL (youtube.com/c/...)
        custom_name = cleaned
        if "/c/" in cleaned:
            custom_name = cleaned.split("/c/")[1].split("/")[0].split("?")[0]
        elif "/user/" in cleaned:
            custom_name = cleaned.split("/user/")[1].split("/")[0].split("?")[0]

        resp_user = youtube.channels().list(part="contentDetails", forUsername=custom_name).execute()
        items_user = resp_user.get("items", [])
        if items_user:
            return items_user[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 6. Fallback final: Search por canal
        search_resp = youtube.search().list(part="snippet", q=cleaned, type="channel", maxResults=1).execute()
        search_items = search_resp.get("items", [])
        if search_items:
            channel_id = search_items[0]["snippet"]["channelId"]
            return self._get_uploads_from_channel_id(youtube, channel_id)

        raise ValueError(f"Canal '{channel_input}' não encontrado no YouTube.")

    def _get_uploads_from_channel_id(self, youtube: Any, channel_id: str) -> str:
        """Obtém o ID da playlist de uploads a partir do ID do canal."""
        # Otimização conhecida: canais UC... têm playlist de uploads UU...
        if channel_id.startswith("UC"):
            return "UU" + channel_id[2:]

        resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        items = resp.get("items", [])
        if not items:
            raise ValueError(f"Canal com ID '{channel_id}' não encontrado.")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def fetch_channel_videos(
        self,
        api_key: str,
        playlist_id: str,
        search_filter: SearchFilter,
        on_video_found: Optional[Callable[[VideoItem], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> list[VideoItem]:
        """Extrai vídeos de uma playlist com paginação inteligente e economia de cota."""
        youtube = self.get_client(api_key)
        videos: list[VideoItem] = []
        next_page_token: Optional[str] = None
        count = 0

        target_qty = search_filter.quantity if search_filter.mode == "quantity" else 0
        start_date = search_filter.start_date
        end_date = search_filter.end_date

        while True:
            if cancel_check and cancel_check():
                break

            # Economia de cota: solicita apenas a quantidade restante se no modo quantidade
            max_results = 50
            if search_filter.mode == "quantity":
                remaining = target_qty - count
                if remaining <= 0:
                    break
                max_results = min(50, max(1, remaining))

            try:
                req = youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=max_results,
                    pageToken=next_page_token,
                )
                resp = req.execute()
            except HttpError as e:
                logger.error("Erro na paginação de playlist: %s", e)
                raise self._format_http_error(e) from e

            items = resp.get("items", [])
            if not items:
                break

            stop_pagination = False
            for item in items:
                if cancel_check and cancel_check():
                    stop_pagination = True
                    break

                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                vid = resource_id.get("videoId")
                if not vid:
                    continue

                title = snippet.get("title", "Sem título")
                pub_at = snippet.get("publishedAt", "")
                
                try:
                    p_date = datetime.strptime(pub_at, "%Y-%m-%dT%H:%M:%SZ")
                    date_str = p_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    p_date = datetime.min
                    date_str = ""

                # Aplica filtros
                if search_filter.mode == "quantity":
                    if count >= target_qty:
                        stop_pagination = True
                        break
                elif search_filter.mode == "date":
                    if end_date and p_date > end_date:
                        continue  # Vídeo mais recente que a data final solicitada
                    if start_date and p_date < start_date:
                        stop_pagination = True  # Já ultrapassou a data inicial (ordem decrescente)
                        break

                count += 1
                thumbs = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbs.get("medium", {}).get("url")
                    or thumbs.get("default", {}).get("url")
                    or ""
                )

                video_item = VideoItem(
                    video_id=vid,
                    title=title,
                    url=f"https://www.youtube.com/watch?v={vid}",
                    published_date=date_str,
                    thumbnail_url=thumb_url,
                )

                videos.append(video_item)
                if on_video_found:
                    on_video_found(video_item)

            if stop_pagination:
                break

            next_page_token = resp.get("nextPageToken")
            if not next_page_token:
                break

        return videos

    @staticmethod
    def _format_http_error(e: Any) -> Exception:
        """Converte erros da API do Google em mensagens amigáveis em português."""
        if not hasattr(e, "resp"):
            return RuntimeError(str(e))

        status_code = e.resp.status
        content = e.content.decode("utf-8", errors="ignore")

        if status_code == 403:
            if "quotaExceeded" in content:
                return RuntimeError("Cota diária da API do YouTube atingida (10.000 unidades). Tente novamente amanhã.")
            return RuntimeError("Acesso negado (403). Verifique se a YouTube Data API v3 está ativada no console do Google Cloud.")
        if status_code == 400:
            if "keyInvalid" in content:
                return RuntimeError("API Key inválida. Verifique sua chave no botão de configuração.")
            return RuntimeError(f"Requisição inválida (400): {content}")
        if status_code == 404:
            return RuntimeError("Canal, playlist ou vídeo não encontrado (404).")

        return RuntimeError(f"Erro na API do YouTube ({status_code}): {getattr(e, 'reason', e)}")
