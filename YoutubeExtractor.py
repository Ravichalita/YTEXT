import customtkinter as ctk
from tkinter import messagebox, filedialog, Toplevel
from tkcalendar import Calendar
import webbrowser
from googleapiclient.discovery import build
from datetime import datetime, date
import csv
import json
import os
import threading
import yt_dlp
import platform
import yt_dlp
import platform
import re
import sys
import urllib.request
from PIL import Image
import io

# =============================================================================
# CONFIGURAÇÃO VISUAL - PALETA MODERNA
# =============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Cores Modernas
COLORS = {
    "primary": "#6366f1",        # Indigo vibrante
    "primary_hover": "#4f46e5",  # Indigo escuro
    "primary_gradient": "#8b5cf6", # Roxo para gradiente
    "secondary": "#10b981",      # Verde emerald
    "secondary_hover": "#059669",
    "accent": "#f59e0b",         # Amber destaque
    "bg_main": "#0f0f23",        # Fundo principal
    "bg_card": "#1a1a2e",        # Cards
    "bg_card_hover": "#252542",  # Cards hover
    "bg_header": "#16213e",      # Header
    "bg_input": "#1e1e3f",       # Inputs
    "text_primary": "#f8fafc",   # Texto principal
    "text_muted": "#94a3b8",     # Texto secundário
    "text_accent": "#a5b4fc",    # Texto accent
    "danger": "#ef4444",         # Vermelho erro
    "success": "#22c55e",        # Verde sucesso
    "warning": "#f59e0b",        # Amarelo aviso
    "border": "#334155",         # Bordas
    "separator": "#1e293b",      # Separadores
}

class CalendarModal(Toplevel):
    """Janela flutuante para seleção de data com estilo moderno"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("📅 Selecione a Data")
        self.geometry("320x280")
        self.configure(bg=COLORS["bg_card"])
        self.grab_set()
        
        # Calendário
        today = date.today()
        self.cal = Calendar(
            self, 
            selectmode='day', 
            year=today.year, 
            month=today.month, 
            day=today.day, 
            date_pattern='y-mm-dd',
            background=COLORS["bg_card"],
            foreground=COLORS["text_primary"],
            headersbackground=COLORS["primary"],
            headersforeground="white",
            selectbackground=COLORS["primary"],
            selectforeground="white",
            normalbackground=COLORS["bg_main"],
            normalforeground=COLORS["text_primary"],
            weekendbackground=COLORS["bg_main"],
            weekendforeground=COLORS["text_accent"],
        )
        self.cal.pack(fill="both", expand=True, padx=15, pady=15)
        
        btn = ctk.CTkButton(
            self, 
            text="✓ Confirmar", 
            command=self.on_confirm,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=35,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn.pack(pady=(0, 15))

    def on_confirm(self):
        selected_date = self.cal.get_date()
        self.callback(selected_date)
        self.destroy()


class ToastNotification(ctk.CTkFrame):
    """Notificação toast que aparece e desaparece automaticamente"""
    def __init__(self, parent, message, toast_type="info", duration=3000):
        super().__init__(parent, corner_radius=10)
        
        colors = {
            "success": (COLORS["success"], "✓"),
            "error": (COLORS["danger"], "✕"),
            "warning": (COLORS["warning"], "⚠"),
            "info": (COLORS["primary"], "ℹ"),
        }
        
        color, icon = colors.get(toast_type, colors["info"])
        self.configure(fg_color=color)
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(padx=15, pady=10)
        
        ctk.CTkLabel(
            content, 
            text=f"{icon}  {message}", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        ).pack()
        
        # Auto-destruir após duration
        self.after(duration, self.destroy)


class APIConfigDialog(ctk.CTkToplevel):
    """Janela de configuração da API Key com instruções detalhadas"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("🔑 Configuração da YouTube API")
        self.geometry("600x700")
        self.configure(fg_color=COLORS["bg_main"])
        self.grab_set()

        # Frame Principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Seção de Input ---
        input_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_card"], corner_radius=10)
        input_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            input_frame, 
            text="Sua API Key:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.api_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Cole sua Google Cloud API Key aqui",
            height=40,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"]
        )
        self.api_entry.pack(fill="x", padx=15, pady=(0, 15))
        
        # Carregar key existente
        self.load_current_key()

        btn_save = ctk.CTkButton(
            input_frame,
            text="💾 Salvar Configuração",
            command=self.save_key,
            fg_color=COLORS["success"],
            hover_color=COLORS["secondary_hover"],
            height=40,
            font=ctk.CTkFont(weight="bold")
        )
        btn_save.pack(fill="x", padx=15, pady=(0, 15))

        # --- Seção de Ajuda ---
        help_label = ctk.CTkLabel(
            main_frame,
            text="📚 Como obter sua API Key (Passo a Passo)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        help_label.pack(anchor="w", pady=(0, 10))

        self.help_text = ctk.CTkTextbox(
            main_frame,
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=13),
            corner_radius=10
        )
        self.help_text.pack(fill="both", expand=True)
        
        instructions = """
1. ACESSO AO GOOGLE CLOUD
   - Acesse: https://console.cloud.google.com/
   - Faça login com sua conta Google.

2. CRIAR PROJETO
   - No topo da página, clique no seletor de projetos.
   - Clique em "Novo Projeto".
   - Dê um nome (ex: "YoutubeExtractor") e clique em "Criar".

3. ATIVAR A API
   - No menu lateral, vá em "APIs e Serviços" > "Biblioteca".
   - Pesquise por: "YouTube Data API v3".
   - Clique nela e depois no botão "Ativar".

4. CRIAR CREDENCIAIS (A CHAVE)
   - Após ativar, clique em "Criar Credenciais" (ou vá em "Credenciais" no menu).
   - Em "Qual API você está usando?", selecione "YouTube Data API v3".
   - Em "Quais dados você acessará?", selecione "Dados públicos".
   - Clique em "Próximo" e sua API Key será gerada!
   - Copie este código e cole no campo acima.

⚠️ LIMITES E COTAS (IMPORTANTE)
   - Nível Gratuito: O Google oferece uma cota diária gratuita de 10.000 unidades.
   - O que isso significa?
     - Cada busca consome cerca de 100 unidades.
     - Cada listagem de vídeos consome mais algumas unidades.
   - Isso é suficiente para uso pessoal moderado/intenso.
   - Se atingir o limite, a API parará de funcionar até o dia seguinte.
   - Você NÃO será cobrado a menos que ative manualmente uma conta de faturamento e configure limites maiores.
"""
        self.help_text.insert("0.0", instructions)
        self.help_text.configure(state="disabled")

    def load_current_key(self):
        if os.path.exists(self.parent.config_file):
            try:
                with open(self.parent.config_file, "r") as f:
                    data = json.load(f)
                    self.api_entry.insert(0, data.get("api_key", ""))
            except:
                pass

    def save_key(self):
        key = self.api_entry.get().strip()
        if not key:
            messagebox.showwarning("Atenção", "Por favor, insira uma API Key válida.")
            return
            
        try:
            with open(self.parent.config_file, "w") as f:
                json.dump({"api_key": key}, f)
            messagebox.showinfo("Sucesso", "API Key salva com sucesso!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")



def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class YoutubeExtractorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("YouTube Extractor Pro")
        self.geometry("1150x900")
        self.configure(fg_color=COLORS["bg_main"])
        
        try:
            self.iconbitmap(resource_path("YTBEX.ico"))
        except:
            pass

        self.config_file = "config.json"
        self.history_file = "history.json"
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Lista ocupa espaço

        self.filter_mode = ctk.StringVar(value="quantity")
        self.videos_data = []
        self.checkbox_vars = []
        self.select_all_var = ctk.BooleanVar(value=False)
        self.is_searching = False

        self.create_widgets()
        # self.load_api_key() # Configuration is now loaded on demand or in dialog

    def show_toast(self, message, toast_type="info"):
        """Exibe notificação toast no canto superior direito"""
        toast = ToastNotification(self, message, toast_type)
        toast.place(relx=0.98, rely=0.02, anchor="ne")

    def create_widgets(self):
        # --- 1. Header Premium ---
        self.header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_header"], corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_content.pack(fill="x", padx=25, pady=20)
        
        # Título com emoji
        title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame, 
            text="YouTube Extractor Pro", 
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame, 
            text="Extraia e baixe vídeos de qualquer canal do YouTube",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(3, 0))

        # --- 2. Configurações ---
        self.config_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.config_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.config_frame.grid_columnconfigure(1, weight=1)

        # Botão Configuração API
        self.btn_config_api = ctk.CTkButton(
            self.config_frame,
            text="🔑 YouTube API",
            command=self.open_api_dialog,
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            width=140,
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_config_api.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="w")

        # Remover inputs antigos de API da grid


        # Canal

        ctk.CTkLabel(
            self.config_frame, 
            text="📺 Canal:", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=(180, 10), pady=(15, 8), sticky="w") # Ajuste de posição para não sobrepor botao API
        
        self.channel_entry = ctk.CTkEntry(
            self.config_frame, 
            placeholder_text="Ex: @MrBeast ou URL do canal",
            height=40,
            corner_radius=8,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12)
        )
        self.channel_entry.grid(row=0, column=1, padx=(0, 10), pady=(15, 8), sticky="ew")
        self.channel_entry.bind('<Return>', lambda e: self.start_extraction())
        
        ctk.CTkButton(
            self.config_frame, 
            text="📋 Histórico", 
            width=90, 
            height=40,
            command=self.show_history_dialog, 
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=2, padx=20, pady=(15, 8))

        # --- 3. Filtros ---
        self.filter_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.filter_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        
        filter_content = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        filter_content.pack(fill="x", padx=20, pady=15)
        
        # Opção Quantidade
        qty_frame = ctk.CTkFrame(filter_content, fg_color="transparent")
        qty_frame.pack(side="left")
        
        self.rb_qty = ctk.CTkRadioButton(
            qty_frame, 
            text="Últimos", 
            variable=self.filter_mode, 
            value="quantity", 
            command=self.toggle_inputs,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"]
        )
        self.rb_qty.pack(side="left", padx=(0, 8))
        
        self.qty_entry = ctk.CTkEntry(
            qty_frame, 
            width=60, 
            height=35,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            justify="center",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.qty_entry.insert(0, "10")
        self.qty_entry.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(
            qty_frame, 
            text="vídeos",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"]
        ).pack(side="left")

        # Separador vertical
        sep = ctk.CTkFrame(filter_content, width=2, height=35, fg_color=COLORS["separator"])
        sep.pack(side="left", padx=25)

        # Opção Data
        date_frame = ctk.CTkFrame(filter_content, fg_color="transparent")
        date_frame.pack(side="left")
        
        self.rb_date = ctk.CTkRadioButton(
            date_frame, 
            text="Período:", 
            variable=self.filter_mode, 
            value="date", 
            command=self.toggle_inputs,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"]
        )
        self.rb_date.pack(side="left", padx=(0, 8))

        # Data Início
        self.date_start_entry = ctk.CTkEntry(
            date_frame, 
            width=100, 
            height=35,
            placeholder_text="AAAA-MM-DD",
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12)
        )
        self.date_start_entry.pack(side="left", padx=(0, 3))
        
        self.btn_cal_start = ctk.CTkButton(
            date_frame, 
            text="📅", 
            width=35, 
            height=35,
            command=lambda: self.open_calendar(self.date_start_entry),
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.btn_cal_start.pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(
            date_frame, 
            text="até",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"]
        ).pack(side="left", padx=5)
        
        # Data Fim
        self.date_end_entry = ctk.CTkEntry(
            date_frame, 
            width=100, 
            height=35,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            font=ctk.CTkFont(size=12)
        )
        self.date_end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_end_entry.pack(side="left", padx=(0, 3))
        
        self.btn_cal_end = ctk.CTkButton(
            date_frame, 
            text="📅", 
            width=35, 
            height=35,
            command=lambda: self.open_calendar(self.date_end_entry),
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.btn_cal_end.pack(side="left")

        # Botão Buscar (destaque principal)
        self.btn_extract = ctk.CTkButton(
            filter_content, 
            text="🔍 BUSCAR VÍDEOS", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            width=180, 
            height=42,
            command=self.start_extraction,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8
        )
        self.btn_extract.pack(side="right")

        # --- 4. Cabeçalho da Lista com Select All ---
        self.header_list_frame = ctk.CTkFrame(self, fg_color=COLORS["primary"], corner_radius=8)
        self.header_list_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(15, 0))
        
        header_content = ctk.CTkFrame(self.header_list_frame, fg_color="transparent")
        header_content.pack(fill="x", padx=5, pady=8)
        
        # Checkbox Select All
        self.select_all_cb = ctk.CTkCheckBox(
            header_content, 
            text="", 
            variable=self.select_all_var,
            command=self.toggle_select_all,
            width=20,
            fg_color="white",
            checkmark_color=COLORS["primary"],
            hover_color="#e0e0ff"
        )
        self.select_all_cb.pack(side="left", padx=(10, 15))
        
        ctk.CTkLabel(
            header_content, 
            text="DATA", 
            width=100, 
            anchor="w", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="white"
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(
            header_content, 
            text="TÍTULO (Clique para abrir no YouTube)", 
            anchor="w", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="white"
        ).pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(
            header_content, 
            text="AÇÕES", 
            width=130, 
            anchor="e", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color="white"
        ).pack(side="right", padx=15)

        # --- 5. Lista de Vídeos ---
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"]
        )
        self.scroll_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=0)
        
        # Espaço reservado para lista (placeholder)
        self.placeholder_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Busque um canal para ver os vídeos aqui",
            font=ctk.CTkFont(size=16),
            text_color=COLORS["text_muted"]
        )
        self.placeholder_label.pack(pady=80)

        # --- 6. Rodapé Premium ---
        self.footer_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        self.footer_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=15)
        
        footer_content = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_content.pack(fill="x", padx=15, pady=12)
        
        # Grupo Esquerdo - Botões de Cópia
        copy_group = ctk.CTkFrame(footer_content, fg_color="transparent")
        copy_group.pack(side="left")
        
        ctk.CTkButton(
            copy_group, 
            text="📋 Copiar Tudo", 
            command=self.copy_all, 
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            width=120,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            copy_group, 
            text="📋 Selecionados", 
            command=self.copy_selected, 
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            width=120,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 8))
        


        # Centro - Status e Contador
        status_group = ctk.CTkFrame(footer_content, fg_color="transparent")
        status_group.pack(side="left", fill="x", expand=True, padx=20)
        
        self.selection_label = ctk.CTkLabel(
            status_group, 
            text="0 selecionados", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_accent"]
        )
        self.selection_label.pack(side="left")
        
        # Separador
        ctk.CTkLabel(
            status_group, 
            text="  •  ",
            text_color=COLORS["text_muted"]
        ).pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            status_group, 
            text="Pronto para buscar", 
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(side="left")
        
        # Grupo Direito - Ações Principais
        action_group = ctk.CTkFrame(footer_content, fg_color="transparent")
        action_group.pack(side="right")
        
        ctk.CTkButton(
            action_group, 
            text="📁 Exportar CSV", 
            command=self.export_csv, 
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            width=130,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))
        
        self.btn_batch_dl = ctk.CTkButton(
            action_group, 
            text="⬇️ Baixar Selecionados", 
            command=self.download_selected, 
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            width=160,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_batch_dl.pack(side="left")

        self.toggle_inputs()

    def toggle_select_all(self):
        """Marca/desmarca todos os checkboxes"""
        state = self.select_all_var.get()
        for var in self.checkbox_vars:
            var.set(state)
        self.update_selection_count()

    def update_selection_count(self):
        """Atualiza o contador de itens selecionados"""
        count = sum(1 for var in self.checkbox_vars if var.get())
        total = len(self.checkbox_vars)
        self.selection_label.configure(text=f"{count} de {total} selecionados")

    def open_calendar(self, entry_widget):
        def set_date(date_str):
            entry_widget.delete(0, "end")
            entry_widget.insert(0, date_str)
        CalendarModal(self, set_date)

    def toggle_inputs(self):
        mode = self.filter_mode.get()
        state_qty = "normal" if mode == "quantity" else "disabled"
        state_date = "normal" if mode == "date" else "disabled"
        color_date = COLORS["bg_input"] if mode == "date" else COLORS["bg_main"]

        self.qty_entry.configure(state=state_qty)
        
        self.date_start_entry.configure(state=state_date, fg_color=color_date)
        self.date_end_entry.configure(state=state_date, fg_color=color_date)
        self.btn_cal_start.configure(state=state_date)
        self.btn_cal_end.configure(state=state_date)

    # --- Lógica API e Extração ---
    def open_api_dialog(self):
        APIConfigDialog(self)

    # load_api_key e save_api_key removidos daqui pois foram movidos para o Dialog ou não são mais usados diretamente no main frame
    def get_api_key(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f: 
                    return json.load(f).get("api_key", "")
            except: 
                pass
        return ""

    def start_extraction(self):
        if self.is_searching:
            return
            
        
        api_key = self.get_api_key()
        channel = self.channel_entry.get().strip()
        
        if not api_key or not channel:
            self.show_toast("Preencha a API Key e o Canal!", "error")
            return

        # Limpar lista
        for widget in self.scroll_frame.winfo_children(): 
            widget.destroy()
        self.videos_data = []
        self.checkbox_vars = []
        self.select_all_var.set(False)

        # Estado de loading
        self.is_searching = True
        self.btn_extract.configure(text="⏳ Buscando...", state="disabled")
        self.status_label.configure(text="Conectando à API do YouTube...", text_color=COLORS["warning"])
        self.update()
        
        threading.Thread(target=self.run_api_search, args=(api_key, channel)).start()
        self.save_history(channel)

    def run_api_search(self, api_key, channel_input):
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            info = None
            
            if "/channel/" in channel_input: 
                cid = channel_input.split("/channel/")[1].split("/")[0]
            elif "/@" in channel_input: 
                h = channel_input.split("/@")[1].split("/")[0]
                r = youtube.channels().list(part="id,contentDetails", forHandle="@"+h).execute()
                info = r['items'][0] if r['items'] else None
            elif channel_input.startswith("@"):
                r = youtube.channels().list(part="id,contentDetails", forHandle=channel_input).execute()
                info = r['items'][0] if r['items'] else None
            else:
                r = youtube.channels().list(part="id,contentDetails", id=channel_input).execute()
                info = r['items'][0] if r['items'] else None
                
            if info: 
                uploads_id = info['contentDetails']['relatedPlaylists']['uploads']
                self.extract_logic(youtube, uploads_id)
            elif not info and "/channel/" in channel_input:
                self.extract_logic(youtube, cid)
            else:
                self.after(0, lambda: self.end_search_state("Canal não encontrado", "error"))

        except Exception as e:
            self.after(0, lambda: self.end_search_state(f"Erro: {str(e)}", "error"))

    def end_search_state(self, message, status_type):
        """Restaura o estado do botão após busca"""
        self.is_searching = False
        self.btn_extract.configure(text="🔍 BUSCAR VÍDEOS", state="normal")
        
        if status_type == "error":
            self.status_label.configure(text=message, text_color=COLORS["danger"])
            self.show_toast(message, "error")
        else:
            self.status_label.configure(text=message, text_color=COLORS["success"])

    def extract_logic(self, youtube, playlist_id):
        mode = self.filter_mode.get()
        token = None
        fetching = True
        count = 0
        
        try:
            t_qty = int(self.qty_entry.get()) if mode == "quantity" else 0
            t_start = datetime.strptime(self.date_start_entry.get(), "%Y-%m-%d") if mode == "date" else None
            t_end = datetime.strptime(self.date_end_entry.get(), "%Y-%m-%d").replace(hour=23, minute=59) if mode == "date" else None
        except:
            self.after(0, lambda: self.end_search_state("Datas inválidas ou quantidade vazia", "error"))
            return

        while fetching:
            req = youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50, pageToken=token)
            resp = req.execute()

            for item in resp['items']:
                vid = item['snippet']['resourceId']['videoId']
                title = item['snippet']['title']
                p_date = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                url = f"https://www.youtube.com/watch?v={vid}"

                should_add = False
                if mode == "quantity":
                    if count >= t_qty: 
                        fetching = False
                        break
                    should_add = True
                elif mode == "date":
                    if p_date > t_end: 
                        continue
                    if p_date < t_start: 
                        fetching = False
                        break
                    should_add = True

                if should_add:
                    count += 1
                    
                    thumb_url = ""
                    try:
                        # Tenta pegar a thumbnail padrão ou média
                        thumb_url = item['snippet']['thumbnails']['medium']['url']
                    except:
                        try:
                            thumb_url = item['snippet']['thumbnails']['default']['url']
                        except:
                            pass

                    self.videos_data.append({"date": p_date.strftime("%Y-%m-%d"), "title": title, "url": url})
                    self.after(0, self.add_row_to_ui, p_date.strftime("%Y-%m-%d"), title, url, thumb_url)

            token = resp.get('nextPageToken')
            if not token: 
                fetching = False
        
        self.after(0, lambda: self.end_search_state(f"✓ {count} vídeos encontrados", "success"))
        self.after(0, self.update_selection_count)
        if count > 0:
            self.after(0, lambda: self.show_toast(f"{count} vídeos carregados!", "success"))

    def load_thumbnail(self, url, label):
        try:
            with urllib.request.urlopen(url) as u:
                raw_data = u.read()
            
            image = Image.open(io.BytesIO(raw_data))
            # Ajustar tamanho (mantendo aspect ratio approx 16:9, height=45)
            # Layout: height=60 pra ficar visivel
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(100, 56))
            
            self.after(0, lambda: label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    def add_row_to_ui(self, date_txt, title_txt, url, thumb_url):
        row = ctk.CTkFrame(
            self.scroll_frame, 
            fg_color=COLORS["bg_card_hover"], 
            corner_radius=8
        )
        row.pack(fill="x", pady=3, padx=8)
        
        # Bind hover effects
        row.bind("<Enter>", lambda e: row.configure(fg_color="#2d2d4a"))
        row.bind("<Leave>", lambda e: row.configure(fg_color=COLORS["bg_card_hover"]))

        # Checkbox
        chk_var = ctk.BooleanVar()
        self.checkbox_vars.append(chk_var)
        
        chk = ctk.CTkCheckBox(
            row, 
            text="", 
            variable=chk_var, 
            width=20,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self.update_selection_count
        )
        chk.pack(side="left", padx=(12, 10), pady=10)

        # Thumbnail Label (Placeholder initially)
        thumb_label = ctk.CTkLabel(row, text="🎬", font=ctk.CTkFont(size=20), width=100, height=56, fg_color="#2b2b40", corner_radius=6)
        thumb_label.pack(side="left", padx=(0, 10))
        
        if thumb_url:
            threading.Thread(target=self.load_thumbnail, args=(thumb_url, thumb_label), daemon=True).start()

        # Data
        ctk.CTkLabel(
            row, 
            text=date_txt, 
            width=90, 
            anchor="w", 
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 10))
        
        # Título clicável
        lbl = ctk.CTkLabel(
            row, 
            text=title_txt[:70] + "..." if len(title_txt) > 70 else title_txt, 
            anchor="w", 
            cursor="hand2", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        lbl.pack(side="left", fill="x", expand=True, padx=5)
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        lbl.bind("<Enter>", lambda e: lbl.configure(text_color=COLORS["text_accent"]))
        lbl.bind("<Leave>", lambda e: lbl.configure(text_color=COLORS["text_primary"]))

        # Botão Baixar
        btn = ctk.CTkButton(
            row, 
            text="⬇️ Baixar", 
            width=90, 
            height=30, 
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn.pack(side="right", padx=10, pady=8)
        btn.configure(command=lambda u=url, b=btn: self.download_video_thread(u, b))

        # Botão Abrir URL
        ctk.CTkButton(
            row, 
            text="🌐", 
            width=35, 
            height=30, 
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=lambda: webbrowser.open(url)
        ).pack(side="right", padx=(0, 5), pady=8)

    # --- Lógica Download ---
    def download_video_thread(self, url, btn_ref):
        save_dir = filedialog.askdirectory()
        if not save_dir: 
            return
        
        master_frame = btn_ref.master
        btn_ref.pack_forget()
        
        progress_bar = ctk.CTkProgressBar(
            master_frame, 
            width=100, 
            progress_color=COLORS["primary"],
            corner_radius=4
        )
        progress_bar.set(0)
        progress_bar.pack(side="right", padx=10, pady=8)
        
        threading.Thread(target=self.run_download, args=(url, save_dir, btn_ref, progress_bar)).start()

    def run_download(self, url, save_dir, btn_ref, progress_bar):
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    p = d.get('_percent_str', '0%')
                    p = re.sub(r'\x1b\[[0-9;]*m', '', p).replace('%','')
                    self.after(0, lambda: progress_bar.set(float(p)/100))
                except: 
                    pass
            elif d['status'] == 'finished':
                self.after(0, lambda: progress_bar.set(1))

        ydl_opts = {
            'paths': {'home': save_dir},
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'format': 'best[ext=mp4][height<=720]/best[height<=720]/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
        }
        
        try:
            filename = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                ydl.download([url])
            
            self.after(0, lambda: progress_bar.destroy())
            
            if filename and os.path.exists(filename):
                self.after(0, lambda: self.update_btn_to_open(btn_ref, filename))
                self.after(0, lambda: self.show_toast("Download concluído!", "success"))
            else:
                self.after(0, lambda: self.restore_btn(btn_ref, "Erro", COLORS["danger"]))
        except Exception as e:
            print(e)
            self.after(0, lambda: progress_bar.destroy())
            self.after(0, lambda: self.restore_btn(btn_ref, "Erro", COLORS["danger"]))
            self.after(0, lambda: self.show_toast("Erro no download", "error"))

    def restore_btn(self, btn, text, color):
        btn.configure(text=text, fg_color=color, state="normal")
        btn.pack(side="right", padx=10, pady=8)

    def update_btn_to_open(self, btn, filepath):
        btn.configure(
            text="📂 Abrir", 
            fg_color=COLORS["success"], 
            hover_color=COLORS["secondary_hover"],
            state="normal", 
            command=lambda: self.open_file(filepath)
        )
        btn.pack(side="right", padx=10, pady=8)

    def open_file(self, filepath):
        try:
            if platform.system() == 'Windows': 
                os.startfile(filepath)
            else:
                import subprocess
                subprocess.call(('xdg-open', filepath))
        except: 
            self.show_toast("Não foi possível abrir o arquivo", "error")

    # --- Funções de Cópia ---
    def copy_selected(self):
        selected_urls = [video['url'] for var, video in zip(self.checkbox_vars, self.videos_data) if var.get()]
        
        if selected_urls:
            self.clipboard_clear()
            self.clipboard_append("\n".join(selected_urls))
            self.show_toast(f"{len(selected_urls)} URLs copiadas!", "success")
        else:
            self.show_toast("Nenhum item selecionado", "warning")

    def copy_all(self):
        if self.videos_data:
            self.clipboard_clear()
            self.clipboard_append("\n".join([v['url'] for v in self.videos_data]))
            self.show_toast(f"Todas as {len(self.videos_data)} URLs copiadas!", "success")
        else:
            self.show_toast("Nenhum vídeo para copiar", "warning")



    def export_csv(self):
        if not self.videos_data: 
            self.show_toast("Nenhum vídeo para exportar", "warning")
            return
            
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if f:
            with open(f, 'w', newline='', encoding='utf-8') as file:
                w = csv.writer(file)
                w.writerow(["Data", "Título", "URL"])
                for v in self.videos_data: 
                    w.writerow([v['date'], v['title'], v['url']])
            self.show_toast("CSV exportado com sucesso!", "success")

    # --- Histórico ---
    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f: 
                    return json.load(f)
            except: 
                return []
        return []

    def save_history(self, channel):
        hist = self.load_history()
        if channel not in hist:
            hist.insert(0, channel)
            if len(hist) > 20: 
                hist.pop()
            try:
                with open(self.history_file, "w") as f: 
                    json.dump(hist, f)
            except: 
                pass

    def show_history_dialog(self):
        hist = self.load_history()
        if not hist:
            self.show_toast("Nenhum histórico encontrado", "info")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("📋 Histórico de Busca")
        dialog.geometry("350x450")
        dialog.configure(fg_color=COLORS["bg_main"])
        dialog.grab_set()

        # Header
        header = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"], corner_radius=0)
        header.pack(fill="x")
        
        ctk.CTkLabel(
            header, 
            text="📺 Canais Recentes", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(pady=15)

        # Lista
        scroll = ctk.CTkScrollableFrame(
            dialog, 
            fg_color=COLORS["bg_card"],
            corner_radius=0
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        for h in hist:
            btn = ctk.CTkButton(
                scroll, 
                text=h, 
                fg_color="transparent", 
                hover_color=COLORS["bg_card_hover"],
                border_width=0,
                text_color=COLORS["text_primary"], 
                anchor="w",
                height=40,
                corner_radius=0,
                font=ctk.CTkFont(size=13)
            )
            btn.pack(fill="x", pady=1, padx=10)
            btn.configure(command=lambda c=h, d=dialog: self.select_history_item(c, d))

    def select_history_item(self, channel, dialog):
        self.channel_entry.delete(0, "end")
        self.channel_entry.insert(0, channel)
        dialog.destroy()
        self.start_extraction()

    # --- Download em Lote ---
    def download_selected(self):
        selected_urls = [(video['title'], video['url']) for var, video in zip(self.checkbox_vars, self.videos_data) if var.get()]
        
        if not selected_urls:
            self.show_toast("Selecione pelo menos um vídeo", "warning")
            return

        save_dir = filedialog.askdirectory()
        if not save_dir: 
            return

        self.btn_batch_dl.pack_forget()
        self.batch_pb = ctk.CTkProgressBar(
            self.btn_batch_dl.master, 
            width=200, 
            progress_color=COLORS["primary"],
            corner_radius=4
        )
        self.batch_pb.set(0)
        self.batch_pb.pack(side="right")

        threading.Thread(target=self.run_batch_download, args=(selected_urls, save_dir)).start()

    def run_batch_download(self, items, save_dir):
        total = len(items)
        
        ydl_opts = {
            'paths': {'home': save_dir},
            'outtmpl': '%(title)s.%(ext)s',
            'restrictfilenames': True,
            'format': 'best[ext=mp4][height<=720]/best[height<=720]/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        success_count = 0
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, (title, url) in enumerate(items):
                try:
                    self.after(0, lambda p=(i/total): self.batch_pb.set(p))
                    self.after(0, lambda t=title: self.status_label.configure(
                        text=f"Baixando: {t[:30]}...", 
                        text_color=COLORS["warning"]
                    ))
                    ydl.download([url])
                    success_count += 1
                except Exception as e:
                    print(f"Erro ao baixar {title}: {e}")
                
                self.after(0, lambda p=((i+1)/total): self.batch_pb.set(p))
        
        # Restaurar UI
        self.after(0, lambda: self.batch_pb.destroy())
        self.after(0, lambda: self.btn_batch_dl.pack(side="right"))
        self.after(0, lambda: self.status_label.configure(
            text=f"✓ {success_count}/{len(items)} downloads concluídos", 
            text_color=COLORS["success"]
        ))
        self.after(0, lambda: self.show_toast(f"Download concluído: {success_count}/{len(items)}", "success"))


if __name__ == "__main__":
    app = YoutubeExtractorApp()
    app.mainloop()