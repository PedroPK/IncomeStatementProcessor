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


def find_cnpj(text: str) -> str:
    """Return first CNPJ found in *text*, or empty string."""
    m = _CNPJ_RE.search(text or '')
    return m.group(0) if m else ''


def find_all_cnpj(text: str) -> list[str]:
    return _CNPJ_RE.findall(text or '')


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
