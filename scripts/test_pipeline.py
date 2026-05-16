import zipfile, tempfile
import os
from pathlib import Path
from src.parser import parse_file
from src.dashboard_generator import generate_dashboard_html
from src.main import validate_single_taxpayer
from src.xlsx_writer import write_xlsx

def main():
    zip_path = Path('input/02.01 Informes de Rendimentos.zip')
    all_entries = []
    errors = []

    if not zip_path.exists():
        print(f"Error: {zip_path} not found.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmpdir)
        pdfs = [p for p in sorted(Path(tmpdir).glob('**/*.pdf')) if not p.name.startswith('._')]
        print(f'Processing {len(pdfs)} PDFs...')
        for pdf in pdfs:
            try:
                entries = parse_file(str(pdf))
                valid = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]
                bad = [e for e in entries if e.secao in ('Erro', 'Desconhecido')]
                if valid:
                                          :4                       tp_name = valid[0].nome_contribuinte[:20]
                                                       valid)} entries | {valid[0].secao} | taxpayer: {tp_name                                    extend(valid)
                                              name_trunc = pdf.name[:45]
                    obs_trunc = bad[0].observacao[:60]
                    print(f'  !! {name_trunc:45s} {obs_trunc}')
                    errors.append(pdf.name)
            except Exception as ex:
                name_trunc = pdf.name[:45]
                print(f'  ERR {name_trunc:45s} {ex}')
                errors.append(pdf.name)

    print(f'\nTotal: {len(all_entries)} valid entries, {len(errors)} errors')

    if all_entries:
        is_valid, msg, _ = validate_single_taxpayer(all_entries)
        print(f'\nValidation: {is_valid}')
        for line in msg.split("\n"):
            if line.strip():
                print(f'  {line}')
        
        Path('output').mkdir(exist_ok=True)
        generate_dashboard_html(all_entries, 'output/dashboard.html')
        write_xlsx(all_entries, 'output/relatorio.xlsx')
        print('\nOutputs generated: output/dashboard.html, output/relatorio.xlsx')

if __name__ == "__main__":
    main()
