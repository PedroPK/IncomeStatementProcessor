import sys
import pdfplumber
import zipfile
import glob
import os
import io

sys.path.insert(0, '.')
from src.parser import parse_clear

zips = set(glob.glob('input/**/*.zip', recursive=True) + glob.glob('input/*.zip'))
for z in zips:
    try:
        with zipfile.ZipFile(z) as zf:
            for name in zf.namelist():
                if 'clear' in name.lower() and name.lower().endswith('.pdf') and 'informe' in name.lower():
                    print(f'\n--- Found: {name} in {z} ---')
                    with zf.open(name) as f:
                        data = io.BytesIO(f.read())
                    with pdfplumber.open(data) as pdf:
                        pages_text = [p.extract_text() or '' for p in pdf.pages]
                        pages_tables = [p.extract_tables() or [] for p in pdf.pages]
                    
                    for i, t in enumerate(pages_text):
                        print(f'\n[Page {i+1} Text Snapshot]')
                        print(t[:500])
                        if 'SALDO' in t.upper():
                            print(f'>> Page {i+1} mentions SALDO <<')
                        
                        if i < len(pages_tables) and pages_tables[i]:
                            print(f'>> Page {i+1} has {len(pages_tables[i])} tables <<')
                            for tidx, table in enumerate(pages_tables[i]):
                                if table:
                                    print(f'   Table {tidx}: {table[0][:3]}... ({len(table)} rows)')

                    entries = parse_clear(name, pages_text, pages_tables)
                    print(f'\nSummary for {name}:')
                    print(f'  Total Entries: {len(entries)}')
                    for e in entries:
                                                                                              r processing {z}: {e}')
