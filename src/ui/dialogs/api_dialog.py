"""API Configuration modal dialog."""

from tkinter import messagebox
from typing import Callable, Optional
import customtkinter as ctk

from src.core.config_manager import ConfigManager
from src.ui.theme import COLORS


class APIConfigDialog(ctk.CTkToplevel):
    """Janela de configuração da YouTube API Key com instruções detalhadas."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        config_manager: ConfigManager,
        on_saved: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.on_saved = on_saved

        self.title("🔑 Configuração da YouTube API")
        self.geometry("620x720")
        self.configure(fg_color=COLORS["bg_main"])
        self.grab_set()

        self._build_ui()
        self._load_current_key()

    def _build_ui(self) -> None:
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Seção de Input
        input_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_card"], corner_radius=10)
        input_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            input_frame,
            text="Sua API Key:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.api_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Cole sua Google Cloud API Key aqui",
            height=40,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.api_entry.pack(fill="x", padx=15, pady=(0, 15))

        btn_save = ctk.CTkButton(
            input_frame,
            text="💾 Salvar Configuração",
            command=self.save_key,
            fg_color=COLORS["success"],
            hover_color=COLORS["secondary_hover"],
            height=40,
            font=ctk.CTkFont(weight="bold"),
        )
        btn_save.pack(fill="x", padx=15, pady=(0, 15))

        # Seção de Ajuda / Instruções
        ctk.CTkLabel(
            main_frame,
            text="📚 Como obter sua API Key (Passo a Passo)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 10))

        self.help_text = ctk.CTkTextbox(
            main_frame,
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=13),
            corner_radius=10,
        )
        self.help_text.pack(fill="both", expand=True)

        instructions = """1. ACESSO AO GOOGLE CLOUD
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
     - Listagens de vídeos consomem apenas 1 unidade por página.
   - Suficiente para uso pessoal diário moderado/intenso.
   - Se atingir o limite, a API voltará a funcionar no dia seguinte.
   - Não há cobrança sem associação prévia e voluntária de cartão de crédito.
"""
        self.help_text.insert("0.0", instructions)
        self.help_text.configure(state="disabled")

    def _load_current_key(self) -> None:
        key = self.config_manager.load_api_key()
        if key:
            self.api_entry.insert(0, key)

    def save_key(self) -> None:
        key = self.api_entry.get().strip()
        if not key:
            messagebox.showwarning("Atenção", "Por favor, insira uma API Key válida.")
            return

        try:
            self.config_manager.save_api_key(key)
            if self.on_saved:
                self.on_saved(key)
            messagebox.showinfo("Sucesso", "API Key salva com sucesso!")
            self.destroy()
        except PermissionError:
            messagebox.showerror(
                "Erro de Permissão",
                f"Sem permissão para gravar em:\n{self.config_manager.config_path}\n\n"
                "Verifique se o arquivo não está aberto em outro programa ou se a pasta não é somente leitura.",
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")
