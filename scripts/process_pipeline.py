import zipfile
from pathlib import Path
import tempfile
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html
from src.main import validate_single_taxpayer
from src.xlsx_writer import write_xlsx

def main():
    zip_path = Path('input/02.01 Informes de Rendimentos.zip')
    if not zip_path.exists():
        print(f'Error: {zip_path} not found')
        return

    print('Processing Ana Gloria PDFs...')
    all_entries = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(tmpdir)
        
        pdfs = list(Path(tmpdir).glob('**/*.pdf'))
        print(f'Found {len(pdfs)} PDFs')
        
        for pdf_file in pdfs:
            try:
                entries = parse_file(str(pdf_file))
                if entries:
                    valid_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]
                    all_entries.extend(valid_entries)
            except Exception as e:
                print(f'Error parsing {pdf_file.name}: {e}')
        
        print(f'Total valid entries: {len(all_entries)}')
        
        if all_entries:
            first = all_entries[0]
            print(f'Taxpayer: {first.nome_contribuinte} / {first.cpf_contribuinte}')
            
            is_valid, msg, conflicts = validate_single_taxpayer(all_entries)
            print(f'Validation: {is_valid}')
            if msg:
                print(f'Message: {msg}')
            
            Path('output').mkdir(exist_ok=True)
            
            dashboard_path = 'output/dashboard.html'
            generate_dashboard_html(all_entries, dashboard_path)
            print(f'Dashboard generated: {dashboard_path}')
            
            xlsx_path = 'output/relatorio.xlsx'
            write_xlsx(all_entries, xlsx_path)
            print(f'XLSX generated: {xlsx_path}')
            
            with open(dashboard_path, 'r') as f:
                content = f.read()
                if first.nome_contribuinte in content:
                    print('Taxpayer info verified in dashboard')

if __name__ == '__main__':
    main()
