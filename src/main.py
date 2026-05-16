"""Orchestration entrypoint with web-first flow and legacy CLI mode.

Default mode starts a local web UI where the user chooses between:
1) processing files already available in input/
2) drag-and-drop upload of PDF(s) or ZIP(s)

Use --cli to keep the previous behavior (process input/ immediately).
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Suppress noisy pdfminer font warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

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
from src.custodia_parser import parse_custodia_xlsx
from src.xlsx_writer import write_xlsx


# ── Supported file extensions ─────────────────────────────────────────────────
_PDF_EXTENSIONS = {'.pdf', '.aspx', '.asp'}   # ASPX is served as PDF by some portals
_XLSX_EXTENSIONS = {'.xlsx', '.xls'}


_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def _is_ignored_artifact(filename: str) -> bool:
    """Return True for metadata/resource files that should never be processed."""
    name = Path(filename).name
    if name in {'.DS_Store', 'Thumbs.db'}:
        return True
    if name.startswith('._'):
        return True
    return False


def _format_duration(seconds: float | None) -> str:
    """Format seconds as HH:MM:SS (or MM:SS for short durations)."""
    if seconds is None:
        return '--:--'
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    return f'{minutes:02d}:{secs:02d}'


def _create_job() -> str:
    """Create a new processing job and return its ID."""
    job_id = uuid.uuid4().hex
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            'job_id': job_id,
            'state': 'queued',
            'stage': 'Aguardando execução',
            'current_file': '',
            'processed_steps': 0,
            'total_steps': 0,
            'percent': 0.0,
            'elapsed_seconds': 0.0,
            'eta_seconds': None,
            'started_at_monotonic': None,
            'updated_at': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'terminal_last_line': 'Aguardando execução.',
            'result': None,
            'error': None,
        }
    return job_id


def _read_job(job_id: str) -> dict[str, Any] | None:
    """Safely return a shallow copy of job state."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def validate_single_taxpayer(entries: list) -> tuple[bool, str, dict[str, list[str]]]:
    """Validate that all entries belong to the same taxpayer.
    
    Args:
        entries: List of Entry objects
        
    Returns:
        (is_valid, message, conflicts_dict)
        - is_valid: True if all entries have same taxpayer info
        - message: Human-readable validation message
        - conflicts_dict: Dict with keys 'nome' and 'cpf', each containing 
                         list of distinct values found (empty if valid)
    """
    if not entries:
        return True, "Nenhuma entrada para validar", {}
    
    # Collect distinct taxpayer info from entries with data
    distinct_names = set()
    distinct_cpfs = set()
    files_by_name = {}
    files_by_cpf = {}
    
    for entry in entries:
        nome = entry.nome_contribuinte or ""
        cpf = entry.cpf_contribuinte or ""
        
        if nome:
            distinct_names.add(nome)
            if nome not in files_by_name:
                files_by_name[nome] = []
            files_by_name[nome].append(entry.arquivo)
        
        if cpf:
            distinct_cpfs.add(cpf)
            if cpf not in files_by_cpf:
                files_by_cpf[cpf] = []
            files_by_cpf[cpf].append(entry.arquivo)
    
    conflicts = {}
    messages = []
    
    # Check name consistency
    if len(distinct_names) > 1:
        conflicts['nome'] = sorted(distinct_names)
        conflicts_str = ", ".join(sorted(distinct_names))
        messages.append(f"⚠️  Nomes diferentes encontrados: {conflicts_str}")
    elif distinct_names:
        messages.append(f"✅ Nome do contribuinte: {distinct_names.pop()}")
    
    # Check CPF consistency  
    if len(distinct_cpfs) > 1:
        conflicts['cpf'] = sorted(distinct_cpfs)
        conflicts_str = ", ".join(sorted(distinct_cpfs))
        messages.append(f"⚠️  CPFs diferentes encontrados: {conflicts_str}")
    elif distinct_cpfs:
        messages.append(f"✅ CPF do contribuinte: {distinct_cpfs.pop()}")
    
    is_valid = len(distinct_names) <= 1 and len(distinct_cpfs) <= 1
    message = "\n".join(messages) if messages else "Validação concluída (sem dados de contribuinte)"
    
    return is_valid, message, conflicts


def _update_job(job_id: str, **updates: Any) -> None:
    """Patch job state with the provided fields."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job['updated_at'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')


def _build_progress_callback(job_id: str) -> Callable[[dict[str, Any]], None]:
    """Create a callback that updates both terminal and shared job state."""
    start_ts = time.monotonic()

    def _callback(event: dict[str, Any]) -> None:
        processed = int(event.get('processed_steps', 0) or 0)
        total = int(event.get('total_steps', 0) or 0)
        stage = str(event.get('stage', 'Processando'))
        current_file = str(event.get('current_file', ''))

        elapsed = max(time.monotonic() - start_ts, 0.0)
        percent = (processed / total * 100.0) if total > 0 else 0.0
        eta = None
        if processed > 0 and total > processed:
            remaining_steps = total - processed
            eta = (elapsed / processed) * remaining_steps

        filename_info = f' | arquivo: {current_file}' if current_file else ''
        line = (
            f'[progresso] {processed}/{total} ({percent:5.1f}%)'
            f' | etapa: {stage}'
            f'{filename_info}'
            f' | decorrido: {_format_duration(elapsed)}'
            f' | ETA: {_format_duration(eta)}'
        )
        print(line)

        _update_job(
            job_id,
            state='running',
            stage=stage,
            current_file=current_file,
            processed_steps=processed,
            total_steps=total,
            percent=percent,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            started_at_monotonic=start_ts,
            terminal_last_line=line,
        )

    return _callback


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


def _extract_broker_name(filename: str) -> str:
    """Extract broker/corretora name from filename.
    
    Examples:
        'ClearCustodia_2025.xlsx' -> 'Clear'
        'Custódia_XP.xlsx' -> 'XP'
    """
    name = Path(filename).stem.lower()
    
    # Common broker names to detect
    brokers = {
        'clear': 'Clear',
        'xp': 'XP Investimentos',
        'avenue': 'Avenue Securities',
        'inter': 'Banco Inter',
        'nubank': 'NuBank',
        'bradesco': 'Bradesco',
        'itau': 'Itaú',
        'accenture': 'Accenture',
    }
    
    for key, display_name in brokers.items():
        if key in name:
            return display_name
    
    # Default: use filename without extension
    return name.replace('custodia', '').replace('_', ' ').strip().title() or 'Custódia Personalizada'


def _detect_custody_year(filename: str) -> int:
    """Detect the custody reference year from the XLSX filename.

    Looks for patterns like "31 Dezembro 2024" or "Dezembro 2025" or
    "Custódia YYYY" in the filename.  Falls back to 2025 if nothing is found.
    """
    import re
    # Match "Dezembro YYYY" or "dezembro YYYY" (with optional "31 " before it)
    m = re.search(r'dezembro\s+(\d{4})', filename, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Fallback: last 4-digit year found before ".xlsx"
    years = re.findall(r'\b(20\d{2})\b', filename)
    if years:
        return int(years[-1])
    return 2025


def _merge_file_maps(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    """Merge two file maps, renaming duplicate keys deterministically."""
    for name, path in extra.items():
        candidate = name
        stem = Path(name).stem
        suffix = Path(name).suffix
        index = 1
        while candidate in base:
            candidate = f'{stem}_{index}{suffix}'
            index += 1
        base[candidate] = path
    return base


def _collect_upload_file_map(uploaded_paths: list[Path]) -> tuple[dict[str, str], list[tempfile.TemporaryDirectory]]:
    """Collect a normalized filename->path map from uploaded files.

    ZIP files are extracted and merged into the resulting file map.
    """
    file_map: dict[str, str] = {}
    temp_dirs: list[tempfile.TemporaryDirectory] = []

    for uploaded_path in uploaded_paths:
        suffix = uploaded_path.suffix.lower()
        if _is_ignored_artifact(uploaded_path.name):
            continue
        if suffix == '.zip':
            extracted = extract_zip(str(uploaded_path))
            _merge_file_maps(file_map, extracted)
            continue

        if suffix in _PDF_EXTENSIONS or suffix in _XLSX_EXTENSIONS:
            _merge_file_maps(file_map, {uploaded_path.name: str(uploaded_path)})

    return file_map, temp_dirs


def _parse_file_map(
    file_map: dict[str, str],
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[list, list[str], int, int]:
    """Parse PDFs/XLSX from an extracted file map and return entries/errors."""
    all_entries = []
    errors: list[str] = []
    pdf_files = [
        name for name in sorted(file_map)
        if Path(name).suffix.lower() in _PDF_EXTENSIONS and not _is_ignored_artifact(name)
    ]
    xlsx_files = [
        name for name in sorted(file_map)
        if Path(name).suffix.lower() in _XLSX_EXTENSIONS and not _is_ignored_artifact(name)
    ]

    processed = 0
    total = len(pdf_files) + len(xlsx_files)

    def notify(stage: str, current_file: str = '') -> None:
        if progress_callback is None:
            return
        progress_callback({
            'stage': stage,
            'current_file': current_file,
            'processed_steps': processed,
            'total_steps': total,
        })

    notify('Iniciando leitura dos arquivos')

    # Parse PDF files
    for filename in pdf_files:
        filepath = file_map[filename]

        print(f'  Processando: {filename}')
        notify('Processando arquivo PDF', filename)
        try:
            entries = parse_file(filepath)
        except Exception as exc:  # noqa: BLE001
            print(f'    [erro] Erro ao processar {filename}: {exc}')
            errors.append(filename)
            processed += 1
            notify('Arquivo PDF concluído com erro', filename)
            continue

        if not entries:
            print(f'    [aviso] Nenhuma entrada extraída de {filename}')
            errors.append(filename)
            processed += 1
            notify('Arquivo PDF concluído sem dados', filename)
            continue

        err_entries = [e for e in entries if e.secao in ('Erro', 'Desconhecido')]
        ok_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]

        if err_entries:
            for entry in err_entries:
                print(f'    [aviso] {entry.observacao}')
            errors.append(filename)

        print(f'    -> {len(ok_entries)} entradas extraídas.')
        all_entries.extend(ok_entries)
        processed += 1
        notify('Arquivo PDF concluído', filename)

    # Parse custody XLSX files
    if xlsx_files:
        for xlsx_filename in sorted(xlsx_files):
            ref_year = _detect_custody_year(xlsx_filename)
            print(f'  Processando custódia: {xlsx_filename} (ano de referência: {ref_year})')
            notify('Processando arquivo XLSX de custódia', xlsx_filename)
            try:
                xlsx_entries = parse_custodia_xlsx(
                    file_map[xlsx_filename],
                    instituicao=_extract_broker_name(xlsx_filename),
                    reference_year=ref_year,
                )
                if xlsx_entries:
                    print(f'    -> {len(xlsx_entries)} ativos em custódia extraídos.')
                    all_entries.extend(xlsx_entries)
                else:
                    print(f'    [aviso] Nenhum ativo extraído de {xlsx_filename}')
                    errors.append(xlsx_filename)
            except Exception as exc:  # noqa: BLE001
                print(f'    [erro] Erro ao processar {xlsx_filename}: {exc}')
                errors.append(xlsx_filename)

            processed += 1
            notify('Arquivo XLSX concluído', xlsx_filename)
    else:
        print('  [info] Nenhum arquivo XLSX de custódia encontrado.')

    return all_entries, errors, processed, total


def _run_pipeline(
    file_map: dict[str, str],
    config: dict,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict:
    """Run parse + outputs generation and return summary metadata."""
    xlsx_path = config.get('output', {}).get('xlsx_path', 'output/informes_rendimentos.xlsx')
    dashboard_path = config.get('output', {}).get('dashboard_path', 'output/dashboard.html')
    gs_config = config.get('google_sheets', {})
    has_sheets = bool(gs_config.get('enabled', False))

    parse_steps_expected = sum(1 for name in file_map if Path(name).suffix.lower() in (_PDF_EXTENSIONS | _XLSX_EXTENSIONS))
    total_steps = parse_steps_expected + 2 + (1 if has_sheets else 0)
    steps_done = 0

    def notify(stage: str, current_file: str = '') -> None:
        if progress_callback is None:
            return
        progress_callback({
            'stage': stage,
            'current_file': current_file,
            'processed_steps': steps_done,
            'total_steps': total_steps,
        })

    notify('Preparando pipeline')

    def parse_notify(event: dict[str, Any]) -> None:
        nonlocal steps_done
        parse_total = int(event.get('total_steps', 0) or 0)
        parse_processed = int(event.get('processed_steps', 0) or 0)
        # Keep parse progress aligned with global total (parse + output stages)
        steps_done = min(parse_processed, parse_total)
        if progress_callback is None:
            return
        progress_callback({
            'stage': event.get('stage', 'Processando arquivos'),
            'current_file': event.get('current_file', ''),
            'processed_steps': steps_done,
            'total_steps': total_steps,
        })

    all_entries, errors, parse_processed, parse_total = _parse_file_map(file_map, parse_notify)
    steps_done = min(parse_processed, parse_total)

    print(f'\nTotal: {len(all_entries)} entradas processadas.')
    if errors:
        print(f'Arquivos com problemas: {", ".join(errors)}')

    if not all_entries:
        raise RuntimeError('Nenhuma entrada válida. Encerrando sem gerar planilha.')

    # Validate that all entries belong to the same taxpayer
    print('\nValidando dados do contribuinte...')
    is_valid, validation_msg, conflicts = validate_single_taxpayer(all_entries)
    for line in validation_msg.split('\n'):
        print(f'  {line}')
    if not is_valid:
        print('\n⚠️  Aviso: Encontrados documentos de múltiplos contribuintes!')
        print(f'   Nomes: {", ".join(conflicts.get("nome", []))}')
        print(f'   CPFs: {", ".join(conflicts.get("cpf", []))}')
        print('   → Verifique se todos os documentos são da mesma pessoa.')

    print('\nGerando planilha XLSX...')
    notify('Gerando planilha XLSX')
    write_xlsx(all_entries, xlsx_path)
    steps_done += 1
    notify('Planilha XLSX concluída')

    print('Gerando dashboard HTML...')
    from src.dashboard_generator import generate_dashboard_html

    dashboard_dir = Path(dashboard_path).parent
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    notify('Gerando dashboard HTML')
    generate_dashboard_html(all_entries, dashboard_path)
    steps_done += 1
    notify('Dashboard HTML concluído')

    if has_sheets:
        print('\nEnviando para Google Sheets...')
        from src.sheets_writer import push_to_sheets

        notify('Enviando para Google Sheets')
        push_to_sheets(all_entries, gs_config)
        steps_done += 1
        notify('Google Sheets concluído')

    return {
        'entries': len(all_entries),
        'errors': errors,
        'xlsx_path': xlsx_path,
        'dashboard_path': dashboard_path,
        'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }


def _stepper_html() -> str:
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Income Statement Processor - Processamento</title>
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --ok: #2e7d32;
            --bg: #f5f7fb;
            --card: #ffffff;
            --text: #1f2937;
            --muted: #6b7280;
            --border: #dfe5f3;
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            color: var(--text);
            background: radial-gradient(circle at top right, #e6ecff 0%, var(--bg) 45%, #eff2fb 100%);
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }

        .hero {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: #fff;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 24px rgba(58, 74, 130, 0.25);
            margin-bottom: 18px;
        }

        .hero h1 {
            margin: 0;
            font-size: 1.6rem;
        }

        .hero p {
            margin: 6px 0 0;
            opacity: 0.9;
        }

        .stepper {
            display: flex;
            gap: 12px;
            margin: 16px 0 22px;
        }

        .step {
            flex: 1;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .step-index {
            width: 28px;
            height: 28px;
            border-radius: 999px;
            border: 2px solid var(--border);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: var(--muted);
            background: #fff;
        }

        .step.active {
            border-color: #b9c6f5;
            box-shadow: 0 3px 12px rgba(102, 126, 234, 0.15);
        }

        .step.active .step-index {
            border-color: var(--primary);
            color: #fff;
            background: var(--primary);
        }

        .step.done .step-index {
            border-color: var(--ok);
            background: var(--ok);
            color: #fff;
        }

        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 4px 16px rgba(11, 23, 61, 0.06);
        }

        .options {
            display: grid;
            gap: 10px;
            margin-top: 10px;
        }

        .option {
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
        }

        .option label {
            cursor: pointer;
            display: inline-flex;
            gap: 8px;
            align-items: center;
            font-weight: 600;
        }

        .option p {
            margin: 7px 0 0 26px;
            color: var(--muted);
            font-size: 0.92rem;
        }

        .dropzone {
            margin-top: 14px;
            border: 2px dashed #b9c6f5;
            border-radius: 12px;
            min-height: 130px;
            padding: 18px;
            display: none;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: #f8faff;
            color: var(--muted);
            transition: all 0.2s;
        }

        .dropzone.active {
            border-color: var(--primary);
            background: #edf2ff;
            color: var(--text);
        }

        .file-list {
            margin-top: 10px;
            font-size: 0.9rem;
            color: var(--muted);
            word-break: break-word;
        }

        .actions {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 16px;
        }

        button {
            border: 0;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: #fff;
            font-weight: 600;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .status {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .progress-panel {
            margin-top: 14px;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            background: #f8faff;
            display: none;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 0.9rem;
            color: var(--muted);
        }

        .progress-track {
            width: 100%;
            height: 12px;
            background: #e9eefc;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #d8e1fb;
        }

        .progress-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #4f46e5, #0ea5e9);
            transition: width 0.25s ease;
        }

        .progress-meta {
            margin-top: 8px;
            font-size: 0.88rem;
            color: var(--muted);
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 6px;
        }

        .progress-meta strong {
            color: var(--text);
        }

        .progress-file {
            margin-top: 8px;
            font-size: 0.9rem;
            color: #334155;
            word-break: break-word;
        }

        #step2 {
            display: none;
            margin-top: 14px;
        }

        .result {
            margin-top: 10px;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.92rem;
            background: #f4f6fb;
            border: 1px solid var(--border);
        }

        .result.error {
            background: #fff1f1;
            border-color: #f4b4b4;
            color: #7f1d1d;
        }

        iframe {
            width: 100%;
            min-height: 82vh;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: #fff;
        }

        @media (max-width: 768px) {
            .stepper { flex-direction: column; }
            iframe { min-height: 70vh; }
            .progress-meta { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>Income Statement Processor</h1>
            <p>Escolha a fonte dos arquivos e processe no passo 1. O dashboard atual aparece no passo 2.</p>
        </div>

        <div class="stepper">
            <div class="step active" id="stepIndicator1">
                <span class="step-index">1</span>
                <div>
                    <div><strong>Selecionar Fonte e Processar</strong></div>
                    <div class="status">Input ou drag-and-drop de PDF/ZIP</div>
                </div>
            </div>
            <div class="step" id="stepIndicator2">
                <span class="step-index">2</span>
                <div>
                    <div><strong>Visualizar Dashboard</strong></div>
                    <div class="status">Estrutura existente do dashboard</div>
                </div>
            </div>
        </div>

        <div class="card" id="step1">
            <h2 style="margin-top:0; font-size:1.2rem;">Passo 1: Como deseja processar?</h2>

            <div class="options">
                <div class="option">
                    <label>
                        <input type="radio" name="source" value="input" checked>
                        Usar arquivos da pasta input/
                    </label>
                    <p>Usa o primeiro ZIP encontrado em input/ como no fluxo atual.</p>
                </div>

                <div class="option">
                    <label>
                        <input type="radio" name="source" value="upload">
                        Arrastar PDF(s) ou ZIP com PDF(s)
                    </label>
                    <p>Envie um ou mais PDFs e/ou ZIPs para processamento imediato.</p>
                </div>
            </div>

            <div class="dropzone" id="dropzone">
                <div>
                    <div style="font-weight:600; color:#334155; margin-bottom:4px;">Solte arquivos aqui</div>
                    <div>Ou clique para selecionar PDF/ZIP/XLSX</div>
                    <input id="fileInput" type="file" multiple style="display:none;" accept=".pdf,.zip,.aspx,.asp,.xlsx,.xls">
                </div>
            </div>
            <div class="file-list" id="fileList"></div>

            <div class="actions">
                <button id="processBtn">Processar</button>
                <span class="status" id="statusText">Aguardando ação.</span>
            </div>

            <div class="progress-panel" id="progressPanel">
                <div class="progress-header">
                    <span id="progressStage">Aguardando...</span>
                    <strong id="progressPercent">0.0%</strong>
                </div>
                <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-meta">
                    <div>Concluídos: <strong id="progressCount">0/0</strong></div>
                    <div>Decorrido: <strong id="elapsedText">00:00</strong></div>
                    <div>ETA: <strong id="etaText">--:--</strong></div>
                    <div>Atualização: <strong id="updatedText">--</strong></div>
                </div>
                <div class="progress-file" id="currentFileText">Arquivo atual: -</div>
            </div>

            <div id="resultBox" class="result" style="display:none;"></div>
        </div>

        <div id="step2">
            <iframe id="dashboardFrame" title="Dashboard"></iframe>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let progressTimer = null;

        const sourceRadios = document.querySelectorAll('input[name="source"]');
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const processBtn = document.getElementById('processBtn');
        const statusText = document.getElementById('statusText');
        const resultBox = document.getElementById('resultBox');
        const step2 = document.getElementById('step2');
        const dashboardFrame = document.getElementById('dashboardFrame');
        const stepIndicator1 = document.getElementById('stepIndicator1');
        const stepIndicator2 = document.getElementById('stepIndicator2');
        const progressPanel = document.getElementById('progressPanel');
        const progressStage = document.getElementById('progressStage');
        const progressPercent = document.getElementById('progressPercent');
        const progressFill = document.getElementById('progressFill');
        const progressCount = document.getElementById('progressCount');
        const elapsedText = document.getElementById('elapsedText');
        const etaText = document.getElementById('etaText');
        const updatedText = document.getElementById('updatedText');
        const currentFileText = document.getElementById('currentFileText');

        function currentSource() {
            return document.querySelector('input[name="source"]:checked').value;
        }

        function refreshUploadVisibility() {
            const upload = currentSource() === 'upload';
            dropzone.style.display = upload ? 'flex' : 'none';
            if (!upload) {
                selectedFiles = [];
                fileList.textContent = '';
            }
        }

        function showFiles() {
            if (!selectedFiles.length) {
                fileList.textContent = 'Nenhum arquivo selecionado.';
                return;
            }
            fileList.textContent = 'Arquivos: ' + selectedFiles.map((f) => f.name).join(', ');
        }

        sourceRadios.forEach((radio) => {
            radio.addEventListener('change', refreshUploadVisibility);
        });

        dropzone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            selectedFiles = Array.from(fileInput.files || []);
            showFiles();
        });

        ['dragenter', 'dragover'].forEach((eventName) => {
            dropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                dropzone.classList.add('active');
            });
        });

        ['dragleave', 'drop'].forEach((eventName) => {
            dropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                dropzone.classList.remove('active');
            });
        });

        dropzone.addEventListener('drop', (event) => {
            selectedFiles = Array.from(event.dataTransfer.files || []);
            showFiles();
        });

        function setResult(message, isError = false) {
            resultBox.style.display = 'block';
            resultBox.textContent = message;
            if (isError) {
                resultBox.classList.add('error');
            } else {
                resultBox.classList.remove('error');
            }
        }

        function goToStep2(dashboardUrl) {
            stepIndicator1.classList.remove('active');
            stepIndicator1.classList.add('done');
            stepIndicator2.classList.add('active');
            step2.style.display = 'block';
            dashboardFrame.src = dashboardUrl;
            step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function formatDuration(seconds) {
            if (seconds === null || seconds === undefined) {
                return '--:--';
            }
            const total = Math.max(0, Math.floor(Number(seconds)));
            const hours = Math.floor(total / 3600);
            const minutes = Math.floor((total % 3600) / 60);
            const secs = total % 60;
            if (hours > 0) {
                return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }
            return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }

        function updateProgressPanel(payload) {
            progressPanel.style.display = 'block';

            const pct = Number(payload.percent || 0);
            const safePct = Math.max(0, Math.min(100, pct));
            progressStage.textContent = payload.stage || 'Processando...';
            progressPercent.textContent = `${safePct.toFixed(1)}%`;
            progressFill.style.width = `${safePct.toFixed(2)}%`;
            progressCount.textContent = `${payload.processed_steps || 0}/${payload.total_steps || 0}`;
            elapsedText.textContent = formatDuration(payload.elapsed_seconds);
            etaText.textContent = formatDuration(payload.eta_seconds);
            updatedText.textContent = payload.updated_at || '--';
            currentFileText.textContent = `Arquivo atual: ${payload.current_file || '-'}`;
        }

        function stopProgressPolling() {
            if (progressTimer) {
                clearInterval(progressTimer);
                progressTimer = null;
            }
        }

        function startProgressPolling(jobId) {
            stopProgressPolling();

            const poll = async () => {
                const response = await fetch(`/api/progress/${jobId}`);
                const payload = await response.json();
                if (!response.ok || !payload.ok) {
                    throw new Error(payload.error || 'Falha ao consultar progresso.');
                }

                updateProgressPanel(payload);

                if (payload.state === 'done') {
                    stopProgressPolling();
                    const result = payload.result || {};
                    const warning = result.errors && result.errors.length
                        ? ` Arquivos com aviso: ${result.errors.join(', ')}.`
                        : '';
                    setResult(
                        `Concluído com ${result.entries} entradas. XLSX: ${result.xlsx_path}. Dashboard: ${result.dashboard_path}.${warning}`
                    );
                    statusText.textContent = 'Processamento concluído.';
                    goToStep2(result.dashboard_url);
                    processBtn.disabled = false;
                    return;
                }

                if (payload.state === 'error') {
                    stopProgressPolling();
                    throw new Error(payload.error || 'Falha no processamento.');
                }
            };

            poll().catch((error) => {
                stopProgressPolling();
                const message = error instanceof Error ? error.message : String(error);
                setResult(message, true);
                statusText.textContent = 'Falha no processamento.';
                processBtn.disabled = false;
            });

            progressTimer = setInterval(() => {
                poll().catch((error) => {
                    stopProgressPolling();
                    const message = error instanceof Error ? error.message : String(error);
                    setResult(message, true);
                    statusText.textContent = 'Falha no processamento.';
                    processBtn.disabled = false;
                });
            }, 1000);
        }

        processBtn.addEventListener('click', async () => {
            const source = currentSource();
            if (source === 'upload' && !selectedFiles.length) {
                setResult('Selecione ao menos um arquivo para upload.', true);
                return;
            }

            processBtn.disabled = true;
            statusText.textContent = 'Processando arquivos...';
            setResult('Execução iniciada. Aguarde o processamento terminar.');
            progressPanel.style.display = 'block';
            progressStage.textContent = 'Iniciando processamento...';
            progressPercent.textContent = '0.0%';
            progressFill.style.width = '0%';
            progressCount.textContent = '0/0';
            elapsedText.textContent = '00:00';
            etaText.textContent = '--:--';
            currentFileText.textContent = 'Arquivo atual: -';

            try {
                const formData = new FormData();
                formData.append('source', source);
                selectedFiles.forEach((file) => formData.append('files', file));

                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData,
                });
                const payload = await response.json();

                if (!response.ok || !payload.ok) {
                    throw new Error(payload.error || 'Falha no processamento.');
                }
                if (!payload.job_id) {
                    throw new Error('Job de processamento não retornado pelo servidor.');
                }

                startProgressPolling(payload.job_id);
            } catch (error) {
                const message = error instanceof Error ? error.message : String(error);
                setResult(message, true);
                statusText.textContent = 'Falha no processamento.';
                stopProgressPolling();
                processBtn.disabled = false;
            }
        });

        refreshUploadVisibility();
    </script>
</body>
</html>
"""


def _run_cli_mode(config: dict) -> None:
    """Legacy mode: process first ZIP from input/ immediately."""
    zip_path = find_zip('input')
    if not zip_path:
        print('[erro] Nenhum arquivo ZIP encontrado em input/. Encerrando.')
        sys.exit(1)

    print(f'ZIP encontrado: {zip_path}')
    print('Extraindo arquivos...')
    file_map = extract_zip(zip_path)
    print(f'  {len(file_map)} arquivo(s) extraído(s).')

    cli_progress = _build_progress_callback('cli')
    _run_pipeline(file_map, config, cli_progress)
    print('\nConcluído!')


def _run_web_mode(config: dict) -> None:
    """Start local web server with stepper flow and on-demand processing."""
    try:
        from flask import Flask, jsonify, request, send_from_directory
    except ModuleNotFoundError:
        print('[erro] Flask não instalado. Execute: pip install flask')
        sys.exit(1)

    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  # 150MB

    output_dashboard_path = config.get('output', {}).get('dashboard_path', 'output/dashboard.html')
    output_dir = str(Path(output_dashboard_path).parent.resolve())
    dashboard_name = Path(output_dashboard_path).name

    @app.get('/')
    def index():
        return _stepper_html()

    @app.get('/output/<path:filename>')
    def serve_output(filename: str):
        return send_from_directory(output_dir, filename)

    @app.get('/api/progress/<job_id>')
    def progress(job_id: str):
        job = _read_job(job_id)
        if not job:
            return jsonify({'ok': False, 'error': 'Job não encontrado.'}), 404

        return jsonify({
            'ok': True,
            'job_id': job['job_id'],
            'state': job['state'],
            'stage': job['stage'],
            'current_file': job['current_file'],
            'processed_steps': job['processed_steps'],
            'total_steps': job['total_steps'],
            'percent': job['percent'],
            'elapsed_seconds': job['elapsed_seconds'],
            'eta_seconds': job['eta_seconds'],
            'terminal_last_line': job['terminal_last_line'],
            'updated_at': job['updated_at'],
            'result': job['result'],
            'error': job['error'],
        })

    def _run_pipeline_worker(job_id: str, source: str, uploads_data: list[tuple[str, bytes]] | None = None) -> None:
        callback = _build_progress_callback(job_id)

        try:
            if source == 'input':
                zip_path = find_zip('input')
                if not zip_path:
                    raise RuntimeError('Nenhum ZIP encontrado em input/.')

                print(f'ZIP encontrado: {zip_path}')
                print('Extraindo arquivos...')
                file_map = extract_zip(zip_path)
                print(f'  {len(file_map)} arquivo(s) extraído(s).')

                callback({
                    'stage': 'Arquivos extraídos do ZIP',
                    'current_file': Path(zip_path).name,
                    'processed_steps': 0,
                    'total_steps': max(len(file_map), 1),
                })

                result = _run_pipeline(file_map, config, callback)
            elif source == 'upload':
                if not uploads_data:
                    raise RuntimeError('Nenhum arquivo enviado.')

                with tempfile.TemporaryDirectory(prefix='irpf_upload_') as tmpdir:
                    uploaded_paths: list[Path] = []
                    for filename, content in uploads_data:
                        if not filename:
                            continue
                        dest = Path(tmpdir) / Path(filename).name
                        with open(dest, 'wb') as output_fh:
                            output_fh.write(content)
                        uploaded_paths.append(dest)

                    file_map, _ = _collect_upload_file_map(uploaded_paths)
                    if not file_map:
                        raise RuntimeError('Nenhum arquivo válido (PDF/ASPX/ZIP/XLSX).')

                    callback({
                        'stage': 'Arquivos de upload preparados',
                        'current_file': '',
                        'processed_steps': 0,
                        'total_steps': max(len(file_map), 1),
                    })

                    result = _run_pipeline(file_map, config, callback)
            else:
                raise RuntimeError('Fonte inválida.')

            dashboard_url = f'/output/{dashboard_name}?t={int(datetime.now().timestamp())}'
            result_with_url = {
                **result,
                'dashboard_url': dashboard_url,
            }

            _update_job(
                job_id,
                state='done',
                stage='Processamento concluído',
                percent=100.0,
                result=result_with_url,
                error=None,
                terminal_last_line='[progresso] 100.0% | Processamento concluído com sucesso.',
            )
        except Exception as exc:  # noqa: BLE001
            _update_job(
                job_id,
                state='error',
                stage='Falha no processamento',
                error=str(exc),
                terminal_last_line=f'[erro] {exc}',
            )

    @app.post('/api/process')
    def process():
        source = (request.form.get('source') or 'input').strip().lower()

        if source not in {'input', 'upload'}:
            return jsonify({'ok': False, 'error': 'Fonte inválida.'}), 400

        uploads_data: list[tuple[str, bytes]] | None = None

        if source == 'upload':
            uploads = request.files.getlist('files')
            if not uploads:
                return jsonify({'ok': False, 'error': 'Nenhum arquivo enviado.'}), 400

            uploads_data = []
            for item in uploads:
                if not item.filename:
                    continue
                uploads_data.append((Path(item.filename).name, item.read()))

            if not uploads_data:
                return jsonify({'ok': False, 'error': 'Nenhum arquivo enviado.'}), 400

        try:
            job_id = _create_job()
            _update_job(job_id, state='running', stage='Iniciando processamento')

            worker = threading.Thread(
                target=_run_pipeline_worker,
                args=(job_id, source, uploads_data),
                daemon=True,
            )
            worker.start()

            return jsonify({'ok': True, 'job_id': job_id})
        except Exception as exc:  # noqa: BLE001
            return jsonify({'ok': False, 'error': str(exc)}), 500

    host = '127.0.0.1'
    port = 8765
    web_url = f'http://{host}:{port}'
    print(f'\nInterface web iniciada em {web_url}')
    print('Use --cli para o comportamento anterior (processar input/ diretamente).')

    try:
        webbrowser.open(web_url)
    except Exception:  # noqa: BLE001
        pass

    app.run(host=host, port=port, debug=False, threaded=True)


def main() -> None:
    args = [arg for arg in sys.argv[1:] if arg != '--cli']
    cfg_path = args[0] if args else 'config.toml'
    config = load_config(cfg_path)

    if '--cli' in sys.argv[1:]:
        _run_cli_mode(config)
        return

    _run_web_mode(config)


if __name__ == '__main__':
    main()
