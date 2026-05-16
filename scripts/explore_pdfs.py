import zipfile
from pathlib import Path
import tempfile
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html
from src.main import validate_single_taxpayer

def main():
    zip_path = Path('input/02.01 Informes de Rendimentos.zip')
    print('Exploring Ana Gloria PDFs...')    
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(tmpdir)
        
        pdfs = sorted(list(Path(tmpdir).glob('**/*.pdf')))
        print(f'Found {len(pdfs)} PDFs\n')
        
        for pdf_file in pdfs:
            try:
                entries = parse_file(str(pdf_file))
                print(f'- {pdf_file.name}: {len(entries) if entries else 0} entries')
                if entries:
                    for e in entries[:2]:
                        print(f'  [{e.secao}] {e.descricao[:30]}...')
            except Exception as e:
                print(f'- {pdf_file.name}: Error {e}')

if __name__ == '__main__':
    main()
