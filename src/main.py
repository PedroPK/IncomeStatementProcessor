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
import webbrowser
from datetime import datetime
from pathlib import Path

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
        if suffix == '.zip':
            extracted = extract_zip(str(uploaded_path))
            _merge_file_maps(file_map, extracted)
            continue

        if suffix in _PDF_EXTENSIONS or suffix in _XLSX_EXTENSIONS:
            _merge_file_maps(file_map, {uploaded_path.name: str(uploaded_path)})

    return file_map, temp_dirs


def _parse_file_map(file_map: dict[str, str]) -> tuple[list, list[str]]:
    """Parse PDFs/XLSX from an extracted file map and return entries/errors."""
    all_entries = []
    errors: list[str] = []

    # Parse PDF files
    for filename, filepath in sorted(file_map.items()):
        ext = Path(filename).suffix.lower()
        if ext not in _PDF_EXTENSIONS:
            continue

        print(f'  Processando: {filename}')
        entries = parse_file(filepath)

        if not entries:
            print(f'    [aviso] Nenhuma entrada extraída de {filename}')
            errors.append(filename)
            continue

        err_entries = [e for e in entries if e.secao in ('Erro', 'Desconhecido')]
        ok_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]

        if err_entries:
            for entry in err_entries:
                print(f'    [aviso] {entry.observacao}')
            errors.append(filename)

        print(f'    -> {len(ok_entries)} entradas extraídas.')
        all_entries.extend(ok_entries)

    # Parse custody XLSX files
    xlsx_files = [f for f in file_map if Path(f).suffix.lower() in _XLSX_EXTENSIONS]
    if xlsx_files:
        for xlsx_filename in xlsx_files:
            ref_year = _detect_custody_year(xlsx_filename)
            print(f'  Processando custódia: {xlsx_filename} (ano de referência: {ref_year})')
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
    else:
        print('  [info] Nenhum arquivo XLSX de custódia encontrado.')

    return all_entries, errors


def _run_pipeline(file_map: dict[str, str], config: dict) -> dict:
    """Run parse + outputs generation and return summary metadata."""
    xlsx_path = config.get('output', {}).get('xlsx_path', 'output/informes_rendimentos.xlsx')
    dashboard_path = config.get('output', {}).get('dashboard_path', 'output/dashboard.html')
    gs_config = config.get('google_sheets', {})

    all_entries, errors = _parse_file_map(file_map)

    print(f'\nTotal: {len(all_entries)} entradas processadas.')
    if errors:
        print(f'Arquivos com problemas: {", ".join(errors)}')

    if not all_entries:
        raise RuntimeError('Nenhuma entrada válida. Encerrando sem gerar planilha.')

    print('\nGerando planilha XLSX...')
    write_xlsx(all_entries, xlsx_path)

    print('Gerando dashboard HTML...')
    from src.dashboard_generator import generate_dashboard_html

    dashboard_dir = Path(dashboard_path).parent
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    generate_dashboard_html(all_entries, dashboard_path)

    if gs_config.get('enabled', False):
        print('\nEnviando para Google Sheets...')
        from src.sheets_writer import push_to_sheets

        push_to_sheets(all_entries, gs_config)

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

            <div id="resultBox" class="result" style="display:none;"></div>
        </div>

        <div id="step2">
            <iframe id="dashboardFrame" title="Dashboard"></iframe>
        </div>
    </div>

    <script>
        let selectedFiles = [];

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

        processBtn.addEventListener('click', async () => {
            const source = currentSource();
            if (source === 'upload' && !selectedFiles.length) {
                setResult('Selecione ao menos um arquivo para upload.', true);
                return;
            }

            processBtn.disabled = true;
            statusText.textContent = 'Processando arquivos...';
            setResult('Execução iniciada. Aguarde o processamento terminar.');

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

                const warning = payload.errors && payload.errors.length
                    ? ` Arquivos com aviso: ${payload.errors.join(', ')}.`
                    : '';
                setResult(
                    `Concluído com ${payload.entries} entradas. XLSX: ${payload.xlsx_path}. Dashboard: ${payload.dashboard_path}.${warning}`
                );
                statusText.textContent = 'Processamento concluído.';
                goToStep2(payload.dashboard_url);
            } catch (error) {
                const message = error instanceof Error ? error.message : String(error);
                setResult(message, true);
                statusText.textContent = 'Falha no processamento.';
            } finally {
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

    _run_pipeline(file_map, config)
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

    @app.post('/api/process')
    def process():
        source = (request.form.get('source') or 'input').strip().lower()

        try:
            if source == 'input':
                zip_path = find_zip('input')
                if not zip_path:
                    return jsonify({'ok': False, 'error': 'Nenhum ZIP encontrado em input/.'}), 400
                print(f'ZIP encontrado: {zip_path}')
                print('Extraindo arquivos...')
                file_map = extract_zip(zip_path)
                print(f'  {len(file_map)} arquivo(s) extraído(s).')
            elif source == 'upload':
                uploads = request.files.getlist('files')
                if not uploads:
                    return jsonify({'ok': False, 'error': 'Nenhum arquivo enviado.'}), 400

                with tempfile.TemporaryDirectory(prefix='irpf_upload_') as tmpdir:
                    uploaded_paths: list[Path] = []
                    for item in uploads:
                        if not item.filename:
                            continue
                        dest = Path(tmpdir) / Path(item.filename).name
                        item.save(dest)
                        uploaded_paths.append(dest)

                    file_map, _ = _collect_upload_file_map(uploaded_paths)
                    if not file_map:
                        return jsonify({'ok': False, 'error': 'Nenhum arquivo válido (PDF/ASPX/ZIP/XLSX).'}), 400

                    result = _run_pipeline(file_map, config)
            else:
                return jsonify({'ok': False, 'error': 'Fonte inválida.'}), 400

            if source == 'input':
                result = _run_pipeline(file_map, config)

            dashboard_url = f'/output/{dashboard_name}?t={int(datetime.now().timestamp())}'

            return jsonify({
                'ok': True,
                'entries': result['entries'],
                'errors': result['errors'],
                'xlsx_path': result['xlsx_path'],
                'dashboard_path': result['dashboard_path'],
                'generated_at': result['generated_at'],
                'dashboard_url': dashboard_url,
            })
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

    app.run(host=host, port=port, debug=False)


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
