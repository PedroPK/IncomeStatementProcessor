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
    
    # Generate HTML
    html_content = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Income Statement Processor - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --bg-light: #f8f9fa;
            --bg-light-card: #ffffff;
            --text-light: #333333;
            --text-muted: #999999;
            --border-light: #e9ecef;
            --table-header-light: #f0f0f0;
        }}
        
        html.dark-mode {{
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --bg-light: #1a1a1a;
            --bg-light-card: #2d2d2d;
            --text-light: #e0e0e0;
            --text-muted: #999999;
            --border-light: #3d3d3d;
            --table-header-light: #3d3d3d;
        }}
        
        * {{
            transition: background-color 0.3s, color 0.3s;
        }}
        
        body {{
            background-color: var(--bg-light);
            color: var(--text-light);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .navbar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            background-color: #667eea !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .navbar-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            padding: 0 15px;
        }}
        
        .navbar-title {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .theme-toggle {{
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.3);
            box-shadow: 0 0 10px rgba(255,255,255,0.2);
        }}
        
        .card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            background-color: var(--bg-light-card);
            color: var(--text-light);
            border: 1px solid var(--border-light);
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}
        
        .metric-card {{
            border-left: 4px solid var(--primary-color);
            padding: 20px;
        }}
        
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: var(--primary-color);
        }}
        
        .metric-label {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-top: 5px;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .nav-tabs .nav-link {{
            color: var(--text-muted);
            border: none;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
        }}
        
        .nav-tabs .nav-link.active {{
            color: var(--primary-color);
            background-color: transparent;
            border-bottom: 2px solid var(--primary-color);
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        
        #chartInstitution {{
            min-height: 350px !important;
        }}
        
        table {{
            font-size: 13px;
            background-color: var(--bg-light-card);
            color: var(--text-light);
        }}
        
        thead {{
            background-color: var(--table-header-light) !important;
            font-weight: 600;
            color: var(--text-light) !important;
            border-color: var(--border-light) !important;
        }}
        
        tbody tr {{
            background-color: var(--bg-light-card) !important;
            color: var(--text-light) !important;
            border-color: var(--border-light) !important;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: var(--bg-light-card) !important;
        }}
        
        html.dark-mode tbody tr {{
            background-color: #2d2d2d !important;
        }}
        
        html.dark-mode tbody tr:nth-child(even) {{
            background-color: #353535 !important;
        }}
        
        tbody tr:hover {{
            background-color: var(--border-light) !important;
            cursor: pointer;
        }}
        
        tbody td {{
            border-color: var(--border-light) !important;
            color: var(--text-light) !important;
        }}
        
        table.table-striped tbody tr:nth-child(odd) td {{
            background-color: var(--bg-light-card) !important;
        }}
        
        table.table-striped tbody tr:nth-child(even) td {{
            background-color: var(--bg-light-card) !important;
        }}
        
        html.dark-mode table.table-striped tbody tr:nth-child(odd) td {{
            background-color: #2d2d2d !important;
        }}
        
        html.dark-mode table.table-striped tbody tr:nth-child(even) td {{
            background-color: #353535 !important;
        }}
        
        .currency {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}

        /* ── Dados Brutos: sortable headers ──────────────────────────────── */
        #dados-brutos th.sortable {{
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        #dados-brutos th.sortable:hover {{
            background-color: var(--primary-color) !important;
            color: white !important;
        }}
        #dados-brutos th.sortable .sort-icon {{
            display: inline-block;
            margin-left: 4px;
            opacity: 0.35;
            font-size: 0.72em;
        }}
        #dados-brutos th.sortable.asc .sort-icon,
        #dados-brutos th.sortable.desc .sort-icon {{
            opacity: 1;
        }}
        /* ── Dados Brutos: filter row ──────────────────────────────────────── */
        #dados-brutos thead tr.filter-row th {{
            padding: 3px 6px;
            background: inherit;
        }}
        #dados-brutos thead tr.filter-row input {{
            width: 100%;
            padding: 3px 6px;
            font-size: 0.78em;
            border: 1px solid var(--border-light);
            border-radius: 4px;
            background: var(--bg-light);
            color: var(--text-light);
            box-sizing: border-box;
        }}
        html.dark-mode #dados-brutos thead tr.filter-row input {{
            background: #2a2a2a;
            border-color: #555;
            color: #ddd;
        }}
        #dados-brutos .brutos-no-results {{
            text-align: center;
            padding: 20px;
            font-style: italic;
            color: #999;
        }}
        #table-brutos tfoot tr.subtotal-row {{
            font-weight: bold;
            background-color: rgba(102, 126, 234, 0.15);
            border-top: 2px solid var(--primary-color);
        }}
        #table-brutos tfoot tr.subtotal-row td {{
            padding: 6px 8px;
            color: var(--text-light);
        }}
        html.dark-mode #table-brutos tfoot tr.subtotal-row {{
            background-color: rgba(102, 126, 234, 0.30);
        }}
        html.dark-mode #table-brutos tfoot tr.subtotal-row td {{
            color: #d0d8ff;
        }}
        #table-brutos tfoot tr.subtotal-row td.subtotal-label {{
            font-style: italic;
            opacity: 0.85;
        }}

        .irpf-asset-group {{
            border: 1px solid var(--border-light);
            border-radius: 8px;
            background: var(--bg-light-card);
            margin-bottom: 12px;
            overflow: hidden;
        }}

        .irpf-asset-group summary {{
            list-style: none;
            cursor: pointer;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            background: rgba(102, 126, 234, 0.08);
        }}

        .irpf-asset-group summary::-webkit-details-marker {{
            display: none;
        }}

        .irpf-asset-group summary::after {{
            content: '▾';
            font-size: 0.9rem;
            color: var(--primary-color);
        }}

        .irpf-asset-group[open] summary::after {{
            content: '▴';
        }}

        .irpf-asset-group-title {{
            font-weight: 600;
            color: var(--text-light);
        }}

        .irpf-asset-group-meta {{
            display: flex;
            gap: 14px;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            white-space: nowrap;
        }}

        .irpf-asset-group table {{
            margin-bottom: 0;
        }}

        .irpf-section-subtotal {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 5px;
            margin-bottom: 15px;
            font-weight: bold;
            padding: 10px;
            background-color: var(--bg-light-card);
            border: 1px solid var(--border-light);
            border-top: 2px solid var(--primary-color);
        }}

        /* Institution-level accordion */
        .irpf-institution-group {{
            border: 2px solid var(--primary-color);
            border-radius: 10px;
            margin-top: 20px;
            margin-bottom: 8px;
            overflow: hidden;
        }}

        .irpf-institution-group > summary {{
            list-style: none;
            cursor: pointer;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
            background: rgba(102, 126, 234, 0.18);
            border-bottom: 2px solid var(--primary-color);
        }}

        .irpf-institution-group > summary::-webkit-details-marker {{
            display: none;
        }}

        .irpf-institution-group > summary::after {{
            content: '▾';
            font-size: 1rem;
            color: var(--primary-color);
        }}

        .irpf-institution-group[open] > summary::after {{
            content: '▴';
        }}

        .irpf-institution-name {{
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--primary-color);
            letter-spacing: 0.04em;
        }}

        .irpf-institution-meta {{
            display: flex;
            gap: 16px;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            white-space: nowrap;
        }}

        .irpf-institution-body {{
            padding: 12px 16px 4px 16px;
        }}

        /* Section-level accordion */
        .irpf-section-group {{
            border: 1px solid var(--border-light);
            border-left: 3px solid var(--secondary-color);
            border-radius: 6px;
            margin-top: 10px;
            margin-bottom: 6px;
            overflow: hidden;
        }}

        .irpf-section-group > summary {{
            list-style: none;
            cursor: pointer;
            padding: 10px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            background: rgba(118, 75, 162, 0.07);
        }}

        .irpf-section-group > summary::-webkit-details-marker {{
            display: none;
        }}

        .irpf-section-group > summary::after {{
            content: '▾';
            font-size: 0.85rem;
            color: var(--secondary-color);
        }}

        .irpf-section-group[open] > summary::after {{
            content: '▴';
        }}

        .irpf-section-name {{
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--secondary-color);
        }}

        .irpf-section-meta {{
            display: flex;
            gap: 14px;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.82rem;
            white-space: nowrap;
        }}

        .irpf-section-body {{
            padding: 8px 10px 4px 10px;
        }}

        @media (max-width: 768px) {{
            .irpf-asset-group summary,
            .irpf-institution-group > summary,
            .irpf-section-group > summary {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .irpf-asset-group-meta,
            .irpf-institution-meta,
            .irpf-section-meta {{
                white-space: normal;
                flex-wrap: wrap;
            }}
        }}
        
        .section-header {{
            background-color: var(--primary-color);
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin-top: 15px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .total-row {{
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
        }}
        
        .navbar-brand {{
            color: white !important;
            font-weight: bold;
            margin: 0;
        }}
        
        .navbar-text {{
            color: rgba(255,255,255,0.8) !important;
            margin: 0;
        }}
        
        .generated-at {{
            font-size: 0.82rem;
            text-align: right;
            color: #666666;
        }}
        
        html.dark-mode .generated-at {{
            color: #aaaaaa;
        }}
        
        .container-fluid {{
            background-color: var(--bg-light);
        }}
        
        footer {{
            color: var(--text-muted);
            border-top: 1px solid var(--border-light);
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.2); padding: 12px 0 6px 0; margin-bottom: 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; padding: 0 20px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="color:#ffffff; font-weight:bold; font-size:1.5rem;">📊 Income Statement Processor</span>
                <span style="color:rgba(255,255,255,0.85); font-size:1rem;">Dashboard - IRPF 2026</span>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">
                <span id="theme-icon">🌙 Dark Mode</span>
            </button>
        </div>
        <div style="text-align:right; padding: 4px 20px 0 20px;">
            <span style="font-size:0.78rem; color:rgba(255,255,255,0.75);">Gerado em {generated_at}</span>
        </div>
    </div>

    <div class="container-fluid mt-2">

        <!-- Taxpayer Information Card -->
        {f'''
        <div class="row mb-4">
            <div class="col-12">
                <div class="card p-3" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-left: 4px solid #667eea;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h5 style="margin: 0; color: var(--primary-color); font-weight: 600;">
                                👤 Contribuinte
                            </h5>
                            <div style="margin-top: 12px; display: flex; gap: 30px;">
                                <div>
                                    <p style="margin: 0; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase;">Nome</p>
                                    <p style="margin: 5px 0 0 0; font-size: 1rem; font-weight: 500; color: var(--text-light);">
                                        {nome_contribuinte or "Não informado"}
                                    </p>
                                </div>
                                <div>
                                    <p style="margin: 0; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase;">CPF</p>
                                    <p style="margin: 5px 0 0 0; font-size: 1rem; font-weight: 500; color: var(--text-light); font-family: 'Courier New', monospace;">
                                        {cpf_contribuinte or "Não informado"}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div style="text-align: right; padding-right: 10px;">
                            <div style="font-size: 3rem; opacity: 0.3;">📋</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        ''' if nome_contribuinte or cpf_contribuinte else ''}

        <!-- Key Metrics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_2024)}</div>
                    <div class="metric-label">Total 2024</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_2025)}</div>
                    <div class="metric-label">Total 2025</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_rendimento)}</div>
                    <div class="metric-label">Rendimentos</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{len(entries)}</div>
                    <div class="metric-label">Entradas Processadas</div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="card-title">Distribuição por Instituição (2025)</h6>
                    <div class="chart-container">
                        <canvas id="chartInstitution"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="card-title">Evolução 2024 → 2025</h6>
                    <div class="chart-container">
                        <canvas id="chartEvolution"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabs Section -->
        <div class="card">
            <div class="card-body">
                <!-- Tab Navigation -->
                <ul class="nav nav-tabs mb-3" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active" href="#" onclick="switchTab('dados-brutos', event)">📋 Dados Brutos</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('resumo', event)">📈 Resumo</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('totais', event)">💰 Totais</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('para-irpf', event)">📝 Para IRPF</a>
                    </li>
                </ul>

                <!-- Tab 1: Dados Brutos -->
                <div id="dados-brutos" class="tab-content active">
                    <div class="table-responsive">
                        <table class="table table-striped table-hover" id="table-brutos">
                            <thead>
                                <tr>
                                    <th class="sortable" data-col="arquivo">Arquivo <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="instituicao">Instituição <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="secao">Seção <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="grupo">Grupo <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="codigo">Código <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="descricao">Descrição <span class="sort-icon">↕</span></th>
                                    <th class="sortable" data-col="discriminacao">Título <span class="sort-icon">↕</span></th>
                                    <th class="sortable currency" data-col="v2024">2024 <span class="sort-icon">↕</span></th>
                                    <th class="sortable currency" data-col="v2025">2025 <span class="sort-icon">↕</span></th>
                                    <th class="sortable currency" data-col="rendimento">Rendimento <span class="sort-icon">↕</span></th>
                                </tr>
                                <tr class="filter-row">
                                    <th><input type="text" data-col="arquivo" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="instituicao" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="secao" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="grupo" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="codigo" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="descricao" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="discriminacao" placeholder="filtrar…"></th>
                                    <th><input type="text" data-col="v2024" placeholder="ex: >1000"></th>
                                    <th><input type="text" data-col="v2025" placeholder="ex: >1000"></th>
                                    <th><input type="text" data-col="rendimento" placeholder="ex: >0"></th>
                                </tr>
                            </thead>
                            <tbody id="tbody-brutos"></tbody>
                            <tfoot id="tfoot-brutos"></tfoot>
                        </table>
                    </div>
                </div>

                <!-- Tab 2: Resumo -->
                <div id="resumo" class="tab-content">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Seção</th>
                                    <th>Instituição</th>
                                    <th class="currency">Valor 2024</th>
                                    <th class="currency">Valor 2025</th>
                                    <th class="currency">Rendimento</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-resumo"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Tab 3: Totais -->
                <div id="totais" class="tab-content">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Grupo</th>
                                    <th>Código</th>
                                    <th>Descrição</th>
                                    <th class="currency">2024</th>
                                    <th class="currency">2025</th>
                                    <th class="currency">Rendimento</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-totais"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Tab 4: Para IRPF -->
                <div id="para-irpf" class="tab-content">
                    <div id="irpf-content"></div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="text-center mt-5 mb-3">
            <small>
                Income Statement Processor v1.1.0 | 
                Gerado em 2026-05-02 | 
                Com suporte a Dark Mode 🌙
            </small>
        </footer>
    </div>

    <script>
        // Data embedded in HTML
        const mockData = {json.dumps(data_json)};
        const dashboardConfig = {json.dumps(dashboard_config)};

        // Utility function to truncate labels based on configuration
        function truncateLabel(label, config) {{
            const mode = config.label_truncation_mode || 'separator';
            const value = config.label_truncation_value || 'LTDA';
            const addEllipsis = config.label_add_ellipsis !== false;
            
            let truncated = label;
            
            if (mode === 'max_length') {{
                const maxLen = parseInt(value) || 30;
                if (label.length > maxLen) {{
                    truncated = label.substring(0, maxLen);
                }}
            }} else if (mode === 'separator') {{
                const idx = label.indexOf(value);
                if (idx !== -1) {{
                    truncated = label.substring(0, idx + value.length).trim();
                }}
            }}
            
            if (addEllipsis && truncated !== label) {{
                truncated += '...';
            }}
            
            return truncated;
        }}

        // Theme Management
        window.appTheme = 'light'; // In-memory theme tracker for file:// URLs
        
        function initializeTheme() {{
            let savedTheme = 'light';
            try {{
                savedTheme = localStorage.getItem('dashboard-theme') || 'light';
            }} catch(e) {{
                console.log('localStorage not available, using in-memory theme');
            }}
            window.appTheme = savedTheme;
            if (savedTheme === 'dark') {{
                document.documentElement.classList.add('dark-mode');
                document.getElementById('theme-icon').textContent = '☀️ Light Mode';
            }}
        }}
        
        function toggleTheme() {{
            const html = document.documentElement;
            const isDark = html.classList.contains('dark-mode');
            
            if (isDark) {{
                html.classList.remove('dark-mode');
                window.appTheme = 'light';
                try {{
                    localStorage.setItem('dashboard-theme', 'light');
                }} catch(e) {{}}
                document.getElementById('theme-icon').textContent = '🌙 Dark Mode';
                updateCharts('light');
            }} else {{
                html.classList.add('dark-mode');
                window.appTheme = 'dark';
                try {{
                    localStorage.setItem('dashboard-theme', 'dark');
                }} catch(e) {{}}
                document.getElementById('theme-icon').textContent = '☀️ Light Mode';
                updateCharts('dark');
            }}
        }}

        // Format currency
        function formatCurrency(value) {{
            return new Intl.NumberFormat('pt-BR', {{
                style: 'currency',
                currency: 'BRL'
            }}).format(value);
        }}

        // Tab Switching
        function switchTab(tabName, event) {{
            event.preventDefault();
            
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Remove active from all links
            const links = document.querySelectorAll('.nav-link');
            links.forEach(link => link.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}

        // ── Dados Brutos: sorting + filtering ────────────────────────────────
        const _BRUTOS_COLS = ['arquivo','instituicao','secao','grupo','codigo','descricao','discriminacao','v2024','v2025','rendimento'];
        const _BRUTOS_NUMERIC = new Set(['v2024','v2025','rendimento']);
        let _brutosSort  = {{ col: null, dir: 1 }};   // dir: 1=asc, -1=desc
        let _brutosFilters = {{}};                       // col -> string

        function _parseNumericFilter(expr, value) {{
            // Supports: >500  >=500  <500  <=500  =500  500 (bare → >=)
            const m = expr.trim().match(/^([><=!]=?)?(-?[\\d.,]+)$/);
            if (!m) return true;    // invalid expr → don't filter
            const op  = m[1] || '>=';
            const ref = parseFloat(m[2].replace(/\\./g,'').replace(',','.'));
            if (isNaN(ref)) return true;
            switch (op) {{
                case '>':  return value >  ref;
                case '>=': return value >= ref;
                case '<':  return value <  ref;
                case '<=': return value <= ref;
                case '=':
                case '==': return value === ref;
                case '!=': return value !== ref;
            }}
            return true;
        }}

        function renderDadosBrutos() {{
            // 1. Filter
            let rows = mockData.filter(row => {{
                for (const col of _BRUTOS_COLS) {{
                    const f = (_brutosFilters[col] || '').trim();
                    if (!f) continue;
                    if (_BRUTOS_NUMERIC.has(col)) {{
                        if (!_parseNumericFilter(f, row[col] || 0)) return false;
                    }} else {{
                        const cell = (row[col] || '').toString().toLowerCase();
                        if (!cell.includes(f.toLowerCase())) return false;
                    }}
                }}
                return true;
            }});

            // 2. Sort
            if (_brutosSort.col) {{
                const col = _brutosSort.col;
                const dir = _brutosSort.dir;
                rows = [...rows].sort((a, b) => {{
                    const va = _BRUTOS_NUMERIC.has(col) ? (a[col] || 0) : (a[col] || '').toString().toLowerCase();
                    const vb = _BRUTOS_NUMERIC.has(col) ? (b[col] || 0) : (b[col] || '').toString().toLowerCase();
                    if (va < vb) return -dir;
                    if (va > vb) return  dir;
                    return 0;
                }});
            }}

            // 3. Render
            const tbody = document.getElementById('tbody-brutos');
            const tfoot = document.getElementById('tfoot-brutos');
            tbody.innerHTML = '';
            tfoot.innerHTML = '';
            if (rows.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="10" class="brutos-no-results">Nenhum resultado para os filtros aplicados.</td></tr>';
                return;
            }}
            let sub2024 = 0, sub2025 = 0, subRend = 0;
            rows.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.arquivo}}</td>
                    <td>${{row.instituicao}}</td>
                    <td>${{row.secao}}</td>
                    <td>${{row.grupo}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.descricao}}</td>
                    <td>${{row.discriminacao || '-'}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbody.appendChild(tr);
                sub2024 += row.v2024 || 0;
                sub2025 += row.v2025 || 0;
                subRend += row.rendimento || 0;
            }});
            const tfootTr = document.createElement('tr');
            tfootTr.className = 'subtotal-row';
            tfootTr.innerHTML = `
                <td colspan="7" class="subtotal-label">SubTotal (${{rows.length}} registro${{rows.length !== 1 ? 's' : ''}})</td>
                <td class="currency">${{formatCurrency(sub2024)}}</td>
                <td class="currency">${{formatCurrency(sub2025)}}</td>
                <td class="currency">${{formatCurrency(subRend)}}</td>
            `;
            tfoot.appendChild(tfootTr);
        }}

        function initDadosBrutosSortFilter() {{
            // Sort: header click
            document.querySelectorAll('#dados-brutos th.sortable').forEach(th => {{
                th.addEventListener('click', () => {{
                    const col = th.dataset.col;
                    if (_brutosSort.col === col) {{
                        _brutosSort.dir *= -1;
                    }} else {{
                        _brutosSort = {{ col, dir: 1 }};
                    }}
                    // Update header indicators
                    document.querySelectorAll('#dados-brutos th.sortable').forEach(h => {{
                        h.classList.remove('asc','desc');
                        h.querySelector('.sort-icon').textContent = '↕';
                    }});
                    th.classList.add(_brutosSort.dir === 1 ? 'asc' : 'desc');
                    th.querySelector('.sort-icon').textContent = _brutosSort.dir === 1 ? '↑' : '↓';
                    renderDadosBrutos();
                }});
            }});

            // Filter: input events
            document.querySelectorAll('#dados-brutos thead tr.filter-row input').forEach(input => {{
                input.addEventListener('input', () => {{
                    _brutosFilters[input.dataset.col] = input.value;
                    renderDadosBrutos();
                }});
            }});
        }}

        // Populate tabs
        function populateTabs() {{
            // Tab 1: Dados Brutos
            renderDadosBrutos();
            initDadosBrutosSortFilter();

            // Tab 2: Resumo
            const resumo = {{}};
            mockData.forEach(row => {{
                const key = row.secao + '|' + row.instituicao;
                if (!resumo[key]) {{
                    resumo[key] = {{
                        secao: row.secao,
                        instituicao: row.instituicao,
                        v2024: 0,
                        v2025: 0,
                        rendimento: 0
                    }};
                }}
                resumo[key].v2024 += row.v2024;
                resumo[key].v2025 += row.v2025;
                resumo[key].rendimento += row.rendimento;
            }});
            
            const tbodyResumo = document.getElementById('tbody-resumo');
            Object.values(resumo).forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.secao}}</td>
                    <td>${{row.instituicao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbodyResumo.appendChild(tr);
            }});

            // Tab 3: Totais
            const totais = {{}};
            mockData.forEach(row => {{
                const key = row.grupo + '|' + row.codigo;
                if (!totais[key]) {{
                    totais[key] = {{
                        grupo: row.grupo,
                        codigo: row.codigo,
                        descricao: row.descricao,
                        v2024: 0,
                        v2025: 0,
                        rendimento: 0
                    }};
                }}
                totais[key].v2024 += row.v2024;
                totais[key].v2025 += row.v2025;
                totais[key].rendimento += row.rendimento;
            }});
            
            const tbodyTotais = document.getElementById('tbody-totais');
            Object.values(totais).forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.grupo || '-'}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.descricao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbodyTotais.appendChild(tr);
            }});

            // Tab 4: Para IRPF
            gerarTabelasIRPF();
        }}

        // Chart Configuration based on theme
        let chartInstance1 = null;
        let chartInstance2 = null;

        function getChartColors(isDark) {{
            return {{
                text: isDark ? '#e0e0e0' : '#333333',
                grid: isDark ? '#3d3d3d' : '#e9ecef',
                primary: '#667eea',
                secondary: '#764ba2'
            }};
        }}

        function updateCharts(theme) {{
            const isDark = theme === 'dark';
            const colors = getChartColors(isDark);
            
            if (chartInstance1) {{
                chartInstance1.options.plugins.legend.labels.color = colors.text;
                chartInstance1.options.plugins.tooltip.bodyColor = colors.text;
                chartInstance1.update();
            }}
            
            if (chartInstance2) {{
                chartInstance2.options.scales.y.ticks.color = colors.text;
                chartInstance2.options.scales.x.ticks.color = colors.text;
                chartInstance2.options.scales.y.grid.color = colors.grid;
                chartInstance2.options.plugins.legend.labels.color = colors.text;
                chartInstance2.update();
            }}
        }}

        function createCharts() {{
            const isDark = document.documentElement.classList.contains('dark-mode');
            const colors = getChartColors(isDark);

            // Prepare data
            const institutions = {{}};
            mockData.forEach(row => {{
                if (!institutions[row.instituicao]) {{
                    institutions[row.instituicao] = 0;
                }}
                institutions[row.instituicao] += row.v2025;
            }});

            // Truncate institution labels
            const truncatedInstitutions = {{}};
            const institutionLabels = [];
            Object.keys(institutions).forEach(inst => {{
                const truncated = truncateLabel(inst, dashboardConfig);
                truncatedInstitutions[truncated] = institutions[inst];
                institutionLabels.push(truncated);
            }});

            // Chart 1: Institution Distribution
            const ctx1 = document.getElementById('chartInstitution').getContext('2d');
            chartInstance1 = new Chart(ctx1, {{
                type: 'doughnut',
                data: {{
                    labels: institutionLabels,
                    datasets: [{{
                        data: Object.values(truncatedInstitutions),
                        backgroundColor: [
                            '#667eea', '#764ba2', '#f093fb', '#4facfe',
                            '#43e97b', '#fa709a', '#30cfd0', '#a8edea'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ 
                                color: colors.text,
                                padding: 15,
                                font: {{ size: 12 }}
                            }}
                        }},
                        tooltip: {{
                            bodyColor: colors.text,
                            backgroundColor: isDark ? '#2d2d2d' : '#ffffff'
                        }}
                    }}
                }}
            }});

            // Chart 2: Evolution
            const ctx2 = document.getElementById('chartEvolution').getContext('2d');
            const evolution = {{}};
            mockData.forEach(row => {{
                if (!evolution[row.instituicao]) {{
                    evolution[row.instituicao] = {{ v2024: 0, v2025: 0 }};
                }}
                evolution[row.instituicao].v2024 += row.v2024;
                evolution[row.instituicao].v2025 += row.v2025;
            }});

            // Truncate evolution labels
            const truncatedEvolution = {{}};
            const evolutionLabels = [];
            Object.keys(evolution).forEach(inst => {{
                const truncated = truncateLabel(inst, dashboardConfig);
                truncatedEvolution[truncated] = evolution[inst];
                evolutionLabels.push(truncated);
            }});

            chartInstance2 = new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: evolutionLabels,
                    datasets: [
                        {{
                            label: '2024',
                            data: Object.values(truncatedEvolution).map(e => e.v2024),
                            backgroundColor: '#667eea'
                        }},
                        {{
                            label: '2025',
                            data: Object.values(truncatedEvolution).map(e => e.v2025),
                            backgroundColor: '#764ba2'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {{
                        y: {{
                            ticks: {{ color: colors.text }},
                            grid: {{ color: colors.grid }}
                        }},
                        x: {{
                            ticks: {{ 
                                color: colors.text,
                                maxRotation: {dashboard_config.get('chart_label_rotation', 45)},
                                minRotation: {dashboard_config.get('chart_label_rotation', 45)}
                            }},
                            grid: {{ color: colors.grid }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            labels: {{ color: colors.text }}
                        }},
                        tooltip: {{
                            bodyColor: colors.text,
                            backgroundColor: isDark ? '#2d2d2d' : '#ffffff'
                        }}
                    }}
                }}
            }});
        }}

        // Derive a display label for renda fixa assets from the discriminacao,
        // so that Tesouro Selic/Prefixado/IPCA+ and CDB/RDB appear as separate
        // lines in the IRPF tab instead of being merged under the same code.
        function hasToken(text, token) {{
            const pattern = new RegExp(`(^|[^A-Z0-9])${{token}}([^A-Z0-9]|$)`);
            return pattern.test(text);
        }}

        function irpfSubtypeFromDiscriminacao(d) {{
            if (d.includes('TESOURO')) {{
                if (d.includes('SELIC'))     return 'Tesouro Selic';
                if (d.includes('IPCA'))      return 'Tesouro IPCA+';
                if (d.includes('PREFIXADO')) return 'Tesouro Prefixado';
                return 'Tesouro Direto';
            }}
            if (hasToken(d, 'CDB')) return 'CDB \u2013 Certificado de Dep\u00f3sito Banc\u00e1rio';
            if (hasToken(d, 'RDB')) return 'RDB \u2013 Recibo de Dep\u00f3sito Banc\u00e1rio';
            if (hasToken(d, 'LCI')) return 'LCI \u2013 Letra de Cr\u00e9dito Imobili\u00e1rio';
            if (hasToken(d, 'LCA')) return 'LCA \u2013 Letra de Cr\u00e9dito do Agroneg\u00f3cio';
            if (hasToken(d, 'CRI')) return 'CRI \u2013 Certificado de Receb\u00edveis Imobili\u00e1rios';
            if (hasToken(d, 'CRA')) return 'CRA \u2013 Certificado de Receb\u00edveis do Agroneg\u00f3cio';
            if (hasToken(d, 'LCD')) return 'LCD \u2013 Letra de C\u00e2mbio';
            if (hasToken(d, 'LIG')) return 'LIG \u2013 Letra Imobili\u00e1ria Garantida';
            if (/(^|[^A-Z0-9])DEB(?:ENTURE|ENTURES)?([^A-Z0-9]|$)/.test(d)) return 'Deb\u00eantures de Infraestrutura';
            return null;
        }}

        function irpfDisplayLabel(r) {{
            if (r.fixedIncomeSubtype) return r.fixedIncomeSubtype;

            if (r.grupo === '04' && (r.codigo === '02' || r.codigo === '03')) {{
                const d = (r.discriminacao || '').toUpperCase();
                const subtype = irpfSubtypeFromDiscriminacao(d);
                if (subtype) return subtype;
            }}
            // XP and some brokers place CDBs under 07/08 (ETF RF) in their PDFs;
            // override the display label when the discriminacao reveals the true instrument.
            if (r.grupo === '07' && r.codigo === '08') {{
                const d = (r.discriminacao || '').toUpperCase();
                const subtype = irpfSubtypeFromDiscriminacao(d);
                if (subtype) return subtype;
            }}
            return r.descricao;
        }}

        function irpfAssetCategory(r) {{
            if (r.assetCategory) return r.assetCategory;

            const descricao = (r.descricao || '').toUpperCase();
            const discriminacao = (r.discriminacao || '').toUpperCase();
            const subtype = irpfSubtypeFromDiscriminacao(discriminacao);
            if (subtype) return subtype;

            if (descricao.includes('AÇÃO') || descricao.includes('ACOE') || discriminacao.includes(' AÇÃO') || discriminacao.includes(' ACOE')) {{
                return 'Ações';
            }}
            if (descricao.includes('FII') || descricao.includes('FUNDO IMOBILI') || /\\b[A-Z]{{4}}11\\b/.test(discriminacao)) {{
                return 'FIIs';
            }}
            if (descricao.includes('ETF') || discriminacao.includes('ETF')) {{
                return 'ETFs';
            }}
            if (descricao.includes('BDR') || discriminacao.includes('BDR')) {{
                return 'BDRs';
            }}
            if (descricao.includes('DEB') || discriminacao.includes('DEB')) {{
                return 'Debêntures';
            }}
            if (descricao.includes('FUNDO') || discriminacao.includes('FUNDO')) {{
                return 'Fundos';
            }}
            if (descricao.includes('TESOURO')) {{
                return 'Tesouro Direto';
            }}

            return r.descricao || 'Outros ativos';
        }}

        function createIrpfRowsTable(rows, footerLabel) {{
            const table = document.createElement('table');
            table.className = 'table table-sm table-striped';
            table.style.marginBottom = '15px';
            const totals = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};

            table.innerHTML = `
                <thead>
                    <tr style="background-color: var(--table-header-light);">
                        <th>Grupo</th>
                        <th>Código</th>
                        <th>Descrição</th>
                        <th class="currency">2024 (R$)</th>
                        <th class="currency">2025 (R$)</th>
                        <th class="currency">Rendimento (R$)</th>
                        <th class="currency">IRRF (R$)</th>
                    </tr>
                </thead>
                <tbody>
                    ${{rows.map(r => {{
                        totals.v2024 += r.v2024 || 0;
                        totals.v2025 += r.v2025 || 0;
                        totals.rendimento += r.rendimento || 0;
                        totals.irrf += r.irrf || 0;
                        const tickerMatch = r.discriminacao && r.discriminacao.match(/^([A-Z0-9]{{3,7}})\\s*[\u2013-]/);
                        const ticker = tickerMatch ? tickerMatch[1] : null;
                        const baseDesc = r.discriminacao || r.descricao;
                        const descDisplay = ticker ? `<strong>${{ticker}}</strong> — ${{baseDesc}}` : baseDesc;
                        return `
                            <tr>
                                <td>${{r.grupo || '-'}}</td>
                                <td>${{r.codigo}}</td>
                                <td>${{descDisplay}}</td>
                                <td class="currency">${{formatCurrency(r.v2024)}}</td>
                                <td class="currency">${{formatCurrency(r.v2025)}}</td>
                                <td class="currency">${{formatCurrency(r.rendimento)}}</td>
                                <td class="currency">${{formatCurrency(r.irrf)}}</td>
                            </tr>
                        `;
                    }}).join('')}}
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background-color: var(--bg-light-card); border-top: 2px solid var(--border-light);">
                        <td colspan="3">${{footerLabel}}</td>
                        <td class="currency">${{formatCurrency(totals.v2024)}}</td>
                        <td class="currency">${{formatCurrency(totals.v2025)}}</td>
                        <td class="currency">${{formatCurrency(totals.rendimento)}}</td>
                        <td class="currency">${{formatCurrency(totals.irrf)}}</td>
                    </tr>
                </tfoot>
            `;

            return {{ table, totals }};
        }}

        // Generate IRPF Tables grouped by Instituição (Broker)
        function gerarTabelasIRPF() {{
            const irpfContent = document.getElementById('irpf-content');
            
            // Group by Instituição, then by Seção
            const instituicoes = {{}};
            let totalGeral = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
            
            mockData.forEach(row => {{
                if (!instituicoes[row.instituicao]) {{
                    instituicoes[row.instituicao] = {{}};
                }}
                if (!instituicoes[row.instituicao][row.secao]) {{
                    instituicoes[row.instituicao][row.secao] = [];
                }}
                instituicoes[row.instituicao][row.secao].push(row);
                
                // Accumulate totals
                totalGeral.v2024 += row.v2024 || 0;
                totalGeral.v2025 += row.v2025 || 0;
                totalGeral.rendimento += row.rendimento || 0;
                totalGeral.irrf += row.irrf || 0;
            }});

            // Sort instituições alphabetically
            const sortedInstitucoes = Object.keys(instituicoes).sort();

            sortedInstitucoes.forEach(instituicao => {{
                const instData = instituicoes[instituicao];
                const sortedSecoes = Object.keys(instData).sort();

                // Pre-compute institution total from raw rows so the summary can
                // display it before the sections are rendered.
                let instTotal = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
                sortedSecoes.forEach(s => instData[s].forEach(r => {{
                    instTotal.v2024      += r.v2024      || 0;
                    instTotal.v2025      += r.v2025      || 0;
                    instTotal.rendimento += r.rendimento || 0;
                    instTotal.irrf       += r.irrf       || 0;
                }}));

                // Institution-level collapsible accordion
                const instDetails = document.createElement('details');
                instDetails.className = 'irpf-institution-group';
                instDetails.open = true;

                const instSummary = document.createElement('summary');
                instSummary.innerHTML = `
                    <span class="irpf-institution-name">${{instituicao.toUpperCase()}}</span>
                    <span class="irpf-institution-meta">
                        <span>${{sortedSecoes.length}} seção${{sortedSecoes.length !== 1 ? 'ões' : ''}}</span>
                        <span>2025: <strong>${{formatCurrency(instTotal.v2025)}}</strong></span>
                        <span>Rendimentos: <strong>${{formatCurrency(instTotal.rendimento)}}</strong></span>
                    </span>
                `;
                instDetails.appendChild(instSummary);

                const instBody = document.createElement('div');
                instBody.className = 'irpf-institution-body';
                instDetails.appendChild(instBody);
                irpfContent.appendChild(instDetails);

                // For each seção within this instituição
                sortedSecoes.forEach(secao => {{
                    const rawRows = instData[secao];

                    // Aggregate by (grupo, codigo, display_label). For renda fixa
                    // (04/02 and 04/03) the label is derived from discriminacao so
                    // Tesouro Selic/Prefixado/IPCA+ and CDB appear as separate lines.
                    const mergedRows = [];
                    const seenKey   = {{}};
                    rawRows.forEach(r => {{
                        const displayLabel = irpfDisplayLabel(r);
                        // Bens e Direitos: each asset must appear on its own IRPF line.
                        // Rendimentos sections are aggregated by type within institution/section.
                        const key = (secao === 'Bens e Direitos')
                            ? `${{r.grupo || ''}}|${{r.codigo}}|${{r.discriminacao || displayLabel}}`
                            : `${{r.grupo || ''}}|${{r.codigo}}|${{displayLabel}}`;
                        if (seenKey[key] !== undefined) {{
                            mergedRows[seenKey[key]].v2024      += r.v2024      || 0;
                            mergedRows[seenKey[key]].v2025      += r.v2025      || 0;
                            mergedRows[seenKey[key]].rendimento += r.rendimento || 0;
                            mergedRows[seenKey[key]].irrf       += r.irrf       || 0;
                        }} else {{
                            seenKey[key] = mergedRows.length;
                            const merged = Object.assign({{}}, r);
                            merged.descricao = displayLabel;
                            mergedRows.push(merged);
                        }}
                    }});
                    const secaoRows = mergedRows;

                    // Accumulate section total
                    const secaoTotal = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
                    secaoRows.forEach(r => {{
                        secaoTotal.v2024      += r.v2024      || 0;
                        secaoTotal.v2025      += r.v2025      || 0;
                        secaoTotal.rendimento += r.rendimento || 0;
                        secaoTotal.irrf       += r.irrf       || 0;
                    }});

                    // Section-level collapsible accordion
                    const secaoDetails = document.createElement('details');
                    secaoDetails.className = 'irpf-section-group';
                    secaoDetails.open = true;

                    const secaoSummary = document.createElement('summary');
                    secaoSummary.innerHTML = `
                        <span class="irpf-section-name">${{secao}}</span>
                        <span class="irpf-section-meta">
                            <span>${{secaoRows.length}} item${{secaoRows.length !== 1 ? 's' : ''}}</span>
                            <span>2025: <strong>${{formatCurrency(secaoTotal.v2025)}}</strong></span>
                            <span>Rendimentos: <strong>${{formatCurrency(secaoTotal.rendimento)}}</strong></span>
                        </span>
                    `;
                    secaoDetails.appendChild(secaoSummary);

                    const secaoBody = document.createElement('div');
                    secaoBody.className = 'irpf-section-body';
                    secaoDetails.appendChild(secaoBody);
                    instBody.appendChild(secaoDetails);

                    if (secao === 'Bens e Direitos') {{
                        const groupedRows = {{}};
                        secaoRows.forEach(r => {{
                            const category = irpfAssetCategory(r);
                            if (!groupedRows[category]) {{
                                groupedRows[category] = [];
                            }}
                            groupedRows[category].push(r);
                        }});

                        Object.keys(groupedRows).sort().forEach((category, index) => {{
                            const groupRows = groupedRows[category];
                            const details = document.createElement('details');
                            details.className = 'irpf-asset-group';
                            if (index === 0) {{
                                details.open = true;
                            }}

                            const summary = document.createElement('summary');
                            const groupTotal = groupRows.reduce((acc, row) => {{
                                acc.v2024 += row.v2024 || 0;
                                acc.v2025 += row.v2025 || 0;
                                acc.rendimento += row.rendimento || 0;
                                acc.irrf += row.irrf || 0;
                                return acc;
                            }}, {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }});
                            summary.innerHTML = `
                                <span class="irpf-asset-group-title">${{category}}</span>
                                <span class="irpf-asset-group-meta">
                                    <span>${{groupRows.length}} registro${{groupRows.length !== 1 ? 's' : ''}}</span>
                                    <span>Subtotal 2025: <strong>${{formatCurrency(groupTotal.v2025)}}</strong></span>
                                </span>
                            `;
                            details.appendChild(summary);

                            const groupTableResult = createIrpfRowsTable(groupRows, `SubTotal ${{category}}`);
                            details.appendChild(groupTableResult.table);
                            secaoBody.appendChild(details);
                        }});

                        const secaoSubtotalDiv = document.createElement('div');
                        secaoSubtotalDiv.className = 'irpf-section-subtotal';
                        secaoSubtotalDiv.innerHTML = `
                            <div style="grid-column: 1/4;">SubTotal ${{secao}}</div>
                            <div class="currency" style="textAlign: right;">${{formatCurrency(secaoTotal.v2024)}}</div>
                            <div class="currency" style="textAlign: right;">${{formatCurrency(secaoTotal.v2025)}}</div>
                            <div class="currency" style="textAlign: right;">${{formatCurrency(secaoTotal.rendimento)}}</div>
                            <div class="currency" style="textAlign: right;">${{formatCurrency(secaoTotal.irrf)}}</div>
                        `;
                        secaoBody.appendChild(secaoSubtotalDiv);
                    }} else {{
                        const tableResult = createIrpfRowsTable(secaoRows, `SubTotal ${{secao}}`);
                        secaoBody.appendChild(tableResult.table);
                    }}
                }});

                // Institution subtotal (inside the institution accordion body)
                const instSubtotalDiv = document.createElement('div');
                instSubtotalDiv.style.display = 'grid';
                instSubtotalDiv.style.gridTemplateColumns = 'repeat(7, 1fr)';
                instSubtotalDiv.style.gap = '5px';
                instSubtotalDiv.style.marginTop = '6px';
                instSubtotalDiv.style.marginBottom = '8px';
                instSubtotalDiv.style.fontWeight = 'bold';
                instSubtotalDiv.style.padding = '10px';
                instSubtotalDiv.style.backgroundColor = 'var(--bg-light-card)';
                instSubtotalDiv.style.border = '1px solid var(--border-light)';
                instSubtotalDiv.innerHTML = `
                    <div style="grid-column: 1/4;">Subtotal ${{instituicao}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.v2024)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.v2025)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.rendimento)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.irrf)}}</div>
                `;
                instBody.appendChild(instSubtotalDiv);
            }});
            
            // Grand Total
            const grandTotalDiv = document.createElement('div');
            grandTotalDiv.style.display = 'grid';
            grandTotalDiv.style.gridTemplateColumns = 'repeat(7, 1fr)';
            grandTotalDiv.style.gap = '5px';
            grandTotalDiv.style.marginTop = '30px';
            grandTotalDiv.style.fontWeight = 'bold';
            grandTotalDiv.style.fontSize = '16px';
            grandTotalDiv.style.padding = '10px';
            grandTotalDiv.style.backgroundColor = 'var(--primary-color)';
            grandTotalDiv.style.color = 'white';
            grandTotalDiv.style.border = '2px solid var(--secondary-color)';
            grandTotalDiv.innerHTML = `
                <div style="grid-column: 1/4;">TOTAL GERAL</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.v2024)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.v2025)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.rendimento)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.irrf)}}</div>
            `;
            irpfContent.appendChild(grandTotalDiv);
        }}

        // Initialize
        window.addEventListener('DOMContentLoaded', function() {{
            initializeTheme();
            populateTabs();
            createCharts();
        }});
    </script>
</body>
</html>
'''
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'  Dashboard gerado em: {output_path} (com Dark Mode 🌙)')
