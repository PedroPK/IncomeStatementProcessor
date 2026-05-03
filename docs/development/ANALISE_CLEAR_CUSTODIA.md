# Análise: PDF "Clear - 04 Custódia - Ano Base 2025"

## 📄 Estrutura do Documento

| Aspecto | Detalhes |
|---------|----------|
| **Páginas** | 8 |
| **Tabelas** | 6 tabelas estruturadas |
| **Ativos** | ~27 diferentes (ações, FIIs, ETFs) |
| **Formato** | Posição Consolidada + Posição Detalhada |
| **Localização** | Todas em Brasil |

## 📊 Estrutura de Tabelas

```
Colunas:
┌─────────┬──────────────┬──────┬───────┬──────┬───────┬─────────┬──────┬─────┬────────────────┐
│ Ativo   │ Qtd Disponi  │ Proj │ Dia   │ Gar  │ Bloq  │ Estrut  │ Total│ P.M │ Ult. Cotação   │
├─────────┼──────────────┼──────┼───────┼──────┼───────┼─────────┼──────┼─────┼────────────────┤
│ PSSA3   │ 400          │ 0    │ 0     │ 0    │ 0     │ 0       │ 400  │ Indef│ R$ 48,36      │
│ PLAG11  │ 190          │ 0    │ 0     │ 0    │ 190   │ 0       │ 0%   │ R$ 51,50       │
│ SNFF11  │ 350          │ 0    │ 0     │ 0    │ 350   │ 0       │ 0%   │ R$ 76,14       │
└─────────┴──────────────┴──────┴───────┴──────┴───────┴─────────┴──────┴─────┴────────────────┘
```

## 🔍 Padrões de Extração

### 1. Tickers
```regex
[A-Z][A-Z0-9]{3}[0-9]{1,2}
```
Exemplos: PSSA3, PLAG11, VGIR11, MXRF11

### 2. Valores Monetários
```regex
R\$\s*[\d.]+,\d{2}
```
Exemplos: R$ 19.344,00, R$ 7.745,95, R$ 51,50

### 3. Datas
```regex
\d{2}/\d{2}/\d{4}
```
Exemplos: 31/12/2025, 30/04/2026, 02/05/2026

### 4. Quantidades
```regex
\d+
```
Exemplos: 400, 190, 2125

## 📑 Seções Principais

### 1. **POSIÇÃO CONSOLIDADA**
Resumo por tipo de ativo:
- 4.89% Ações = R$ 19.344,00
- 95.11% Fundos Imobiliários = R$ 367.876,14
- Saldo Disponível: R$ 7.745,95

### 2. **POSIÇÃO DETALHADA DOS ATIVOS**
Tabelas com dados de cada ativo:
- Ticker, Quantidades (7 tipos), Preço médio, Rentabilidade, Última cotação, Posição

### 3. **JUROS SOBRE CAPITAL**
Rendimentos separados por ticker e data:
```
VIVT3 | 30/04/2026 | Qtd 405  | Valor R$ 41,52
PSSA3 | 30/04/2026 | Qtd 385  | Valor R$ 205,51
VIVT3 | 30/04/2026 | Qtd 400  | Valor R$ 24,77
PSSA3 | 30/11/2026 | Qtd 400  | Valor R$ 215,04
```

## 💾 Dados Extraídos

### ✅ Disponível no PDF
- Ticker do ativo (PSSA3, PLAG11, etc)
- Quantidade total em 31/12/2025
- Preço médio e última cotação
- Valor total em R$ da posição
- Data de rendimento (Juros sobre Capital)
- Valor do rendimento
- Saldo em dinheiro

### ❌ Não Disponível
- CNPJ da empresa emissora
- Nome completo da empresa
- Tipo de ativo (Ação vs FII vs ETF) – apenas inferível pelo ticker
- Custodia CNPJ
- Data de compra/aquisição

## 🔄 Comparação com Avenue

| Critério | Avenue | Clear |
|----------|--------|-------|
| **Moeda** | USD (com Ptax/conversão) | BRL direto |
| **Grupo-Código** | Explícito (03-01) | Precisa inferir |
| **Rendimento** | Por ativo, IRRF sep | Seção "Juros Sobre Capital" |
| **Localização** | Exterior (USA) | Brasil |
| **Cambial** | USD cost + BRL cost | Apenas BRL |
| **CNPJ** | Presente | Ausente |
| **Tipo Ativo** | Explícito | Inferir do ticker |

**Conclusão**: Clear é mais simples (sem conversão cambial), mas requer inferência de tipo de ativo pelo ticker.

## 📋 Mapeamento para Entry (secao="Bens e Direitos")

### Tipo 1: AÇÕES (Grupo 04, Código 01)
```python
Entry(
    arquivo="Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf",
    instituicao="Clear Corretora",
    cnpj_instituicao="CLEAR_CNPJ",  # TBD
    ano_calendario=2025,
    
    secao="Bens e Direitos",
    grupo="04",
    grupo_desc="Aplicações e Investimentos",
    codigo="01",
    codigo_desc="Ações",
    
    discriminacao="PSSA3 – Petrobras (ou similar)",
    localizacao="105 - Brasil",
    
    valor_2025=19_344.00,  # Qtd (400) × Última Cotação (R$ 48,36)
    rendimento=0.0,  # Juros sobre Capital encontrado em seção separada
)
```

### Tipo 2: FUNDOS IMOBILIÁRIOS (Grupo 04, Código 02)
```python
Entry(
    # ... mesmo que acima, mas:
    codigo="02",
    codigo_desc="Fundos Imobiliários",
    
    discriminacao="PLAG11 – Fundo A (ou similar)",
    valor_2025=9_785.00,  # 190 × R$ 51,50
)
```

### Tipo 3: SALDO EM DINHEIRO (Grupo 06, Código 01)
```python
Entry(
    # ... mesmo que acima, mas:
    grupo="06",
    grupo_desc="Depósito à Vista e Numerário",
    codigo="01",
    codigo_desc="Depósito à Vista",
    
    discriminacao="Saldo em Custódia – Clear",
    valor_2025=7_745.95,
)
```

## 🎯 Estratégia de Implementação

### 1. Detectar tipo de ativo pelo ticker
```python
def infer_asset_type(ticker: str) -> tuple[str, str]:
    """Infer (codigo, codigo_desc) from ticker suffix"""
    # PSSAX = Ação (no 3)
    # PLAG11, SNFF11 = FII (terminam em 11, 13, 21)
    # VIVT3 = Ação (terminam em 3, 4, 5)
    if ticker[-2:] in ['11', '13', '21', '24', '39']:
        return "02", "Fundos Imobiliários"
    else:
        return "01", "Ações"
```

### 2. Processar tabelas
```python
def parse_clear_assets(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                # Processa cada linha de ativo
                # Match ticker com formato: [A-Z][A-Z0-9]{3}[0-9]{1,2}
```

### 3. Match rendimentos
```python
def match_juros_sobre_capital(full_text: str, ticker: str) -> float:
    """Find 'Juros sobre Capital' entries for specific ticker"""
    pattern = f"JUROS SOBRE CAPITAL.*?{ticker}.*?R\$\s*([\d.,]+)"
    # Soma todos os valores encontrados
```

### 4. Criar Entry
```python
entries.append(Entry(
    arquivo=os.path.basename(pdf_path),
    instituicao="Clear Corretora",
    cnpj_instituicao="...",  # TBD
    ano_calendario=2025,
    secao="Bens e Direitos",
    grupo="04",
    grupo_desc="Aplicações e Investimentos",
    codigo=codigo,
    codigo_desc=codigo_desc,
    discriminacao=f"{ticker} – Custódia",
    valor_2025=posicao_total,
    rendimento=juros_encontrados,
    localizacao="105 - Brasil",
))
```

## 📝 Notas de Implementação

1. **Sem Cambial**: Não precisa de conversão USD→BRL (tudo já em BRL)
2. **Tipo Inferido**: Usar regex do ticker para classificar Ação vs FII
3. **Rendimentos**: Buscar em seção separada "JUROS SOBRE CAPITAL"
4. **Saldo**: Adicionar uma Entry para "Saldo Disponível" em Grupo 06
5. **CNPJ**: Verificar se há informação em outro documento/seção
6. **Nome Empresa**: Usar lookup table ou deixar como "–"

## 🔗 Próximos Passos

- [ ] Implementar `parse_clear()` em `parser.py`
- [ ] Criar função para classificar tipos de ativos
- [ ] Testar com arquivos reais
- [ ] Adicionar testes em `test_dashboard.py`
- [ ] Atualizar documentação

---
**Análise Concluída**: 03/05/2026  
**Arquivo Analisado**: Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf (668 KB, 8 páginas)
