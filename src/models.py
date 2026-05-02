"""Data model for a single IRPF entry extracted from an informe."""
from dataclasses import dataclass, field


@dataclass
class Entry:
    # ── Source ────────────────────────────────────────────────────────────────
    arquivo: str            # original filename inside the ZIP
    instituicao: str        # human-readable institution name
    cnpj_instituicao: str   # CNPJ of the issuing institution
    ano_calendario: int     # reference year (e.g. 2025)

    # ── IRPF Classification ───────────────────────────────────────────────────
    secao: str              # "Bens e Direitos", "Rendimentos Isentos",
                            # "Rendimentos Tributação Exclusiva",
                            # "Rendimentos Tributáveis PJ", "Contribuições"
    grupo: str              # Grupo number, e.g. "04" (empty for Rendimentos)
    grupo_desc: str         # Grupo description
    codigo: str             # Código number, e.g. "02"
    codigo_desc: str        # Código description

    # ── Fonte Pagadora ────────────────────────────────────────────────────────
    fonte_pagadora: str = ""
    cnpj_fonte: str = ""
    localizacao: str = "105 - Brasil"
    discriminacao: str = ""

    # ── Values ────────────────────────────────────────────────────────────────
    valor_2024: float = 0.0     # Situação em 31/12/2024
    valor_2025: float = 0.0     # Situação em 31/12/2025
    rendimento: float = 0.0     # Rendimento / Income earned
    tipo_rendimento: str = ""   # "Isento", "Tributação Exclusiva", "Tributável"
    irrf: float = 0.0           # IR Retido na Fonte
    observacao: str = ""
