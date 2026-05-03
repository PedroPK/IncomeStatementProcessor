# Income Statement Processor (Processador de Informes de Rendimentos)

Ferramenta Python para extrair, processar e consolidar Informes de Rendimentos (IRPF 2026) de 7 instituições financeiras brasileiras e internacionais, gerando um relatório Excel multitabs com classificação automática por grupo/código e categorização de rendimentos.

## 📋 Funcionalidades

- **Extração de múltiplos formatos PDF**: Suporte nativo para 7 instituições:
  - Accenture (Comprovante de Rendimentos)
  - Avenue Securities (Ativos em custódia + depósitos)
  - Clear (Fundos + renda fixa + Tesouro Direto)
  - Inter (Renda fixa + criptoativos)
  - NuBank (Renda fixa + fundos)
  - XP Investimentos (Fundos + renda fixa + Tesouro Direto)
  - XP Vida e Previdência (VGBL/PGBL)

- **Processamento robusto**:
  - Detecção automática de instituição por nome de arquivo
  - Leitura de ZIP com suporte a codificação UTF-8 e CP437
  - Extração de tabelas PDF (pdfplumber) + análise de texto
  - Normalização de valores monetários brasileiros (1.234,56 → 1234.56)
  - Localização de CPF/CNPJ via regex

- **Saída estruturada (XLSX)**:
  - **Dados Brutos**: Todas as 59 entradas com 19 colunas
  - **Resumo**: Pivot por Seção × Grupo/Código × Instituição
  - **Totais**: Agregação por grupo com linha de total
  - **Para IRPF**: Formatado por instituição com separadores de seção

- **Exportação opcional para Google Sheets** (via config `google_sheets.enabled`)

## 🚀 Instalação

### Requisitos
- Python 3.11+
- pip

### Setup

```bash
# Clone ou navegue para o diretório do projeto
cd /Users/pedropk/Downloads/Apps/Development/IDEs/VsWorkspace/IncomeStatementProcessor

# Crie um ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# ou: .venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

## 📖 Como Usar

### 1. Preparar dados de entrada

- Coloque os PDFs em um ZIP na pasta `input/`
- Ou coloque um ZIP denominado `*.zip` em `input/`
- Nomes de arquivo esperados (sistema detecta automaticamente):
  ```
  Accenture*.aspx
  Avenue*.pdf
  Clear*.pdf
  Inter*.pdf
  NuBank*.pdf
  XP*.pdf          (main report)
  XP*Previdência*.pdf
  ```

### 2. Configurar (opcional)

Edite `config.toml`:
```toml
[output]
xlsx_path = "output/informes_rendimentos.xlsx"

[google_sheets]
enabled = false  # true para exportar para Sheets
spreadsheet_name = "Informes de Rendimentos"
credentials_file = "credentials/credentials.json"
token_file = "credentials/token.json"
```

### 3. Executar

```bash
python3 -m src.main
```

Saída esperada:
```
ZIP encontrado: input/drive-download-20260502T172444Z-3-001.zip
Extraindo arquivos...
  6 arquivo(s) extraído(s).
  Processando: Accenture - Informe de Rendimentos...
    → 5 entradas extraídas.
  ...
Total: 59 entradas de 6 arquivo(s).

Gerando planilha XLSX...
  Planilha salva em: output/informes_rendimentos.xlsx
```

## 📊 Estrutura de Dados

Cada entrada contém:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `arquivo` | str | Nome do arquivo PDF |
| `instituicao` | str | Nome da instituição |
| `cnpj_instituicao` | str | CNPJ ou vazio |
| `ano_calendario` | int | Ano do informe (2025) |
| `secao` | str | Rendimentos/Bens/Contribuições |
| `grupo` | str | Código de grupo IRPF (01-99) |
| `grupo_desc` | str | Descrição do grupo |
| `codigo` | str | Código dentro do grupo |
| `codigo_desc` | str | Descrição do código |
| `localizacao` | str | Localização do ativo (país/região) |
| `discriminacao` | str | Detalhes do ativo |
| `valor_2024` | float | Valor em 31/12/2024 |
| `valor_2025` | float | Valor em 31/12/2025 |
| `rendimento` | float | Rendimento/dividendo |
| `tipo_rendimento` | str | Tributação Exclusiva/Isenta |
| `irrf` | float | Imposto retido na fonte |
| `fonte_pagadora` | str | Nome da fonte |
| `cnpj_fonte` | str | CNPJ da fonte |
| `observacao` | str | Notas adicionais |

## 🏗️ Arquitetura

### Fluxo de Processamento

```
input/*.zip
    ↓
[extractor.py] → extract ZIP com suporte UTF-8/CP437
    ↓
PDFs extraídos
    ↓
[parser.py] → detect_institution() → institution-specific parser
    ↓
list[Entry]
    ↓
[xlsx_writer.py] → openpyxl → 4 abas (Dados, Resumo, Totais, Para IRPF)
    ↓
output/informes_rendimentos.xlsx
    ↓ (se enabled)
[sheets_writer.py] → gspread + OAuth2 → Google Sheets
```

### Módulos

| Arquivo | Responsabilidade |
|---------|------------------|
| `models.py` | Dataclass `Entry` — estrutura de dados |
| `normalizer.py` | `parse_brl()`, `find_cnpj()`, `clean()` |
| `extractor.py` | `extract_zip()`, `find_zip()` |
| `parser.py` | 7 parsers por instituição + `detect_institution()` |
| `xlsx_writer.py` | Geração de 4 abas XLSX com openpyxl |
| `sheets_writer.py` | Exportação opcional para Google Sheets |
| `main.py` | Orquestração principal |

### Parsers por Instituição

#### Accenture
- **Entrada**: PDF/ASPX com Comprovante de Rendimentos
- **Extração**: Quadros 3, 4, 5 (rendimentos por tipo)
- **Saída**: Rendimentos Tributáveis PJ + Contribuições

#### Avenue Securities
- **Entrada**: PDF com tabelas estruturadas de ativos
- **Extração**: Página 1 (saldo em conta) + Páginas 2-4 (tabelas de stocks/ETFs)
- **Método**: `pdfplumber.extract_tables()` (não text regex)
- **Saída**: Bens e Direitos por ativo individual

#### Clear
- **Entrada**: PDF com formato padrão Ministério da Economia (Informe de Rendimentos)
- **Extração**: Reutiliza parser XP (mesmo formato de documento)
- **Saída**: Rendimentos Tributação Exclusiva + Bens e Direitos (fundos, renda fixa, etc.)

#### Inter
- **Entrada**: PDF com seções denominadas
- **Extração**: Text parsing com regex por tipo (títulos, criptos)
- **Saída**: Bens e Direitos + Rendimentos Tributação Exclusiva

#### NuBank
- **Entrada**: PDF com blocos de Grupo/Código
- **Extração**: Padrão "249 - GRUPO" + linhas de dados estruturadas
- **Saída**: Bens e Direitos + Rendimentos (renda fixa + criptoativos)

#### XP Investimentos
- **Entrada**: PDF com seções de Rendimentos + tabelas de Bens
- **Extração**: Página 1 (resumo) + Páginas 4-6 (detalhes + associação com declarações)
- **Saída**: Rendimentos Tributação Exclusiva + Bens e Direitos

#### XP Vida e Previdência
- **Entrada**: PDF com VGBL/PGBL
- **Extração**: Tabelas estruturadas + regex para valores BRL
- **Saída**: Bens e Direitos (previdência privada) + Contribuições

## 🔧 Configuração Avançada

### Google Sheets (Opcional)

1. Habilite em `config.toml`:
   ```toml
   [google_sheets]
   enabled = true
   ```

2. Crie credenciais OAuth2:
   - Google Cloud Console → Create Project
   - Enable Google Sheets API
   - Create OAuth 2.0 Desktop App credentials → `credentials.json`
   - Coloque em `credentials/credentials.json`

3. Na primeira execução, o programa abrirá browser para autenticação (gera `token.json`)

### Enviroment Variables (Opcional)

```bash
export GOOGLE_SHEETS_ENABLED=true
export GOOGLE_SHEETS_SPREADSHEET_NAME="Meus Informes IRPF"
```

## � Exemplos de Saída (Dados Mockados)

### Aba 1: Dados Brutos

Contém todas as 10 entradas com 19 colunas, formatadas como Excel Table com linhas alternadas:

| Arquivo | Instituição | Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|---------|-------------|-------|-------|--------|-----------|------|------|-----------|
| Accenture - Informe... | Accenture | Rendimentos Tributáveis PJ | | 01 | Rendimentos de PJ | R$ 0 | R$ 45,000 | R$ 0.00 |
| Accenture - Informe... | Accenture | Rendimentos Tributação Exclusiva | | 11 | PLR 2025 | R$ 0 | R$ 0 | R$ 12,500.00 |
| Itau - Informe... | Itaú Bank | Bens e Direitos | 04 | 02 | Títulos públicos/privados | R$ 50,000 | R$ 52,500 | R$ 0.00 |
| Itau - Informe... | Itaú Bank | Rendimentos Tributação Exclusiva | | 06 | Rendimento de aplicações | R$ 0 | R$ 0 | R$ 2,500.00 |
| Bradesco - Informe... | Bradesco Corretora | Bens e Direitos | 07 | 01 | Fundos de investimento | R$ 100,000 | R$ 115,000 | R$ 0.00 |

### Aba 2: Resumo (Pivot por Seção × Instituição)

Agrupa os valores por seção e instituição para visão consolidada:

| Seção | Accenture | Bradesco | Itaú Bank | NuBank | XP | Total |
|-------|-----------|----------|-----------|--------|-----|-------|
| **Bens e Direitos** | R$ 0 | R$ 215,000 | R$ 52,500 | R$ 53,700 | R$ 2,150 | R$ 323,350 |
| **Rendimentos Tributáveis PJ** | R$ 45,000 | — | — | — | — | R$ 45,000 |
| **Rendimentos Tributação Exclusiva** | R$ 12,500 | R$ 8,750 | R$ 2,500 | — | R$ 125.50 | R$ 23,875.50 |
| **TOTAL** | **R$ 57,500** | **R$ 223,750** | **R$ 55,000** | **R$ 53,700** | **R$ 2,275.50** | **R$ 392,225.50** |

### Aba 3: Totais (Agregação por Grupo/Código)

Consolida todos os valores por classificação IRPF (Grupo/Código):

| Grupo | Código | Descrição | 2024 | 2025 | Rendimento | Total |
|-------|--------|-----------|------|------|-----------|-------|
| — | 01 | Rendimentos de PJ | R$ 0 | R$ 45,000 | R$ 0 | R$ 45,000 |
| — | 06 | Rendimento de aplicações financeiras | R$ 0 | R$ 0 | R$ 11,375.50 | R$ 11,375.50 |
| — | 11 | Participação nos lucros/resultados | R$ 0 | R$ 0 | R$ 12,500 | R$ 12,500 |
| **03** | **01** | **Ações** | **R$ 1,850** | **R$ 2,150** | **R$ 0** | **R$ 4,000** |
| **04** | **02** | **Títulos públicos/privados** | **R$ 80,000** | **R$ 83,700** | **R$ 0** | **R$ 163,700** |
| **07** | **01** | **Fundos de investimento** | **R$ 100,000** | **R$ 115,000** | **R$ 0** | **R$ 215,000** |
| **08** | **01** | **Bitcoin (BTC)** | **R$ 15,000** | **R$ 22,500** | **R$ 0** | **R$ 37,500** |
| **TOTAL GERAL** | | | **R$ 196,850** | **R$ 268,350** | **R$ 23,875.50** | **R$ 489,075.50** |

### Aba 4: Para IRPF (Agrupado por Instituição)

Organizado por instituição com subtotais por seção — facilita preenchimento direto da DIRPF:

| Instituição | Seção | Grupo | Código | 2024 | 2025 | Rendimento |
|-------------|-------|-------|--------|------|------|-----------|
| **Accenture** | Rendimentos Tributáveis PJ | — | 01 | R$ 0 | R$ 45,000 | R$ 0 |
| | Rendimentos Tributação Exclusiva | — | 11 | R$ 0 | R$ 0 | R$ 12,500 |
| | *Subtotal Accenture* | | | R$ 0 | R$ 45,000 | R$ 12,500 |
| **Bradesco Corretora** | Bens e Direitos | 07 | 01 | R$ 100,000 | R$ 115,000 | R$ 0 |
| | Rendimentos Tributação Exclusiva | — | 06 | R$ 0 | R$ 0 | R$ 8,750 |
| | *Subtotal Bradesco* | | | R$ 100,000 | R$ 115,000 | R$ 8,750 |
| **Itaú Bank** | Bens e Direitos | 04 | 02 | R$ 50,000 | R$ 52,500 | R$ 0 |
| | Rendimentos Tributação Exclusiva | — | 06 | R$ 0 | R$ 0 | R$ 2,500 |
| | *Subtotal Itaú* | | | R$ 50,000 | R$ 52,500 | R$ 2,500 |

**Resumo de Dados Mockados:**
```
Entradas: 10 de 5 instituições
Total 2024: R$ 196,850.00
Total 2025: R$ 268,350.00
Total Rendimentos: R$ 23,875.50
Total IRRF: R$ 5,287.65
```

## 📊 Dashboard Interativo

O projeto gera automaticamente um **dashboard HTML interativo** que visualiza os dados de forma dinâmica:

### Recursos

- **4 Abas Interativas**: Dados Brutos, Resumo, Totais, Para IRPF (mesmos dados do XLSX)
- **Gráficos Dinâmicos**: 
  - Pie chart: Distribuição de ativos por instituição (2025)
  - Bar chart: Evolução 2024 → 2025 por instituição
- **Métricas-Chave**: Cards destacando Total 2024, Total 2025, Rendimentos, Quantidade de Entradas
- **Tabelas Responsivas**: Currency formatting automático (Intl.NumberFormat pt-BR)
- **Bootstrap 5.3**: Design profissional e mobile-friendly

### Visualização

```bash
# O dashboard é gerado automaticamente após a execução:
python3 -m src.main

# Saída:
# Gerando dashboard HTML...
# ✅ Dashboard gerado: output/dashboard.html
#    Entradas: 59
#    Total 2024: R$ 466.311,07
#    Total 2025: R$ 651.499,50
#    Total Rendimentos: R$ 55.792,97

# Abra em seu navegador:
open output/dashboard.html  # macOS
# ou firefox output/dashboard.html  # Linux
# ou start output/dashboard.html    # Windows
```

### Geração Programática

Para gerar o dashboard a partir de código Python:

```python
from src.dashboard_generator import generate_dashboard_html
from src.models import Entry

# Com lista de entradas
entries = [...]  # list[Entry]
generate_dashboard_html(entries, 'meu_dashboard.html')
```

### Configuração

Customize o caminho de saída do dashboard em `config.toml`:

```toml
[output]
xlsx_path = "output/informes_rendimentos.xlsx"
dashboard_path = "output/dashboard.html"
```

### 📚 Documentação Completa do Dashboard

Para uma visualização completa com exemplos de dados, veja:
- **[DASHBOARD_VISUAL.md](DASHBOARD_VISUAL.md)** — Tabelas e exemplos de todas as 4 abas
- **[DASHBOARD.md](DASHBOARD.md)** — Arquitetura, customização e API
- **[examples/README.md](examples/README.md)** — 5 cenários de uso práticos

## 🧪 Testes Automatizados

O projeto inclui testes de integração com dados mockados que cobrem o pipeline completo:

```bash
# Executar testes de integração
python3 test_integration.py

# Executar testes do dashboard
python3 test_dashboard.py
```

**Testes incluídos:**

### test_integration.py (Mock Data)
- ✅ `test_mock_data_integrity()`: Valida estrutura e consistência de dados
- ✅ `test_xlsx_generation_with_mock_data()`: Testa geração XLSX completa (4 abas)
- ✅ `test_mock_data_summary()`: Imprime resumo de dados e consolidação
- ✅ `get_markdown_tables_for_documentation()`: Gera tabelas para documentação

### test_dashboard.py (Dashboard Tests)
- ✅ `test_dashboard_generation` — HTML gerado com sucesso
- ✅ `test_dashboard_data_embedding` — JSON embedded corretamente
- ✅ `test_dashboard_tabs` — 4 abas presentes e funcionais
- ✅ `test_dashboard_charts` — Charts Chart.js configurados
- ✅ `test_dashboard_metrics` — Cards de métricas calculados corretamente
- ✅ `test_dashboard_with_extended_data` — Funciona com conjuntos maiores
- ✅ `test_dashboard_responsive_design` — Classes Bootstrap presentes
- ✅ `test_dashboard_currency_formatting` — Formatação de moeda OK
- ✅ `test_dashboard_all_institutions` — Todas as instituições aparecem
- ✅ `test_dashboard_section_aggregation` — Seções agregadas corretamente

**Resultado**: ✅ 20/20 testes passando

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| `ZIP não encontrado` | Coloque arquivo `.zip` em `input/` |
| `Instituição desconhecida` | Verifique nome do arquivo — deve conter "Accenture", "Avenue", "Inter", "NuBank", "XP" |
| `0 entradas extraídas` | Verifique estrutura do PDF — pode ser necessário ajustar o parser |
| `Erro de encoding` | O sistema trata automaticamente UTF-8 e CP437; verifique se ZIP está corrompido |
| `Google Sheets erro de autenticação` | Verifique `credentials/credentials.json` e `credentials/token.json` |

## 📦 Dependências

```
pdfplumber>=0.11      # Extração de tabelas e texto PDF
pandas>=2.0           # DataFrames para pivot/agregação
openpyxl>=3.1         # Geração de XLSX
tomli>=2.0            # Parsing de config.toml (Python < 3.11)
gspread>=6.0          # API Google Sheets
google-auth-oauthlib>=1.2  # OAuth2 para Google
```

## 📄 Licença

MIT License - Use livremente em seus projetos.

## 👤 Autor

Pedro Carlos Ferreira Santos  
Desenvolvido com ❤️ para IRPF 2026

## 📅 Histórico de Versões

Veja [CHANGELOG.md](CHANGELOG.md) para o histórico completo de mudanças.
