# Arquitetura do Income Statement Processor

## 📐 Visão Geral

O Income Statement Processor segue uma arquitetura **pipeline em cascata** com separação clara de responsabilidades:

```
Input ZIP
   ↓
[Extraction Layer] ← Descompactação + Detecção
   ↓
PDFs Individualizados
   ↓
[Parsing Layer] ← 6 Parsers especializados + Dispatcher
   ↓
Entradas Normalizadas (list[Entry])
   ↓
[Output Layer] ← XLSX + Google Sheets (opcional)
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

### 2. Camada de Parsing (`parser.py`)

#### 2.1 Detector de Instituição

```python
def detect_institution(filename: str, first_page: str) -> str
```

**Estratégia:** Pattern matching progressivo
1. Nome do arquivo (mais confiável)
2. Texto da primeira página (fallback)

**Padrões:**

| Instituição | Pattern |
|---|---|
| Accenture | `accenture` (case-insensitive) |
| Avenue | `avenue` |
| Inter | `inter` |
| NuBank | `nubank` |
| XP | `xp` + (não contém "previdência") |
| XP Previdência | `xp` + `previdência` |

#### 2.2 Dispatcher Principal

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
