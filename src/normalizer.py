"""Value normalisation utilities."""
import re


_CNPJ_RE = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
_CPF_RE = re.compile(r'\d{3}[\.*]{3}[\.*]{3}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}')
_BRL_RE = re.compile(r'[\d.]+,\d{2}')


def parse_brl(value: str) -> float:
    """Convert a Brazilian monetary string to float.

    Examples::
        parse_brl("1.234,56") -> 1234.56
        parse_brl("R$ 1.234,56") -> 1234.56
        parse_brl("-") -> 0.0
        parse_brl("–") -> 0.0
    """
    if not value:
        return 0.0
    value = str(value).strip()
    if value in ("-", "–", ""):
        return 0.0
    # Strip "R$" and whitespace
    value = re.sub(r'R\$\s*', '', value).strip()
    m = _BRL_RE.search(value)
    if not m:
        return 0.0
    raw = m.group(0)
    raw = raw.replace('.', '').replace(',', '.')
    try:
        return float(raw)
    except ValueError:
        return 0.0


def clean(text: str) -> str:
    """Collapse multiple whitespace characters into a single space."""
    return re.sub(r'\s+', ' ', (text or '').strip())


def extract_year(text: str, default: int = 2025) -> int:
    """Extract reference year from text like 'Ano-Calendário 2025'."""
    m = re.search(r'(?:ano[- ]calend[aá]rio|ano\s+base)[^\d]*(\d{4})', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'\bIRPF(\d{4})\b', text, re.IGNORECASE)
    if m:
        return int(m.group(1)) - 1
    return default


def find_cpf(text: str) -> str:
    """Return first CPF found in *text*, or empty string.
    
    Matches both formatted (XXX.XXX.XXX-XX) and unformatted (XXXXXXXXXXX) CPFs.
    Returns in formatted style: XXX.XXX.XXX-XX
    """
    m = _CPF_RE.search(text or '')
    if not m:
        return ''
    cpf = m.group(0)
    # Normalize to XXX.XXX.XXX-XX format
    digits = re.sub(r'\D', '', cpf)
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return cpf


def find_cnpj(text: str) -> str:
    """Return first CNPJ found in *text*, or empty string."""
    m = _CNPJ_RE.search(text or '')
    return m.group(0) if m else ''


def find_all_cnpj(text: str) -> list[str]:
    return _CNPJ_RE.findall(text or '')


def find_all_cpf(text: str) -> list[str]:
    """Return all CPFs found in *text* in formatted style."""
    matches = _CPF_RE.findall(text or '')
    result = []
    for cpf in matches:
        digits = re.sub(r'\D', '', cpf)
        if len(digits) == 11:
            result.append(f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}')
        else:
            result.append(cpf)
    return result


def _is_valid_name(text: str, min_ratio: float = 0.65) -> bool:
    """Check if text looks like a person's name (mostly letters and spaces)."""
    if not text or len(text) < 4:
        return False
    letter_ratio = sum(1 for c in text if c.isalpha() or c == ' ') / len(text)
    return letter_ratio >= min_ratio


def extract_taxpayer_info(text: str) -> tuple[str, str]:
    """Extract taxpayer name and CPF from document header.

    Handles multiple real-world PDF formats:
    - Avenue:  "CPF : 11927011353 Nome : Ana Gloria Ferreira Silva"
    - FACHESF: Name and CPF on separate lines without spaces
               "ANAGLORIAFERREIRASILVA" then "119.270.113-53 BENEFICIO..."
    - INSS:    "119.270.113-53 ANA GLORIA FERREIRA SILVA 135.050.353-0"
    - NuBank:  "Ana Gloria Ferreira Silva 119.***.***-53"
    - Clear/XP: "PEDRO CARLOS FERREIRA SANTOS 039.821.084-54"

    Returns: (nome_contribuinte, cpf_contribuinte)
    """
    nome = ""
    cpf = ""

    if not text:
        return nome, cpf

    lines = text.split('\n')

    # ── Step 1: Extract CPF ──────────────────────────────────────────────────
    # Try formatted CPF first (with dots), then masked, then raw 11-digit
    cpf_re_formatted = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
    cpf_re_masked = re.compile(r'\d{3}\.\*+\.\*+-\d{2}')
    cpf_re_raw = re.compile(r'(?<!\d)(\d{11})(?!\d)')

    for cpf_re in (cpf_re_formatted, cpf_re_masked, cpf_re_raw):
        m = cpf_re.search(text)
        if m:
            cpf_raw = m.group(0)
            digits = re.sub(r'\D', '', cpf_raw)
            if len(digits) == 11:
                cpf = f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
            else:
                cpf = cpf_raw
            break

    # ── Step 2: Extract Name from first 25 lines ─────────────────────────────
    for i, line in enumerate(lines[:25]):
        s = line.strip()
        if not s or len(s) < 3:
            continue

        # Pattern A: "Nome : <name>" or "Nome: <name>" (Avenue style)
        m = re.search(r'[Nn]ome\s*:\s*(.+?)(?:\s*$)', s)
        if m:
            candidate = clean(m.group(1)).strip()
            if _is_valid_name(candidate, 0.7):
                nome = candidate
                break

        # Pattern B: name and formatted/masked CPF on same line
        for cpf_re in (cpf_re_formatted, cpf_re_masked):
            m = cpf_re.search(s)
            if not m:
                continue

            before = s[:m.start()].strip()
            after = s[m.end():].strip()

            # Remove common label prefixes from `before`
            before_clean = re.sub(
                r'^(?:CPF[E]?|Pessoa\s+[Ff]ísica|Beneficiário)[:\s]*',
                '', before, flags=re.IGNORECASE
            ).strip()

            if before_clean and _is_valid_name(before_clean):
                nome = before_clean
                break

            # Name may come after CPF (e.g. INSS: "119.270.113-53 ANA GLORIA...")
            if after:
                # Strip leading benefit numbers or other digits
                after_clean = re.sub(r'^\d[\d.\-/]*\s*', '', after).strip()
                if after_clean and _is_valid_name(after_clean):
                    nome = after_clean
                    break

        if nome:
            break

    # ── Step 3: FACHESF-style — name on its own line, CPF on nearby line ────
    # Name is all-caps letters with no spaces (PDF glues words), CPF is nearby
    if not nome and cpf:
        for i, line in enumerate(lines[:25]):
            s = line.strip()
            if not s or len(s) < 5:
                continue
            # Skip lines that contain digits or punctuation typical of non-names
            if re.search(r'\d', s):
                continue
            # The line must be almost entirely letters (no spaces = glued words)
            letter_ratio = sum(1 for c in s if c.isalpha()) / len(s)
            if letter_ratio >= 0.9 and s.isupper() and len(s) >= 10:
                nome = s
                break

    # ── Step 4: Fallback — explicit label patterns ───────────────────────────
    if not nome:
        fallback_patterns = [
            r'[Cc]ontribuinte[:\s]+([^\n/|]+?)(?:\s+CPF|$)',
            r'[Dd]eclarante[:\s]+([^\n/|]+?)(?:\s+CPF|$)',
            r'[Bb]enefici[aá]rio[:\s]+([^\n/|]+?)(?:\s+CPF|$)',
            r'(?:CPF|CNPJ)[^\n]*\n\s*([A-ZÁÉÍÓÚ][^\n]{3,50})(?:\s+\d{3}|$)',
        ]
        for pattern in fallback_patterns:
            m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if m:
                candidate = clean(m.group(1)).strip()
                if _is_valid_name(candidate, 0.6):
                    nome = candidate
                    break

    return nome, cpf
