#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = '/Users/pedropk/Downloads/Apps/Development/IDEs/VsWorkspace/IncomeStatementProcessor/input/Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print("=== ANALISE DO PDF DE CUSTODIA DA CLEAR ===\n")
    print(f"Total de paginas: {len(pdf.pages)}\n")
    
    # Analise das 2 primeiras paginas
    for page_num in range(min(2, len(pdf.pages))):
        page = pdf.pages[page_num]
        print(f"\n--- PAGINA {page_num + 1} ---")
        text = page.extract_text()
        print(f"Texto (primeiros 1500 caracteres):\n{text[:1500]}\n")
        
        # Tabelas
        tables = page.extract_tables()
        print(f"Tabelas encontradas: {len(tables)}")
        if tables:
            for i, table in enumerate(tables[:2]):  # Primeiras 2 tabelas
                print(f"\n  Tabela {i+1} ({len(table)} linhas x {len(table[0]) if table else 0} colunas):")
                for row in table[:4]:  # Primeiras 4 linhas
                    print(f"    {row}")
    
    # Analise de TODAS as tabelas
    print(f"\n\n=== RESUMO DE TODAS AS TABELAS ===")
    table_count = 0
    all_headers = set()
    for page_idx, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        if tables:
            for table in tables:
                table_count += 1
                # Extrai headers (primeira linha)
                if table and len(table) > 0:
                    headers = table[0]
                    for h in headers:
                        if h:
                            all_headers.add(str(h).strip())
    
    print(f"Total de tabelas em todo o documento: {table_count}")
    print(f"\nHeaders encontrados em todas as tabelas:")
    for h in sorted(all_headers)[:20]:  # Primeiros 20 headers
        print(f"  - {h}")
    
    # Busca por padrões de dados
    print(f"\n=== PADROES DE DADOS ===")
    text_full = ""
    for page in pdf.pages:
        text_full += page.extract_text() + "\n"
    
    # Busca por padrões
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', text_full)
    cnpjs = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text_full)
    values = re.findall(r'R\$\s*[\d.,]+', text_full)
    
    print(f"Datas encontradas: {len(dates)} exemplos: {list(set(dates))[:5]}")
    print(f"CNPJs encontrados: {len(cnpjs)} exemplos: {list(set(cnpjs))[:5]}")
    print(f"Valores (R$) encontrados: {len(values)} exemplos: {list(set(values))[:5]}")
    
    # Sections/headers principais
    print(f"\n=== SECOES PRINCIPAIS ===")
    lines = text_full.split('\n')
    for i, line in enumerate(lines[:100]):  # Primeiras 100 linhas
        if len(line) > 10 and line.isupper():
            print(f"  {line}")
