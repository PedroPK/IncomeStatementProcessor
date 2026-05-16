import zipfile
from pathlib import Path
import tempfile
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html

print('Processing PDFs and generating dashboard...')

zip_path = Path('input/drive-download-20260505T232835Z-3-001.zip')
all_entries = []

if not zip_path.exists():
    print(f'Error: Zip file not found at {zip_path}')
    exit(1)

with tempfile.TemporaryDirectory() as tmpdir:
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmpdir)
    pdf_files = list(Path(tmpdir).glob('**/*.pdf'))
    print(f'Found {len(pdf_files)} PDF files.')
    for pdf_file in pdf_files:
        try:
            entries = parse_file(str(pdf_file))
            if entries:
                valid_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]
                all_entries.extend(valid_entries)
        except Exception as e:
            print(f'Error parsing {pdf_file}: {e}')

if all_entries:
    first = all_entries[    first = all_entries[    firses    first = atr    first = all_entriespa    first =.nome    first = all_entries[    firsribuinte}')
    
    dashboard_path = 'output/dashboard_test.ht    dashboard_path = 'output/dashboard_test.ht    nerate_dashboard_html(all_entries, dashboard_path)
    print(f'Dashboard generated at {dashboard_path}')
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
        print(f'Taxpayer name found: {first.nome_contribuinte in content}')
        print(f'Taxpayer CPF found: {first.cpf_co        print(f'Taxpayer CPF found: {first.cpf_co  entries extracted.')
