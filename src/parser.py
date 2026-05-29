"""PDF parsers for each institution's informe de rendimentos format.

Each public function has the signature:
    parse_<institution>(filename, pages_text, pages_tables) -> list[Entry]

The module-level ``parse_file`` function detects the institution and
dispatches to the appropriate parser.
"""

from __future__ import annotations

import re
import pdfplumber
from pathlib import Path
from typing import Any

from src.models import Entry
from src.normalizer import parse_brl, find_cnpj, extract_taxpayer_info, clean, extract_year


# ── Institution detection ─────────────────────────────────────────────────────


# ── Institution detection ─────────────────────────────────────────────────────

def detect_institution(filename: str, first_page: str) -> str:
    fname = filename.lower()
    text = (first_page or '').lower()

    if 'accenture' in fname:
        return 'accenture'
    if 'clear' in fname or 'www.clear.com.br' in text:
        return 'clear'
    if 'nubank' in fname or 'nu bank' in fname:
        return 'nubank'
    if ('xp' in fname and 'prev' in fname) or 'previd' in fname:
        return 'xp_previdencia'
    if 'xp' in fname or 'xp investimentos' in text:
        return 'xp'
    if 'avenue' in fname:
        return 'avenue'
    if 'inter' in fname:
        return 'inter'
    if 'fachesf' in fname or 'chesf' in fname or 'fundacao chesf' in text:
        return 'fachesf'
    if 'inss' in fname or 'regime geral de previdencia' in text or 'frgps' in text:
        return 'inss'
    # Generic Receita Federal "Comprovante de Rendimentos" format
    # (used by pension funds and employers following the Ministry of Finance template)
    if 'comprovante de rendimentos' in text and (
        'razão social / nome' in text or 'razao social / nome' in text
    ):
        return 'comprovante_rendimentos'
    return 'unknown'


# ── Entry factory helper ──────────────────────────────────────────────────────

def _entry(filename: str, instituicao: str, cnpj_inst: str, ano: int,
           secao: str, grupo: str, grupo_desc: str,
           codigo: str, codigo_desc: str, 
           nome_contribuinte: str = "", cpf_contribuinte: str = "",
           **kwargs) -> Entry:
    return Entry(
        arquivo=filename,
        instituicao=instituicao,
        cnpj_instituicao=cnpj_inst,
        ano_calendario=ano,
        secao=secao,
        grupo=grupo.zfill(2) if grupo.isdigit() else grupo,
        grupo_desc=grupo_desc,
        codigo=codigo.zfill(2) if codigo.isdigit() else codigo,
        codigo_desc=codigo_desc,
        nome_contribuinte=nome_contribuinte,
        cpf_contribuinte=cpf_contribuinte,
        **kwargs,
    )


# ── Public dispatcher ─────────────────────────────────────────────────────────

def parse_file(filepath: str) -> list[Entry]:
    """Parse a single file (PDF or PDF-with-other-extension) into Entries."""
    filename = Path(filepath).name

    with pdfplumber.open(filepath) as pdf:
        pages_text = [p.extract_text() or '' for p in pdf.pages]
        pages_tables = [p.extract_tables() or [] for p in pdf.pages]

    full_text = '\n'.join(pages_text)
    
    # Extract taxpayer information once from the document
    nome_contribuinte, cpf_contribuinte = extract_taxpayer_info(full_text)

    institution = detect_institution(filename, pages_text[0] if pages_text else '')

    parsers = {
        'accenture': parse_accenture,
        'nubank': parse_nubank,
        'xp_previdencia': parse_xp_previdencia,
        'xp': parse_xp,
        'avenue': parse_avenue,
        'inter': parse_inter,
        'clear': parse_clear,
        'fachesf': parse_fachesf,
        'inss': parse_inss,
        'comprovante_rendimentos': parse_comprovante_rendimentos,
    }

    parser_fn = parsers.get(institution)
    if parser_fn is None:
        return [Entry(
            arquivo=filename, instituicao=filename,
            cnpj_instituicao='', ano_calendario=0,
            secao='Desconhecido', grupo='', grupo_desc='',
            codigo='', codigo_desc='',
            nome_contribuinte=nome_contribuinte,
            cpf_contribuinte=cpf_contribuinte,
            observacao='Formato não reconhecido',
        )]

    try:
        entries = parser_fn(filename, pages_text, pages_tables)
        # Add taxpayer information to all entries from this document
        for entry in entries:
            entry.nome_contribuinte = nome_contribuinte
            entry.cpf_contribuinte = cpf_contribuinte
        return entries
    except Exception as exc:  # noqa: BLE001
        return [Entry(
            arquivo=filename, instituicao=institution,
            cnpj_instituicao='', ano_calendario=0,
            secao='Erro', grupo='', grupo_desc='',
            codigo='', codigo_desc='',
            nome_contribuinte=nome_contribuinte,
            cpf_contribuinte=cpf_contribuinte,
            observacao=f'Erro ao processar: {exc}',
        )]


# ─────────────────────────────────────────────────────────────────────────────
# ACCENTURE  (Comprovante de Rendimentos – empregador)
# ─────────────────────────────────────────────────────────────────────────────

def parse_accenture(filename: str, pages_text: list[str],
                    pages_tables: list[list]) -> list[Entry]:
    text = '\n'.join(pages_text)
    entries: list[Entry] = []

    # ── Institution / year ──────────────────────────────────────────────────
    cnpj_m = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+([^\n]+)', text)
    cnpj = cnpj_m.group(1) if cnpj_m else '96.534.094/0001-58'
    inst = clean(cnpj_m.group(2)) if cnpj_m else 'ACCENTURE DO BRASIL LTDA'
    ano = extract_year(text)

    def add(secao, grupo, gdesc, codigo, cdesc, **kw):
        entries.append(_entry(filename, inst, cnpj, ano,
                               secao, grupo, gdesc, codigo, cdesc, **kw))

    # Helper: extract the value at the end of a numbered line
    def _val(pattern: str) -> float:
        m = re.search(pattern + r'[^\n]*([\d.]+,\d{2})', text, re.IGNORECASE | re.DOTALL)
        return parse_brl(m.group(1)) if m else 0.0

    # ── Quadro 3: Rendimentos Tributáveis ──────────────────────────────────
    q3_sec = 'Rendimentos Tributáveis PJ'
    total_rend = _val(r'1\.\s+Total dos rendimentos')
    inss       = _val(r'2\.\s+Contribuição previdenciária oficial')
    prev_comp  = _val(r'3\.\s+Contribuição a entidades de previdência complementar')
    irrf_rend  = _val(r'5\.\s+Imposto sobre a Renda Retido na Fonte \(IRRF\)\s*\n')

    if total_rend:
        add(q3_sec, '', 'Trabalho Assalariado', '01', 'Total dos Rendimentos (incl. férias)',
            valor_2025=total_rend, tipo_rendimento='Tributável')
    if inss:
        add(q3_sec, '', 'Deduções', '02', 'Contribuição Previdenciária Oficial (INSS)',
            valor_2025=inss, tipo_rendimento='Dedução')
    if prev_comp:
        add(q3_sec, '', 'Deduções', '03', 'Contribuição Previdência Complementar',
            valor_2025=prev_comp, tipo_rendimento='Dedução')
    if irrf_rend:
        add(q3_sec, '', 'Imposto', '05', 'IR Retido na Fonte (IRRF)',
            valor_2025=irrf_rend, irrf=irrf_rend, tipo_rendimento='Tributável')

    # ── Quadro 4: Rendimentos Isentos ──────────────────────────────────────
    # (extract all non-zero items)
    q4_labels = [
        (r'1\.\s+Parcela isenta dos proventos de aposentadoria', '01', 'Parcela isenta aposentadoria (65+)'),
        (r'3\.\s+Diárias e ajudas de custo',                    '03', 'Diárias e ajudas de custo'),
        (r'7\.\s+Indenizações por rescisão de contrato',        '07', 'Indenizações por rescisão/PDV'),
        (r'9\.\s+Outros \(especificar\)',                       '09', 'Outros rendimentos isentos'),
    ]
    for pattern, cod, desc in q4_labels:
        v = _val(pattern)
        if v:
            add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
                cod, desc, rendimento=v, tipo_rendimento='Isento')

    # ── Quadro 5: Rendimentos Tributação Exclusiva ─────────────────────────
    dec13  = _val(r'1\.\s+13º \(décimo terceiro\) salário\s*\n')
    irrf13 = _val(r'2\.\s+Imposto sobre a Renda Retido na Fonte sobre 13º')

    # PLR – may appear on "3. Outros" block
    plr_m = re.search(r'OUTROS PLR\s+([\d.]+,\d{2})', text, re.IGNORECASE)
    outros_m = re.search(r'3\.\s+Outros[^\n]*\n([^\n]+)\n[^\n]*([\d.]+,\d{2})', text, re.IGNORECASE)
    plr = parse_brl(plr_m.group(1)) if plr_m else 0.0
    outros_desc = 'Outros (PLR)'
    if not plr and outros_m:
        plr = parse_brl(outros_m.group(2))
        outros_desc = clean(outros_m.group(1)) or 'Outros'

    if dec13:
        add('Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos – Empregador',
            '01', '13º Salário', rendimento=dec13,
            irrf=irrf13, tipo_rendimento='Tributação Exclusiva')
    if plr:
        add('Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos – Empregador',
            '11', outros_desc, rendimento=plr, tipo_rendimento='Tributação Exclusiva')

    # ── Quadro 7 / Informações Complementares: Previdência Complementar ────
    prev_cnpj_m = re.search(
        r'CNPJ\s*:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s*-\s*([^\n]+?)\s*\nBeneficiários.*?'
        r'([\d.]+,\d{2})',
        text, re.DOTALL | re.IGNORECASE)
    if prev_cnpj_m:
        add('Contribuições Previdenciárias', '', 'Pagamentos Efetuados',
            '36', f'Contrib. Previdência Complementar – {clean(prev_cnpj_m.group(2))}',
            valor_2025=parse_brl(prev_cnpj_m.group(3)),
            cnpj_fonte=prev_cnpj_m.group(1),
            tipo_rendimento='Dedução')

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# XP INVESTIMENTOS  (Informe padrão Ministério da Economia – tabelas)
# ─────────────────────────────────────────────────────────────────────────────

def parse_xp(filename: str, pages_text: list[str],
             pages_tables: list[list]) -> list[Entry]:
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)
    ano = extract_year(full_text)

    # Detect institutions and CNPJs present in the document
    cnpj_names: dict[str, str] = {}
    for m in re.finditer(
            r'(XP Investimentos CCTVM S/A|BANCO XP S\.?A\.?|XP INVESTIMENTOS CCTVM S/A)'
            r'(?:[^\n]*?CNPJ[:\s]+)?'
            r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
            full_text, re.IGNORECASE):
        cnpj_names[m.group(2)] = clean(m.group(1))

    if not cnpj_names:
        cnpj_names['02.332.886/0001-04'] = 'XP Investimentos CCTVM S/A'

    primary_inst = 'XP Investimentos'
    primary_cnpj = '02.332.886/0001-04'

    # Pages 1–2 are consolidated summaries; page 3 notes this explicitly.
    # All financial data is extracted exclusively from "Detalhamento dos Ativos"
    # (pages 4+). Contributor identification (nome/CPF) is captured by
    # extract_taxpayer_info() in parse_file(), so nothing is lost.

    # ── Pages 4–6 (index 3–5): Bens e Direitos detailed breakdown ───────────
    detail_tables: list[Any] = []
    for pi in range(3, min(6, len(pages_tables))):
        detail_tables.extend(pages_tables[pi])

    table_entries = _xp_parse_detail_tables(filename, detail_tables,
                                            primary_inst, primary_cnpj, ano, cnpj_names)
    entries += table_entries

    # XP PDFs use a 2-column layout on pages 4-5: pdfplumber's extract_tables()
    # only captures the LEFT column. The RIGHT column (same count of securities)
    # appears only in the page text. Supplement with any IDs not yet captured.
    seen_ids: set[str] = set()
    for e in table_entries:
        disc = e.discriminacao or ''
        # "CDB FLU CDB7244L9D5" → extract CDB7244L9D5
        for m in re.finditer(
            r'(?:CDB|LCA|LCI|LIG|LCD|CRI|CRA|RDB|DEB)\s+\S+\s+(\S+)', disc, re.IGNORECASE
        ):
            seen_ids.add(m.group(1))
        # single-token IDs like "LCA 24L03394025"
        for m in re.finditer(
            r'(?:LCA|LCI|LIG|LCD|CRI|CRA)\s+([A-Z0-9]{8,})', disc, re.IGNORECASE
        ):
            seen_ids.add(m.group(1))

    entries += _xp_supplement_text(
        filename, pages_text, primary_inst, primary_cnpj, ano, cnpj_names, seen_ids
    )

    # ── SALDO EM CONTA (Bens e Direitos – Grupo 06 / Código 99) ─────────────
    # This section appears on the summary page (page 1) AND on the detail page
    # (page 3 for 3-page Clear informes).  The detail page has the cleanest
    # format: "Saldo em conta - Institution  v24  v25" on a single line.
    # Extend search to pages[:3] to capture both Clear (3-page) and XP formats.
    summary_text = '\n'.join(pages_text[:min(3, len(pages_text))])
    saldo_idx = summary_text.upper().find('SALDO EM CONTA')
    if saldo_idx >= 0:
        saldo_block = summary_text[saldo_idx:]
        for row in _xp_summary_rows(saldo_block):
            desc, v24, v25, _rend = row
            if not desc or v24 + v25 == 0:
                continue
            f_cnpj = _detect_cnpj_in_block(saldo_block, cnpj_names) or primary_cnpj
            f_inst = cnpj_names.get(f_cnpj, primary_inst)
            entries.append(_entry(
                filename, f_inst, primary_cnpj, ano,
                'Bens e Direitos', '06', 'Depósito à Vista e Numerário', '99',
                'Outros depósitos à vista',
                fonte_pagadora=f_inst, cnpj_fonte=f_cnpj,
                discriminacao=desc,
                valor_2024=v24, valor_2025=v25,
                rendimento=0.0,
            ))

    return entries


def _xp_supplement_text(
    filename: str,
    pages_text: list[str],
    inst: str,
    cnpj: str,
    ano: int,
    cnpj_names: dict,
    seen_ids: set[str],
) -> list[Entry]:
    """
    XP PDFs render pages 4-5 in a 2-column grid; pdfplumber's table extractor
    only captures the LEFT column. This function scans the full page TEXT to
    find securities in the RIGHT column (identified by instrument-ID lines whose
    code is not yet in seen_ids) and returns the missing Entry objects.
    """
    # Combine text of detail pages (pages 4-5, indices 3-4)
    combined = '\n'.join(pages_text[3:min(5, len(pages_text))])
    lines = combined.split('\n')
    entries: list[Entry] = []

    # A "values line" ends with exactly 3 monetary amounts (val_2024, val_2025, rend)
    _val_re = re.compile(
        r'^(.+?)\s+([\d.]*\d,\d{2})\s+([\d.]*\d,\d{2})\s+([\d.]*\d,\d{2})\s*$'
    )
    # Instrument ID line: starts with an instrument type keyword
    _instr_re = re.compile(
        r'^(CDB|LCA|LCI|LIG|LCD|CRI|CRA|RDB|DEB(?:ENTURE|ÊNTURE)?)\s+',
        re.IGNORECASE,
    )
    # Lines that are clearly declaration / ficha metadata — skip as bank-name continuations
    _meta_markers = (
        'Declaração', 'IRPF', 'Ficha', 'CNPJ:', 'Grupo ', 'Cód.',
        'XP INVESTIMENTOS', 'Página ', 'ATENDIMENTO', 'AUTOATENDIMENTO',
        'OUVIDORIA', 'SAC:', 'AV.', 'DIAS ÚTEIS', 'GERADO EM', 'WWW.XPI',
        'Total:', 'Saldos em', 'TRIBUTAÇÃO', 'DETALHAMENTO',
    )

    # Lookup tables (duplicated locally to keep function self-contained)
    _grupo_descs: dict[str, str] = {
        '04': 'Aplicações e Investimentos',
        '06': 'Depósito à Vista e Numerário',
        '07': 'Fundos',
    }
    _codigo_descs: dict[tuple[str, str], str] = {
        ('04', '02'): 'Títulos públicos e privados sujeitos à tributação (CDB, RDB, Tesouro)',
        ('04', '03'): 'Títulos isentos de tributação (LCI, LCA, LCD, CRI, CRA, LIG, Debêntures de Infraestrutura e outros)',
        ('06', '99'): 'Outros depósitos à vista',
        ('07', '08'): 'Fundos de Índice de Renda Fixa (ETF RF)',
    }

    # Current section state: (secao, grupo, codigo)
    # Default = Sujeitos Renda Fixa; will be updated by section headers.
    section_state = ('Bens e Direitos', '04', '02')

    for li, raw_line in enumerate(lines):
        stripped = raw_line.strip()

        # ── Update section from headers ───────────────────────────────────────
        if 'RENDIMENTOS ISENTOS' in stripped:
            section_state = ('Rendimentos Isentos', '04', '03')
        elif 'RENDIMENTOS SUJEITOS' in stripped and 'ETF' not in stripped:
            section_state = ('Bens e Direitos', '04', '02')
        elif 'ETF de Renda Fixa' in stripped:
            section_state = ('Bens e Direitos', '07', '08')
        elif 'SALDO EM CONTA' in stripped:
            section_state = ('Bens e Direitos', '06', '99')

        # ── Only act on instrument ID lines ──────────────────────────────────
        if not _instr_re.match(stripped):
            continue

        tokens = stripped.split()
        # "CDB FLU ID" → tokens[2]; "LCA ID" → tokens[1]
        if len(tokens) >= 3:
            sec_id = tokens[2]
        elif len(tokens) == 2:
            sec_id = tokens[1]
        else:
            continue

        if sec_id in seen_ids:
            continue  # Already captured by table parser

        # ── Look backward for the values line (up to 12 lines back) ──────────
        bank_name: str | None = None
        val_line_idx: int = -1
        v24 = v25 = rend = 0.0

        for back in range(1, 13):
            if li - back < 0:
                break
            prev = lines[li - back].strip()
            vm = _val_re.match(prev)
            if vm:
                raw_bank = vm.group(1).strip()
                # Strip column-header prefix that pdfplumber sometimes prepends
                raw_bank = re.sub(r'^\s*\(Valores em Reais\)\s*', '', raw_bank).strip()
                if not raw_bank or raw_bank.lower().startswith('total'):
                    break  # Hit a totals/header line — no match
                bank_name = raw_bank
                val_line_idx = li - back
                v24 = parse_brl(vm.group(2))
                v25 = parse_brl(vm.group(3))
                rend = parse_brl(vm.group(4))
                break

        if bank_name is None:
            continue

        # Collect continuation lines between values line and ID line
        # (e.g., "CREDITO, F" after "FACTA FINANCEIRA S.A.") but skip metadata
        name_parts = [bank_name]
        for j in range(val_line_idx + 1, li):
            cont = lines[j].strip()
            if not cont:
                continue
            if any(marker in cont for marker in _meta_markers):
                continue
            if _instr_re.match(cont):
                break
            if re.match(r'^\d{2}/\d{2}/\d{4}$', cont):
                continue
            name_parts.append(cont)

        discriminacao = clean('\n'.join(name_parts) + '\n' + stripped)

        secao, grupo, codigo = section_state
        grupo_desc = _grupo_descs.get(grupo, 'Aplicações e Investimentos')
        codigo_desc = _codigo_descs.get((grupo, codigo), f'Código {codigo}')

        # Use the same resolved institution name as the table parser so that
        # left-column and right-column entries are grouped under one heading.
        resolved_inst = cnpj_names.get(cnpj, inst)

        entries.append(_entry(
            filename, resolved_inst, cnpj, ano,
            secao, grupo, grupo_desc, codigo, codigo_desc,
            fonte_pagadora=resolved_inst, cnpj_fonte=cnpj,
            discriminacao=discriminacao,
            valor_2024=v24, valor_2025=v25,
            rendimento=rend,
            tipo_rendimento='Tributação Exclusiva' if grupo in ('04', '07') else '',
        ))
        seen_ids.add(sec_id)

    return entries


def _xp_parse_page1(filename, text, inst, cnpj, ano, cnpj_names):
    """Parse the XP summary page for Rendimentos entries."""
    entries = []

    # Patterns like: "Declaração Cód. 12 XP Investimentos CCTVM S/A CNPJ 02.332.886/0001-04"
    # followed by rows: "Description val_2024 val_2025 rendimento"

    # ── Rendimentos Isentos (Código 12) ──
    block = _extract_between(text, 'RENDIMENTOS ISENTOS', 'RENDIMENTOS SUJEITOS')
    if block:
        for row in _xp_summary_rows(block):
            desc, v24, v25, rend = row
            if not desc or v24 + v25 + rend == 0:
                continue
            # Find which CNPJ/institution this row belongs to
            f_cnpj = _detect_cnpj_in_block(block, cnpj_names) or cnpj
            f_inst = cnpj_names.get(f_cnpj, inst)
            entries.append(_entry(
                filename, f_inst, cnpj, ano,
                'Rendimentos Isentos', '', 'Rendimentos Isentos',
                '12', desc,
                fonte_pagadora=f_inst, cnpj_fonte=f_cnpj,
                valor_2024=v24, valor_2025=v25,
                rendimento=rend, tipo_rendimento='Isento',
            ))

    # ── Rendimentos Sujeitos à Tributação Exclusiva (Código 06) ──
    block = _extract_between(text, 'RENDIMENTOS SUJEITOS À TRIBUTAÇÃO EXCLUSIVA', 'SALDO EM CONTA')
    if block:
        cur_inst = inst
        cur_cnpj = cnpj
        for row in _xp_summary_rows(block):
            desc, v24, v25, rend = row
            if not desc:
                continue
            # Institution change lines look like "Banco XP S/A CNPJ ..."
            m_inst = re.search(
                r'((?:XP Investimentos CCTVM S/A|Banco XP S/A)[^\d]*)'
                r'CNPJ\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
                desc, re.IGNORECASE)
            if m_inst:
                cur_inst = clean(m_inst.group(1))
                cur_cnpj = m_inst.group(2)
                continue
            # Skip rows with zero values (nothing to report)
            if v24 + v25 + rend == 0:
                continue
            entries.append(_entry(
                filename, cur_inst, cnpj, ano,
                'Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos',
                '06', desc,
                fonte_pagadora=cur_inst, cnpj_fonte=cur_cnpj,
                valor_2024=v24, valor_2025=v25,
                rendimento=rend, tipo_rendimento='Tributação Exclusiva',
            ))

    # ── Rendimentos Tributáveis ──
    block = _extract_between(text,
                             'RENDIMENTOS TRIBUTÁVEIS, DEDUÇÕES E IMPOSTO RETIDO NA FONTE',
                             'Página')
    if block:
        for row in _xp_summary_rows(block):
            desc, v24, v25, rend = row
            if not desc or rend == 0:
                continue
            entries.append(_entry(
                filename, inst, cnpj, ano,
                'Rendimentos Tributáveis PJ', '', 'Rendimentos Tributáveis',
                '01', desc,
                valor_2025=rend, rendimento=rend, tipo_rendimento='Tributável',
            ))

    return entries


def _xp_parse_detail_tables(filename, tables, inst, cnpj, ano, cnpj_names):
    """Parse XP detail pages tables for Bens e Direitos entries."""
    entries = []

    # Categorise each table
    tagged: list[tuple[str, list]] = []
    for t in tables:
        if not t:
            continue
        first_cell = str(t[0][0] or '') if t[0] else ''
        if 'Declaração' in first_cell and 'IRPF' in first_cell:
            tagged.append(('decl', t))
        elif 'Ficha' in first_cell:
            tagged.append(('ficha', t))
        elif len(t[0]) >= 3 and any(any(c for c in row) for row in t):
            # Only tag as data if at least one row has non-empty cells;
            # empty placeholder tables (all blank) are treated as 'other' to
            # avoid corrupting the declaration-assignment algorithm.
            tagged.append(('data', t))
        else:
            tagged.append(('other', t))

    decl_positions = [i for i, (tag, _) in enumerate(tagged) if tag == 'decl']
    ficha_positions = [i for i, (tag, _) in enumerate(tagged) if tag == 'ficha']

    # For each data table find its owning declaration (next decl, else last seen decl)
    last_decl_idx: int | None = None
    last_ficha_idx: int | None = None

    # Build: decl_idx → (grupo, codigo, cnpj_section, ficha_text)
    decl_info: dict[int, dict] = {}
    for di in decl_positions:
        dt = tagged[di][1]
        decl_cell = str(dt[0][1] or '') if len(dt[0]) > 1 else ''
        gm = re.search(r'Grupo\s+(\d+)', decl_cell, re.IGNORECASE)
        cm = re.search(r'[Cc]ód\.?\s*(\d+|ao lado)', decl_cell, re.IGNORECASE)
        grupo = gm.group(1) if gm else ''
        codigo_raw = cm.group(1) if cm else ''
        # Find associated Ficha table
        fi = next((f for f in ficha_positions if f > di), None)
        ficha_text = ''
        ficha_cnpj = cnpj
        if fi is not None:
            ft = tagged[fi][1]
            ficha_text = str(ft[0][0] or '') if ft else ''
            c = find_cnpj(ficha_text)
            if c:
                ficha_cnpj = c
        decl_info[di] = {
            'grupo': grupo,
            'codigo_raw': codigo_raw,
            'ficha_cnpj': ficha_cnpj,
            'ficha_text': ficha_text,
        }

    # Process data tables
    for i, (tag, t) in enumerate(tagged):
        if tag != 'data':
            continue
        # Find owning declaration.
        # Pattern in XP PDFs: the declaration row appears IMMEDIATELY after the
        # FIRST data row of each group (no other data rows between them).
        # Subsequent data rows of the same group have no declaration after them
        # until the next group starts — so they must use the PREVIOUS declaration.
        # Using "next_decl" blindly causes CDB tables on page 5 to be wrongly
        # assigned to the ETF declaration that follows later on the same page.
        next_decl = next((d for d in decl_positions if d > i), None)
        prev_decl = next((d for d in reversed(decl_positions) if d < i), None)
        if next_decl is not None:
            # Use next_decl only when this data table is the FIRST of its group,
            # i.e. no other data tables sit between it and the declaration.
            data_between = any(tagged[j][0] == 'data' for j in range(i + 1, next_decl))
            own_decl = prev_decl if data_between else next_decl
        else:
            own_decl = prev_decl
        if own_decl is None:
            continue

        info = decl_info.get(own_decl, {})
        grupo = info.get('grupo', '')
        codigo_raw = info.get('codigo_raw', '')
        f_cnpj = info.get('ficha_cnpj', cnpj)
        f_inst = cnpj_names.get(f_cnpj, inst)

        # Determine section from Ficha text
        ficha_text = info.get('ficha_text', '')
        if 'Bens e Direitos' in ficha_text or 'Bens' in ficha_text:
            secao = 'Bens e Direitos'
        elif 'Rendimentos Sujeitos' in ficha_text:
            secao = 'Rendimentos Tributação Exclusiva'
        elif 'Rendimentos Isentos' in ficha_text:
            secao = 'Rendimentos Isentos'
        else:
            secao = 'Bens e Direitos'

        for row in t:
            if not row or not any(row):
                continue
            desc_cell = str(row[0] or '')
            if 'Total:' in desc_cell or 'Total' == desc_cell.strip():
                continue

            # Extract values (columns: description, val_2024, val_2025, rendimento)
            vals = [parse_brl(str(row[j])) if j < len(row) else 0.0 for j in range(1, 4)]
            v24, v25, rend = vals[0], vals[1], vals[2] if len(vals) > 2 else 0.0

            # When codigo_raw = "ao lado", extract from description cell
            if codigo_raw.lower() == 'ao lado':
                cm = re.search(r'[Cc]ód\.?\s*(\d+)', desc_cell)
                codigo = cm.group(1) if cm else '99'
            else:
                codigo = codigo_raw if codigo_raw.isdigit() else '99'

            # Extract description and grupo_desc
            # Clean up the description cell: remove CNPJ, codes, dates
            desc_clean = re.sub(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', '', desc_cell)
            desc_clean = re.sub(r'[Cc]ód\.?\s*\d+', '', desc_clean)
            desc_clean = re.sub(r'\d{2}/\d{2}/\d{4}', '', desc_clean)
            desc_clean = clean(desc_clean)

            grupo_descs = {
                '03': 'Participações Societárias', '04': 'Aplicações e Investimentos',
                '05': 'Créditos e Empréstimos', '06': 'Depósito à Vista e Numerário',
                '07': 'Fundos', '08': 'Criptoativos',
            }
            codigo_descs = {
                ('04', '02'): 'Títulos públicos e privados sujeitos à tributação (CDB, RDB, Tesouro)',
                ('04', '03'): 'Títulos isentos de tributação (LCI, LCA, LCD, CRI, CRA, LIG, Debêntures de Infraestrutura e outros)',
                ('06', '01'): 'Depósito em conta corrente ou conta pagamento',
                ('06', '99'): 'Outros depósitos à vista',
                ('07', '01'): 'Fundos sujeitos à tributação periódica (come-cotas)',
                ('07', '06'): 'Fundos de Investimento em Participações (FIP)',
                ('07', '08'): 'Fundos de Índice de Renda Fixa (ETF RF)',
                ('07', '99'): 'Outros Fundos',
            }

            grupo_desc = grupo_descs.get(grupo, 'Aplicações e Investimentos')
            cdesc = codigo_descs.get((grupo, codigo), desc_clean or f'Código {codigo}')

            entries.append(_entry(
                filename, f_inst, cnpj, ano,
                secao, grupo, grupo_desc, codigo, cdesc,
                fonte_pagadora=f_inst, cnpj_fonte=f_cnpj,
                discriminacao=desc_clean,
                valor_2024=v24, valor_2025=v25,
                rendimento=rend,
                tipo_rendimento='Tributação Exclusiva' if secao == 'Rendimentos Tributação Exclusiva' else '',
            ))

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# XP PREVIDÊNCIA
# ─────────────────────────────────────────────────────────────────────────────

def parse_xp_previdencia(filename: str, pages_text: list[str],
                         pages_tables: list[list]) -> list[Entry]:
    entries = []
    text = '\n'.join(pages_text)
    ano = extract_year(text)

    cnpj_m = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', text)
    cnpj = cnpj_m.group(1) if cnpj_m else '29.408.732/0001-05'
    inst = 'XP Vida e Previdência S.A.'

    # Helper: get value from a pattern in text
    def _v(pattern):
        m = re.search(pattern + r'[^\n]*([\d.]+,\d{2}|\–|\-)', text, re.IGNORECASE | re.DOTALL)
        if not m:
            return 0.0
        return parse_brl(m.group(1))

    # ── Bens e Direitos: VGBL saldo ──────────────────────────────────────
    # "Informar: Grupo 99 | Código 06"  values in table row "Total 1.000,00 1.000,00"
    # Extract from tables
    for page_tables in pages_tables:
        for t in page_tables:
            for row in t:
                row_str = ' '.join(str(c or '') for c in row)
                if '1.000,00' in row_str or ('Total' in row_str and re.search(r'[\d.]+,\d{2}', row_str)):
                    vals = re.findall(r'([\d.]+,\d{2})', row_str)
                    if len(vals) >= 2:
                        v24, v25 = parse_brl(vals[0]), parse_brl(vals[1])
                        if v24 > 0 or v25 > 0:
                            entries.append(_entry(
                                filename, inst, cnpj, ano,
                                'Bens e Direitos', '99', 'Outros Bens e Direitos',
                                '06', 'Previdência Privada (VGBL)',
                                fonte_pagadora=inst, cnpj_fonte=cnpj,
                                valor_2024=v24, valor_2025=v25,
                            ))
                            break
            else:
                continue
            break

    # ── Contribuições para PGBL (Código 36) ──────────────────────────────
    contrib_m = re.search(r'Contribuição para PGBL\s+([\d.]+,\d{2})', text, re.IGNORECASE)
    if not contrib_m:
        # Try from tables
        for page_tables in pages_tables:
            for t in page_tables:
                for row in t:
                    row_str = ' '.join(str(c or '') for c in row)
                    if re.search(r'15[\d.]+,\d{2}', row_str):  # large contribution value
                        vals = re.findall(r'([\d.]+,\d{2})', row_str)
                        if vals:
                            contrib_m = type('M', (), {'group': lambda s, n: vals[0]})()

    if contrib_m:
        entries.append(_entry(
            filename, inst, cnpj, ano,
            'Contribuições Previdenciárias', '', 'Pagamentos Efetuados',
            '36', 'Contribuições para PGBL (Código 36)',
            fonte_pagadora=inst, cnpj_fonte=cnpj,
            valor_2025=parse_brl(contrib_m.group(1)),
            tipo_rendimento='Dedução',
        ))

    # If no contrib from regex, try a direct pattern
    if not any(e.codigo == '36' for e in entries):
        m = re.search(r'([\d.]+,\d{2})\s*$', text.split('Contribuição para PGBL')[-1][:50]
                      if 'Contribuição para PGBL' in text else '', re.MULTILINE)
        if m:
            entries.append(_entry(
                filename, inst, cnpj, ano,
                'Contribuições Previdenciárias', '', 'Pagamentos Efetuados',
                '36', 'Contribuições para PGBL (Código 36)',
                fonte_pagadora=inst, cnpj_fonte=cnpj,
                valor_2025=parse_brl(m.group(1)), tipo_rendimento='Dedução',
            ))

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# CLEAR  (Informe padrão Ministério da Economia – reutiliza lógica XP)
# ─────────────────────────────────────────────────────────────────────────────

def parse_clear(filename: str, pages_text: list[str],
                pages_tables: list[list]) -> list[Entry]:
    """
    Parse Clear broker documents: Informe de Rendimentos or Custódia (Assets).
    
    Clear offers investment brokerage through XP's infrastructure, supporting:
    1. "Informe de Rendimentos" - uses standard "Informe de Rendimentos" format
    2. "Custódia" - detailed asset position with holdings breakdown
    """
    from dataclasses import replace

    # Detect document type by looking at page 1 only.
    # Use a positive match for "INFORME DE RENDIMENTOS" so that mentions of
    # "custódia" that appear in footnotes/informational text on the informe
    # (e.g. "...com posição em custódia...") do not mis-route the file.
    page1_text = pages_text[0] if pages_text else ''
    if 'INFORME DE RENDIMENTOS' in page1_text.upper():
        # Use the same parsing logic as XP since Clear uses the standard format
        entries = parse_xp(filename, pages_text, pages_tables)
    else:
        # Parse custody/assets document
        entries = _parse_clear_custodia(filename, pages_text, pages_tables)
    
    # Update institution name to "Clear" while preserving other parsed data
    entries = [replace(e, instituicao='Clear') for e in entries]
    
    return entries


def _parse_clear_custodia(filename: str, pages_text: list[str],
                          pages_tables: list[list]) -> list[Entry]:
    """
    Parse Clear custody document (Posição Consolidada de Ativos).
    
    Extracts individual security holdings (ações, FIIs, ETFs, etc.)
    and calculates their values based on market prices.
    """
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)
    inst = 'Clear'
    ano = extract_year(full_text)
    primary_cnpj = ''  # Clear doesn't provide CNPJ in custody docs
    
    # ── Classifier helper ────────────────────────────────────────────────────
    def classify_asset_type(ticker: str) -> tuple[str, str]:
        """Classify asset type by ticker pattern.
        
        Returns: (group, codigo, codigo_desc)
        - FII/ETF: ends with 11, 13, 21, 24, 39, 65
        - Ação: others
        """
        ticker_upper = ticker.strip().upper()
        # Check last 2-3 chars for FII/ETF pattern
        if len(ticker_upper) >= 4:
            last_chars = ticker_upper[-2:]
            if last_chars in ('11', '13', '21', '24', '39', '65'):
                return ('07', '99', 'Fundos de Investimento')  # FII/ETF
        # Default: Ação
        return ('04', '01', 'Ações')
    
    # ── Parse asset tables ───────────────────────────────────────────────────
    # Tables contain rows with: ticker, qty, prices, position value
    for page_idx, page_tables in enumerate(pages_tables):
        for table in page_tables:
            for row_idx, row in enumerate(table):
                if not row or len(row) < 2:
                    continue
                
                ticker = str(row[0] or '').strip()
                
                # Skip header/footer rows
                if not ticker or ticker.lower() in ('ativo', 'ticker', 'posição',
                                                      'total', 'saldo', 'disponível'):
                    continue
                
                # Validate ticker format (usually 4-6 chars: ABCD3, ABCD11, etc)
                if not re.match(r'^[A-Z]{2,4}[0-9]{1,3}$', ticker):
                    continue
                
                # Extract position value (last numeric column)
                position_value = 0.0
                for cell in reversed(row):
                    val = parse_brl(str(cell or ''))
                    if val > 0:
                        position_value = val
                        break
                
                if position_value == 0:
                    continue
                
                # Classify and create entry
                grupo, codigo, codigo_desc = classify_asset_type(ticker)
                grupo_desc = _grupo_desc(grupo)
                
                entries.append(_entry(
                    filename, inst, primary_cnpj, ano,
                    'Bens e Direitos', grupo, grupo_desc, codigo, codigo_desc,
                    fonte_pagadora=inst,
                    cnpj_fonte=primary_cnpj,
                    localizacao='105 - Brasil',
                    discriminacao=f'{ticker} - Ativo em Custódia',
                    valor_2024=0.0,
                    valor_2025=position_value,
                    rendimento=0.0,
                ))
    
    # Note: saldo em conta is extracted from the "Informe de Rendimentos" (parse_xp)
    # which has both 2024 and 2025 values. The custody document only has the 2025
    # position and would create a duplicate with an incorrect 2024 value of R$ 0,00.

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# NUBANK
# ─────────────────────────────────────────────────────────────────────────────

_GRUPO_CODIGO_RE = re.compile(
    r'Grupo\s+(\d+)\s*[-–]\s*([^\n]+)\n\s*Código\s+(\d+)\s*[-–]\s*([^\n]+)',
    re.IGNORECASE,
)
_NUBANK_ROW_RE = re.compile(
    r'(?:\d{2}/\d{2}/\d{4}|\d{4}\s+[\w-]+)\s+'        # date OR agencia+conta
    r'R\$\s*([\d.]+,\d{2})\s+R\$\s*([\d.]+,\d{2})'    # val_2024  val_2025
    r'(?:\s+R\$\s*([\d.]+,\d{2}))?',                   # optional rendimento
)
_NUBANK_FUND_ROW_RE = re.compile(
    r'(?:[A-ZÁÉÍÓÚ][\w\s]+)\s+(\d{14})\s+'
    r'R\$\s*([\d.]+,\d{2})\s+R\$\s*([\d.]+,\d{2})'
    r'(?:\s+R\$\s*([\d.]+,\d{2}))?',
)
_NUBANK_CRYPTO_ROW_RE = re.compile(
    r'(BTC|ETH|USDC|USDT|[A-Z]{2,10})\s+'
    r'[\d.]+\s+R\$\s*([\d.]+,\d{2})\s+'  # qty2024 cost2024
    r'[\d.]+\s+R\$\s*([\d.]+,\d{2})',    # qty2025 cost2025
)
# Matches content that disqualifies a line from being a wrapped name continuation.
# A continuation line is pure text — no monetary values, no dates, no section headers.
_NUBANK_CONT_SKIP_RE = re.compile(
    r'R\$|\d{2}/\d{2}/\d{4}|Total:|Grupo\s+\d+|Código\s+\d+'
    r'|CNPJ:|Fonte pagadora:|Localização|Título\s+Vencimento'
)


def parse_nubank(filename: str, pages_text: list[str],
                 pages_tables: list[list]) -> list[Entry]:
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)

    # Institution
    inst = 'Nubank'
    ano = extract_year(full_text)

    # Find all Grupo/Código block boundaries
    block_starts = [(m.start(), m) for m in _GRUPO_CODIGO_RE.finditer(full_text)]

    for idx, (start, hdr) in enumerate(block_starts):
        end = block_starts[idx + 1][0] if idx + 1 < len(block_starts) else len(full_text)
        block = full_text[start:end]

        grupo = hdr.group(1).strip()
        grupo_desc = clean(hdr.group(2))
        codigo = hdr.group(3).strip()
        codigo_desc = clean(hdr.group(4))

        # CNPJ / fonte
        cnpj_m = re.search(r'CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', block)
        cnpj_fonte = cnpj_m.group(1) if cnpj_m else ''
        fonte_m = re.search(r'Fonte pagadora:\s*([^\n]+)', block)
        fonte = clean(fonte_m.group(1)) if fonte_m else inst

        loc_m = re.search(r'Localização \(País\):\s*([^\n]+)', block)
        loc = clean(loc_m.group(1)) if loc_m else '105 - Brasil'

        # Determine rendimento type from column header
        tipo_rend = 'Tributação Exclusiva'
        if re.search(r'[Rr]endimento\s+[Ii]sento', block):
            tipo_rend = 'Isento'
        elif grupo == '08':
            tipo_rend = ''  # Crypto: no income

        # Collect per-row data: (discriminacao, v24, v25, rend).
        # Creating one entry per row lets xlsx_writer and the dashboard
        # separate Tesouro Selic/Prefixado/IPCA+ from CDB within the
        # same Grupo/Código block using _renda_fixa_subtype.
        row_data: list[tuple[str, float, float, float]] = []

        # Standard rows (date-anchored) – capture description from line prefix
        for m in _NUBANK_ROW_RE.finditer(block):
            line_start = block.rfind('\n', 0, m.start()) + 1
            line_end = block.find('\n', m.start())
            line = block[line_start:line_end if line_end != -1 else len(block)]
            if 'Total:' in line or '31/12' in line:
                continue
            raw_desc = re.sub(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*', '',
                               block[line_start:m.start()])
            desc = clean(raw_desc) or codigo_desc
            # Some PDFs wrap long bank names onto the next line (e.g. "CDB BANCO\nRENDIMENTO").
            # A valid continuation is ALL-CAPS (bank names in NuBank PDFs are uppercase)
            # and contains no monetary values, dates, or section headers.
            if line_end != -1:
                next_start = line_end + 1
                next_end = block.find('\n', next_start)
                next_line = block[next_start: next_end if next_end != -1 else len(block)].strip()
                if (next_line
                        and next_line == next_line.upper()
                        and not _NUBANK_CONT_SKIP_RE.search(next_line)):
                    desc = f"{desc} {next_line}".strip() if desc else next_line
            row_data.append((desc, parse_brl(m.group(1)), parse_brl(m.group(2)),
                             parse_brl(m.group(3)) if m.group(3) else 0.0))

        # Fund rows (CNPJ-anchored)
        for m in _NUBANK_FUND_ROW_RE.finditer(block):
            row_data.append((codigo_desc, parse_brl(m.group(2)), parse_brl(m.group(3)),
                             parse_brl(m.group(4)) if m.group(4) else 0.0))

        # Crypto rows
        if grupo == '08':
            row_data = [
                (m.group(1), parse_brl(m.group(2)), parse_brl(m.group(3)), 0.0)
                for m in _NUBANK_CRYPTO_ROW_RE.finditer(block)
            ]

        # Fallback: if no rows matched, check for a Total: line
        if not row_data:
            total_m = re.search(r'Total:\s*R\$\s*([\d.]+,\d{2})', block)
            if total_m:
                row_data.append((codigo_desc, 0.0, 0.0, parse_brl(total_m.group(1))))
            else:
                continue

        for desc, v24, v25, rend in row_data:
            if v24 + v25 + rend == 0:
                continue
            entries.append(_entry(
                filename, inst, cnpj_fonte or inst, ano,
                'Bens e Direitos', grupo, grupo_desc, codigo, codigo_desc,
                fonte_pagadora=fonte, cnpj_fonte=cnpj_fonte,
                localizacao=loc,
                discriminacao=desc,
                valor_2024=v24, valor_2025=v25,
                rendimento=rend, tipo_rendimento=tipo_rend,
            ))

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# INTER
# ─────────────────────────────────────────────────────────────────────────────

def parse_inter(filename: str, pages_text: list[str],
                pages_tables: list[list]) -> list[Entry]:
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)
    inst = 'Banco Inter'
    ano = extract_year(full_text)

    # Primary CNPJ
    primary_cnpj = '00.416.968/0001-01'

    # ── Bens e Direitos ──────────────────────────────────────────────────────
    # Pattern: "Grupo XX - Description / Código YY - ... | Localização: ..."
    # Followed by a table: CNPJ | Descrição | [Agência | Conta] | dez/2024 | dez/2025
    bd_block_re = re.compile(
        r'Grupo\s+(\d+)\s*[-–]\s*([^\n]+)\nCódigo\s+(\d+)\s*[-–]\s*([^\n]+)',
        re.IGNORECASE,
    )

    for m in bd_block_re.finditer(full_text):
        grupo = m.group(1).strip()
        grupo_desc = clean(m.group(2).split('|')[0].split('Código')[0])
        codigo = m.group(3).strip()
        codigo_desc = clean(m.group(4).split('|')[0])

        # Extract the block text (up to the next Grupo marker or Rendimentos section)
        block_end = re.search(r'\nGrupo\s+\d+|\nRendimentos\s+i', full_text[m.end():],
                              re.IGNORECASE)
        block = full_text[m.end(): m.end() + (block_end.start() if block_end else 500)]

        # Localização
        loc_m = re.search(r'Localização[:\s]+([^\n|]+)', m.group(4) + block, re.IGNORECASE)
        loc = clean(loc_m.group(1)) if loc_m else '105 - Brasil'

        # Collect (CNPJ, val_2024, val_2025) from rows
        row_re = re.compile(
            r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+([^\n]+?)\s+'
            r'R\$\s*([\d.]+,\d{2})\s+R\$\s*([\d.]+,\d{2})',
        )
        for rm in row_re.finditer(block):
            c_cnpj = rm.group(1)
            c_desc = clean(rm.group(2))
            v24 = parse_brl(rm.group(3))
            v25 = parse_brl(rm.group(4))
            entries.append(_entry(
                filename, inst, primary_cnpj, ano,
                'Bens e Direitos', grupo, grupo_desc, codigo, codigo_desc,
                fonte_pagadora=c_desc, cnpj_fonte=c_cnpj,
                localizacao=loc,
                valor_2024=v24, valor_2025=v25,
            ))

    # ── Rendimentos Isentos ──────────────────────────────────────────────────
    # "Código 12 - ..."
    # "CNPJ   Nome   Valor"
    cod12_m = re.search(r'Código\s+12\s*[-–]\s*([^\n]+)', full_text, re.IGNORECASE)
    if cod12_m:
        block = full_text[cod12_m.end():cod12_m.end() + 400]
        row_re = re.compile(
            r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+([^\n\d]+?)\s+R\$\s*([\d.]+,\d{2})',
        )
        for rm in row_re.finditer(block):
            v = parse_brl(rm.group(3))
            if v == 0:
                continue
            entries.append(_entry(
                filename, inst, primary_cnpj, ano,
                'Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
                '12', clean(cod12_m.group(1)),
                fonte_pagadora=clean(rm.group(2)), cnpj_fonte=rm.group(1),
                rendimento=v, tipo_rendimento='Isento',
            ))

    # ── Rendimentos Tributação Exclusiva ─────────────────────────────────────
    # "Código 06 - ..."
    cod06_m = re.search(r'Código\s+06\s*[-–]\s*([^\n]+)', full_text, re.IGNORECASE)
    if cod06_m:
        block = full_text[cod06_m.end():cod06_m.end() + 400]
        row_re = re.compile(
            r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+([^\n\d]+?)\s+R\$\s*([\d.]+,\d{2})',
        )
        for rm in row_re.finditer(block):
            v = parse_brl(rm.group(3))
            if v == 0:
                continue
            entries.append(_entry(
                filename, inst, primary_cnpj, ano,
                'Rendimentos Tributação Exclusiva', '', 'Rendimentos Sujeitos à Tributação Exclusiva',
                '06', clean(cod06_m.group(1)),
                fonte_pagadora=clean(rm.group(2)), cnpj_fonte=rm.group(1),
                rendimento=v, tipo_rendimento='Tributação Exclusiva',
            ))

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# AVENUE  (Relatório auxiliar com ativos individuais – usa extração de tabelas)
# ─────────────────────────────────────────────────────────────────────────────

def parse_avenue(filename: str, pages_text: list[str],
                 pages_tables: list[list]) -> list[Entry]:
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)
    inst = 'Avenue Securities LLC'
    cnpj = ''  # US broker – no Brazilian CNPJ
    ano = extract_year(full_text)
    loc_exterior = '249 - Estados Unidos'

    # ── Bens e Direitos: Saldo em conta (page 1 text) ────────────────────────
    # Text line: "06-99 ESTADOS R$ 1.415,92 R$ 1.082,42"
    conta_re = re.compile(
        r'(\d{2}-\d{2})\s+[A-Z]+\s+'
        r'R\$\s*([\d.]+,\d{2})\s+R\$\s*([\d.]+,\d{2})',
    )
    for m in conta_re.finditer(full_text):
        gc = m.group(1)
        grupo, codigo = gc.split('-')
        v24 = parse_brl(m.group(2))
        v25 = parse_brl(m.group(3))
        entries.append(_entry(
            filename, inst, cnpj, ano,
            'Bens e Direitos', grupo, _grupo_desc(grupo), codigo,
            'Depósito em conta corrente ou conta pagamento',
            localizacao=loc_exterior,
            discriminacao='Saldo em conta – Avenue Securities LLC',
            valor_2024=v24, valor_2025=v25,
        ))

    # ── Ativos em Custódia – parse from pdfplumber tables ────────────────────
    # Table columns on pages 2+:
    # [Grupo e Código, Localização, Tipo, Símbolo, Empresa, Qtde, USD cost, Ptax, BRL cost]
    # Rendimento row has "Aplicação Financeira =>" in cell[0]

    rend_re  = re.compile(
        r'Rendimento ou perda:\s*R\$\s*([\d.]+,\d{2}).*?'
        r'Imposto pago no exterior:\s*R\$\s*([\d.]+,\d{2})',
        re.IGNORECASE | re.DOTALL,
    )
    lucro_re = re.compile(
        r'Valor recebido:\s*R\$\s*([\d.]+,\d{2})',
        re.IGNORECASE,
    )

    pending: dict | None = None  # last asset row waiting for its rendimento row

    def flush(rend: float, irrf: float, dividendo: float) -> None:
        if pending is None:
            return
        brl_cost = pending['brl_cost']
        if brl_cost + rend + dividendo == 0:
            return
        entries.append(_entry(
            filename, inst, cnpj, ano,
            'Bens e Direitos',
            pending['grupo'], _grupo_desc(pending['grupo']),
            pending['codigo'],
            f"{pending['symbol']} – {pending['company']}",
            localizacao=loc_exterior,
            discriminacao=f"{pending['symbol']} – {pending['company']}",
            valor_2025=brl_cost,
            rendimento=rend + dividendo,
            irrf=irrf,
            tipo_rendimento='Tributação Exclusiva' if (rend + dividendo) else '',
        ))

    for page_tables in pages_tables:  # page 1 also contains asset rows (e.g. AAPL, AMZN, BRKB)
        for table in page_tables:
            for row in table:
                if not row or not row[0]:
                    continue
                cell0 = str(row[0])

                # Rendimento/IRRF row
                if 'Aplicação Financeira' in cell0:
                    rm = rend_re.search(cell0)
                    lm = lucro_re.search(cell0)
                    rend      = parse_brl(rm.group(1))  if rm else 0.0
                    irrf      = parse_brl(rm.group(2))  if rm else 0.0
                    dividendo = parse_brl(lm.group(1))  if lm else 0.0
                    flush(rend, irrf, dividendo)
                    pending = None
                    continue

                # Header row
                if 'Grupo' in cell0 or 'Código' in cell0:
                    continue

                # Asset data row: cell0 = "03-01"
                # Page 1 table has extra None columns interspersed; compact to
                # normalise layout so symbol/company indices are consistent.
                gc_m = re.match(r'(\d{2})-(\d{2})$', cell0.strip())
                if not gc_m:
                    continue
                grupo  = gc_m.group(1)
                codigo = gc_m.group(2)

                compact = [c for c in row if c is not None]
                symbol  = str(compact[3] if len(compact) > 3 else '').strip()
                company = clean(str(compact[4] if len(compact) > 4 else ''))

                # Skip non-asset rows (e.g. saldo row which has no ticker symbol)
                if not re.match(r'^[A-Z][A-Z0-9.]{0,14}$', symbol):
                    continue

                # BRL cost is the last column
                brl_cost = 0.0
                for cell in reversed(row):
                    c = parse_brl(str(cell or ''))
                    if c > 0:
                        brl_cost = c
                        break

                # Flush previous pending asset (rendimento row may have been missing)
                if pending is not None:
                    flush(0.0, 0.0, 0.0)

                pending = {
                    'grupo': grupo, 'codigo': codigo,
                    'symbol': symbol, 'company': company,
                    'brl_cost': brl_cost,
                }

    # Flush last pending asset
    if pending is not None:
        flush(0.0, 0.0, 0.0)

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# FACHESF  (Fundação CHESF de Assistência e Seguridade Social)
# Format: Comprovante de Rendimentos Pagos – numbered fields, single page
# ─────────────────────────────────────────────────────────────────────────────

def parse_fachesf(filename: str, pages_text: list[str],
                  pages_tables: list[list]) -> list[Entry]:
    text = '\n'.join(pages_text)
    entries: list[Entry] = []

    # Institution / CNPJ
    cnpj_m = re.search(r'(\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\.\s]?\d{4}[\-\s]?\d{2})', text)
    if cnpj_m:
        raw = re.sub(r'\D', '', cnpj_m.group(1))
        cnpj = f'{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}' if len(raw) == 14 else cnpj_m.group(1)
    else:
        cnpj = '42.160.192/0001-43'
    inst = 'FACHESF – Fundação CHESF de Assistência e Seguridade Social'
    ano = extract_year(text)

    def _v(pattern: str) -> float:
        m = re.search(pattern + r'[^\n]*([\d.]+,\d{2})', text, re.IGNORECASE | re.DOTALL)
        return parse_brl(m.group(1)) if m else 0.0

    def add(secao, grupo, gdesc, codigo, cdesc, **kw):
        entries.append(_entry(filename, inst, cnpj, ano,
                               secao, grupo, gdesc, codigo, cdesc,
                               fonte_pagadora=inst, cnpj_fonte=cnpj, **kw))

    # ── Quadro 3: Rendimentos Tributáveis ─────────────────────────────────
    total_rend = _v(r'01\.\s*TOTAL\s*DOS\s*RENDIMENTOS')
    prev_priv  = _v(r'03\.\s*CONTRIBUI[CÇ][AÃ]O\s*[AÀ]?\s*PREVID[EÊ]NCIA\s*PRIVADA')
    irrf       = _v(r'05\.\s*IMPOSTO\s*DE\s*RENDA\s*RETIDO\s*NA\s*FONTE')

    if total_rend:
        add('Rendimentos Tributáveis PJ', '', 'Previdência Complementar',
            '01', 'Total dos Rendimentos',
            valor_2025=total_rend, tipo_rendimento='Tributável')
    if prev_priv:
        add('Rendimentos Tributáveis PJ', '', 'Deduções',
            '03', 'Contribuição à Previdência Privada',
            valor_2025=prev_priv, tipo_rendimento='Dedução')
    if irrf:
        add('Rendimentos Tributáveis PJ', '', 'Imposto',
            '05', 'IR Retido na Fonte (IRRF)',
            valor_2025=irrf, irrf=irrf, tipo_rendimento='Tributável')

    # ── Quadro 4: Rendimentos Isentos ─────────────────────────────────────
    apos_isenta = _v(r'01\.\s*PARCELA\s*ISENTA\s*DOS\s*PROVENTOS')
    abono13     = _v(r'02\.\s*PARCELA\s*ISENTA.*?13')
    apos_molest = _v(r'04\.\s*PENS[AÃ]O.*?MOLÉSTIA')
    outros_is   = _v(r'07\.\s*OUTROS')

    for val, cod, desc in [
        (apos_isenta, '01', 'Parcela Isenta Aposentadoria/Pensão (65+)'),
        (abono13,     '02', 'Parcela Isenta 13º Abono Anual Aposentadoria'),
        (apos_molest, '04', 'Aposentadoria por Moléstia Grave'),
        (outros_is,   '07', 'Outros Rendimentos Isentos'),
    ]:
        if val:
            add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
                cod, desc, rendimento=val, tipo_rendimento='Isento')

    # ── Quadro 5: Rendimentos Tributação Exclusiva ─────────────────────────
    dec13      = _v(r'01\.\s*D[EÉ]CIMO\s*TERCEIRO\s*SAL[AÁ]RIO')
    irrf13     = _v(r'02\.\s*IRRF\s*SOBRE\s*D[EÉ]CIMO\s*TERCEIRO')
    outros_exc = _v(r'03\.\s*OUTROS')

    if dec13:
        add('Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos',
            '01', '13º Salário / Abono Anual',
            rendimento=dec13, irrf=irrf13, tipo_rendimento='Tributação Exclusiva')
    if outros_exc:
        add('Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos',
            '03', 'Outros (PLA/PLR)',
            rendimento=outros_exc, tipo_rendimento='Tributação Exclusiva')

    # If nothing was extracted (all zeros), still return one entry to confirm parsing
    if not entries:
        add('Rendimentos Tributáveis PJ', '', 'Previdência Complementar',
            '01', 'Total dos Rendimentos (zerado)',
            valor_2025=0.0, tipo_rendimento='Tributável')

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# INSS  (Comprovante de Rendimentos – Fundo do Regime Geral de Previdência)
# Format: Ministério da Fazenda / Receita Federal – numbered fields
# ─────────────────────────────────────────────────────────────────────────────

def parse_inss(filename: str, pages_text: list[str],
               pages_tables: list[list]) -> list[Entry]:
    text = '\n'.join(pages_text)
    entries: list[Entry] = []

    cnpj = '16.727.230/0001-97'
    inst = 'INSS – Fundo do Regime Geral de Previdência Social'
    ano = extract_year(text)

    def _v(pattern: str) -> float:
        m = re.search(pattern + r'[^\n]*([\d.]+,\d{2}|\d+,\d{2})', text, re.IGNORECASE | re.DOTALL)
        return parse_brl(m.group(1)) if m else 0.0

    def _v_bare(pattern: str) -> float:
        """Match value directly after pattern on same or next line (no label prefix)."""
        m = re.search(pattern + r'\s+([\d.]+,\d{2}|\d{1,10},\d{2})', text, re.IGNORECASE)
        return parse_brl(m.group(1)) if m else 0.0

    def add(secao, grupo, gdesc, codigo, cdesc, **kw):
        entries.append(_entry(filename, inst, cnpj, ano,
                               secao, grupo, gdesc, codigo, cdesc,
                               fonte_pagadora=inst, cnpj_fonte=cnpj, **kw))

    # ── Quadro 3: Rendimentos Tributáveis ─────────────────────────────────
    total_rend = _v_bare(r'1\s*-\s*Total de Rendimentos.*?férias\)')
    inss_dedu  = _v(r'2\s*-\s*Contribui[cç][aã]o Previdenci[aá]ria Oficial')
    prev_priv  = _v(r'3\s*-\s*Contribui[cç][aã]o.*?Previd[eê]ncia Privada')
    irrf       = _v(r'5\s*-\s*Imposto Retido na Fonte')

    if total_rend:
        add('Rendimentos Tributáveis PJ', '', 'Proventos de Aposentadoria/Pensão',
            '01', 'Total dos Rendimentos (incl. férias)',
            valor_2025=total_rend, tipo_rendimento='Tributável')
    if inss_dedu:
        add('Rendimentos Tributáveis PJ', '', 'Deduções',
            '02', 'Contribuição Previdenciária Oficial (INSS)',
            valor_2025=inss_dedu, tipo_rendimento='Dedução')
    if prev_priv:
        add('Rendimentos Tributáveis PJ', '', 'Deduções',
            '03', 'Contribuição à Previdência Privada / FAPI',
            valor_2025=prev_priv, tipo_rendimento='Dedução')
    if irrf:
        add('Rendimentos Tributáveis PJ', '', 'Imposto',
            '05', 'IR Retido na Fonte (IRRF)',
            valor_2025=irrf, irrf=irrf, tipo_rendimento='Tributável')

    # ── Quadro 4: Rendimentos Isentos ─────────────────────────────────────
    apos_isenta = _v_bare(r'1\s*-\s*Parcela Isenta dos Proventos.*?Pensão.*?(?:mais\)[\s,]*)')
    outros_is   = _v(r'(?:6|7)\s*-\s*Outros\s*$')

    if apos_isenta:
        add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
            '01', 'Parcela Isenta Aposentadoria/Pensão (65+)',
            rendimento=apos_isenta, tipo_rendimento='Isento')
    if outros_is:
        add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
            '07', 'Outros Rendimentos Isentos',
            rendimento=outros_is, tipo_rendimento='Isento')

    # If nothing was extracted, still return an entry to confirm parsing
    if not entries:
        add('Rendimentos Tributáveis PJ', '', 'Proventos de Aposentadoria/Pensão',
            '01', 'Total dos Rendimentos (zerado)',
            valor_2025=0.0, tipo_rendimento='Tributável')

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# COMPROVANTE DE RENDIMENTOS  (Receita Federal standard – pension funds / employers)
# Format: Ministério da Fazenda / Secretaria da Receita Federal template with
# numbered quadros 1–7 and "RAZÃO SOCIAL / NOME:" field.
# Used by NPS/Funame, SPSM, and other pension funds that follow this template.
# ─────────────────────────────────────────────────────────────────────────────

def parse_comprovante_rendimentos(filename: str, pages_text: list[str],
                                   pages_tables: list[list]) -> list[Entry]:
    """Parse the standard RFB 'Comprovante de Rendimentos' multi-quadro format."""
    text = '\n'.join(pages_text)
    entries: list[Entry] = []

    # ── Institution & year ───────────────────────────────────────────────────
    cnpj_m = re.search(
        r'CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+RAZ[ÃA]O SOCIAL\s*/\s*NOME:\s*(.+)',
        text, re.IGNORECASE,
    )
    cnpj = cnpj_m.group(1) if cnpj_m else find_cnpj(text)
    inst = clean(cnpj_m.group(2)) if cnpj_m else 'Previdência'

    ano_m = re.search(r'ANO CALEND[ÁA]RIO:\s*(\d{4})', text, re.IGNORECASE)
    ano = int(ano_m.group(1)) if ano_m else extract_year(text)

    def add(secao: str, grupo: str, gdesc: str, codigo: str, cdesc: str, **kw) -> None:
        entries.append(_entry(filename, inst, cnpj, ano,
                               secao, grupo, gdesc, codigo, cdesc,
                               fonte_pagadora=inst, cnpj_fonte=cnpj, **kw))

    def _section(start_pat: str, end_pat: str) -> str:
        """Slice text between two section-header patterns."""
        s = re.search(start_pat, text, re.IGNORECASE)
        if not s:
            return ''
        e = re.search(end_pat, text[s.end():], re.IGNORECASE)
        end_pos = s.end() + e.start() if e else len(text)
        return text[s.start():end_pos]

    def _val_in(block: str, item_num: int) -> float:
        """Extract the BRL value for a numbered item (same-line or next-line).

        Uses a space separator before the value so backtracking anchors to the
        last number on the line rather than the shortest suffix (e.g. captures
        '45.085,56' not just '5,56').
        """
        # Value at end of line, separated from description by a space
        m = re.search(
            rf'0?{item_num}\s*[-–][^\n]* ([\d.]+,\d{{2}})\s*$',
            block, re.IGNORECASE | re.MULTILINE,
        )
        if m:
            return parse_brl(m.group(1))
        # Wrapped: description spans to next line, value is on the line below
        m = re.search(
            rf'0?{item_num}\s*[-–]\s*[^\n]*\n([\d.]+,\d{{2}})',
            block, re.IGNORECASE,
        )
        return parse_brl(m.group(1)) if m else 0.0

    # ── Quadro 3: Rendimentos Tributáveis ────────────────────────────────────
    q3 = _section(r'RENDIMENTOS TRIBUT[ÁA]VEIS', r'RENDIMENTOS ISENTOS')
    total_rend = _val_in(q3, 1)
    inss_dedu  = _val_in(q3, 2)
    prev_priv  = _val_in(q3, 3)
    irrf       = _val_in(q3, 5)

    if total_rend:
        add('Rendimentos Tributáveis PJ', '', 'Proventos de Aposentadoria/Pensão',
            '01', 'Total dos Rendimentos',
            valor_2025=total_rend, tipo_rendimento='Tributável')
    if inss_dedu:
        add('Rendimentos Tributáveis PJ', '', 'Deduções',
            '02', 'Contribuição Previdenciária Oficial (INSS)',
            valor_2025=inss_dedu, tipo_rendimento='Dedução')
    if prev_priv:
        add('Rendimentos Tributáveis PJ', '', 'Deduções',
            '03', 'Contribuição à Previdência Privada / FAPI',
            valor_2025=prev_priv, tipo_rendimento='Dedução')
    if irrf:
        add('Rendimentos Tributáveis PJ', '', 'Imposto',
            '05', 'IR Retido na Fonte (IRRF)',
            valor_2025=irrf, irrf=irrf, tipo_rendimento='Tributável')

    # ── Quadro 4: Rendimentos Isentos ─────────────────────────────────────────
    q4 = _section(r'RENDIMENTOS ISENTOS E N[ÃA]O TRIBUT[ÁA]VEIS',
                  r'TRIBUTA[CÇ][ÃA]O EXCLUSIVA')
    apos_isenta  = _val_in(q4, 1)
    dec13_isento = _val_in(q4, 2)

    if apos_isenta:
        add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
            '01', 'Parcela Isenta Aposentadoria/Pensão (65+)',
            rendimento=apos_isenta, tipo_rendimento='Isento')
    if dec13_isento:
        add('Rendimentos Isentos', '', 'Rendimentos Isentos e Não Tributáveis',
            '06', 'Parcela Isenta 13º Salário Aposentadoria (65+)',
            rendimento=dec13_isento, tipo_rendimento='Isento')

    # ── Quadro 5: Tributação Exclusiva ────────────────────────────────────────
    q5 = _section(r'TRIBUTA[CÇ][ÃA]O EXCLUSIVA',
                  r'RENDIMENTOS RECEBIDOS ACUMULADAMENTE|INFORMA[CÇ][ÕO]ES COMPLEMENTARES')
    dec13   = _val_in(q5, 1)
    irrf_13 = _val_in(q5, 2)

    if dec13:
        add('Rendimentos Tributação Exclusiva', '', 'Rendimentos Exclusivos',
            '01', '13º Salário',
            rendimento=dec13, irrf=irrf_13, tipo_rendimento='Tributação Exclusiva')

    if not entries:
        add('Rendimentos Tributáveis PJ', '', 'Proventos de Aposentadoria/Pensão',
            '01', 'Total dos Rendimentos (zerado)',
            valor_2025=0.0, tipo_rendimento='Tributável')

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _grupo_desc(grupo: str) -> str:
    return {
        '01': 'Bens Imóveis', '02': 'Bens Móveis',
        '03': 'Participações Societárias', '04': 'Aplicações e Investimentos',
        '05': 'Créditos e Empréstimos', '06': 'Depósito à Vista e Numerário',
        '07': 'Fundos', '08': 'Criptoativos', '99': 'Outros Bens e Direitos',
    }.get(grupo.strip(), 'Bens e Direitos')


def _extract_between(text: str, start_marker: str, end_marker: str) -> str:
    """Return the text between two markers (case-insensitive)."""
    s = re.search(re.escape(start_marker), text, re.IGNORECASE)
    e = re.search(re.escape(end_marker), text, re.IGNORECASE)
    if not s:
        return ''
    end_pos = e.start() if e and e.start() > s.start() else len(text)
    return text[s.start():end_pos]


def _xp_summary_rows(block: str) -> list[tuple[str, float, float, float]]:
    """Extract (description, val_2024, val_2025, rendimento) rows from an XP summary block."""
    rows = []
    # Match lines like: "Description 62.371,82 67.562,19 5.133,46"
    row_re = re.compile(
        r'^([A-Za-záéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ /()0-9.-]{3,60}?)\s+'
        r'([\d.]+,\d{2})\s+([\d.]+,\d{2})(?:\s+([\d.]+,\d{2}))?',
        re.MULTILINE,
    )
    for m in row_re.finditer(block):
        desc = clean(m.group(1))
        if any(skip in desc for skip in ('Declaração', 'IRPF', 'Ficha', 'Especificação',
                                          'Saldos em', 'Valores em', 'Total:')):
            continue
        v24 = parse_brl(m.group(2))
        v25 = parse_brl(m.group(3))
        rend = parse_brl(m.group(4)) if m.group(4) else 0.0
        rows.append((desc, v24, v25, rend))
    return rows


def _detect_cnpj_in_block(block: str, cnpj_names: dict) -> str:
    """Return the first known CNPJ found in *block*."""
    for c in cnpj_names:
        if c in block:
            return c
    # Fallback: first CNPJ found
    m = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', block)
    return m.group(0) if m else ''
