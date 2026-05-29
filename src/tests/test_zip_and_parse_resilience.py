"""Resilience tests for ZIP extraction and per-file parse failures."""

from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

from src.extractor import extract_zip
from src import main
from src.parser import detect_institution, parse_comprovante_rendimentos
from src.normalizer import extract_taxpayer_info


def test_extract_zip_ignores_macos_artifacts(tmp_path: Path) -> None:
    """Ignore AppleDouble and metadata entries that are not real documents."""
    zip_path = tmp_path / 'input.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('__MACOSX/._Avenue.pdf', b'not-a-real-pdf')
        zf.writestr('._Avenue.pdf', b'not-a-real-pdf')
        zf.writestr('.DS_Store', b'finder-metadata')
        zf.writestr('Avenue.pdf', b'%PDF-1.7 real-content')

    extracted = extract_zip(str(zip_path))

    assert 'Avenue.pdf' in extracted
    assert all(not name.startswith('._') for name in extracted)
    assert '.DS_Store' not in extracted


def test_parse_file_map_continues_when_single_pdf_fails(monkeypatch) -> None:
    """A single invalid PDF should be reported but should not abort the whole batch."""

    def fake_parse(path: str):
        if path.endswith('bad.pdf'):
            raise RuntimeError('No /Root object! - Is this really a PDF?')
        return [SimpleNamespace(secao='Bens e Direitos', observacao='ok')]

    monkeypatch.setattr(main, 'parse_file', fake_parse)

    file_map = {
        'bad.pdf': '/tmp/bad.pdf',
        'ok.pdf': '/tmp/ok.pdf',
    }

    entries, errors, processed, total = main._parse_file_map(file_map)

    assert total == 2
    assert processed == 2
    assert 'bad.pdf' in errors
    assert len(entries) == 1


def test_parse_file_map_ignores_dot_underscore_entries(monkeypatch) -> None:
    """AppleDouble filenames should be skipped even if they end with .pdf/.xlsx."""

    def fake_parse(_: str):
        return [SimpleNamespace(secao='Bens e Direitos', observacao='ok')]

    monkeypatch.setattr(main, 'parse_file', fake_parse)

    file_map = {
        '._Avenue.pdf': '/tmp/._Avenue.pdf',
        'Avenue.pdf': '/tmp/Avenue.pdf',
        '._Custodia.xlsx': '/tmp/._Custodia.xlsx',
    }

    entries, errors, processed, total = main._parse_file_map(file_map)

    assert total == 1
    assert processed == 1
    assert errors == []
    assert len(entries) == 1


# ─────────────────────────────────────────────────────────────────────────────
# detect_institution – Comprovante RFB format
# ─────────────────────────────────────────────────────────────────────────────

def test_detect_institution_comprovante_rfb() -> None:
    """Text with 'COMPROVANTE DE RENDIMENTOS' and 'RAZÃO SOCIAL / NOME:' is detected."""
    first_page = (
        'COMPROVANTE DE RENDIMENTOS\n'
        'MINISTÉRIO DA FAZENDA PAGOS E DE\n'
        'SECRETARIA DA RECEITA FEDERAL RETENÇÃO DE IMPOSTO DE RENDA NA FONTE\n'
        '1 - FONTE PAGADORA PESSOA JURÍDICA\n'
        'CNPJ: 45.694.193/0001-66 RAZÃO SOCIAL / NOME: PREVIDENCIA SPSM\n'
    )
    assert detect_institution('qualquer_arquivo.pdf', first_page) == 'comprovante_rendimentos'


def test_detect_institution_comprovante_rfb_not_triggered_without_marker() -> None:
    """Without both required markers the format should NOT be detected."""
    first_page = 'COMPROVANTE DE RENDIMENTOS\nSem o campo razão social aqui'
    result = detect_institution('qualquer_arquivo.pdf', first_page)
    assert result != 'comprovante_rendimentos'


def test_detect_institution_known_names_still_take_priority() -> None:
    """Known filename patterns win over the generic RFB marker."""
    first_page = (
        'COMPROVANTE DE RENDIMENTOS\n'
        'CNPJ: 16.727.230/0001-97 RAZÃO SOCIAL / NOME: INSS\n'
    )
    # 'inss' in filename → should detect as 'inss', not generic comprovante
    assert detect_institution('INSS - extrato-ir.pdf', first_page) == 'inss'


# ─────────────────────────────────────────────────────────────────────────────
# parse_comprovante_rendimentos – value extraction
# ─────────────────────────────────────────────────────────────────────────────

# Minimal synthetic text mirroring the NPS/Funame PDF layout
_COMPROVANTE_PAGE = """\
COMPROVANTE DE RENDIMENTOS
MINISTÉRIO DA FAZENDA PAGOS E DE
SECRETARIA DA RECEITA FEDERAL RETENÇÃO DE IMPOSTO DE RENDA NA FONTE
1 - FONTE PAGADORA PESSOA JURÍDICA
CNPJ: 45.694.193/0001-66 RAZÃO SOCIAL / NOME: PREVIDENCIA SPSM
ENDEREÇO: Rua Exemplo 100 CIDADE: RECIFE UF: PE
2 - PESSOA FÍSICA BENEFICIÁRIA DOS RENDIMENTOS:
NATUREZA DE RENDIMENTO: Aposentadoria ANO CALENDÁRIO: 2025 CPF: 264.957.244-20
NOME COMPLETO:JOSEFA NELITA BARBOSA DOS SANTOS MATRÍCULA: 1850709/02
3 - RENDIMENTOS TRIBUTÁVEIS, DEDUÇÕES E IMPOSTO RETIDO NA FONTE: VALORES EM REAL
01 - TOTAL DOS RENDIMENTOS 45.085,56
02 - CONTRIBUIÇÃO PREVIDÊNCIA OFICIAL 7.133,04
03 - CONTRIBUIÇÃO À PREVIDÊNCIA PRIVADA E A FAPI 0,00
04 - PENSÃO ALIMENTÍCIA 0,00
05 - IMPOSTO RETIDO NA FONTE (IRRF) 998,48
4 - RENDIMENTOS ISENTOS E NÃO TRIBUTÁVEIS: VALORES EM REAL
01 - PARCELA ISENTA DOS PROVENTOS DE APOSENTADORIA,RESERVA REMUNERADA, REFORMA E PENSÃO (65ANOS OU
22.847,76
MAIS), EXCETO A PARCELA ISENTA DO 13.(DÉCIMO TERCEIRO ) SALÁRIO
02 - PARCELA ISENTA DO 13.SALÁRIO DE APOSENTADORIA, RESERVA REMUNERADA, REFORMA E PENSÃO (65 ANOS OU MAIS) 1.903,98
5 - RENDIMENTOS SUJEITOS À TRIBUTAÇÃO EXCLUSIVA (LÍQUIDO) VALORES EM REAL
01 - DÉCIMO TERCEIRO SALÁRIO 3.084,38
02 - IMPOSTO, SOBRE A RENDA RETIDO NA FONTE SOBRE 13.SALÁRIO 78,33
"""


def test_comprovante_q3_tributaveis() -> None:
    """Quadro 3 values are extracted correctly."""
    entries = parse_comprovante_rendimentos(
        'NPS Funame.pdf', [_COMPROVANTE_PAGE], [[]]
    )
    q3 = {e.codigo: e for e in entries if e.secao == 'Rendimentos Tributáveis PJ'}

    assert q3['01'].valor_2025 == 45085.56
    assert q3['02'].valor_2025 == 7133.04
    assert q3['05'].irrf == 998.48


def test_comprovante_q4_isentos() -> None:
    """Quadro 4 values — including wrapped-line value — are extracted correctly."""
    entries = parse_comprovante_rendimentos(
        'NPS Funame.pdf', [_COMPROVANTE_PAGE], [[]]
    )
    q4 = {e.codigo: e for e in entries if e.secao == 'Rendimentos Isentos'}

    assert q4['01'].rendimento == 22847.76   # value on continuation line
    assert q4['06'].rendimento == 1903.98


def test_comprovante_q5_exclusiva() -> None:
    """Quadro 5 13º salário and its IRRF are extracted correctly."""
    entries = parse_comprovante_rendimentos(
        'NPS Funame.pdf', [_COMPROVANTE_PAGE], [[]]
    )
    q5 = {e.codigo: e for e in entries
          if e.secao == 'Rendimentos Tributação Exclusiva'}

    assert q5['01'].rendimento == 3084.38
    assert q5['01'].irrf == 78.33


def test_comprovante_institution_and_year() -> None:
    """Institution name, CNPJ and year are populated from the header."""
    entries = parse_comprovante_rendimentos(
        'NPS Funame.pdf', [_COMPROVANTE_PAGE], [[]]
    )
    e = entries[0]
    assert e.instituicao == 'PREVIDENCIA SPSM'
    assert e.cnpj_instituicao == '45.694.193/0001-66'
    assert e.ano_calendario == 2025


def test_comprovante_zero_values_not_emitted() -> None:
    """Items with value 0,00 should not generate entries."""
    entries = parse_comprovante_rendimentos(
        'NPS Funame.pdf', [_COMPROVANTE_PAGE], [[]]
    )
    # Items 03 and 04 of Q3 are zero — they must not appear
    q3_codigos = [e.codigo for e in entries if e.secao == 'Rendimentos Tributáveis PJ']
    assert '03' not in q3_codigos
    assert '04' not in q3_codigos


# ─────────────────────────────────────────────────────────────────────────────
# extract_taxpayer_info – NOME COMPLETO: pattern
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_taxpayer_nome_completo_label() -> None:
    """NOME COMPLETO: on a separate line after a CPF-bearing line is extracted correctly."""
    text = (
        'NATUREZA DE RENDIMENTO: Aposentadoria ANO CALENDÁRIO: 2025 CPF: 264.957.244-20\n'
        'NOME COMPLETO:JOSEFA NELITA BARBOSA DOS SANTOS MATRÍCULA: 1850709/02\n'
    )
    nome, cpf = extract_taxpayer_info(text)
    assert nome == 'JOSEFA NELITA BARBOSA DOS SANTOS'
    assert cpf == '264.957.244-20'


def test_extract_taxpayer_nome_completo_rejects_header_label() -> None:
    """'NOME COMPLETO: Uso Interno:' (column header) must not be used as taxpayer name."""
    text = (
        'CNPJ/CPF: Nome da Empresa/Nome Completo: Uso Interno:\n'
        '16.727.230/0001-97 Fundo do Regime Geral de Previdência Social - FRGPS\n'
        'CPF: Nome Completo: Número do Benefício:\n'
        '264.957.244-20 JOSEFA NELITA BARBOSA DOS SANTOS 162.830.318-0\n'
    )
    nome, cpf = extract_taxpayer_info(text)
    assert 'Uso Interno' not in nome
    assert 'JOSEFA' in nome
    assert cpf == '264.957.244-20'

