"""
Generate interactive HTML dashboard from Income Statement Processor data.

This script creates a bootstrap-based dashboard with charts and tables
from either real XLSX data or mock test data, with light/dark mode support.
"""

import json
import re
import tomllib
import unicodedata
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from src import __version__
from src.models import Entry


def load_dashboard_config() -> dict:
    """Load dashboard configuration from config.toml."""
    config_path = Path('config.toml')
    if config_path.exists():
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
            return config.get('dashboard', {})
    return {}


def truncate_label(label: str, config: dict) -> str:
    """
    Truncate label based on configuration.
    
    Args:
        label: Original label text
        config: Dashboard configuration dictionary
        
    Returns:
        Truncated label
    """
    mode = config.get('label_truncation_mode', 'separator')
    value = config.get('label_truncation_value', 'LTDA')
    add_ellipsis = config.get('label_add_ellipsis', True)
    
    truncated = label
    
    if mode == 'max_length':
        # Truncate by maximum length
        max_len = int(value) if isinstance(value, (int, str)) else 30
        if len(label) > max_len:
            truncated = label[:max_len]
    elif mode == 'separator':
        # Truncate at separator
        if value in label:
            truncated = label[:label.index(value) + len(value)].strip()
    
    # Add ellipsis if truncated and configured
    if add_ellipsis and truncated != label:
        truncated += '...'
    
    return truncated


def format_currency(value: float) -> str:
    """Format value as Brazilian currency."""
    return f"R$ {value:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')


def _normalize_asset_text(value: str | None) -> str:
    """Normalize text for broker-specific asset categorization heuristics."""
    if not value:
        return ''
    normalized = unicodedata.normalize('NFKD', value)
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_only.upper().strip()


def _contains_token(text: str, token: str) -> bool:
    """Return True when token appears as a standalone instrument marker."""
    pattern = rf'(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])'
    return re.search(pattern, text) is not None


def _infer_fixed_income_subtype(descricao: str | None, discriminacao: str | None) -> str | None:
    """Return a specific fixed-income label when the instrument is identifiable.

    Strategy: discriminacao is the per-asset label (e.g. "CDB BANCO MASTER",
    "DEB CEMIG", "IPCA") and takes full priority.  descricao is the generic
    IRPF section name (e.g. "Títulos públicos e privados sujeitos à tributação
    (Tesouro Direto, CDB, RDB e Outros)") and must NEVER override what the
    discriminacao says – otherwise every entry under Nubank's code 04/02 ends
    up as "Tesouro Direto".
    """
    disc = _normalize_asset_text(discriminacao)
    desc = _normalize_asset_text(descricao)

    # ── Phase 1: match specific private instruments in discriminacao only ──
    if disc:
        if _contains_token(disc, 'CDB'):
            return 'CDB – Certificado de Depósito Bancário'
        if _contains_token(disc, 'RDB'):
            return 'RDB – Recibo de Depósito Bancário'
        if _contains_token(disc, 'LCI'):
            return 'LCI – Letra de Crédito Imobiliário'
        if _contains_token(disc, 'LCA'):
            return 'LCA – Letra de Crédito do Agronegócio'
        if _contains_token(disc, 'CRI'):
            return 'CRI – Certificado de Recebíveis Imobiliários'
        if _contains_token(disc, 'CRA'):
            return 'CRA – Certificado de Recebíveis do Agronegócio'
        if _contains_token(disc, 'LCD'):
            return 'LCD – Letra de Câmbio'
        if _contains_token(disc, 'LIG'):
            return 'LIG – Letra Imobiliária Garantida'
        if re.search(r'(?<![A-Z0-9])DEB(?:ENTURE|ENTURES)?(?![A-Z0-9])', disc):
            return 'Debêntures de Infraestrutura'

    # ── Phase 2: Tesouro Direto — check discriminacao first, fall back to
    #    descricao only when discriminacao is absent/blank (Nubank omits it).
    # Tesouro shorthand tickers that some brokers put in discriminacao:
    #   IPCA, SELIC, PREFIXADO, NTN-B, NTN-F, LFT, LTN
    _TESOURO_KEYWORDS = ('TESOURO', 'SELIC', 'LFT', 'NTN', 'LTN', 'PREFIXADO')
    _is_tesouro_disc = disc and (
        'TESOURO' in disc
        or any(kw in disc for kw in ('SELIC', 'LFT', 'LTN', 'PREFIXADO'))
        or re.search(r'\bNTN[-\s]?[BF]?\b', disc)
        or (disc == 'IPCA')  # Nubank uses bare "IPCA" for NTN-B
    )
    _is_tesouro_desc = not disc and 'TESOURO' in desc

    if _is_tesouro_disc or _is_tesouro_desc:
        src = disc if _is_tesouro_disc else desc
        if 'SELIC' in src or 'LFT' in src:
            return 'Tesouro Selic'
        if 'IPCA' in src or 'NTN-B' in src or 'NTNB' in src:
            return 'Tesouro IPCA+'
        if 'PREFIXADO' in src or 'LTN' in src or 'NTN-F' in src or 'NTNF' in src:
            return 'Tesouro Prefixado'
        return 'Tesouro Direto'

    return None


def _extract_ticker(text: str) -> str:
    """Extract a likely ticker from the beginning of an asset label."""
    match = re.match(r'^([A-Z0-9]{2,8})\b', text)
    return match.group(1) if match else ''


def infer_asset_category(entry: Entry) -> str:
    """Infer the dashboard grouping label for an asset row."""
    grupo = (entry.grupo or '').strip()
    codigo = (entry.codigo or '').strip()
    descricao = _normalize_asset_text(entry.codigo_desc)
    discriminacao = _normalize_asset_text(entry.discriminacao)
    grupo_desc = _normalize_asset_text(entry.grupo_desc)
    observacao = _normalize_asset_text(entry.observacao)
    instituicao = _normalize_asset_text(entry.instituicao)
    merged_text = ' '.join(part for part in [descricao, discriminacao, grupo_desc, observacao] if part)
    ticker = _extract_ticker(discriminacao or descricao)

    subtype = _infer_fixed_income_subtype(entry.codigo_desc, entry.discriminacao)
    if subtype:
        return subtype

    if grupo == '04' and codigo in {'02', '03'}:
        return 'Renda Fixa'

    if 'BDR' in merged_text:
        return 'BDRs'

    etf_issuers = (
        'ISHARES', 'INVESCO', 'VANGUARD', 'SPDR', 'SCHWAB', 'PROSHARES',
        'GLOBAL X', 'FIRST TRUST', 'VANECK', 'WISDOMTREE', 'DIREXION', 'ARK '
    )
    if (
        grupo == '07' and codigo in {'03', '08'}
        or 'ETF' in merged_text
        or any(issuer in merged_text for issuer in etf_issuers)
    ):
        return 'ETFs'

    if (
        'FII' in merged_text
        or 'FUNDO IMOBILI' in merged_text
        or 'FUNDOS IMOBILIARI' in merged_text
        or (grupo == '07' and codigo == '02')
        or (grupo == '07' and codigo == '99' and ticker.endswith('11'))
    ):
        return 'FIIs'

    if grupo == '07' or 'FUNDO' in merged_text or 'MULTIMERCADO' in merged_text:
        return 'Fundos'

    if 'VGBL' in merged_text or 'PGBL' in merged_text or grupo == '31':
        return 'Previdência'

    if (
        'ACAO' in merged_text
        or 'ACOES' in merged_text
        or 'STOCK' in merged_text
        or ((grupo in {'03', '04'} and codigo == '01') and not instituicao.startswith('INTER'))
        or (instituicao.startswith('AVENUE') and grupo == '03' and codigo == '01')
    ):
        return 'Ações'

    return entry.codigo_desc or 'Outros ativos'


def generate_dashboard_html(entries: list, output_path: str = 'dashboard.html') -> None:
    """
    Generate interactive dashboard from entries with dark mode support.
    
    Args:
        entries: List of Entry objects
        output_path: Path to write HTML dashboard
    """
    
    # Load dashboard configuration
    dashboard_config = load_dashboard_config()
    
    # Prepare data for JSON embedding
    data_json = []
    for entry in entries:
        data_json.append({
            'arquivo': Path(entry.arquivo).name[:40],
            'instituicao': entry.instituicao,
            'secao': entry.secao,
            'grupo': entry.grupo,
            'codigo': entry.codigo,
            'descricao': entry.codigo_desc,
            'discriminacao': entry.discriminacao,
            'assetCategory': infer_asset_category(entry),
            'fixedIncomeSubtype': _infer_fixed_income_subtype(entry.codigo_desc, entry.discriminacao),
            'v2024': entry.valor_2024,
            'v2025': entry.valor_2025,
            'rendimento': entry.rendimento,
            'irrf': entry.irrf
        })
    
    # Generate timestamp
    generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')

    # Extract taxpayer information (should be the same for all entries)
    nome_contribuinte = ""
    cpf_contribuinte = ""
    for entry in entries:
        if entry.nome_contribuinte or entry.cpf_contribuinte:
            nome_contribuinte = entry.nome_contribuinte or ""
            cpf_contribuinte = entry.cpf_contribuinte or ""
            break

    # Calculate metrics
    total_2024 = sum(e.valor_2024 for e in entries)
    total_2025 = sum(e.valor_2025 for e in entries)
    total_rendimento = sum(e.rendimento for e in entries)
    total_irrf = sum(e.irrf for e in entries)
    
    # Render HTML via Jinja2 template
    _template_dir = Path(__file__).parent / 'templates'
    _env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=False)
    _tmpl = _env.get_template('dashboard.html')
    html_content = _tmpl.render(
        version=__version__,
        generated_at=generated_at,
        nome_contribuinte=nome_contribuinte,
        cpf_contribuinte=cpf_contribuinte,
        total_2024_fmt=format_currency(total_2024),
        total_2025_fmt=format_currency(total_2025),
        total_rendimento_fmt=format_currency(total_rendimento),
        entry_count=len(entries),
        data_json=json.dumps(data_json),
        dashboard_config_json=json.dumps(dashboard_config),
        chart_label_rotation=dashboard_config.get('chart_label_rotation', 45),
    )
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'  Dashboard gerado em: {output_path} (com Dark Mode 🌙)')
