# Parser Flow Diagram & Clear Document Mapping

## Overall Parser Architecture

```
PDF File Input
     ↓
parse_file(filepath)
     ├─ Extract filename
     ├─ pdfplumber.open()
     │  ├─ pages_text = [text per page]
     │  └─ pages_tables = [tables per page]
     ├─ detect_institution(filename, pages_text[0])
     │  └─ Match against filename/header patterns
     └─ Dispatch to parser_fn: parse_<institution>(...)
          ├─ Error handling: Return Entry with observacao
          └─ Success: Return list[Entry]
               ↓
          Excel/Sheets Writer
```

## Detailed parse_xp() Flow (Template for Clear)

```
parse_xp(filename, pages_text, pages_tables)
│
├─ PHASE 1: METADATA EXTRACTION
│  ├─ ano = extract_year(full_text)
│  ├─ cnpj_names = regex_search_all(
│  │   r'(XP Investimentos|Banco XP).*CNPJ (\d{2}\.\d{3}...)' 
│  │   )
│  └─ primary_inst, primary_cnpj = defaults
│
├─ PHASE 2: SUMMARY ENTRIES (Page 1, text-based)
│  │
│  ├─ _xp_parse_page1(...)
│  │  │
│  │  ├─ BLOCK 1: RENDIMENTOS ISENTOS (Código 12)
│  │  │  ├─ block = _extract_between(
│  │  │  │   'RENDIMENTOS ISENTOS', 'RENDIMENTOS SUJEITOS'
│  │  │  │  )
│  │  │  ├─ for row in _xp_summary_rows(block):
│  │  │  │   ├─ Extract: desc, val_2024, val_2025, rendimento
│  │  │  │   ├─ Create _entry(..., secao='Rendimentos Isentos',
│  │  │  │   │               codigo='12', tipo_rendimento='Isento')
│  │  │  │   └─ append to entries
│  │  │  └─ Result: ~2-10 Entry objects
│  │  │
│  │  ├─ BLOCK 2: RENDIMENTOS TRIBUTAÇÃO EXCLUSIVA (Código 06)
│  │  │  ├─ block = _extract_between(...)
│  │  │  └─ Same pattern → Entries with codigo='06'
│  │  │
│  │  └─ BLOCK 3: RENDIMENTOS TRIBUTÁVEIS (Código 01)
│  │     └─ Same pattern → Entries with codigo='01'
│  │
│  └─ Result: ~10-50 summary Entries
│
├─ PHASE 3: DETAIL ENTRIES (Pages 4–6, table-based)
│  │
│  ├─ _xp_parse_detail_tables(pages_tables[3:6], ...)
│  │  │
│  │  ├─ Step 3a: TAG TABLES
│  │  │  ├─ for table in tables:
│  │  │  │  ├─ If cell[0][0] contains "Declaração IRPF"
│  │  │  │  │  └─ tag = 'decl'
│  │  │  │  ├─ Else if contains "Ficha"
│  │  │  │  │  └─ tag = 'ficha'
│  │  │  │  ├─ Else if len(table[0]) >= 3 data-like
│  │  │  │  │  └─ tag = 'data'
│  │  │  │  └─ Else tag = 'other'
│  │  │  └─ Result: tagged = [(tag, table), ...]
│  │  │
│  │  ├─ Step 3b: EXTRACT DECLARATION METADATA
│  │  │  ├─ for each 'decl' table:
│  │  │  │  ├─ Extract: grupo = regex(r'Grupo (\d+)', cell)
│  │  │  │  ├─ Extract: codigo_raw = regex(r'Código (\d+)', cell)
│  │  │  │  ├─ Find associated 'ficha' table
│  │  │  │  ├─ From ficha cell: Extract CNPJ & section type
│  │  │  │  └─ Store in decl_info[decl_idx]
│  │  │  └─ Result: decl_info = {
│  │  │          0: {'grupo': '04', 'codigo_raw': '02', 'ficha_cnpj': '...', ...},
│  │  │          1: {...},
│  │  │        }
│  │  │
│  │  └─ Step 3c: PARSE DATA TABLES
│  │     ├─ for each 'data' table with index i:
│  │     │  ├─ Find owning declaration:
│  │     │  │  next_decl = next decl_idx > i
│  │     │  │  prev_decl = last decl_idx < i
│  │     │  │  own_decl = next_decl or prev_decl
│  │     │  │
│  │     │  ├─ Retrieve info = decl_info[own_decl]
│  │     │  ├─ for each row in table:
│  │     │  │  ├─ Skip headers & totals
│  │     │  │  ├─ Extract: desc_cell, val_2024, val_2025, rendimento
│  │     │  │  ├─ Determine codigo from row or info['codigo_raw']
│  │     │  │  ├─ Determine secao from ficha text
│  │     │  │  │  (e.g., 'Bens e Direitos', 'Rendimentos Tributação Exclusiva')
│  │     │  │  ├─ Map (grupo, codigo) → codigo_desc
│  │     │  │  │  ('04', '02') → 'Títulos públicos/privados (CDB, RDB, Tesouro)'
│  │     │  │  ├─ Create _entry(..., grupo, codigo, desc, valores)
│  │     │  │  └─ append to entries
│  │     │  └─ Result: ~100-1000 detail Entries
│  │     └─ return entries
│  │
│  └─ Result: ~100-1000 detail Entries
│
└─ RETURN: list[Entry] with ~110-1050 total entries
     └─ Each Entry ready for XLSX/Sheets writer
```

## Text Row Parsing Pattern

```python
# XP summary row regex:
_XP_ROW_PATTERN = r'^([A-Za-z...]{3,60}?)\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})(?:\s+([\d.]+,\d{2}))?'

# Parse result per row:
# "Dividendos - Ações 62.371,82 67.562,19 5.133,46"
#  ↓
# desc        = "Dividendos - Ações"
# val_2024    = 62371.82
# val_2025    = 67562.19
# rendimento  = 5133.46 (optional)
```

## Table Data Row Parsing Pattern

```python
# Typical Bens e Direitos table (XP detail):
# ┌────────────────────┬──────────┬──────────┬────────────┐
# │ Descrição          │ dez/2024 │ dez/2025 │ Rendimento │
# ├────────────────────┼──────────┼──────────┼────────────┤
# │ Ações: AAPL        │ 1.000,00 │ 1.100,00 │      100,00│
# │ ETF: BOVESPA       │ 5.000,00 │ 5.200,00 │      200,00│
# │ TOTAL              │ 6.000,00 │ 6.300,00 │      300,00│
# └────────────────────┴──────────┴──────────┴────────────┘

# Parse logic:
for row in table:
    if "TOTAL" in row[0]:
        continue  # skip footer
    desc = clean(row[0])
    val_2024 = parse_brl(row[1])    # → 1000.00
    val_2025 = parse_brl(row[2])    # → 1100.00
    rendimento = parse_brl(row[3])  # → 100.00
```

## Clear Document: Expected Structure & Parsing Strategy

### Scenario 1: Clear Issues Grupo/Código-Based Informe (like XP/Nubank)

```
Clear Informe de Rendimentos
├─ Page 1: Summary
│  ├─ Section: "Bens e Direitos em 31/12/2025"
│  │  ├─ Grupo XX – Tipo de Ativo
│  │  │  └─ Código YY – Subtipo
│  │  │     ├─ Ativo 1: 1.234,56
│  │  │     ├─ Ativo 2: 2.345,67
│  │  │     └─ Total: 3.580,23
│  │  └─ [repeat for other Grupos/Códigos]
│  │
│  └─ Section: "Rendimentos Tributação Exclusiva"
│     ├─ Dividendos: 1.000,00
│     ├─ Juros s/ Capital: 500,00
│     └─ Total: 1.500,00
│
└─ Pages 2+: Details (optional, like XP)
   └─ Ativo por ativo com Qtde, Preço, Rendimento
```

**Parse Strategy**:
- Use same `_extract_between()` pattern for sections
- Use Grupo/Código header regex (like Nubank) OR simpler asset-type mapping
- Reuse `_xp_summary_rows()` or variant for line parsing

### Scenario 2: Clear Issues Asset-Holdings-Only Informe (like Avenue)

```
Clear Carteira de Ativos
├─ Table 1: Ações
│  ├─ [TICKER, Qtde, Preço Médio, Valor Total (2025)]
│  ├─ AAPL      100    150,00    15.000,00
│  └─ PETR4     200     25,00     5.000,00
│
├─ Table 2: ETFs
│  ├─ IVVB11   1000     50,00    50.000,00
│  └─ ...
│
└─ Table 3: Rendimentos (dividends/income)
   ├─ [Source, Tipo, Valor]
   ├─ AAPL Dividends 100,00
   └─ PETR4 Dividends 200,00
```

**Parse Strategy**:
- Use table parsing (pdfplumber) like Avenue
- Tag tables: Skip headers, parse data rows, match rendimentos to holdings
- Map asset type (AÇÃO, ETF, CRYPTO) → grupo (03, 07, 08)

### Clear Asset Type → Grupo Mapping (Proposed)

```python
CLEAR_ASSET_MAP = {
    'AÇÃO': {
        'grupo': '03',
        'grupo_desc': 'Participações Societárias',
        'codigo': '01',  # or extracted from table
        'codigo_desc': 'Ações',
    },
    'ETF': {
        'grupo': '07',
        'grupo_desc': 'Fundos',
        'codigo': '08',
        'codigo_desc': 'Fundos de Índice (ETF)',
    },
    'FUNDO IMOBILIÁRIO': {
        'grupo': '07',
        'grupo_desc': 'Fundos',
        'codigo': '99',
        'codigo_desc': 'Outros Fundos (FII)',
    },
    'CRIPTO': {
        'grupo': '08',
        'grupo_desc': 'Criptoativos',
        'codigo': '01',
        'codigo_desc': 'Criptomoedas',
    },
    'RENDA FIXA': {
        'grupo': '04',
        'grupo_desc': 'Aplicações e Investimentos',
        'codigo': '02',
        'codigo_desc': 'Títulos públicos/privados',
    },
}
```

---

## Quick Reference: Existing Parser Strengths

| Parser | Strength | Reusable for Clear? |
|--------|----------|---------------------|
| **XP** | Dual-page (summary + detail), complex table tagging | ✅ Asset holdings + income sections |
| **Nubank** | Regex Grupo/Código header blocks, per-category parsing | ✅ If Clear uses structured sections |
| **Avenue** | Asset table parsing, symbol→tipo mapping | ✅ If Clear provides asset tables |
| **Accenture** | Text-based value extraction via patterns | ✅ For rendimentos summary parsing |
| **Inter** | Simpler Grupo/Código blocks, location handling | ✅ If Clear structure is cleaner |

---

## Implementation Pseudo-code for parse_clear()

```python
def parse_clear(filename: str, pages_text: list[str],
                pages_tables: list[list]) -> list[Entry]:
    entries = []
    full_text = '\n'.join(pages_text)
    
    # 1. METADATA
    inst = 'Clear Corretora'
    cnpj = '00.000.000/0000-00'  # placeholder or regex extract
    ano = extract_year(full_text)
    
    # 2. ROUTE TO SUB-PARSER BASED ON SECTION DETECTION
    if 'Bens e Direitos' in full_text:
        entries.extend(_parse_clear_assets(filename, pages_text, pages_tables, inst, cnpj, ano))
    
    if 'Rendimentos' in full_text or 'Dividendos' in full_text:
        entries.extend(_parse_clear_income(filename, pages_text, pages_tables, inst, cnpj, ano))
    
    # 3. ERROR HANDLING
    if not entries:
        entries.append(Entry(
            arquivo=filename, instituicao=inst,
            cnpj_instituicao=cnpj, ano_calendario=ano,
            secao='Aviso', grupo='', grupo_desc='',
            codigo='', codigo_desc='',
            observacao='Nenhuma seção reconhecida',
        ))
    
    return entries


def _parse_clear_assets(filename, pages_text, pages_tables, inst, cnpj, ano):
    """Parse Bens e Direitos section (asset holdings)."""
    entries = []
    full_text = '\n'.join(pages_text)
    
    # Extract "Bens e Direitos" block
    bd_block = _extract_between(full_text, 'Bens e Direitos', 'Rendimentos')
    
    # Option A: If Clear uses Grupo/Código headers (like XP/Nubank):
    # for m in GRUPO_CODIGO_RE.finditer(bd_block):
    #     grupo = m.group(1)
    #     codigo = m.group(3)
    #     # parse rows...
    
    # Option B: If Clear provides structured tables:
    # for table in pages_tables:
    #     for row in table:
    #         asset_type = row[0]  # e.g., "AÇÃO"
    #         desc = row[1]        # e.g., "AAPL"
    #         valor = parse_brl(row[-1])  # last column = BRL value
    #         grupo, codigo = CLEAR_ASSET_MAP[asset_type]
    #         entries.append(_entry(filename, inst, cnpj, ano,
    #                               'Bens e Direitos', grupo, ..., codigo, ...))
    
    return entries


def _parse_clear_income(filename, pages_text, pages_tables, inst, cnpj, ano):
    """Parse Rendimentos sections (dividends, interest, etc.)."""
    entries = []
    full_text = '\n'.join(pages_text)
    
    # Extract "Rendimentos" block(s)
    # for tipo_rend in ['Tributação Exclusiva', 'Isento']:
    #     block = _extract_between(full_text, f'Rendimentos {tipo_rend}', next_section)
    #     for row in _xp_summary_rows(block):  # reuse pattern
    #         entries.append(_entry(..., codigo='06', tipo_rendimento=tipo_rend))
    
    return entries
```

---

## Summary Table: Clear vs. Existing Parsers

| Aspect | XP | Nubank | Avenue | Inter | Clear (Proposed) |
|--------|----|----|--------|-------|-----------------|
| **Document Type** | Brazilian broker informe | Brazilian fintech | US broker | Brazilian bank | Brazilian broker |
| **Asset Sections** | Text + Tables | Grouped blocks | Structured tables | Simple blocks | ? (TBD) |
| **Rendimento Type** | Summary + Detail | Per-category totals | N/A | Explicit lines | ? (TBD) |
| **Reusable Pattern** | `_extract_between`, table tagging | Grupo/Código regex | Asset table parsing | Simpler blocks | All? (TBD) |
| **Entry Count** | 100–1000 | 10–100 | 10–100 | 20–200 | ? |

---

## Next Steps
1. **Obtain sample Clear informe PDF**
2. **Analyze document structure** (summary vs. detail, sections, table format)
3. **Choose primary reuse pattern** (XP, Nubank, or Avenue style)
4. **Implement parse_clear() with sub-parsers**
5. **Test and refine asset-type → grupo mapping**
6. **Add to dispatcher and detect_institution()**
