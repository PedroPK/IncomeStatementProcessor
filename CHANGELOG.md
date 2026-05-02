# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-05-02

### ✨ Adicionado

#### Arquitetura e Estrutura
- Inicializado projeto Python com estrutura modular (`src/`)
- Implementado padrão dispatcher para detecção e parsing de múltiplas instituições
- Configuração via `config.toml` com suporte a `tomllib` (Python 3.11+) e fallback `tomli`
- Suporte a variáveis de ambiente para configuração dinâmica

#### Modelos de Dados
- Dataclass `Entry` em `models.py` com 19 campos para representar um informes de rendimento
- Campos estruturados: arquivo, instituição, CNPJ, ano, seção, grupo, código, valores 2024/2025, rendimentos, IRRF, etc.

#### Extração de Dados
- **`extractor.py`**:
  - `extract_zip()`: Descompactação de ZIP com suporte a codificação CP437 (XP Previdência) e UTF-8
  - `find_zip()`: Busca automática de arquivo `.zip` em diretório `input/`
  - Tratamento de erros de encoding transparente

#### Normalização
- **`normalizer.py`**:
  - `parse_brl()`: Conversão de valores monetários brasileiros (1.234,56 → 1234.56)
  - `find_cnpj()` / `find_all_cnpj()`: Extração de CNPJ via regex
  - `clean()`: Limpeza de textos (trim, remove quebras de linha, normaliza espaços)
  - `extract_year()`: Extração automática de ano do informe

#### Parsers PDF (6 Instituições)
- **`parser.py`**:
  - `detect_institution()`: Pattern matching em nome de arquivo para identificação automática
  - `parse_file()`: Dispatcher que abre PDF e chama parser específico por instituição

  **Parsers específicos:**
  1. **Accenture** (`parse_accenture`):
     - Entrada: Comprovante de Rendimentos (PDF via .aspx)
     - Extração: Quadros 3, 4, 5 (rendimentos, contribuições)
     - Saída: 5 entradas (Rendimentos Tributáveis PJ, Contribuições Previdenciárias)

  2. **Avenue Securities** (`parse_avenue`):
     - Entrada: Relatório auxiliar com tabelas estruturadas
     - Extração: `pdfplumber.extract_tables()` em páginas 2-4 (stocks/ETFs individuais)
     - Extração: Text parsing em página 1 para saldo em conta
     - Saída: 16 entradas (1 saldo + 15 ativos com rendimentos/IRRF)
     - ⚠️ **CORREÇÃO v1.0**: Reescrita completa após debug — era 0 entradas em alpha

  3. **Inter** (`parse_inter`):
     - Entrada: PDF com seções denominadas (títulos, criptos, poupança)
     - Extração: Text regex por tipo de ativo
     - Saída: 8 entradas (Bens e Direitos + Rendimentos Isentos/Exclusivos)

  4. **NuBank** (`parse_nubank`):
     - Entrada: PDF com blocos de Grupo/Código estruturados
     - Extração: Padrão "GRUPO - NNN" seguido de linhas de ativos
     - Suporte: Renda fixa, fundos, criptoativos (Bitcoin, USDC, stablecoins)
     - Saída: 8 entradas (Bens e Direitos por tipo de ativo)

  5. **XP Investimentos** (`parse_xp`):
     - Entrada: PDF com 2 seções: resumo (p1) + detalhes (p4-6)
     - Extração: 
       - Página 1: Seções de Rendimentos (Isentos/Tributação Exclusiva)
       - Páginas 4-6: Tabelas de Bens e Direitos com associação a Declarações
     - Algoritmo especial: "next declaration" para associar dados com contexto
     - Saída: 20 entradas (Rendimentos + Bens e Direitos diversificados)

  6. **XP Vida e Previdência** (`parse_xp_previdencia`):
     - Entrada: Informe de previdência privada (VGBL/PGBL)
     - Extração: Tabelas + regex para valores BRL
     - Saída: 2 entradas (Bens e Direitos + Contribuições Previdenciárias)

#### Geração de Saída (XLSX)
- **`xlsx_writer.py`**:
  - `write_xlsx()`: Orquestração de escrita em 4 abas
  - **Aba 1 - Dados Brutos**:
    - Todas as 59 entradas com 19 colunas
    - Formatação: Excel Table com linhas alternadas (fill)
    - Freeze panes em cabeçalho + auto-adjust de largura
  - **Aba 2 - Resumo**:
    - Pivot por Seção × Grupo/Código × Instituição
    - Separadores visuais por seção
  - **Aba 3 - Totais**:
    - Agregação por Grupo/Código
    - Linha de total geral com valores 2024, 2025, rendimento
  - **Aba 4 - Para IRPF**:
    - Agrupado por instituição
    - Subtotais por seção
    - Facilitação para cópia de valores direto na DIRPF

#### Exportação Opcional para Google Sheets
- **`sheets_writer.py`**:
  - Autenticação OAuth2 com `gspread` + `google-auth-oauthlib`
  - Criação/abertura automática de spreadsheet
  - Escrita das mesmas 4 abas que o XLSX
  - Configuração via `config.toml` (`google_sheets.enabled`)

#### Orquestração
- **`main.py`**:
  - `__main__` block:
    - Busca ZIP em `input/`
    - Extrai arquivos
    - Detecta e processa cada instituição
    - Consolida 59 entradas
    - Gera XLSX
    - Opcionalmente exporta para Google Sheets

#### Configuração
- **`config.toml`**:
  - Paths de saída (XLSX)
  - Credenciais e configuração Google Sheets
  - Estrutura pronta para expansão

#### Arquivos de Suporte
- **`requirements.txt`**: Lista de dependências com versões mínimas
- **`.gitignore`**: Exclusões padrão (Python, credentials, output)
- **`src/__init__.py`**: Marcador de pacote Python

### 🔧 Corrigido

- ❌ **Avenue parser (v0.9 → v1.0)**:
  - **Problema**: Retornava 0 entradas porque usava regex em texto fragmentado de PDF multi-coluna
  - **Root cause**: `pdfplumber.extract_text()` em layout multi-coluna produz linhas como:
    ```
    '249 - ESTADOS R$ R$'
    '03-01 STOCK GOOGL ...'
    'UNIDOS 5,3923 2.013,39'
    ```
  - **Solução**: Reescrita completa para usar `pdfplumber.extract_tables()` que produz 9 colunas estruturadas
  - **Resultado**: 16 entradas extraídas com sucesso (1 saldo + 15 ativos)

### 📊 Status de Testes

| Instituição | Entradas | Status |
|---|---|---|
| Accenture | 5 | ✅ Produção |
| Avenue | 16 | ✅ Produção (v1.0 fix) |
| Inter | 8 | ✅ Produção |
| NuBank | 8 | ✅ Produção |
| XP | 20 | ✅ Produção |
| XP Previdência | 2 | ✅ Produção |
| **TOTAL** | **59** | ✅ |

### 🗂️ Estrutura de Projeto

```
IncomeStatementProcessor/
├── README.md                              # Documentação principal
├── CHANGELOG.md                           # Este arquivo
├── requirements.txt                       # Dependências
├── config.toml                            # Configuração
├── .gitignore                             # Exclusões Git
├── .git/                                  # Repositório Git
├── input/
│   └── drive-download-20260502T172444Z-3-001.zip
├── output/
│   └── informes_rendimentos.xlsx          # XLSX gerado
├── credentials/                           # (criado se Google Sheets habilitado)
│   ├── credentials.json
│   └── token.json
└── src/
    ├── __init__.py
    ├── models.py                          # Dataclass Entry
    ├── normalizer.py                      # Funções de normalização
    ├── extractor.py                       # Extração de ZIP
    ├── parser.py                          # 6 Parsers PDF + dispatcher
    ├── xlsx_writer.py                     # Geração XLSX
    ├── sheets_writer.py                   # Exportação Google Sheets (opcional)
    └── main.py                            # Orquestração
```

### 📦 Dependências Instaladas

```
pdfplumber==0.11.9        # Extração PDF
pandas==3.0.2             # DataFrames
openpyxl==3.1.5           # XLSX
tomli==2.0.1              # config.toml parsing
gspread==6.1.2            # Google Sheets API
google-auth-oauthlib==1.2.1  # OAuth2
```

### ✅ Checklist de Entrega (v1.0)

- ✅ Extração de 6 instituições
- ✅ 59 entradas consolidadas
- ✅ XLSX com 4 abas funcionais
- ✅ Configuração via `config.toml`
- ✅ Suporte Google Sheets (opcional)
- ✅ Tratamento de erros e codificação
- ✅ Documentação em README.md
- ✅ Changelog estruturado
- ✅ Repositório Git inicializado

---

## Plano para Próximas Versões

### [1.1.0] - Planejado
- [ ] Suporte a novos formatos (CSV, JSON)
- [ ] Validação automática de CPF/CNPJ
- [ ] Dashboard HTML de visualização
- [ ] Filtros e buscas avançadas no XLSX

### [1.2.0] - Planejado
- [ ] Integração com API da Receita Federal (simulação)
- [ ] Relatórios consolidados de impacto fiscal
- [ ] Exportação para softwares IRPF (Sefip, etc.)

### [2.0.0] - Futuro
- [ ] Web UI com autenticação
- [ ] Banco de dados (SQLite/PostgreSQL)
- [ ] Scheduling automático mensal
- [ ] Suporte multilíngue
