"""Optimized video row component with asynchronous thumbnail loading and inline download controls."""

import webbrowser
from typing import Callable, Optional
import customtkinter as ctk
from PIL import Image

from src.core.download_service import DownloadService
from src.core.image_loader import ThumbnailLoader
from src.core.models import DownloadFormat, DownloadProgress, VideoItem
from src.ui.theme import COLORS


class VideoRow(ctk.CTkFrame):
    """Componente de linha individual para exibição de vídeo na lista de resultados."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        video: VideoItem,
        thumbnail_loader: ThumbnailLoader,
        download_service: DownloadService,
        on_selection_changed: Callable[[], None],
        on_toast_requested: Callable[[str, str], None],
        get_download_format: Callable[[], DownloadFormat],
        get_save_directory: Callable[[], Optional[str]],
    ) -> None:
        super().__init__(parent, fg_color=COLORS["bg_card_hover"], corner_radius=8)

        self.video = video
        self.thumbnail_loader = thumbnail_loader
        self.download_service = download_service
        self.on_selection_changed = on_selection_changed
        self.on_toast_requested = on_toast_requested
        self.get_download_format = get_download_format
        self.get_save_directory = get_save_directory

        self.checkbox_var = ctk.BooleanVar(value=video.is_selected)
        self.downloaded_path: Optional[str] = None
        self._ctk_image: Optional[ctk.CTkImage] = None

        self._build_ui()
        self._load_thumbnail()

    def _build_ui(self) -> None:
        """Monta a estrutura visual da linha."""
        self.pack(fill="x", pady=3, padx=8)

        # Efeito de hover suave no container
        self.bind("<Enter>", lambda e: self.configure(fg_color="#2d2d4a"))
        self.bind("<Leave>", lambda e: self.configure(fg_color=COLORS["bg_card_hover"]))

        # 1. Checkbox de seleção
        self.chk = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.checkbox_var,
            width=20,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._on_check_toggle,
        )
        self.chk.pack(side="left", padx=(12, 10), pady=10)

        # 2. Thumbnail (Placeholder inicial)
        self.thumb_label = ctk.CTkLabel(
            self,
            text="🎬",
            font=ctk.CTkFont(size=20),
            width=100,
            height=56,
            fg_color=COLORS["thumb_placeholder"],
            corner_radius=6,
        )
        self.thumb_label.pack(side="left", padx=(0, 10))

        # 3. Data de publicação
        ctk.CTkLabel(
            self,
            text=self.video.published_date or "—",
            width=90,
            anchor="w",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 10))

        # 4. Título clicável com link para o YouTube
        title_text = self.video.title
        display_title = title_text[:70] + "..." if len(title_text) > 70 else title_text

        self.title_label = ctk.CTkLabel(
            self,
            text=display_title,
            anchor="w",
            cursor="hand2",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=5)
        self.title_label.bind("<Button-1>", lambda e: webbrowser.open(self.video.url))
        self.title_label.bind("<Enter>", lambda e: self.title_label.configure(text_color=COLORS["text_accent"]))
        self.title_label.bind("<Leave>", lambda e: self.title_label.configure(text_color=COLORS["text_primary"]))

        # 5. Ações (Lado direito): Botão de Download e Botão de Abrir Link
        self.btn_download = ctk.CTkButton(
            self,
            text="⬇️ Baixar",
            width=90,
            height=30,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._start_single_download,
        )
        self.btn_download.pack(side="right", padx=10, pady=8)

        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=90,
            progress_color=COLORS["primary"],
            corner_radius=4,
        )

        btn_open_url = ctk.CTkButton(
            self,
            text="🌐",
            width=35,
            height=30,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=lambda: webbrowser.open(self.video.url),
        )
        btn_open_url.pack(side="right", padx=(0, 5), pady=8)

    def _on_check_toggle(self) -> None:
        """Atualiza estado de seleção do modelo."""
        self.video.is_selected = self.checkbox_var.get()
        self.on_selection_changed()

    def set_selected(self, selected: bool) -> None:
        """Define programaticamente o estado da seleção."""
        self.checkbox_var.set(selected)
        self.video.is_selected = selected

    def _load_thumbnail(self) -> None:
        """Solicita carregamento assíncrono da imagem de miniatura."""
        if not self.video.thumbnail_url:
            return

        def _on_img_ready(pil_img: Image.Image) -> None:
            # Garante que a criação do CTkImage ocorra na thread da UI
            def _apply() -> None:
                if not self.winfo_exists():
                    return
                self._ctk_image = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(100, 56),
                )
                self.thumb_label.configure(image=self._ctk_image, text="")

            self.after(0, _apply)

        self.thumbnail_loader.load_async(
            url=self.video.thumbnail_url,
            target_size=(100, 56),
            on_success=_on_img_ready,
        )

    def _start_single_download(self) -> None:
        """Inicia download individual do vídeo desta linha."""
        save_dir = self.get_save_directory()
        if not save_dir:
            return

        fmt = self.get_download_format()

        # Oculta botão e exibe barra de progresso
        self.btn_download.pack_forget()
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=10, pady=8)

        import threading

        def _thread_target() -> None:
            def _progress_cb(p: DownloadProgress) -> None:
                def _update() -> None:
                    if self.winfo_exists():
                        self.progress_bar.set(p.percentage)
                self.after(0, _update)

            try:
                out_path = self.download_service.download_single(
                    url=self.video.url,
                    output_dir=save_dir,
                    fmt=fmt,
                    on_progress=_progress_cb,
                )
                self.downloaded_path = out_path

                def _finish_success() -> None:
                    if not self.winfo_exists():
                        return
                    self.progress_bar.pack_forget()
                    self.btn_download.configure(
                        text="📂 Abrir",
                        fg_color=COLORS["success"],
                        hover_color=COLORS["secondary_hover"],
                        state="normal",
                        command=self._open_local_file,
                    )
                    self.btn_download.pack(side="right", padx=10, pady=8)
                    self.on_toast_requested("Download concluído!", "success")

                self.after(0, _finish_success)

            except Exception as e:
                def _finish_error() -> None:
                    if not self.winfo_exists():
                        return
                    self.progress_bar.pack_forget()
                    self.btn_download.configure(
                        text="Erro ↺",
                        fg_color=COLORS["danger"],
                        hover_color=COLORS["danger_hover"],
                        state="normal",
                        command=self._start_single_download,
                    )
                    self.btn_download.pack(side="right", padx=10, pady=8)
                    self.on_toast_requested(f"Erro no download: {e}", "error")

                self.after(0, _finish_error)

        threading.Thread(target=_thread_target, daemon=True).start()

    def _open_local_file(self) -> None:
        """Abre o arquivo baixado."""
        if self.downloaded_path:
            try:
                self.download_service.open_downloaded_file(self.downloaded_path)
            except Exception as e:
                self.on_toast_requested(f"Não foi possível abrir o arquivo: {e}", "error")
