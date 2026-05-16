import zipfile
from pathlib import Path
import tempfile
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html
from src.main import validate_single_taxpayer
from src.xlsx_writer import write_xlsx

def main():
    zip_path = Path('input/02.01 Informes de Rendimentos.zip')
    print('Processing Ana Gloria PDFs...')    
    all_entries = []
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(tmpdir)
        
        pdfs = sorted(list(Path(tmpdir).glob('**/*.pdf')))
        pdfs = [p for p in pdfs if not p.name.startswith('._')]
        print(f'Found {len(pdfs)} valid PDFs\n')
        
        for pdf_file in pdfs:
            try:
                entries = parse_file(str(pdf_file))
                if entries:
                    valid_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]
                    if valid_entries:
                        print(f'✓ {pdf_file.name[:40]:40s} - {len(valid_entries)} entries')
                        all_entries.extend(valid_entries)
                    else:
                        print(f'  {pdf_file.name[:40]:40s} - 0 valid entries (found {len(entries)})')
            except Exception as e:
                print(f'! {pdf_file.name[:40]:40s} - Error: {e}')
        
        print(f'\nTotal valid entries: {len(all_entries)}\n')
        
        if all_entries:
            first = all_entries[0]
            print(f'Taxpayer: {first.nome_contribuinte} / {first.cpf_contribuinte}\n')
            
            is_valid, msg, conflicts = validate_single_taxpayer(all_entries)
            print(f'Validation: {is_valid}')
            for line in msg.split('\n'):
                if line.strip():
                    print(f'  {line}')
            
            Path('output').mkdir(exist_ok=True)
            
            dashboard_path = 'output/dashboard.html'
            generate_dashboard_html(all_entries, dashboard_path)
            print(f'✓ Dashboard: {dashboard_path}')
            
            xlsx_path = 'output/relatorio.xlsx'
            write_xlsx(all_entries, xlsx_path)
            print(f'✓ XLSX: {xlsx_path}')
        else:
            print('ERROR: No valid entries found')

if __name__ == '__main__':
    main()
