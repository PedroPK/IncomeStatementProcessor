"""Orchestration: ZIP → parse → XLSX (+ optional Google Sheets)."""
from __future__ import annotations

import os
import sys
import tempfile
import shutil
from pathlib import Path

# ── Config loading (Python 3.11+ has tomllib built-in) ───────────────────────
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from src.extractor import extract_zip, find_zip
from src.parser import parse_file
from src.xlsx_writer import write_xlsx


# ── Supported file extensions ─────────────────────────────────────────────────
_PDF_EXTENSIONS = {'.pdf', '.aspx', '.asp'}   # ASPX is served as PDF by some portals


def load_config(path: str = 'config.toml') -> dict:
    if tomllib is None:
        print('[aviso] tomllib/tomli não disponível – usando configuração padrão.')
        return _default_config()
    if not os.path.exists(path):
        print(f'[aviso] {path} não encontrado – usando configuração padrão.')
        return _default_config()
    with open(path, 'rb') as fh:
        return tomllib.load(fh)


def _default_config() -> dict:
    return {
        'output': {'xlsx_path': 'output/informes_rendimentos.xlsx'},
        'google_sheets': {'enabled': False},
    }


def main() -> None:
    # ── Load config ───────────────────────────────────────────────────────────
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else 'config.toml'
    config = load_config(cfg_path)

    xlsx_path = config.get('output', {}).get('xlsx_path', 'output/informes_rendimentos.xlsx')
    gs_config = config.get('google_sheets', {})

    # ── Find ZIP in input/ ────────────────────────────────────────────────────
    zip_path = find_zip('input')
    if not zip_path:
        print('[erro] Nenhum arquivo ZIP encontrado em input/. Encerrando.')
        sys.exit(1)
    print(f'ZIP encontrado: {zip_path}')

    # ── Extract ───────────────────────────────────────────────────────────────
    print('Extraindo arquivos...')
    file_map = extract_zip(zip_path)
    print(f'  {len(file_map)} arquivo(s) extraído(s).')

    # ── Parse each file ───────────────────────────────────────────────────────
    all_entries = []
    errors = []

    for filename, filepath in sorted(file_map.items()):
        ext = Path(filename).suffix.lower()
        if ext not in _PDF_EXTENSIONS:
            print(f'  [ignorado] {filename} (extensão não suportada: {ext})')
            continue

        print(f'  Processando: {filename}')
        entries = parse_file(filepath)

        if not entries:
            print(f'    [aviso] Nenhuma entrada extraída de {filename}')
            errors.append(filename)
            continue

        err_entries = [e for e in entries if e.secao in ('Erro', 'Desconhecido')]
        ok_entries  = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]

        if err_entries:
            for e in err_entries:
                print(f'    [aviso] {e.observacao}')
            errors.append(filename)

        print(f'    → {len(ok_entries)} entradas extraídas.')
        all_entries.extend(ok_entries)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f'\nTotal: {len(all_entries)} entradas de {len(file_map)} arquivo(s).')
    if errors:
        print(f'Arquivos com problemas: {", ".join(errors)}')

    if not all_entries:
        print('[erro] Nenhuma entrada válida. Encerrando sem gerar planilha.')
        sys.exit(1)

    # ── Write XLSX ────────────────────────────────────────────────────────────
    print('\nGerando planilha XLSX...')
    write_xlsx(all_entries, xlsx_path)

    # ── Generate Dashboard ────────────────────────────────────────────────────
    print('Gerando dashboard HTML...')
    from src.dashboard_generator import generate_dashboard_html
    dashboard_path = config.get('output', {}).get('dashboard_path', 'dashboard.html')
    generate_dashboard_html(all_entries, dashboard_path)

    # ── Optional Google Sheets ────────────────────────────────────────────────
    if gs_config.get('enabled', False):
        print('\nEnviando para Google Sheets...')
        from src.sheets_writer import push_to_sheets
        push_to_sheets(all_entries, gs_config)

    print('\nConcluído!')


if __name__ == '__main__':
    main()
