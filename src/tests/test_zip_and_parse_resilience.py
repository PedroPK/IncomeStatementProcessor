"""Resilience tests for ZIP extraction and per-file parse failures."""

from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

from src.extractor import extract_zip
from src import main


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
