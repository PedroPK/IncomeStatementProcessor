# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.2.0] - 2026-05-03

### ✨ Adicionado

#### ✨ Suporte para XLSX com Dados de Custódia (NOVO)
- **Parser de Custódia XLSX**: Novo módulo `src/custodia_parser.py`
  - Lê arquivo XLSX com colun as: Ativo, Quantidade de Cotas, Preço Médio
  - Calcula automaticamente: `custo_aquisicao = quantidade × preço_médio`
  - Mapeamento inteligente de ticker para grupo/código IRPF:
    - FII (terminam em 11): Grupo 07, Código 02
    - Ações (terminam em 3, 4): Grupo 04, Código 01
    - BDRs (terminam em 34, 35): Grupo 03, Código 01
    - ETFs: Grupo 07, Código 03
  - Gera Entry com seção "Bens e Direitos" e localizacao "105 - Brasil"
  - Suporta qualquer nome de arquivo `*custodia*.xlsx` (case-insensitive)
  - Detecta broker automaticamente do nome do arquivo (Clear, XP, Avenue, etc.)

- **Integração ao Pipeline**:
  - `src/main.py` agora processa XLSX após PDFs
  - Detecta automaticamente arquivo XLSX dentro do ZIP
  - Saída unificada: Dados de Informes + Custódia na mesma planilha XLSX
  - Dashboard inclui ativos de custódia nos gráficos

- **Suporte no ZIP**:
  - ZIP pode conter PDFs + arquivo XLSX simultaneamente
  - Exemplo: `input/meu_arquivo.zip` contendo:
    - `Accenture - Informe de Rendimentos...pdf`
    - `Clear - 01 Informe de Rendimentos...pdf`
    - `ClearCustodia_31dez2025.xlsx` ← processado automaticamente

#### Reorganização da Estrutura de Diretórios
- **Nova hierarquia em `src/`**:
  ```
  src/
    tests/              # Testes automatizados
      test_integration.py
      test_dashboard.py
    analysis/           # Ferramentas de análise
      analyze_clear_pdf.py
      analyze_mapping.py
    examples/           # Exemplos de uso
      examples_dashboard.py
    generators/         # Geradores de documentação
      generate_dashboard_docs.py
    custodia_parser.py  # ✨ NOVO
    main.py, models.py, parser.py, etc.
  ```
  
- **Vantagens**:
  - Organização mais clara por responsabilidade
  - Separação entre código produção e ferramentas auxiliares
  - Facilita futuros testes e manutenção
  - Testes executáveis via `python3 -m src.tests.test_integration`

- **Importações atualizadas**:
  - `test_dashboard.py` agora importa de `src.tests.test_integration`
  - `examples_dashboard.py` importa de `src.tests` e `src.examples`
  - `generate_dashboard_docs.py` importa de `src.tests`
  - Todos os imports relativos (`.` e `..`) funcionando corretamente

### 📝 Documentação Atualizada

#### ARCHITECTURE.md
- Adicionada seção "Estrutura de Pastas" com nova hierarquia
- Novo documento "Parser de Custódia (`custodia_parser.py`)"
  - Responsabilidades
  - Estrutura esperada do XLSX
  - Algoritmo de processamento
  - Mapeamento de ticker → grupo/código
  - Exemplos de entrada/saída
- Atualizado pipeline visual para incluir XLSX

#### README.md
- Adicionadas funcionalidades novas em destaque (✨ NOVO)
- Nova seção "XLSX com Dados de Custódia"
  - Instruções passo-a-passo
  - Tabela de colunas obrigatórias
  - Exemplo prático (arquivo `ClearCustodia.xlsx`)
  - Nomes de arquivo suportados
  - Resultado esperado no XLSX final
- Exemplo de saída atualizado com processamento de custódia
- Testes agora com comando `python3 -m src.tests.*`
- Nova seção "Estrutura de Diretórios"

#### Exemplos de Uso Atualizado
- Saída esperada mostra processamento de XLSX:
  ```
  Processando custódia: ClearCustodia.xlsx
    ✅ PSSA3: 400 cotas × R$ 48,36 = R$ 19.344,00
    ✅ PLAG11: 81 cotas × R$ 120,80 = R$ 9.784,80
    → 3 ativos em custódia extraídos.
  ```

### 🔧 Melhorado

- **Validação de XLSX**: 
  - Detecta header automaticamente (busca por "ativo")
  - Trata dados faltantes com avisos informativos
  - Valida quantidade e preço (deve ser > 0)

- **Tratamento de Erros**:
  - Erros em processamento de XLSX não interrompem pipeline
  - Mensagens de aviso claras para linhas inválidas
  - Logging de sucesso para cada ativo processado

## [1.1.0] - 2026-05-03

### ✨ Adicionado

#### Suporte para Custódia de Ativos (Clear)
- **Parser de Custódia da Clear**: Novo suporte para documento "Clear - 04 Custódia"
  - Função `_parse_clear_custodia()` em `src/parser.py`
  - Detecta automaticamente tipo de documento (Informe vs Custódia)
  - Extrai ativos individuais (ações, FIIs, ETFs) com posições consolidadas
  - Classificação automática de tipo de ativo por padrão de ticker:
    - FII/ETF: Tickers terminando em 11, 13, 21, 24, 39, 65
    - Ações: Demais padrões
  - Inclui saldo em conta (cash disponível)
  - Seção: "Bens e Direitos" com grupos apropriados (Grupo 04, 06, 07)

- **Dados de Teste**: Adicionadas 3 entradas mockadas de custódia da Clear
  - PSSA3 (Ação): R$ 19.344,00
  - PLAG11 (FII): R$ 9.785,00
  - Saldo disponível: R$ 7.745,95
  - Mock data total agora: 15 entradas (antes: 12)

#### Dark Mode no Dashboard
- **Tema Escuro Completo**: Implementação de modo noturno
  - CSS Variables (Custom Properties) para fácil tema switching
  - Suporte automático para light/dark mode com toggle button
  - Persistência de preferência do usuário via localStorage
  - Cores otimizadas para redução de fadiga ocular:
    - Light mode: Background #f8f9fa, Texto #333333
    - Dark mode: Background #1a1a1a, Texto #e0e0e0
  - Navbar com botão toggle (🌙 Dark Mode / ☀️ Light Mode)
  - Transições suaves (300ms) entre temas
  - Atualizações dinâmicas de gráficos ao trocar tema

- **Persistência de Tema**: 
  - localStorage key: `dashboard-theme` (valores: 'light' ou 'dark')
  - Carregado automaticamente ao reabrir dashboard

- **Gráficos Responsivos**:
  - Chart.js com atualização de cores dinamicamente
  - Cores de grade e texto adaptadas por tema
  - Background de tooltip responsivo

### 🔧 Melhorado

- **Dashboard Generator**: Reescrito para suportar temas com CSS Variables
  - Arquivo: `src/dashboard_generator.py` completamente refatorado
  - Mantém compatibilidade com todas as abas e funcionalidades anteriores
  - JavaScript melhorado para theme management

- **Detecção de Documento Clear**:
  - `parse_clear()` agora detecta tipo de documento ('custódia' no nome ou conteúdo)
  - Mantém compatibilidade com "Informe de Rendimentos" (fallback para parse_xp)

### 🧪 Testes

- **Novo teste de Dark Mode**: `test_dashboard_dark_mode()`
  - Valida presença de CSS variables
  - Verifica toggle functionality
  - Confirma localStorage persistence
  - Testa inicialização de tema

- **Mock data expandido**:
  - test_integration.py: +3 entradas de custódia da Clear
  - test_dashboard.py: Suporta novos dados de custódia

### 📋 Documentação

- README.md: Atualizado com informações sobre Dark Mode
- ARCHITECTURE.md: Seção sobre processamento de custódia
- Novos comentários em código (docstrings) para `_parse_clear_custodia()`

### 📊 Dados

- **Instituições suportadas**: 7 (sem mudança)
- **Documentos por instituição (Clear)**: 
  - ✅ 01 Informe de Rendimentos (rendimentos tributáveis/isentos)
  - ✅ 04 Custódia (ativos em posição consolidada) - NOVO
  - ℹ️ 02 Operações Normais (informativo, não estruturado)
  - ℹ️ 03 Proventos (informativo, não estruturado)

## [1.0.2] - 2026-05-02

### ✨ Adicionado

#### Suporte para Clear Corretora
- **Parser da Clear**: Novo suporte para documentos "Informe de Rendimentos" da Clear
  - Reutiliza lógica do parser XP (mesmo formato padrão Ministério da Economia)
  - Função `parse_clear()` em `src/parser.py`
  - Detecção automática na função `detect_institution()` (antes de XP para evitar confusão)
  - Processa documentos: "Clear - 01 Informe de Rendimentos..."
  
- **Dados de Teste**: Adicionadas 2 entradas mockadas da Clear
  - Fundos de Investimento Multimercado
  - Rendimentos de Fundo
  - Mock data total agora: 12 entradas (antes: 10)
  - Testes de integração atualizados

- **Documentação**: 
  - README.md atualizado com Clear na lista de 7 instituições suportadas
  - Padrão de nome: `Clear*.pdf`
  - Descrição de parser: "Formato padrão Ministério da Economia (reutiliza XP)"

### 🔧 Melhorado

- **Detecção de Instituição**: Reordenada verificação para priorizar Clear antes de XP
  - Evita falso positivo: documentos Clear contêm "XP Investimentos" nos dados internos
  - Ordem: Accenture → Clear → NuBank → XP_Previdência → XP → Avenue → Inter

### 📊 Dados Reais

- **Total de instituições suportadas**: 7 (Accenture, Avenue, Clear, Inter, NuBank, XP, XP Vida)
- **Dados processados na execução mais recente**: 60 entradas de 8 arquivos
  - Clear contribui com 6 entradas extraídas (documento "01 Informe de Rendimentos")
  - Documentos "02 Operações Normais" e "03 Proventos" são informativos (não estruturados para extração)

## [1.0.1] - 2026-05-02

### ✨ Adicionado

#### Dashboard Interativo
- **`src/dashboard_generator.py`**: Módulo para geração programática de dashboard HTML
  - Função `generate_dashboard_html(entries, output_path)`: Recebe lista de `Entry` e gera HTML
  - **4 abas interativas**: Dados Brutos, Resumo, Totais, Para IRPF (sincronizadas com XLSX)
  - **Gráficos dinâmicos** usando Chart.js:
    - Pie chart: Distribuição de ativos por instituição (2025)
    - Bar chart: Evolução 2024 → 2025 por instituição
  - **Métricas-chave**: Cards com Total 2024, Total 2025, Rendimentos, Contagem
  - **Design responsivo**: Bootstrap 5.3.0 com tema gradiente roxo
  - **Formatação automática**: Moeda brasileira (Intl.NumberFormat pt-BR)
  - Integrado automaticamente no pipeline `src/main.py`

#### Integração no Pipeline
- **`src/main.py`** atualizado: Gera dashboard automaticamente após XLSX
  - Nova etapa: "Gerando dashboard HTML..." após XLSX
  - Suporta configuração em `config.toml` (`output.dashboard_path`)
- **`config.toml`** expandido com nova opção:
  ```toml
  [output]
  xlsx_path = "output/informes_rendimentos.xlsx"
  dashboard_path = "output/dashboard.html"
  ```

#### Documentação Dashboard
- **README.md** com nova seção "📊 Dashboard Interativo"
  - Instruções de visualização e uso programático
  - Exemplo de saída com 59 entradas reais processadas
  - Configuração através de `config.toml`

#### Testes Automatizados
- **`test_integration.py`**: Suite completa de testes de integração com dados mockados
  - `test_mock_data_integrity()`: Valida estrutura e consistência de 10 entradas fictícias
  - `test_xlsx_generation_with_mock_data()`: Testa geração de XLSX com 4 abas formatadas
  - `test_mock_data_summary()`: Imprime resumo consolidado de dados (R$ 489k total)
  - `get_markdown_tables_for_documentation()`: Gera tabelas Markdown para documentação
  - Cobertura: 5 instituições mockadas (Accenture, Itaú, Bradesco, XP, NuBank)
  - Nenhum dado pessoal real — valores completamente fictícios

- **`test_dashboard.py`** (NOVO): Suite completa de testes para dashboard (10 testes)
  - `test_dashboard_generation()`: Verifica geração de HTML válido
  - `test_dashboard_data_embedding()`: Valida JSON embarcado
  - `test_dashboard_tabs()`: Confirma 4 abas presentes e funcionais
  - `test_dashboard_charts()`: Verifica configuração Chart.js (Pie + Bar)
  - `test_dashboard_metrics()`: Valida cards de métricas
  - `test_dashboard_with_extended_data()`: Testa com dados estendidos (7 entradas)
  - `test_dashboard_responsive_design()`: Verifica classes Bootstrap
  - `test_dashboard_currency_formatting()`: Valida formatação BRL
  - `test_dashboard_all_institutions()`: Confirma agrupamento de instituições
  - `test_dashboard_section_aggregation()`: Verifica agregação de seções
  - **Resultado**: ✅ 10/10 testes passando

- **`EXTENDED_TEST_DATA`** (NOVO): Conjunto estendido de dados de teste
  - 7 entradas fictícias de 6 instituições (mais realistas que mock data)
  - Total 2024: R$ 563.500,00
  - Total 2025: R$ 709.700,00
  - Rendimentos: R$ 74.250,00
  - Uso: Testes abrangentes do dashboard, cenários complexos

#### Documentação Visual
- **`DASHBOARD_VISUAL.md`** (NOVO): Documentação completa com exemplos visuais
  - 356 linhas de documentação estruturada
  - Métricas principais com dados mockados e reais
  - Exemplos de todas as 4 abas com dados de exemplo
  - Gráficos explicados (Pie + Bar)
  - Recursos de design (cores, responsividade)
  - Comparação de volumes (Mock vs Extended vs Real)
  - **10 tabelas markdown** mostrando exatamente como ficam as abas

- **`generate_dashboard_docs.py`** (NOVO): Script gerador de documentação
  - Gera `DASHBOARD_VISUAL.md` automaticamente
  - Função `generate_dashboard_documentation()` reutilizável
  - Mantém documentação sincronizada com código
- **README.md atualizado** com exemplos de saída das 4 abas XLSX:
  - **Aba 1 - Dados Brutos**: Tabela com 5 primeiras linhas (19 colunas)
  - **Aba 2 - Resumo**: Pivot por Seção × Instituição com consolidação
  - **Aba 3 - Totais**: Agregação por Grupo/Código com linha de total geral
  - **Aba 4 - Para IRPF**: Agrupado por instituição com subtotais por seção
  - Todas as tabelas usando dados mockados para referência clara

#### Limpeza de Repositório
- Removido arquivo `input/` do histórico Git (pasta mantida localmente para usuários)
- Adicionado `input/` ao `.gitignore`
- Commit: `chore: remove input/ folder from version control`
- Repositório agora seguro para publicação no GitHub (sem exposição de dados)

### 🔧 Melhorado

- Documentação de teste agora inclui exemplos práticos e execução automatizada
- README com referências visuais para cada aba gerada
- Confiabilidade para publicação online — sem risco de expor dados sensíveis
- Pipeline automatizado gera 3 outputs simultâneos: XLSX, Dashboard HTML, Google Sheets (opcional)

### 📊 Métricas (Dados Mockados)

```
Entradas testadas: 10
Instituições: 5
Total 2024: R$ 196,850.00
Total 2025: R$ 268,350.00
Total Rendimentos: R$ 23,875.50
Total IRRF: R$ 5,287.65
XLSX gerado: 12.9KB
Dashboard: 572 linhas HTML/JS/CSS
```

### ✅ Checklist v1.0.1

- ✅ Testes automatizados com dados mockados
- ✅ Exemplos visuais das 4 abas no README
- ✅ Histórico Git limpo (input/ removido)
- ✅ Pronto para publicação no GitHub
- ✅ Documentação atualizada

---

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
- **`README.md`**: Documentação completa com instalação, uso, troubleshooting
- **`CHANGELOG.md`**: Histórico de versões
- **`LICENSE`**: MIT License
- **`CONTRIBUTING.md`**: Guia para desenvolvedores
- **`ARCHITECTURE.md`**: Documentação técnica de design

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
├── CONTRIBUTING.md                        # Guia para contribuidores
├── ARCHITECTURE.md                        # Documentação técnica
├── LICENSE                                # MIT License
├── requirements.txt                       # Dependências
├── config.toml                            # Configuração
├── .gitignore                             # Exclusões Git
├── test_integration.py                    # Testes automatizados
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
