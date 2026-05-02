# Income Statement Processor (Processador de Informes de Rendimentos)

Ferramenta Python para extrair, processar e consolidar Informes de Rendimentos (IRPF 2026) de 6 instituições financeiras brasileiras e internacionais, gerando um relatório Excel multitabs com classificação automática por grupo/código e categorização de rendimentos.

## 📋 Funcionalidades

- **Extração de múltiplos formatos PDF**: Suporte nativo para 6 instituições:
  - Accenture (Comprovante de Rendimentos)
  - Avenue Securities (Ativos em custódia + depósitos)
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
| `parser.py` | 6 parsers por instituição + `detect_institution()` |
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

## 📝 Exemplos de Saída

### Dados Brutos (Tab 1)
```
Arquivo | Instituição | CNPJ | Ano | Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento
Avenue...pdf | Avenue Securities LLC | | 2025 | Bens e Direitos | 03 | 01 | GOOGL – Alphabet Inc | 0.00 | 2,013.39 | 6.18
XP...pdf | XP Investimentos | | 2025 | Rendimentos Trib. Excl. | | 06 | Fundos/Clubes | 62,371.82 | 67,562.19 | 5,133.46
```

### Resumo (Tab 2)
```
Seção | Grupo | Código | Accenture | Avenue | Inter | ... | TOTAL
Bens e Direitos | 03 | 01 | 0.00 | 2,013.39 | 0.00 | | 2,013.39
Rendimentos Trib. Excl. | | 06 | 0.00 | 0.00 | 1,243.13 | | 1,243.13
```

### Totais (Tab 3)
```
Grupo | Código | Descrição | 2024 | 2025 | Rendimento | Total
03 | 01 | Ações | 0.00 | 2,013.39 | 6.18 | 2,019.57
04 | 02 | Títulos Públicos/Privados | 266,860.99 | 322,222.75 | 18,285.14 | 340,507.89
06 | 01 | Depósitos em Conta | 323.05 | 1,082.42 | 0.00 | 1,082.42
...
TOTAL GERAL | | | 614,445.82 | 689,842.38 | 51,227.04 | 741,069.42
```

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
