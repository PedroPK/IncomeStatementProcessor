# Arquitetura do Income Statement Processor

## � Estrutura de Pastas

```
src/
  __init__.py
  main.py                    # Orquestração principal (web + CLI)
  models.py                  # Data model (Entry)
  extractor.py              # Extração de ZIP (com filtro de artefatos macOS)
  parser.py                 # Parser de PDFs (9 instituições)
  custodia_parser.py        # Parser de XLSX com dados de custódia
  normalizer.py             # Normalização de valores e extração de contribuinte
  dashboard_generator.py    # Geração de dashboard HTML interativo
  sheets_writer.py          # Integração com Google Sheets
  xlsx_writer.py            # Escrita de planilha XLSX (4 abas)
  
  tests/                    # Testes automatizados
    __init__.py
    test_integration.py         # Testes de integração com dados mockados
    test_dashboard.py           # Testes do dashboard
    test_zip_and_parse_resilience.py  # Testes de resiliência (artefatos macOS, timeout)
  
  analysis/                 # Ferramentas de análise
    __init__.py
    analyze_clear_pdf.py    # Análise de PDF da Clear
    analyze_mapping.py      # Mapeamento de campos
  
  examples/                 # Exemplos de uso
    __init__.py
    examples_dashboard.py   # Exemplos de geração de dashboard
  
  generators/               # Geradores de documentação
    __init__.py
    generate_dashboard_docs.py  # Documentação visual do dashboard

scripts/                    # Scripts auxiliares e de desenvolvimento
  explore_pdfs.py
  process_ana_gloria.py
  process_pipeline.py
  test_dashboard.py
  test_dashboard_v2.py
  test_extraction.py
  test_pipeline.py
```

## 📐 Visão Geral do Pipeline

O Income Statement Processor segue uma arquitetura **pipeline em cascata** com separação clara de responsabilidades:

```
Input ZIP
   ├── PDFs (Informes de Rendimentos)
   └── XLSX (Dados de Custódia)
      ↓
[Extraction Layer] ← Descompactação + Detecção
      ↓
   ├── PDFs Individualizados
   └── XLSX Custódia
      ↓
[Parsing Layer] ← 6 Parsers PDFs + Parser XLSX
      ↓
Entradas Normalizadas (list[Entry])
      ↓
[Output Layer] ← XLSX + Dashboard HTML + Google Sheets (opcional)
      ↓
Artefatos de Saída
```

## 🏗️ Componentes

### 1. Camada de Extração (`extractor.py`)

**Responsabilidades:**
- Localizar arquivo ZIP em `input/`
- Descompactar com suporte a múltiplas codificações
- Retornar mapa de arquivos extraídos

**Funções:**
- `find_zip(input_dir: str) -> str | None`
  - Busca recursiva por `*.zip`
  - Retorna caminho ou `None`

- `extract_zip(zip_path: str) -> dict[str, str]`
  - Descompacta ZIP tratando CP437 (XP Previdência)
  - Retorna `{filename: extracted_path}`
  - **Novo**: Extrai também arquivos XLSX para custódia

**Fluxo de Tratamento de Encoding:**

```
ZIP file (bytes)
    ↓
Try UTF-8 decode
    ↓ (falha)
Try CP437 decode
    ↓ (sucesso)
Escreve arquivo
```

**Problema Resolvido:** O arquivo `XP - Previdência...pdf` tem nome com `é` (cedilha) que em ZIP histórico (CP437) não é UTF-8. Solução: `ZipFile(... encoding='utf-8')` com fallback manual.

---

### 2. Camada de Parsing

#### 2.1 Parser de PDFs (`parser.py`)

**Detector de Instituição:**

```python
def detect_institution(filename: str, first_page: str) -> str
```

**Estratégia:** Pattern matching progressivo
1. Nome do arquivo (mais confiável)
2. Texto da primeira página (fallback)

**Padrões:**

| Instituição | Pattern |
|---|---|
| Accenture | `accenture` no filename |
| Avenue | `avenue` no filename |
| Clear | `clear` no filename ou `www.clear.com.br` no texto |
| Inter | `inter` no filename |
| NuBank | `nubank` ou `nu bank` no filename |
| XP | `xp` no filename (sem `previdência`) |
| XP Previdência | `xp` + `prev`/`previd` no filename |
| FACHESF | `fachesf` ou `chesf` no filename, ou `fundacao chesf` no texto |
| INSS | `inss` no filename, ou `regime geral de previdencia`/`frgps` no texto |

**Dispatcher Principal:**

```python
def parse_file(filepath: str) -> list[Entry]
```

**Fluxo:**
1. Abre PDF com pdfplumber
2. Extrai `pages_text` (texto por página)
3. Extrai `pages_tables` (tabelas estruturadas por página)
4. Detecta instituição
5. Chama parser específico
6. Retorna `list[Entry]`

#### 2.2 Parser de Custódia (`custodia_parser.py`)  ✨ NOVO

**Responsabilidades:**
- Ler arquivo XLSX com dados de custódia
- Mapear tickers para grupo/código IRPF
- Calcular custo de aquisição (quantidade × preço_médio)

**Estrutura Esperada do XLSX:**

| Coluna | Descrição | Tipo | Exemplo |
|--------|-----------|------|---------|
| A | Ativo (Ticker) | String | PSSA3, PLAG11 |
| B | Quantidade de Cotas | Float | 100, 50.5 |
| C | Preço Médio (BRL) | Float | 45.50, 120.00 |

**Algoritmo:**

```python
def parse_custodia_xlsx(filepath: str, instituicao: str) -> list[Entry]
```

1. Abre workbook com openpyxl
2. Localiza header row ("ativo", "quantidade", "preço")
3. Para cada linha de dados:
   - Extrai: ticker, quantidade, preço_médio
   - Calcula: custo_aquisicao = quantidade × preço_médio
   - Mapeia ticker → (grupo, codigo)
   - Cria Entry com secao="Bens e Direitos"
4. Retorna `list[Entry]`

**Mapeamento de Ticker para Grupo/Código:**

| Padrão | Grupo | Código | Descrição |
|--------|-------|--------|-----------|
| Termina em 11 | 07 | 02 | Fundos Imobiliários (FII) |
| Termina em 3 ou 4 | 04 | 01 | Ações |
| Termina em 34, 35 | 03 | 01 | BDRs (Ações exterior) |
| Contains "ETF" | 07 | 03 | ETFs |
| Default | 04 | 99 | Aplicações e Investimentos (outros) |

**Exemplo de Processamento:**

```
Entrada:
  Ativo: PSSA3
  Quantidade: 400
  Preço Médio: R$ 48,36

Saída Entry:
  secao: "Bens e Direitos"
  grupo: "04"
  codigo: "01"  (Ações)
  discriminacao: "PSSA3 – Ativo em Custódia"
  valor_2025: 19.344,00  (400 × 48,36)
  observacao: "Custódia: 400.00 cotas × R$ 48,36"
```

#### 2.3 Parsers Especializados de PDFs

Cada parser implementa interface comum:
```python
def parse_BANCO(filename: str, pages_text: list[str],
                pages_tables: list[list]) -> list[Entry]
```

| Parser | Instituição | Quadros Extraídos |
|---|---|---|
| `parse_accenture` | Accenture do Brasil | Q3 Tributáveis, Q4 Isentos, Q5 Exclusivos |
| `parse_clear` | Clear Corretora | Informe + Custódia |
| `parse_inter` | Banco Inter | Q3 Tributáveis, Q4 Isentos |
| `parse_nubank` | NuBank | Q3 Tributáveis, Q4 Isentos |
| `parse_xp` | XP Investimentos | Q3 Tributáveis, Q4 Isentos, Bens e Direitos |
| `parse_xp_previdencia` | XP Previdência | Q3 Tributáveis, Q4 Isentos, Q5 Exclusivos |
| `parse_avenue` | Avenue Securities | Q3 Tributáveis, Bens e Direitos (exterior) |
| `parse_fachesf` | FACHESF | Q3 Tributáveis, Q4 Isentos, Q5 Exclusivos |
| `parse_inss` | INSS / FRGPS | Q3 Tributáveis, Q4 Isentos |

---

### 3. Camada de Saída (`xlsx_writer.py`, `dashboard_generator.py`)

**XLSX Generation:**
- Aba 1: Dados Brutos (todas as entradas, 19 colunas)
- Aba 2: Resumo (Seção × Instituição)
- Aba 3: Totais (Grupo × Código)
- Aba 4: Para IRPF (Agrupado por instituição, com rótulos de renda fixa derivados de `discriminacao`)

**Rótulos de Renda Fixa (`_renda_fixa_subtype`):**

Ativos de Renda Fixa com Grupo `04` e Código `02`/`03` são diferenciados por subtipo derivado da `discriminacao`:

| Palavra-chave em discriminacao | Rótulo exibido |
|---|---|
| TESOURO + SELIC | Tesouro Selic |
| TESOURO + IPCA | Tesouro IPCA+ |
| TESOURO + PREFIXADO | Tesouro Prefixado |
| TESOURO (genérico) | Tesouro Direto |
| CDB | CDB – Certificado de Depósito Bancário |
| RDB | RDB – Recibo de Depósito Bancário |
| LCI | LCI – Letra de Crédito Imobiliário |
| LCA | LCA – Letra de Crédito do Agronegócio |
| CRI | CRI – Certificado de Recebíveis Imobiliários |
| CRA | CRA – Certificado de Recebíveis do Agronegócio |

**Dashboard HTML:**
- 4 cards de métricas-chave
- Gráfico Pizza (distribuição por instituição)
- Gráfico Barras (evolução 2024 vs 2025)
- 4 abas de dados com formatação responsiva

**Aba Dados Brutos – Funcionalidades Interativas:**
- **Ordenação por coluna**: clique no cabeçalho `↕` ordena crescente/decrescente
- **Filtragem por coluna**: linha de inputs abaixo do cabeçalho; suporte a texto livre e expressões numéricas (`>1000`, `<500`)
- **Coluna Discriminação**: visível na tabela para facilitar filtragem de ativos específicos
- **Linha de subtotal** (`<tfoot>`): exibe soma de 2024, 2025 e Rendimento das linhas visíveis (atualizada dinamicamente com os filtros)

**Aba Para IRPF:**
- Agregação por `(Grupo, Código, rótulo_derivado)` — para renda fixa, o rótulo vem de `irpfDisplayLabel()` (dashboard) / `_renda_fixa_subtype()` (XLSX), separando Tesouro Selic/Prefixado/IPCA+ e CDB em linhas distintas

---

### 4. Pipeline de Processamento (`main.py`)

**Controle de Stall Timeout:**
- Cada arquivo PDF/XLSX é processado em thread isolada via `ThreadPoolExecutor`
- Se o parsing travar sem retornar, o arquivo é ignorado e o pipeline continua
- Configurável via `config.toml`:
  ```toml
  [processing]
  stall_timeout_seconds = 60
  ```

**Fluxo resumido:**
```
_run_pipeline(file_map, config)
  → _parse_file_map(file_map, callback, stall_timeout)
      ├── PDF: ThreadPoolExecutor (timeout/erro → registra, continua)
      └── XLSX: parse_custodia_xlsx
  → validate_single_taxpayer(entries)
  → write_xlsx + generate_dashboard_html
```

---

### 5. Módulos de Teste e Análise

#### Tests (`src/tests/`)
- `test_integration.py`: Dados mockados (12 entradas)
- `test_dashboard.py`: Testes de geração HTML
- `test_zip_and_parse_resilience.py`: Testes de artefatos macOS e resiliência

#### Analysis (`src/analysis/`)
- `analyze_clear_pdf.py`: Inspeção de PDF da Clear
- `analyze_mapping.py`: Mapeamento de campos

#### Examples (`src/examples/`)
- `examples_dashboard.py`: 5 exemplos de uso

#### Generators (`src/generators/`)
- `generate_dashboard_docs.py`: Documentação visual

```python
def parse_file(filepath: str) -> list[Entry]
```

**Fluxo:**
1. Abre PDF com pdfplumber
2. Extrai `pages_text` (texto por página)
3. Extrai `pages_tables` (tabelas estruturadas por página)
4. Detecta instituição
5. Chama parser específico
6. Retorna `list[Entry]`

**Tratamento de Erros:**
```python
try:
    return parser_func(filename, pages_text, pages_tables)
except Exception as e:
    logger.warning(f"Parser failed for {filename}: {e}")
    return []  # Retorna lista vazia, não falha globalmente
```

#### 2.3 Parsers Especializados

Cada parser implementa interface comum:
```python
def parse_BANCO(filename: str, pages_text: list[str],
                pages_tables: list[list]) -> list[Entry]
```

**Helper Functions:**

```python
def _entry(
    filename: str, instituicao: str, cnpj: str, ano: int,
    secao: str, grupo: str, grupo_desc: str, codigo: str,
    codigo_desc: str,
    # Campos opcionais
    localizacao: str = '',
    discriminacao: str = '',
    valor_2024: float = 0.0,
    valor_2025: float = 0.0,
    rendimento: float = 0.0,
    tipo_rendimento: str = '',
    irrf: float = 0.0,
    # ...
) -> Entry
```

Funções auxiliares:
- `_grupo_desc(grupo: str) -> str`: Descrição do grupo IRPF
- `_extract_between(text: str, start: str, end: str) -> str`: Substring
- `_xp_summary_rows(text: str) -> list[str]`: Split em blocos
- `_detect_cnpj_in_block(text: str) -> str`: Regex CNPJ

---

##### **Parser: Accenture** (`parse_accenture`)

**Estrutura do PDF:**
- Comprovante de Rendimentos IRPF 2026
- Quadros 3, 4, 5 com valores de rendimentos

**Algoritmo:**
1. Regex para encontrar seções de rendimento
2. Extrai valores por tipo (salário, INSS, PLR, benefícios)
3. Cria Entry por tipo

**Exemplos de Valores:**
```
Quadro 3: "Total dos Rendimentos (incl. férias): R$ 5,48"
Quadro 4: "Contribuição Previdenciária Oficial (INSS): R$ 9,44"
Quadro 11: "Outros (PLR): R$ 15,980.45"
```

---

##### **Parser: Avenue Securities** (`parse_avenue`)

**Estrutura do PDF:**
- Página 1: Informações do beneficiário + saldo em conta
- Páginas 2-4: Tabelas de ativos (stocks, ETFs)

**Algoritmo:**

```
Página 1 (texto):
  Regex "(\d{2}-\d{2}) ESTADOS R$ ([\d.]+,\d{2}) R$ ([\d.]+,\d{2})"
  → Extrai saldo conta (06-99)

Páginas 2-4 (tabelas):
  Para cada tabela:
    Para cada linha:
      Se len(row) >= 9 e row[0] matches \d{2}-\d{2}:
        → Asset data row
        Extrai: grupo, código, símbolo, empresa, BRL cost
      Se row[0] contém "Aplicação Financeira":
        → Rendimento row (next line após asset)
        Regex "Rendimento ou perda: R$ (...)"
        Associa com asset anterior
```

**Tratamento Multi-Coluna:**
- ❌ Problema anterior: Text extraction fragmentado
- ✅ Solução v1.0: `extract_tables()` produz estrutura limpa

**Exemplo de Row Tabela:**
```python
[
  '03-01',                          # Grupo-Código
  '249 - ESTADOS\nUNIDOS',         # Localização
  'STOCK',                          # Tipo
  'GOOGL',                          # Símbolo
  'Alphabet Inc - Class A',         # Empresa
  '2',                              # Quantidade
  '$ 373.38',                       # USD cost
  'R$\n5,3923',                     # Ptax
  'R$\n2.013,39'                    # BRL cost (31/12/2025)
]
```

---

##### **Parser: Inter** (`parse_inter`)

**Estrutura:**
- Seções denominadas: "TÍTULOS PÚBLICOS", "INVESTIMENTOS EM CRIPTO", etc.

**Algoritmo:**
1. Split em seções por padrão `"^\s*[A-Z][A-Z\s]+$"` (linha de seção)
2. Para cada seção, apply regex específico por tipo
3. Extrai valores com `parse_brl()`

**Regex por Tipo:**
- Títulos renda fixa: `(GRUPO \d+)|(CÓDIGO \d+)|(Descri[çc][ão]|Valor)`
- Criptos: `(Bitcoin|USDC|Stablecoin).*?R\$\s*([\d.]+,\d{2})`

---

##### **Parser: NuBank** (`parse_nubank`)

**Estrutura:**
- Blocos de "249 - GRUPO XXX" seguidos de linhas de ativos

**Algoritmo:**

```
1. Regex para blocos: "249\s*-\s*GRUPO\s+(\d{2})"
2. Para cada bloco:
     3. Find grupo code e description
     4. Split asset rows:
        - Padrão renda fixa: "(\d{2}-\d{2}).*?R\$\s*(\d+\.\d+,\d{2})"
        - Pattern crypto: "(BTC|USDC).*?R\$\s*([\d.]+,\d{2})"
```

**Tratamento de Múltiplos Ativos do Mesmo Código:**
- Agrupa por (grupo, código)
- Cria Entry separada por ativo/moeda

---

##### **Parser: XP Investimentos** (`parse_xp`)

**Estrutura Complexa:**
- Página 1: Resumo com seções de Rendimentos
- Páginas 4-6: Tabelas com Bens e Direitos

**Algoritmo:**

```
Página 1:
  1. Regex seções: "RENDIMENTOS\s+(TRIBUTÁVEIS|ISENTOS|EXCLUSIVOS)"
  2. Para cada seção, extrai grupos de valores

Páginas 4-6 (Bens e Direitos):
  1. Itera tabelas
  2. Para cada tabela:
       - Se header: skip
       - Se "Declaração": track current_declaration
       - Se asset row: cria Entry com associação
       
  Associação (algoritmo "next declaration"):
     asset_rows = [1, 2, 3]
     declaration_rows = [0, 4]
     
     asset 1 → declaration antes de 4 → declaration 0
     asset 2 → declaration antes de 4 → declaration 0
     asset 3 → declaration antes de 4 → declaration 0
```

**Helper Específico:**

```python
def _xp_parse_detail_tables(pages_text: list[str]) -> list[Entry]
```

Lógica de associação de contexto é complexa pois as declarações estão em ordem diferente dos dados.

---

##### **Parser: XP Vida e Previdência** (`parse_xp_previdencia`)

**Estrutura:**
- Tabelas simples de VGBL/PGBL
- Valores em BRL com normalização

**Algoritmo:**
1. Extract tables
2. Skip headers
3. Para cada row, regex de valores BRL
4. Cria Entry com grupo 99 (previdência privada)

---

### 3. Camada de Normalização (`normalizer.py`)

**Funções Utilitárias:**

```python
def parse_brl(value: str) -> float
```
Converte "1.234,56" → 1234.56

Algoritmo:
```python
value = value.strip()
value = value.replace('.', '')  # Remove thousands separator
value = value.replace(',', '.')  # Comma to dot
return float(value)
```

```python
def find_cnpj(text: str) -> str
def find_all_cnpj(text: str) -> list[str]
```

Regex: `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` (com variações)

```python
def clean(text: str) -> str
```
- Trim
- Remove quebras de linha
- Normaliza múltiplos espaços

```python
def extract_year(text: str, default: int = 2025) -> int
```
Regex: `(19|20)\d{2}`

---

### 4. Camada de Saída (`xlsx_writer.py`)

**Arquitetura:**

```
list[Entry]
    ↓
_entries_to_df() → pandas.DataFrame (19 colunas)
    ↓
openpyxl.Workbook criado
    ↓
_write_dados_brutos()  → Aba 1: Table com freeze panes
_write_resumo()        → Aba 2: Pivot
_write_totais()        → Aba 3: Aggregation
_write_para_irpf()     → Aba 4: By institution
    ↓
wb.save()
```

#### Aba 1: Dados Brutos

```python
def _write_dados_brutos(wb, df: pd.DataFrame)
```

- Todas as linhas do DataFrame
- Formatação: Excel Table (banded rows)
- Freeze panes: 1 linha + 1 coluna
- Auto-width: calcula max width por coluna

#### Aba 2: Resumo (Pivot)

```python
def _write_resumo(wb, df: pd.DataFrame)
```

- Pivot table: index=(Seção, Grupo, Código) × columns=Instituições
- Agregação: sum de valores
- Separadores visuais por seção (merged cells + borders)

#### Aba 3: Totais

```python
def _write_totais(wb, df: pd.DataFrame)
```

- Groupby (Grupo, Código)
- Agregação: sum de 2024, 2025, rendimento
- Linha final com TOTAL GERAL

#### Aba 4: Para IRPF

```python
def _write_para_irpf(wb, df: pd.DataFrame)
```

- Agrupado por Instituição
- Dentro de cada instituição: seções
- Subtotais por seção
- Facilitação para cópia direto em formulário IRPF

---

### 5. Exportação Google Sheets (`sheets_writer.py`)

**Fluxo OAuth2:**

```
1. Verifica credentials.json
2. Se não existe ou expired:
   - Abre browser para autenticação
   - Salva token.json
3. Cria/abre spreadsheet
4. Escreve 4 abas via gspread
```

**Funções:**

```python
def push_to_sheets(entries: list[Entry], config: dict) -> None
```

- Autenticação OAuth2
- Criação/abertura de spreadsheet
- Escrita de dados

---

### 6. Orquestração (`main.py`)

**Sequência de Execução:**

```python
def main():
    # 1. Encontrar ZIP
    zip_path = find_zip('input')
    assert zip_path, "ZIP não encontrado"
    
    # 2. Extrair
    file_map = extract_zip(zip_path)
    
    # 3. Processar cada arquivo
    all_entries: list[Entry] = []
    for filename, filepath in file_map.items():
        entries = parse_file(filepath)
        all_entries.extend(entries)
    
    # 4. Validar
    assert len(all_entries) > 0, "Nenhuma entrada extraída"
    
    # 5. Gerar XLSX
    output_path = config['output']['xlsx_path']
    write_xlsx(all_entries, output_path)
    
    # 6. Exportar Google Sheets (opcional)
    if config['google_sheets']['enabled']:
        push_to_sheets(all_entries, config)
```

---

## 📊 Fluxo de Dados

### Exemplo: Entrada Avenue

```
Input: Avenue PDF
   ↓
[extractor] → Extract ZIP
   ↓
Avenue - Informe de Rencimentos - Ano Base 2025 IRPF2026 - relatorio anual.pdf
   ↓
[parser.detect_institution]
   Filename match: "avenue" → instituição = 'avenue'
   ↓
[parser.parse_avenue]
   Página 1 (text):
     Regex "06-99 ESTADOS R$ 1.415,92 R$ 1.082,42"
     → Entry(grupo=06, codigo=99, valor_2024=1415.92, valor_2025=1082.42)
   
   Páginas 2-4 (tables):
     Row: ['03-01', '249 - ESTADOS\nUNIDOS', 'STOCK', 'GOOGL', 'Alphabet Inc - Class A', '2', '$ 373.38', 'R$ 5,3923', 'R$ 2.013,39']
     → Entry(grupo=03, codigo=01, ..., valor_2025=2013.39)
     
     Row: ['Aplicação Financeira => Rendimento ou perda: R$ 6,18 / Imposto pago no exterior: R$ 1,86', None, ...]
     → Atualiza entrada anterior: rendimento=6.18, irrf=1.86
     ↓
   list[Entry] (16 entradas)
   ↓
[normalizer]
   parse_brl("2.013,39") → 2013.39
   clean("249 - ESTADOS\nUNIDOS") → "249 - Estados Unidos"
   ↓
Entry normalizada
   ↓
[xlsx_writer]
   Entry → Linha em Dados Brutos
   → Agregação em Resumo (Grupo/Código × Institution)
   → Total por Código
   → Formatação em Para IRPF
   ↓
output/informes_rendimentos.xlsx
```

---

## 🔍 Padrões de Design

### 1. Dispatcher Pattern

**Uso:** Roteamento dinâmico para parsers

```python
if institution == 'accenture':
    return parse_accenture(...)
elif institution == 'avenue':
    return parse_avenue(...)
# ...
```

**Vantagem:** Fácil adicionar nova instituição sem alterar fluxo principal

### 2. Factory Pattern

**Uso:** Criação padronizada de Entries

```python
def _entry(...) -> Entry:
    return Entry(
        grupo=grupo.zfill(2),
        codigo=codigo.zfill(2),
        # ... normalização automática
    )
```

### 3. Pipeline Pattern

**Uso:** Extração → Parsing → Normalização → Output

Cada stage processa saída do anterior.

### 4. Configuration Pattern

**Uso:** `config.toml` para comportamento dinâmico

```toml
[google_sheets]
enabled = true  # Liga/desliga feature
```

---

## ⚠️ Limites e Considerações

### 1. Performance

- PDF parsing com pdfplumber: ~100-500ms por arquivo
- Para 6 arquivos: ~1s total
- XLSX generation com openpyxl: ~100ms
- Google Sheets API: ~2-5s (rate limiting)

### 2. Confiabilidade

- Parsers são resilientes: falha em 1 arquivo não quebra tudo
- Tratamento de encoding: UTF-8 + CP437 fallback
- Validação: Verifica se extrados > 0 antes de output

### 3. Escalabilidade

- Atual: 6 instituições, ~60 entradas
- Próximo: +2-3 instituições (Itaú, Bradesco, etc.)
- Limite: ~10,000 entradas antes de considerar otimização (DataFrame)

### 4. Manutenibilidade

- Cada parser é isolado → fácil manutenção
- Testes por instituição → isolamento de falhas
- Documentação em docstrings

---

## 🚦 Próximos Passos (v1.1+)

1. **Refatoração de Parsers:**
   - Extratificar lógica comum (regex, tables)
   - Criar base class `BaseParser`

2. **Validação:**
   - Schema validation para Entry
   - Verificação de soma (valores 2024 + 2025 + rendimento)

3. **Testes:**
   - Unit tests para cada parser
   - Integration tests end-to-end
   - Fixtures com PDFs reais

4. **Monitoring:**
   - Logging estruturado (DEBUG/INFO/WARNING)
   - Rastreamento de tempo por stage
   - Relatório de qualidade

5. **API Web:**
   - FastAPI para upload de ZIP
   - Async processing
   - WebSocket para progresso em tempo real

---

## 📖 Referências

- [pdfplumber Architecture](https://github.com/jamesturk/pdfplumber#architecture)
- [Python Design Patterns](https://refactoring.guru/design-patterns/python)
- [openpyxl Performance Tips](https://openpyxl.readthedocs.io/en/stable/performance.html)
