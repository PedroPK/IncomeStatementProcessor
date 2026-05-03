#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = '/Users/pedropk/Downloads/Apps/Development/IDEs/VsWorkspace/IncomeStatementProcessor/input/Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print("=== ANALISE COMPARATIVA: CLEAR vs AVENUE ===\n")
    
    # Extract all text
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text() + "\n"
    
    # Extrair dados estruturados
    lines = full_text.split('\n')
    
    # Identificar seções
    print("=== SECOES ENCONTRADAS ===")
    sections = {}
    current_section = None
    for i, line in enumerate(lines):
        if 'POSICAO DETALHADA DOS ATIVOS' in line.upper():
            # Próxima linha deve ter o tipo
            if i+1 < len(lines):
                section_type = lines[i+1].strip()
                current_section = section_type
                if current_section not in sections:
                    sections[current_section] = []
    
    print(f"Seções identificadas: {list(set(sections.keys()))}")
    
    # Extrair ativos com padrão: Ticker + dados
    print("\n=== ATIVOS IDENTIFICADOS ===")
    
    # Padrão para línhas de ação/fundo
    # TICKER QQQQQ PP.PP R$ VV.VVV,VV
    ticker_pattern = r'^([A-Z][A-Z0-9]{3}[0-9]{1,2})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+R\$\s*([\d.,]+)\s+R\$\s*([\d.,]+)'
    
    assets = {}
    for line in lines:
        m = re.match(r'^([A-Z][A-Z0-9]{3}[0-9]{1,2})\s+(.+)', line.strip())
        if m:
            ticker = m.group(1)
            rest = m.group(2)
            # Tenta extrair valores
            values = re.findall(r'R\$\s*([\d.]+,\d{2})', rest)
            if ticker not in ['POSICAO', 'Ativo', 'Cliente', 'SALDO'] and values:
                assets[ticker] = {
                    'line': line.strip(),
                    'values': values
                }
    
    print(f"Total de ativos identificados: {len(assets)}")
    for ticker in list(assets.keys())[:10]:
        print(f"  {ticker}: {assets[ticker]['line'][:80]}...")
    
    # Extrair "Juros sobre Capital" / rendimentos
    print("\n=== RENDIMENTOS/JUROS SOBRE CAPITAL ===")
    juros_pattern = r'JUROS SOBRE CAPITAL\s+([A-Z][A-Z0-9]{3}[0-9]{1,2})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+R\$\s*([\d.,]+)'
    juros = re.findall(juros_pattern, full_text)
    print(f"Total de registros de Juros sobre Capital: {len(juros)}")
    for ticker, data, qtd, valor in juros[:5]:
        print(f"  {ticker} ({data}): Qtd={qtd}, Valor={valor}")
    
    # Saldo disponível
    print("\n=== SALDOS FINAIS ===")
    saldo_pattern = r'SALDO DISPONIVEL\s+R\$\s*([\d.,]+)'
    saldos = re.findall(saldo_pattern, full_text)
    print(f"Saldos em dinheiro: {saldos}")
    
    # Posição total por tipo
    print("\n=== POSICAO CONSOLIDADA POR TIPO ===")
    tipo_pattern = r'(\d+\.?\d*%)\s+(Acoes|Fundos Imobiliarios|Fundos de Investimento|Outros)'
    tipos = re.findall(tipo_pattern, full_text)
    for perc, tipo in tipos:
        print(f"  {tipo}: {perc}")

print("\n" + "="*60)
print("=== MAPEAMENTO PARA ENTRY ===")
print("="*60)
print("""
Para Clear (Ativos em Custódia):

1. AÇÕES (Grupo 04, Código 01)
   - Exemplo: PSSA3 com 400 unidades @ R$ 48,36
   - Entry:
     * secao = "Bens e Direitos"
     * grupo = "04"
     * grupo_desc = "Aplicações e Investimentos"
     * codigo = "01"
     * codigo_desc = "Ações"
     * discriminacao = "PSSA3 – [Nome da Empresa]"
     * valor_2025 = 19.344,00 (Qtd × Última Cotação)
     * rendimento = [Juros sobre Capital + Dividendos pagos]
     * localizacao = "105 - Brasil" (por enquanto todas são Brasil)

2. FUNDOS IMOBILIARIOS (Grupo 04, Código 02)
   - Exemplo: PLAG11, SNFF11, AFHI11, etc
   - Mesmo mapeamento que Ações

3. SALDO EM DINHEIRO (Grupo 06, Código 01)
   - Saldo Disponível = R$ 7.745,95
   - Entry para "Depósito à Vista e Numerário"

DIFERENÇA DO AVENUE:
- Avenue: tem USD cost, Ptax, conversão cambial explícita
- Clear: valores já em BRL, sem conversão cambial (tudo Brasil)
- Avenue: rendimento/IRRF por ativo
- Clear: Juros sobre Capital em seção separada (precisa de match ticker+data)
- Avenue: grupo-codigo (ex: 03-01)
- Clear: apenas ticker, sem grupo/codigo no PDF (deve ser inferido pelo tipo)

REGEX PATTERNS PARA CLEAR:
1. Ticker: [A-Z][A-Z0-9]{3}[0-9]{1,2}
2. Valor R$: R\$\s*([\d.]+,\d{2})
3. Data: \d{2}/\d{2}/\d{4}
4. Qtd: \d+
""")
