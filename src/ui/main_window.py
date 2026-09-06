"""Main application window for YouTube Extractor Pro."""

import csv
from datetime import datetime
import logging
import os
import sys
import threading
from tkinter import filedialog, messagebox
from typing import Optional
import customtkinter as ctk

from src.core.config_manager import ConfigManager
from src.core.download_service import DownloadService
from src.core.image_loader import ThumbnailLoader
from src.core.models import DownloadFormat, DownloadProgress, SearchFilter, VideoItem
from src.core.youtube_service import YouTubeService
from src.ui.components.toast import ToastNotification
from src.ui.components.video_row import VideoRow
from src.ui.dialogs.api_dialog import APIConfigDialog
from src.ui.dialogs.calendar_dialog import CalendarModal
from src.ui.dialogs.history_dialog import HistoryDialog
from src.ui.theme import COLORS, apply_global_theme

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Janela principal da aplicação YouTube Extractor Pro."""

    def __init__(self) -> None:
        super().__init__()

        apply_global_theme()

        self.title("YouTube Extractor Pro")
        self.geometry("1180x920")
        self.minsize(980, 720)
        self.configure(fg_color=COLORS["bg_main"])

        # Inicializa serviços do Core
        self.config_manager = ConfigManager()
        self.youtube_service = YouTubeService()
        self.thumbnail_loader = ThumbnailLoader(max_workers=4)
        self.download_service = DownloadService()

        # Estado da aplicação
        self.videos: list[VideoItem] = []
        self.video_rows: list[VideoRow] = []
        self.filter_mode = ctk.StringVar(value="quantity")
        self.select_all_var = ctk.BooleanVar(value=False)
        self.format_var = ctk.StringVar(value=DownloadFormat.VIDEO_BEST_720P.value)
        self.is_searching = False
        self.is_batch_downloading = False

        # Ícone do aplicativo
        self._setup_icon()

        # Configuração do Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Lista de vídeos expande

        # Monta interface
        self._create_header()
        self._create_config_bar()
        self._create_filter_bar()
        self._create_list_header()
        self._create_scrollable_list()
        self._create_footer()

        # Finalização e limpeza ao fechar
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_icon(self) -> None:
        """Carrega ícone da janela se disponível."""
        icon_path = os.path.join(self.config_manager.base_dir, "YTBEX.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                logger.debug("Não foi possível aplicar o ícone: %s", e)

    def show_toast(self, message: str, toast_type: str = "info") -> None:
        """Exibe notificação toast no canto superior direito."""
        try:
            toast = ToastNotification(self, message, toast_type=toast_type)
            toast.place(relx=0.98, rely=0.02, anchor="ne")
        except Exception:
            pass

    # =========================================================================
    # CONSTRUÇÃO DOS COMPONENTES VISUAIS
    # =========================================================================

    def _create_header(self) -> None:
        """1. Cabeçalho principal."""
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_header"], corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")

        content = ctk.CTkFrame(header_frame, fg_color="transparent")
        content.pack(fill="x", padx=25, pady=18)

        title_box = ctk.CTkFrame(content, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="YouTube Extractor Pro",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Extraia metadados e baixe vídeos ou áudios de canais com alta performance",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

    def _create_config_bar(self) -> None:
        """2. Barra de entrada do canal e atalhos."""
        config_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        config_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(18, 8))
        config_frame.grid_columnconfigure(1, weight=1)

        # Botão API Key
        ctk.CTkButton(
            config_frame,
            text="🔑 YouTube API",
            command=self._open_api_dialog,
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            width=140,
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, padx=(15, 12), pady=12, sticky="w")

        # Entrada do Canal / URL
        input_container = ctk.CTkFrame(config_frame, fg_color="transparent")
        input_container.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=12)
        input_container.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            input_container,
            text="📺 Canal / Vídeo:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.channel_entry = ctk.CTkEntry(
            input_container,
            placeholder_text="Ex: @MrBeast, URL do canal, playlist ou vídeo individual",
            height=40,
            corner_radius=8,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        )
        self.channel_entry.grid(row=0, column=1, sticky="ew")
        self.channel_entry.bind("<Return>", lambda e: self.start_extraction())

        # Botão Histórico
        ctk.CTkButton(
            config_frame,
            text="📋 Histórico",
            width=100,
            height=40,
            command=self._open_history_dialog,
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=2, padx=(0, 15), pady=12)

    def _create_filter_bar(self) -> None:
        """3. Barra de filtros de quantidade/data e seletor de formato."""
        filter_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        filter_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=6)

        content = ctk.CTkFrame(filter_frame, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)

        # Grupo 1: Modo Quantidade
        qty_box = ctk.CTkFrame(content, fg_color="transparent")
        qty_box.pack(side="left")

        self.rb_qty = ctk.CTkRadioButton(
            qty_box,
            text="Últimos",
            variable=self.filter_mode,
            value="quantity",
            command=self._toggle_filter_inputs,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )
        self.rb_qty.pack(side="left", padx=(0, 8))

        self.qty_entry = ctk.CTkEntry(
            qty_box,
            width=65,
            height=35,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            justify="center",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.qty_entry.insert(0, "10")
        self.qty_entry.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(
            qty_box,
            text="vídeos",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # Separador vertical
        ctk.CTkFrame(content, width=2, height=35, fg_color=COLORS["separator"]).pack(side="left", padx=20)

        # Grupo 2: Modo Período de Data
        date_box = ctk.CTkFrame(content, fg_color="transparent")
        date_box.pack(side="left")

        self.rb_date = ctk.CTkRadioButton(
            date_box,
            text="Período:",
            variable=self.filter_mode,
            value="date",
            command=self._toggle_filter_inputs,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )
        self.rb_date.pack(side="left", padx=(0, 8))

        self.date_start_entry = ctk.CTkEntry(
            date_box,
            width=100,
            height=35,
            placeholder_text="AAAA-MM-DD",
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        )
        self.date_start_entry.pack(side="left", padx=(0, 3))

        self.btn_cal_start = ctk.CTkButton(
            date_box,
            text="📅",
            width=35,
            height=35,
            command=lambda: self._open_calendar(self.date_start_entry),
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            corner_radius=6,
        )
        self.btn_cal_start.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            date_box,
            text="até",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=5)

        self.date_end_entry = ctk.CTkEntry(
            date_box,
            width=100,
            height=35,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        )
        self.date_end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_end_entry.pack(side="left", padx=(0, 3))

        self.btn_cal_end = ctk.CTkButton(
            date_box,
            text="📅",
            width=35,
            height=35,
            command=lambda: self._open_calendar(self.date_end_entry),
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            corner_radius=6,
        )
        self.btn_cal_end.pack(side="left")

        # Separador vertical
        ctk.CTkFrame(content, width=2, height=35, fg_color=COLORS["separator"]).pack(side="left", padx=20)

        # Grupo 3: Seletor de Formato
        fmt_box = ctk.CTkFrame(content, fg_color="transparent")
        fmt_box.pack(side="left")

        ctk.CTkLabel(
            fmt_box,
            text="Formato:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(0, 8))

        self.fmt_menu = ctk.CTkOptionMenu(
            fmt_box,
            variable=self.format_var,
            values=[
                DownloadFormat.VIDEO_BEST_720P.value,
                DownloadFormat.VIDEO_BEST_1080P.value,
                DownloadFormat.AUDIO_ONLY_MP3.value,
            ],
            width=140,
            height=35,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            dropdown_fg_color=COLORS["bg_card"],
        )
        self.fmt_menu.pack(side="left")

        # Botão de Busca
        self.btn_extract = ctk.CTkButton(
            content,
            text="🔍 BUSCAR VÍDEOS",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=170,
            height=40,
            command=self.start_extraction,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8,
        )
        self.btn_extract.pack(side="right")

        self._toggle_filter_inputs()

    def _create_list_header(self) -> None:
        """4. Cabeçalho da listagem."""
        header_list = ctk.CTkFrame(self, fg_color=COLORS["primary"], corner_radius=8)
        header_list.grid(row=3, column=0, sticky="ew", padx=20, pady=(12, 0))

        content = ctk.CTkFrame(header_list, fg_color="transparent")
        content.pack(fill="x", padx=5, pady=8)

        self.select_all_cb = ctk.CTkCheckBox(
            content,
            text="",
            variable=self.select_all_var,
            command=self._toggle_select_all,
            width=20,
            fg_color="white",
            checkmark_color=COLORS["primary"],
            hover_color="#e0e0ff",
        )
        self.select_all_cb.pack(side="left", padx=(10, 15))

        ctk.CTkLabel(
            content,
            text="DATA",
            width=100,
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            content,
            text="TÍTULO (Clique para assistir)",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
        ).pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkLabel(
            content,
            text="AÇÕES",
            width=140,
            anchor="e",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
        ).pack(side="right", padx=15)

    def _create_scrollable_list(self) -> None:
        """5. Área com rolagem para a listagem dos vídeos."""
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"],
        )
        self.scroll_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=0)

        self.placeholder_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Busque um canal ou vídeo para listar os itens aqui",
            font=ctk.CTkFont(size=15),
            text_color=COLORS["text_muted"],
        )
        self.placeholder_label.pack(pady=100)

    def _create_footer(self) -> None:
        """6. Rodapé com ações em lote e exportação."""
        footer_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        footer_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=15)

        content = ctk.CTkFrame(footer_frame, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=10)

        # Grupo Esquerda: Botões de Cópia
        copy_box = ctk.CTkFrame(content, fg_color="transparent")
        copy_box.pack(side="left")

        ctk.CTkButton(
            copy_box,
            text="📋 Copiar Tudo",
            command=self.copy_all_urls,
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            width=110,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            copy_box,
            text="📋 Copiar Selecionados",
            command=self.copy_selected_urls,
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            width=140,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 8))

        # Grupo Centro: Contador e Status
        status_box = ctk.CTkFrame(content, fg_color="transparent")
        status_box.pack(side="left", fill="x", expand=True, padx=15)

        self.selection_label = ctk.CTkLabel(
            status_box,
            text="0 selecionados",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_accent"],
        )
        self.selection_label.pack(side="left")

        ctk.CTkLabel(status_box, text="  •  ", text_color=COLORS["text_muted"]).pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_box,
            text="Pronto para buscar",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self.status_label.pack(side="left")

        # Grupo Direita: Ações Principais
        self.action_box = ctk.CTkFrame(content, fg_color="transparent")
        self.action_box.pack(side="right")

        ctk.CTkButton(
            self.action_box,
            text="📁 Exportar CSV",
            command=self.export_csv,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            width=120,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        self.btn_batch_dl = ctk.CTkButton(
            self.action_box,
            text="⬇️ Baixar Selecionados",
            command=self.download_selected,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            width=160,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.btn_batch_dl.pack(side="left")

        # Barra e botão de cancelar batch (ocultos inicialmente)
        self.batch_progress_bar = ctk.CTkProgressBar(
            self.action_box,
            width=160,
            progress_color=COLORS["primary"],
            corner_radius=4,
        )
        self.btn_cancel_batch = ctk.CTkButton(
            self.action_box,
            text="🛑 Cancelar",
            command=self.cancel_batch_download,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            width=90,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        )

    # =========================================================================
    # LÓGICA DE FILTROS E SELEÇÃO
    # =========================================================================

    def _toggle_filter_inputs(self) -> None:
        """Habilita ou desabilita campos conforme o modo escolhido."""
        is_qty = self.filter_mode.get() == "quantity"
        self.qty_entry.configure(state="normal" if is_qty else "disabled")

        date_state = "disabled" if is_qty else "normal"
        date_bg = COLORS["bg_main"] if is_qty else COLORS["bg_input"]

        self.date_start_entry.configure(state=date_state, fg_color=date_bg)
        self.date_end_entry.configure(state=date_state, fg_color=date_bg)
        self.btn_cal_start.configure(state=date_state)
        self.btn_cal_end.configure(state=date_state)

    def _open_calendar(self, entry_widget: ctk.CTkEntry) -> None:
        """Abre modal de calendário e insere a data selecionada."""
        def _set_date(selected_str: str) -> None:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, selected_str)
        CalendarModal(self, _set_date)

    def _toggle_select_all(self) -> None:
        """Marca ou desmarca todas as linhas da lista."""
        state = self.select_all_var.get()
        for row in self.video_rows:
            row.set_selected(state)
        self.update_selection_counter()

    def update_selection_counter(self) -> None:
        """Atualiza o contador de vídeos selecionados no rodapé."""
        selected_count = sum(1 for v in self.videos if v.is_selected)
        total = len(self.videos)
        self.selection_label.configure(text=f"{selected_count} de {total} selecionados")

    def _open_api_dialog(self) -> None:
        """Abre o diálogo de configuração da API."""
        APIConfigDialog(self, self.config_manager)

    def _open_history_dialog(self) -> None:
        """Abre o diálogo de histórico recente."""
        def _on_select(channel_text: str) -> None:
            self.channel_entry.delete(0, "end")
            self.channel_entry.insert(0, channel_text)
            self.start_extraction()
        HistoryDialog(self, self.config_manager, _on_select)

    def get_selected_download_format(self) -> DownloadFormat:
        """Converte a seleção da combobox para o enum correspondente."""
        val = self.format_var.get()
        for fmt in DownloadFormat:
            if fmt.value == val:
                return fmt
        return DownloadFormat.VIDEO_BEST_720P

    def prompt_save_directory(self) -> Optional[str]:
        """Solicita diretório de salvamento ao usuário."""
        save_dir = filedialog.askdirectory()
        return save_dir if save_dir else None

    # =========================================================================
    # EXTRAÇÃO DE VÍDEOS (YOUTUBE API)
    # =========================================================================

    def start_extraction(self) -> None:
        """Inicia a busca por vídeos em thread separada com proteção contra concorrência."""
        if self.is_searching:
            return

        api_key = self.config_manager.load_api_key()
        channel_input = self.channel_entry.get().strip()

        if not api_key:
            self.show_toast("Configure sua YouTube API Key primeiro!", "error")
            self._open_api_dialog()
            return

        if not channel_input:
            self.show_toast("Informe um canal ou link de vídeo!", "warning")
            return

        # Valida filtros
        mode = self.filter_mode.get()
        search_filter = SearchFilter(mode=mode)
        if mode == "quantity":
            try:
                search_filter.quantity = max(1, int(self.qty_entry.get().strip()))
            except ValueError:
                self.show_toast("Informe uma quantidade válida de vídeos!", "error")
                return
        else:
            try:
                search_filter.start_date = datetime.strptime(self.date_start_entry.get().strip(), "%Y-%m-%d")
                search_filter.end_date = datetime.strptime(
                    self.date_end_entry.get().strip(), "%Y-%m-%d"
                ).replace(hour=23, minute=59, second=59)
            except ValueError:
                self.show_toast("Formato de data inválido (use AAAA-MM-DD)!", "error")
                return

        # Limpa lista atual
        self._clear_results()

        # Altera estado para carregando
        self.is_searching = True
        self.btn_extract.configure(text="⏳ Buscando...", state="disabled")
        self.status_label.configure(text="Conectando à API do YouTube...", text_color=COLORS["warning"])

        # Salva canal no histórico
        self.config_manager.save_history_entry(channel_input)

        threading.Thread(
            target=self._run_extraction_worker,
            args=(api_key, channel_input, search_filter),
            daemon=True,
        ).start()

    def _clear_results(self) -> None:
        """Remove itens da interface e esvazia listas."""
        self.thumbnail_loader.cancel_pending()
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.videos.clear()
        self.video_rows.clear()
        self.select_all_var.set(False)
        self.update_selection_counter()

    def _run_extraction_worker(self, api_key: str, channel_input: str, search_filter: SearchFilter) -> None:
        """Executa a chamada da API do YouTube em background."""
        try:
            # 1. Verifica se a busca é por vídeo individual
            video_id = self.youtube_service.extract_video_id(channel_input)
            if video_id:
                single_video = self.youtube_service.fetch_single_video(api_key, video_id)
                if single_video:
                    self.after(0, lambda: self._add_video_to_ui(single_video))
                    self.after(0, lambda: self._finish_search(f"✓ Vídeo carregado com sucesso", "success"))
                    return

            # 2. Busca canal e uploads playlist
            self.after(0, lambda: self.status_label.configure(text="Localizando canal...", text_color=COLORS["warning"]))
            playlist_id = self.youtube_service.resolve_uploads_playlist_id(api_key, channel_input)

            self.after(0, lambda: self.status_label.configure(text="Listando vídeos...", text_color=COLORS["warning"]))

            # 3. Paginação e coleta de vídeos
            found_videos = self.youtube_service.fetch_channel_videos(
                api_key=api_key,
                playlist_id=playlist_id,
                search_filter=search_filter,
                on_video_found=lambda v: self.after(0, lambda item=v: self._add_video_to_ui(item)),
            )

            count = len(found_videos)
            msg = f"✓ {count} vídeos encontrados" if count > 0 else "Nenhum vídeo encontrado para os filtros informados."
            status_type = "success" if count > 0 else "warning"
            self.after(0, lambda: self._finish_search(msg, status_type))

        except Exception as e:
            logger.error("Erro na busca: %s", e)
            self.after(0, lambda err=str(e): self._finish_search(f"Erro: {err}", "error"))

    def _add_video_to_ui(self, video: VideoItem) -> None:
        """Insere uma linha de vídeo na interface."""
        if hasattr(self, "placeholder_label") and self.placeholder_label.winfo_exists():
            self.placeholder_label.destroy()

        self.videos.append(video)
        row = VideoRow(
            parent=self.scroll_frame,
            video=video,
            thumbnail_loader=self.thumbnail_loader,
            download_service=self.download_service,
            on_selection_changed=self.update_selection_counter,
            on_toast_requested=self.show_toast,
            get_download_format=self.get_selected_download_format,
            get_save_directory=self.prompt_save_directory,
        )
        self.video_rows.append(row)
        self.update_selection_counter()

    def _finish_search(self, message: str, status_type: str) -> None:
        """Restaura o estado após o término da busca."""
        self.is_searching = False
        self.btn_extract.configure(text="🔍 BUSCAR VÍDEOS", state="normal")

        color_map = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
        }
        self.status_label.configure(text=message, text_color=color_map.get(status_type, COLORS["text_muted"]))
        self.show_toast(message, toast_type=status_type)

    # =========================================================================
    # DOWNLOAD EM LOTE E CANCELAMENTO
    # =========================================================================

    def download_selected(self) -> None:
        """Inicia download em lote dos itens selecionados com cancelamento disponível."""
        if self.is_batch_downloading:
            return

        selected_items = [(v.title, v.url) for v in self.videos if v.is_selected]
        if not selected_items:
            self.show_toast("Selecione pelo menos um vídeo para baixar!", "warning")
            return

        save_dir = self.prompt_save_directory()
        if not save_dir:
            return

        fmt = self.get_selected_download_format()
        cancel_token = self.download_service.create_cancel_token()

        self.is_batch_downloading = True
        self.btn_batch_dl.pack_forget()
        self.batch_progress_bar.set(0)
        self.batch_progress_bar.pack(side="left", padx=(0, 10))
        self.btn_cancel_batch.pack(side="left")

        threading.Thread(
            target=self._run_batch_worker,
            args=(selected_items, save_dir, fmt, cancel_token),
            daemon=True,
        ).start()

    def cancel_batch_download(self) -> None:
        """Interrompe o download em lote atual."""
        self.download_service.cancel_active_downloads()
        self.status_label.configure(text="Cancelando downloads...", text_color=COLORS["warning"])
        self.show_toast("Cancelando processo...", "warning")

    def _run_batch_worker(
        self,
        items: list[tuple[str, str]],
        save_dir: str,
        fmt: DownloadFormat,
        cancel_token: threading.Event,
    ) -> None:
        total = len(items)

        def _on_start(idx: int, tot: int, title: str, url: str) -> None:
            def _update() -> None:
                display = title[:35] + "..." if len(title) > 35 else title
                self.status_label.configure(
                    text=f"Baixando ({idx + 1}/{tot}): {display}",
                    text_color=COLORS["warning"],
                )
                self.batch_progress_bar.set(idx / tot)
            self.after(0, _update)

        def _on_item_prog(prog: DownloadProgress) -> None:
            # Progresso interno se necessário
            pass

        def _on_item_done(idx: int, title: str, success: bool, msg: str) -> None:
            def _update() -> None:
                self.batch_progress_bar.set((idx + 1) / total)
            self.after(0, _update)

        success_count, _ = self.download_service.download_batch(
            items=items,
            output_dir=save_dir,
            fmt=fmt,
            on_item_start=_on_start,
            on_item_progress=_on_item_prog,
            on_item_complete=_on_item_done,
            cancel_token=cancel_token,
        )

        def _finish() -> None:
            self.is_batch_downloading = False
            self.batch_progress_bar.pack_forget()
            self.btn_cancel_batch.pack_forget()
            self.btn_batch_dl.pack(side="left")

            if cancel_token.is_set():
                self.status_label.configure(
                    text=f"Processo cancelado. {success_count}/{total} concluídos.",
                    text_color=COLORS["warning"],
                )
                self.show_toast(f"Downloads interrompidos ({success_count}/{total})", "warning")
            else:
                self.status_label.configure(
                    text=f"✓ {success_count}/{total} downloads concluídos com sucesso!",
                    text_color=COLORS["success"],
                )
                self.show_toast(f"Concluído: {success_count}/{total} vídeos baixados!", "success")

        self.after(0, _finish)

    # =========================================================================
    # ÁREA DE TRANSFERÊNCIA E EXPORTAÇÃO CSV
    # =========================================================================

    def copy_selected_urls(self) -> None:
        """Copia as URLs dos vídeos marcados para a área de transferência."""
        selected_urls = [v.url for v in self.videos if v.is_selected]
        if not selected_urls:
            self.show_toast("Nenhum vídeo selecionado.", "warning")
            return

        self.clipboard_clear()
        self.clipboard_append("\n".join(selected_urls))
        self.show_toast(f"{len(selected_urls)} URLs copiadas!", "success")

    def copy_all_urls(self) -> None:
        """Copia todas as URLs listadas para a área de transferência."""
        if not self.videos:
            self.show_toast("Nenhum vídeo disponível para copiar.", "warning")
            return

        urls = [v.url for v in self.videos]
        self.clipboard_clear()
        self.clipboard_append("\n".join(urls))
        self.show_toast(f"Todas as {len(urls)} URLs copiadas!", "success")

    def export_csv(self) -> None:
        """Exporta vídeos em CSV com UTF-8-SIG para total compatibilidade com Excel no Windows."""
        if not self.videos:
            self.show_toast("Nenhum vídeo para exportar.", "warning")
            return

        # Se houver itens selecionados, pergunta se prefere exportar apenas os selecionados
        export_list = self.videos
        selected_items = [v for v in self.videos if v.is_selected]
        if selected_items and len(selected_items) < len(self.videos):
            resp = messagebox.askyesnocancel(
                "Exportar CSV",
                f"Deseja exportar apenas os {len(selected_items)} vídeos selecionados?\n\n"
                "- Sim: Exporta apenas os selecionados\n"
                "- Não: Exporta todos os {len(self.videos)} vídeos listados\n"
                "- Cancelar: Aborta a exportação",
            )
            if resp is None:
                return
            if resp is True:
                export_list = selected_items

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivos CSV (*.csv)", "*.csv"), ("Todos os Arquivos", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["Data de Publicação", "Título do Vídeo", "URL do YouTube"])
                for item in export_list:
                    writer.writerow(item.to_csv_row())

            self.show_toast(f"CSV exportado com sucesso ({len(export_list)} itens)!", "success")
        except Exception as e:
            logger.error("Erro ao exportar CSV: %s", e)
            self.show_toast(f"Erro ao exportar CSV: {e}", "error")

    def _on_close(self) -> None:
        """Encerra threads ativas e fecha a aplicação com segurança."""
        try:
            self.download_service.cancel_active_downloads()
            self.thumbnail_loader.shutdown()
        except Exception:
            pass
        self.destroy()
