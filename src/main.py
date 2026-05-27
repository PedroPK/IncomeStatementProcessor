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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FuturesTimeoutError
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

from src import __version__
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
    stall_timeout: int = 60,
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
            with ThreadPoolExecutor(max_workers=1) as _ex:
                _fut = _ex.submit(parse_file, filepath)
                try:
                    entries = _fut.result(timeout=stall_timeout)
                except _FuturesTimeoutError:
                    print(f'    [timeout] {filename} sem progresso por {stall_timeout}s — ignorado.')
                    errors.append(filename)
                    processed += 1
                    notify('Arquivo PDF ignorado por timeout', filename)
                    continue
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

    all_entries, errors, parse_processed, parse_total = _parse_file_map(
        file_map, parse_notify,
        stall_timeout=config.get('processing', {}).get('stall_timeout_seconds', 60),
    )
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


_STEPPER_TEMPLATE_PATH = Path(__file__).parent / 'templates' / 'stepper.html'


_STEPPER_TEMPLATE_PATH = Path(__file__).parent / 'templates' / 'stepper.html'


def _stepper_html() -> str:
    return _STEPPER_TEMPLATE_PATH.read_text(encoding='utf-8').replace('%%VERSION%%', __version__)


def _run_cli_mode(config: dict) -> None:
    """Legacy mode: process first ZIP from input/ immediately."""
    print(f'Income Statement Processor v{__version__}')
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

    @app.get('/api/status')
    def api_status():
        return jsonify({'ok': True, 'version': __version__})

    @app.post('/api/shutdown')
    def shutdown_server():
        """Encerra o servidor de forma limpa."""
        import signal as _signal

        def _do_shutdown() -> None:
            time.sleep(0.4)
            # Envia SIGTERM ao processo principal — werkzeug encerra limpo
            os.kill(os.getpid(), _signal.SIGTERM)
            time.sleep(1.5)
            # Fallback: forçar saída imediata caso SIGTERM não tenha sido suficiente
            os._exit(0)

        threading.Thread(target=_do_shutdown, daemon=False).start()
        return jsonify({'ok': True, 'message': 'Servidor encerrado.'})

    @app.post('/api/restart')
    def restart_server():
        """Inicia um novo processo e encerra o atual para liberar a porta."""
        import subprocess

        # Raiz do projeto: src/main.py -> dois níveis acima
        project_root = str(Path(__file__).parent.parent.resolve())
        # Preserva argumentos extras passados originalmente (ex.: config.toml, --cli)
        extra_args = sys.argv[1:]

        def _do_restart() -> None:
            # Aguarda o response chegar ao cliente antes de matar o processo
            time.sleep(1.2)
            subprocess.Popen(
                [sys.executable, '-m', 'src.main'] + extra_args,
                cwd=project_root,
            )
            # Força saída imediata sem cleanup para liberar o socket
            os._exit(0)

        # daemon=False garante que o thread não seja morto antes de executar
        threading.Thread(target=_do_restart, daemon=False).start()
        return jsonify({'ok': True, 'message': 'Reiniciando servidor...'})

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
    print(f'\nIncome Statement Processor v{__version__}')
    print(f'Interface web iniciada em {web_url}')
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
