# Parser.py Analysis: Structure, Patterns & Clear Broker Applicability

## Overview
The `parser.py` module contains institution-specific PDF parsers for Brazilian "Informes de Rendimentos" (income statement documents). Each parser converts PDF text/tables into standardized `Entry` objects for IRPF (Brazilian tax return) data.

---

## 1. How `parse_xp()` Works

### Dual-Page Strategy
XP documents contain two distinct sections:
- **Page 1 (Summary)**: Rendimentos (income) totals aggregated by institution and CNPJ
- **Pages 4–6 (Detail)**: "Bens e Direitos" (assets) broken down per holding with per-asset values

### parse_xp() Flow

```
parse_xp(filename, pages_text, pages_tables)
├─ Extract year via regex: extract_year(full_text)
├─ Build CNPJ→Institution name mapping from header regex:
│  Pattern: "XP Investimentos CCTVM S/A ... CNPJ 02.332.886/0001-04"
├─ Call _xp_parse_page1() → Extract summary Rendimentos entries
│  ├─ Extract "RENDIMENTOS ISENTOS" block (Código 12)
│  ├─ Extract "RENDIMENTOS SUJEITOS À TRIBUTAÇÃO EXCLUSIVA" block (Código 06)
│  └─ Extract "RENDIMENTOS TRIBUTÁVEIS" block (Código 01)
├─ Call _xp_parse_detail_tables() → Extract Bens e Direitos entries
│  ├─ Collect tables from pages[3:6] (indices 3–5)
│  ├─ Tag tables: "decl" (Declaração rows), "ficha" (Ficha rows), "data" (actual holdings)
│  ├─ For each data table:
│  │  ├─ Find owning declaration (next decl or last seen decl)
│  │  ├─ Extract Grupo and Código from declaration cell
│  │  ├─ Extract associated Ficha table text & CNPJ
│  │  └─ Parse data rows: description, val_2024, val_2025, rendimento
│  └─ Map Grupo/Código to human-readable descriptions (CDB, LCI, ETF, etc.)
└─ Return list[Entry]
```

### Key Pattern Matching in parse_xp()

**Summary blocks** (page 1):
```python
_extract_between(text, 'RENDIMENTOS ISENTOS', 'RENDIMENTOS SUJEITOS')
→ returns block of text between markers (case-insensitive)

_xp_summary_rows(block)
→ regex: r'^([A-Za-z...]{3,60}?)\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})(?:\s+([\d.]+,\d{2}))?'
→ matches: Description | val_2024 | val_2025 | optional_rendimento
```

**Detail tables** (pages 4–6):
```python
Table detection: Look for cells containing "Declaração", "IRPF", "Ficha", "Bens"
Declaration pattern: r'Grupo\s+(\d+)' and r'[Cc]ód\.?\s*(\d+|ao lado)'
Ficha pattern: Extract CNPJ and section type (Bens vs Rendimentos)
Data rows: (description | val_2024 | val_2025 | rendimento)
```

---

## 2. General Structure of `parse_*()` Functions

### Function Signature (ALL parsers follow this)
```python
def parse_<institution>(filename: str, pages_text: list[str],
                        pages_tables: list[list]) -> list[Entry]:
    """
    Args:
        filename: Original PDF name
        pages_text: List of extracted text per page (concatenatable)
        pages_tables: List of extracted tables per page (from pdfplumber)
    Returns:
        list[Entry]: Zero or more standardized entries
    """
```

### Typical Parse Flow (ANY Parser)
1. **Metadata Extraction** (top of file)
   - Institution name (regex from filename or header text)
   - CNPJ (regex: `r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'`)
   - Year (function: `extract_year(text)` from normalizer module)

2. **Block/Section Identification** (middle)
   - Locate sections by marker (e.g., "RENDIMENTOS ISENTOS", "BENS E DIREITOS")
   - Extract subsections or tables between markers
   - Use regex to categorize table types

3. **Data Row Parsing** (inner loop)
   - For each row in a section/table:
     - Extract cells (description, monetary values, codes)
     - Parse Brazilian currency → float via `parse_brl()` helper
     - Handle optional columns (rendimento, IRRF, etc.)

4. **Entry Construction** (per row)
   - Use `_entry()` helper factory to build `Entry` object
   - Set common fields: arquivo, instituicao, cnpj_instituicao, ano_calendario, secao, grupo, codigo
   - Set optional fields: valor_2024, valor_2025, rendimento, irrf, tipo_rendimento, etc.

5. **Return** → `list[Entry]`

### Common Helper Patterns

| Helper | Purpose | Example |
|--------|---------|---------|
| `_extract_between(text, start, end)` | Find text block between two markers | `_extract_between(text, 'Bens e Direitos', 'Total:')` |
| `_val(pattern)` | Extract single monetary value from text | `_val(r'1\.\s+Total')` |
| `parse_brl(str)` | Convert "1.234,56" → 1234.56 | `parse_brl("1.234,56")` |
| `find_cnpj(text)` | Extract first CNPJ from text | `find_cnpj("CNPJ: 02.332.886/0001-04")` |
| `clean(text)` | Strip whitespace, normalize unicode | `clean("   Abc   ")` |
| `extract_year(text)` | Find 4-digit year in text | `extract_year("Informe 2025")` |
| `_entry(...)` | Create Entry object with defaults | See Entry factory section below |

---

## 3. Entry Object: Required & Optional Fields

### Entry Data Class (`models.py`)

**REQUIRED fields** (no default, must be set):
```python
arquivo: str              # Original filename
instituicao: str          # Human-readable institution name
cnpj_instituicao: str     # CNPJ of issuing institution (not fonte pagadora CNPJ)
ano_calendario: int       # Reference year (2024 or 2025)
secao: str                # Section category (see table below)
grupo: str                # Grupo code ("01"–"99", empty for Rendimentos)
grupo_desc: str           # Human description of grupo (e.g., "Aplicações e Investimentos")
codigo: str               # Código code ("01"–"99")
codigo_desc: str          # Human description of código (e.g., "Depósito em conta corrente")
```

**OPTIONAL fields** (defaults shown):
```python
fonte_pagadora: str = ""           # Payer institution name (may differ from instituicao)
cnpj_fonte: str = ""               # Payer CNPJ (may differ from cnpj_instituicao)
localizacao: str = "105 - Brasil"  # Country code; "249 - Estados Unidos" for US assets
discriminacao: str = ""            # Extra line-item detail (ticker, account number, etc.)
valor_2024: float = 0.0            # Position on 31/12/2024
valor_2025: float = 0.0            # Position on 31/12/2025
rendimento: float = 0.0            # Income earned/realized during period
tipo_rendimento: str = ""          # "Isento", "Tributação Exclusiva", "Tributável", "Dedução"
irrf: float = 0.0                  # IR Retido na Fonte (withholding tax)
observacao: str = ""               # Error message or note (for failed parses)
```

### Entry Factory Helper

```python
def _entry(filename, instituicao, cnpj_inst, ano,
           secao, grupo, grupo_desc, codigo, codigo_desc, **kwargs) -> Entry:
    """Constructs Entry with type conversions and defaults."""
    return Entry(
        arquivo=filename,
        instituicao=instituicao,
        cnpj_instituicao=cnpj_inst,
        ano_calendario=ano,
        secao=secao,
        grupo=grupo.zfill(2) if grupo.isdigit() else grupo,  # pad "1" → "01"
        grupo_desc=grupo_desc,
        codigo=codigo.zfill(2) if codigo.isdigit() else codigo,  # pad codes
        codigo_desc=codigo_desc,
        **kwargs  # fonte_pagadora, valor_2024, rendimento, etc.
    )
```

---

## 4. Existing Parser Patterns Applicable to Clear Broker

### Clear is a Brazilian broker focused on:
- Stocks (Ações)
- Options (Opções)
- Futures (Futuros)
- Currency (Forex)
- Cryptocurrencies
- ETFs

### Document Structure We'd Expect from Clear:

| Section | Likely Content | Parallels in Code |
|---------|---|---|
| **Bens e Direitos** | Held securities at year-end | Like Nubank/XP/Avenue asset holdings |
| **Rendimentos Tributados/Isentos** | Dividends, interest | Like XP summary blocks (Código 06, 12) |
| **Rendimentos de PJ** | Day-trading profits, options income | Like Accenture/XP (Código 01) |
| **Deduções** | Losses, fees | Like INSS pattern in Accenture |

### Patterns We Can REUSE from Existing Parsers

#### 1. **Summary Extraction** (from XP/Nubank model)
```python
# XP pattern: text-based summary with institution blocks
_extract_between(text, 'RENDIMENTOS ISENTOS', 'RENDIMENTOS SUJEITOS')
_xp_summary_rows(block)

# Nubank pattern: Grupo/Código header regex
_GRUPO_CODIGO_RE = re.compile(
    r'Grupo\s+(\d+)\s*[-–]\s*([^\n]+)\n\s*Código\s+(\d+)\s*[-–]\s*([^\n]+)',
    re.IGNORECASE,
)

# Clear likely: Similar headers, extract between sections
```

#### 2. **Table Parsing** (from Avenue/XP detail model)
```python
# Avenue: Parse asset tables with columns [symbol, qty, cost_USD, BRL_cost]
# Detect asset rows, then match with rendimento rows below

# XP detail: Tag tables (decl/ficha/data), match decl → ficha → data rows
# Clear likely: Similar multi-table structure with holdings & associated rendimentos

# General pattern:
for table in pages_tables:
    for row in table:
        if matches_header_pattern(row):
            continue  # skip header
        if matches_total_pattern(row):
            continue  # skip summary line
        extract_data_row(row)
```

#### 3. **CNPJ/Institution Detection** (from all parsers)
```python
# Clear CNPJ (if Brazilian clearing house): regex in document
cnpj_m = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', text)
cnpj = cnpj_m.group(1) if cnpj_m else 'CLEAR_DEFAULT_CNPJ'

# Institution name: from filename or document header
inst = 'Clear' if 'clear' in filename.lower() else extract_from_header(text)
```

#### 4. **Currency Parsing** (from all parsers)
```python
# All use same helper:
valor = parse_brl("1.234,56")  # → 1234.56
```

#### 5. **Year Extraction** (from all parsers)
```python
ano = extract_year(full_text)  # finds first 4-digit year, default 2025
```

---

## 5. Clear Document Parsing Strategy (Proposed)

### Step 1: Detect Clear and Classify Document Type
```python
def parse_clear(filename, pages_text, pages_tables):
    full_text = '\n'.join(pages_text)
    
    # Detect section type
    if 'Bens e Direitos' in full_text:
        return _parse_clear_assets(filename, pages_text, pages_tables)
    elif 'Rendimentos' in full_text or 'Dividendos' in full_text:
        return _parse_clear_rendimentos(filename, pages_text, pages_tables)
    else:
        return _parse_clear_generic(filename, pages_text, pages_tables)
```

### Step 2: Asset Holdings Parser (reuse Avenue/XP table logic)
```python
def _parse_clear_assets(filename, pages_text, pages_tables):
    entries = []
    # Expected columns per row:
    # [Código, Descrição, Qtde, Valor Unit., Valor Total]
    # OR for securities: [Ativo, Qtde, Custo Médio, Valor Atual]
    
    for page_tables in pages_tables:
        for table in page_tables:
            for row in table:
                # Extract (grupo, codigo, desc, valor_2024, valor_2025)
                # Map ativo type (STOCK → grupo 03, CRYPTO → grupo 08, etc.)
                # Create Entry with appropriate secao & grupo
```

### Step 3: Income/Rendimentos Parser (reuse XP/Nubank model)
```python
def _parse_clear_rendimentos(filename, pages_text, pages_tables):
    entries = []
    # Look for:
    # - Dividends (typically Código 06, Tributação Exclusiva)
    # - Interest (Código 01, Tributável)
    # - Losses (dedutível)
    # Pattern: Extract between section markers → parse rows → build Entries
```

### Step 4: Reusable Patterns for Clear
| Clear Section | Reuse Pattern | Entry Fields |
|---|---|---|
| Ativos em Carteira | Avenue asset table + XP detail table | secao='Bens', grupo=3/7/8/etc, rendimento=0 |
| Dividendos | XP summary block | secao='Rendimentos', codigo=06, tipo='Tributação Exclusiva' |
| Juros s/ Capital Próprio | XP summary block | secao='Rendimentos', codigo=06, tipo='Tributação Exclusiva' |
| Resultado da negociação | XP tributação exclusiva | secao='Rendimentos', codigo=06, tipo='Tributação Exclusiva' |
| Rendimentos Isentos | XP isentos block | secao='Rendimentos Isentos', codigo=12, tipo='Isento' |

---

## 6. Implementation Checklist for Clear Parser

- [ ] **Add `parse_clear` to dispatcher in `parse_file()`**
  ```python
  parsers = {
      ...existing...,
      'clear': parse_clear,
  }
  ```

- [ ] **Update `detect_institution()` to recognize Clear**
  ```python
  if 'clear' in fname.lower():
      return 'clear'
  ```

- [ ] **Define Grupo/Código mappings for Clear's asset types**
  ```python
  CLEAR_ASSET_TYPE_MAP = {
      'AÇÃO': ('03', 'Participações Societárias'),
      'ETF': ('07', 'Fundos'),
      'CRYPTO': ('08', 'Criptoativos'),
      'RENDIMENTO FIXO': ('04', 'Aplicações e Investimentos'),
  }
  ```

- [ ] **Test on sample Clear documents**
  - Verify correct Grupo/Código assignment
  - Confirm valor_2024/valor_2025 extraction
  - Check rendimento calculation for dividends/interest

---

## 7. Key Takeaways for Clear Integration

1. **Dual-Source Pattern Works**: Like XP, combine summary text blocks (page 1) + detail tables (pages 3+)
2. **Reuse Helpers**: `parse_brl()`, `extract_year()`, `clean()`, `find_cnpj()` are generic
3. **Section Detection**: Use text markers ("Bens e Direitos", "Rendimentos") to route parsing logic
4. **No New Entry Fields Needed**: Clear data fits existing `Entry` schema (grupo 03/04/07/08, codigo mapping)
5. **Table Tagging**: Like XP, tag tables (header/data/rendimento) to avoid parsing section headers as data
6. **Fallback Gracefully**: If parsing fails, return Entry with observacao="Parse error" rather than crash

---

## Appendix: Helper Functions in normalizer.py

```python
def parse_brl(s: str) -> float:
    """Convert "1.234,56" → 1234.56"""
    
def find_cnpj(text: str) -> str:
    """Extract first CNPJ from text, return ""  if none found"""
    
def clean(text: str) -> str:
    """Strip whitespace, normalize unicode (ç→c), remove excess spaces"""
    
def extract_year(text: str) -> int:
    """Find first 4-digit year in text, default to 2025"""
```

---

## Summary

The parser module uses a **flexible, regex-driven approach** with these core patterns:

| Aspect | Pattern |
|--------|---------|
| **Institution Detection** | Filename + text header regex → institution + CNPJ |
| **Section Finding** | Text markers + regex block extraction |
| **Data Extraction** | Regex row patterns → (description, val_2024, val_2025, rendimiento) |
| **Type Mapping** | Grupo/Código lookup → asset class + income type |
| **Entry Factory** | `_entry()` helper with typed zero-fills (grupo → "01") |
| **Error Handling** | Graceful return of partial/empty Entry with observacao |

**For Clear**: Reuse the XP + Nubank + Avenue patterns. Clear documents likely have similar structure (summary + detail tables), so a **targeted regex approach** with **stock/crypto asset type mapping** will work. No schema changes needed.
