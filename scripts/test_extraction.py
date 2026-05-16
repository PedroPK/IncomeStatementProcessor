import pdfplumber
import zipfile
from pathlib import Path
import tempfile
from src.normalizer import extract_taxpayer_info

zip_path = Path('input/drive-download-20260505T232835Z-3-001.zip')

print('Testing improved extract_taxpayer_info:')
print()

test_pdfs = [
    'Clear - 01 Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
    'XP - Informe de Rendiemntos - Ano Base 2025 - IRPF2026.pdf',
    'NuBank - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
    'Avenue - Informe de Rencimentos - Ano Base 2025 IRPF2026 - relatorio anual.pdf',
    'Inter - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
]

with zipfile.ZipFile(zip_path, 'r') as z:
    for pdf_name in test_pdfs:
        if pdf_name in z.namelist():
            pdf_data = z.read(pdf_name)
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_data)
                tmp.flush()
                
                with pdfplumber.o        name) as pdf:
                    # Check first pages for taxpayer info
                    nome, cpf = None, None
                    for page in pdf.pages:
                        text = page.extract_text() or ''
                        nome, cpf = extract_taxpayer_info(text)
                                                                    break
                    
                    print(f'{pdf_name[:50]:50s}')
                    print(f'  Nome: {nome}')
                    print(f'  CPF:  {cpf}')
                    print()
