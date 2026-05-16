import zipfile
from pathlib import Path
import tempfile
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html

print('Processing PDFs...')

zip_path = Path('input/drive-download-20260505T232835Z-3-001.zip')
all_entries = []

with tempfile.TemporaryDirectory() as tmpdir:
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmpdir)
    pdf_files = list(Path(tmpdir).glob('**/*.pdf'))
    for pdf_file in pdf_files:
        try:
            entries = parse_file(str(pdf_file))
            if entries:
                all_entries.extend([e for e in entries if e.secao not in ('Erro', 'Desconhecido')])
        except: pass

if all_entries:
    first = all_entries[0]
    print(f'Entries: {len(all_entries)}')
    print(f'Taxpayer: {first.nome_contribuinte} / {first.cpf_contribuinte}')
    Path('output').mkdir(exist_ok=True)
    generate_dashboard_html(all_entries, 'output/dashboard_test.html')
    with open('output/dashboard_test.html', 'r') as f: content = f.read()
    print(f'Name in dashboard: {first.nome_contribuinte in content}')
    print(f'CPF in dashboard: {first.cpf_contribuinte in content}')
else: print('No entries.')
