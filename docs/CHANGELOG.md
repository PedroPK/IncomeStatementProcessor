# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere a [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.7.5] - 2026-05-27

### ♻️ Refatorado

#### Template HTML do Stepper extraído para `src/templates/stepper.html`
- As ~896 linhas de HTML que compunham `_STEPPER_HTML_TEMPLATE` em `src/main.py` foram movidas para **`src/templates/stepper.html`**, seguindo o mesmo padrão de `src/templates/dashboard.html`.
- `src/main.py` passou de ~1 680 para **787 linhas** (redução de ~53%).
- Constante `_STEPPER_TEMPLATE_PATH` aponta para o arquivo via `Path(__file__).parent / 'templates' / 'stepper.html'`.
- Função `_stepper_html()` reescrita para ler o arquivo em disco e substituir `%%VERSION%%` em tempo de execução — comportamento idêntico ao anterior.
- Nenhuma funcionalidade alterada; todos os 12 testes continuam passando.

---

## [1.7.4] - 2026-05-27

### ✨ Adicionado

#### Interface Web – Card "O que este aplicativo faz?" na tela inicial
- Novo **card de boas-vindas** (`#aboutCard`) exibido entre o cabeçalho (hero) e os indicadores de passo na tela inicial do stepper (`src/templates/stepper.html`).
  - **3 colunas visuais** descrevendo o fluxo completo:
    - 📂 *Envie seus Informes* — PDFs/ZIPs com os Informes de Rendimentos.
    - ⚙️ *Processamento Automático* — extração, normalização e consolidação de dados.
    - 📊 *Dashboard Interativo* — relatório visual com gráficos, tabelas e exportação Excel.
  - **Chips de instituições suportadas** listando Accenture, Avenue Securities, Clear, Inter, NuBank, XP Investimentos, XP Vida e Previdência e "+ XLSX de custódia".
  - **Botão "Não mostrar novamente"** (`#aboutDismiss`): oculta o card e persiste a preferência em `localStorage` (`aboutDismissed = '1'`). Usuários recorrentes não veem o card nas sessões seguintes.
- CSS dedicado (`.about-card`, `.about-cols`, `.about-col`, `.inst-chips`, `.inst-chip`) com suporte completo a modo escuro via variáveis CSS.
- Screenshots de documentação adicionadas:
  - `docs/screenshots/stepper_about_light.png` — tela inicial (tema claro).
  - `docs/screenshots/stepper_about_dark.png` — tela inicial (tema escuro).
  - `docs/screenshots/stepper_about_card.png` — card de boas-vindas em detalhe.

### 🧪 Testes
- `test_stepper_about_card()` em `src/tests/test_dashboard.py`: verifica presença do `#aboutCard`, do botão `#aboutDismiss`, das 3 colunas de feature, dos chips de instituição e da lógica `localStorage`.
- `take_stepper_screenshots()` em `src/tests/test_dashboard_screenshots.py`: captura com Playwright as 3 screenshots da tela inicial (light, dark, card isolado).

---

## [1.7.3] - 2026-05-27

### ✨ Adicionado

#### Interface Web – Botão "⏹ Desligar"
- Novo botão **"⏹ Desligar"** no hero da página do stepper, ao lado de "↺ Nova Sessão".
  - Estilo avermelhado (`background: rgba(220,53,69,0.25)`) para diferenciar visualmente da ação de restart.
  - Exibe `confirm()` antes de executar para evitar acionamento acidental.
  - Chama `POST /api/shutdown` e, em seguida, `window.close()` para fechar a aba do navegador.
- Novo endpoint **`POST /api/shutdown`** em `src/main.py`:
  - Dispara uma thread com `daemon=False` que envia `SIGTERM` ao processo principal após 0,4 s — o werkzeug intercepta o sinal e encerra o servidor de forma limpa, retornando o prompt ao terminal.
  - Fallback: caso `SIGTERM` não seja suficiente em 1,5 s, `os._exit(0)` força o encerramento imediato.
  - Retorna `{ok: true, message: 'Servidor encerrado.'}` antes de sair.

---

## [1.7.2] - 2026-05-27

### 🔄 Alterado

#### Interface Web – Botão "↺ Nova Sessão"
- O botão **"↺ Nova Sessão"** agora executa `window.location.reload()` em vez de chamar `/api/restart` e aguardar o servidor reiniciar.
  - Removido: diálogo de confirmação, chamada `POST /api/restart`, função `pollUntilAlive` e redirect para `/`.
  - Resultado: refresh imediato na mesma aba, sem interrupção do servidor.

---

## [1.7.1] - 2026-05-27

### 🐛 Corrigido

#### Parser Avenue – AAPL, AMZN e BRKB ausentes na aba IRPF
- **`parse_avenue()` em `src/parser.py`**: os ativos AAPL, AMZN e BRKB não eram extraídos do PDF da Avenue Securities porque o loop de tabelas usava `pages_tables[1:]`, pulando a página 1 (índice 0) por engano. No entanto, o PDF da Avenue inclui uma tabela de ativos **também na página 1**, contendo exatamente esses três papéis.
  - **Root cause 1**: o comentário original dizia *"skip page 1 (no asset table)"*, mas a página 1 do relatório anual Avenue contém tanto o saldo em conta (processado via regex de texto) quanto uma tabela de Ações/Stocks com AAPL, AMZN e BRKB.
  - **Root cause 2**: a tabela da página 1 possui colunas `None` extras intercaladas (células mescladas no cabeçalho), deslocando o índice do Símbolo para a posição 4 em vez de 3, o que quebraria a leitura mesmo se a página fosse processada.
  - **Fix 1**: `pages_tables[1:]` → `pages_tables` (processa todas as páginas).
  - **Fix 2**: antes de indexar Símbolo/Empresa, a linha é *compactada* removendo valores `None`: `compact = [c for c in row if c is not None]`. Com isso `compact[3]` = Símbolo e `compact[4]` = Empresa em ambos os layouts.
  - **Fix 3**: adicionada validação de ticker `re.match(r'^[A-Z][A-Z0-9.]{0,14}$', symbol)` para descartar a linha de saldo (que também tem cell0 `06-99`, mas não possui um ticker válido), evitando entrada duplicada com a já criada pelo parser de texto.
  - Resultado: total de entradas Avenue passou de 16 → 19 (AAPL R$ 4.472,47 · AMZN R$ 2.286,15 · BRKB R$ 2.515,22 incorporados).

---

## [1.7.0] - 2026-05-20

### 🐛 Corrigido

#### Dashboard – Aba "Para IRPF": Categorização de Renda Fixa Nubank com descricao genérica
- **`_infer_fixed_income_subtype()` em `src/dashboard_generator.py`**: A função concatenava `discriminacao` + `descricao` num único texto e rodava os checks em ordem — `'TESOURO' in text` sendo o primeiro. O `codigo_desc` da Nubank para o código `04/02` é a descrição genérica da seção IRPF: *"Títulos públicos e privados sujeitos à tributação (Tesouro Direto, CDB, RDB e Outros)"*, que contém `"TESOURO"`. Isso fazia **todas** as entradas Nubank desse código retornarem `"Tesouro Direto"`, incluindo CDBs, Debêntures, LCIs e LCAs.
  - **Root cause**: a estratégia de junção de texto dava peso idêntico ao `codigo_desc` genérico e ao `discriminacao` específico por ativo.
  - **Fix**: `_infer_fixed_income_subtype` reescrita em duas fases com prioridade explícita:
    1. **Fase 1 – instrumentos privados**: todos os checks (CDB, RDB, LCI, LCA, CRI, CRA, LCD, LIG, DEB) são executados **exclusivamente sobre `discriminacao`**, sem tocar no `descricao`.
    2. **Fase 2 – Tesouro Direto**: detectado em `discriminacao` quando ele contém "TESOURO", "SELIC", "LFT", "LTN", "PREFIXADO", NTN, ou o shorthand `"IPCA"` isolado (padrão Nubank para NTN-B). Somente quando `discriminacao` está **ausente** é que `descricao` é consultado para Tesouro.
  - Resultado verificado no dashboard gerado: 89 CDBs, 8 LCAs, 3 LCIs, 3 Debêntures e 1 Tesouro IPCA+ — todos corretamente separados.

#### Dashboard – Aba "Para IRPF": FIIs da Clear classificados como "Fundos"
- **`infer_asset_category()` em `src/dashboard_generator.py`**: FIIs custodiados na Clear têm `grupo='07'` e `codigo='02'` (Fundos Imobiliários), mas a branch de ETFs verificava `codigo in {'03', '08'}`, e a branch de Fundos usava `grupo == '07'` como guard geral — nunca alcançando a branch de FIIs para `07/02`.
  - **Fix**: a branch de FIIs foi antecipada e estendida para capturar `(grupo == '07' and codigo == '02')` explicitamente.

#### Dashboard – Aba "Para IRPF": `CRI` falso-positivo em entradas de Criptoativos
- **`infer_asset_category()`**: o token `CRI` aparecia como substring de `"CRIPTOATIVOS"` (campo `grupo_desc`), fazendo entradas de crypto serem classificadas como *CRI – Certificado de Recebíveis Imobiliários*.
  - **Fix**: introduzida função auxiliar `_contains_token(text, token)` com lookbehind/lookahead `(?<![A-Z0-9])TOKEN(?![A-Z0-9])` para garantir que só tokens isolados sejam reconhecidos.

#### Dashboard – Aba "Para IRPF": crash de JavaScript no bloco IRPF
- Um token inválido (`co`) estava sendo emitido solto no bloco JS da aba "Para IRPF", causando `SyntaxError` em runtime e impedindo a renderização da aba.
  - **Fix**: removido o token espúrio; bloco JS re-validado.

### ✨ Adicionado

#### Dashboard – Aba "Para IRPF": acordeões por tipo de ativo
- A aba "Para IRPF" agora organiza as entradas de cada instituição em **grupos por tipo de ativo** (`<details class="irpf-asset-group">`), com cabeçalho clicável para expandir/recolher.
- Grupos ordenados por valor (maior primeiro): Ações, ETFs, FIIs, Fundos, CDB, LCI, LCA, Debêntures, Tesouro Direto, Renda Fixa, Previdência, etc.
- Cada grupo exibe o total parcial no cabeçalho.

#### Dashboard – `assetCategory` e `fixedIncomeSubtype` no JSON embarcado
- Dois novos campos adicionados a cada objeto do `mockData` no HTML:
  - **`assetCategory`**: string calculada por `infer_asset_category(entry)` em Python no momento da geração — usada como chave de agrupamento nos acordeões.
  - **`fixedIncomeSubtype`**: string retornada por `_infer_fixed_income_subtype()`, ou `null` — usada como rótulo de exibição dentro do grupo.

#### JavaScript – `hasToken()` para detecção com word-boundary
- Função JS `hasToken(d, token)` adicionada ao dashboard, espelhando o `_contains_token()` Python: usa regex `(?<![A-Z0-9])TOKEN(?![A-Z0-9])` para evitar falsos positivos em nomes compostos.

### 🧪 Testes

#### `test_asset_category_inference_for_brokers` — 10 novos casos de teste
Todos os cenários desta sessão foram adicionados à suíte de testes em `src/tests/test_dashboard.py`:

| ID do caso | Situação testada | Resultado esperado |
|---|---|---|
| `nubank-cdb-real-descricao` | CDB BANCO MASTER com `codigo_desc` genérico Nubank | `CDB – Certificado de Depósito Bancário` |
| `nubank-cdb-banco-generico` | `discriminacao='CDB BANCO'` (parcial) | `CDB – Certificado de Depósito Bancário` |
| `nubank-deb-cemig` | DEB CEMIG com `codigo_desc` genérico Nubank | `Debêntures de Infraestrutura` |
| `nubank-deb-concessionaria` | DEB CONCESSIONARIA com `codigo_desc` genérico | `Debêntures de Infraestrutura` |
| `nubank-lci-real` | LCI BANCO BARI com `codigo_desc` genérico | `LCI – Letra de Crédito Imobiliário` |
| `nubank-lca-real` | LCA BANCO BARI com `codigo_desc` genérico | `LCA – Letra de Crédito do Agronegócio` |
| `nubank-ipca-tesouro` | `discriminacao='IPCA'` (shorthand Nubank para NTN-B) | `Tesouro IPCA+` |
| `tesouro-selic-via-discriminacao` | `discriminacao='Tesouro Selic 2027'` | `Tesouro Selic` |
| `tesouro-prefixado-via-discriminacao` | `discriminacao='Tesouro Prefixado 2029'` | `Tesouro Prefixado` |
| `clear-fii` | FII `07/02` da Clear (custódia) | `FIIs` |

Casos herdados de sessões anteriores mantidos: `avenue-stock`, `avenue-etf`, `inter-fixed-income`, `nubank-fund`, `xp-fund`, `nubank-cri-not-crypto`, `lca-not-lci`, `debenture-not-lci`, `cdb-not-tesouro`.

---

## [1.6.0] - 2026-05-18

### 🐛 Corrigido

#### Parser Clear – Roteamento incorreto do Informe de Rendimentos
- **`parse_clear()` em `src/parser.py`**: A detecção do tipo de documento Clear usava `full_text.lower()` para procurar `"custódia"`. A página 2 do Informe de Rendimentos contém a frase *"com posição em custódia"* em notas explicativas, fazendo o informe ser roteado erroneamente para `_parse_clear_custodia` e não gerar nenhuma entrada.
  - **Fix**: Verificação de roteamento passou a usar exclusivamente o texto da **página 1** (`pages_text[0]`) com busca positiva por `'INFORME DE RENDIMENTOS'`.
  - Informe → `parse_xp` | Custódia → `_parse_clear_custodia`

#### Aba "Para IRPF" – Ativos Clear mesclados em linha única
- **`gerarTabelasIRPF()` em `src/dashboard_generator.py`** e **`_write_para_irpf()` em `src/xlsx_writer.py`**: A chave de mesclagem usava apenas `(grupo, codigo, descricao)` para a seção "Bens e Direitos", colapsando múltiplos ativos de mesmo tipo (ex.: várias FIIs diferentes) numa única linha somada.
  - **Fix**: Para "Bens e Direitos", a chave de mesclagem agora inclui `discriminacao`, mantendo cada ativo como linha separada:
    - **Dashboard JS**: `\`${r.grupo}|${r.codigo}|${r.discriminacao || displayLabel}\``
    - **XLSX Python**: `key = (grupo, codigo, display_desc, r['Discriminação'] or '')`
  - Seções de Rendimentos continuam usando a chave antiga `(grupo, codigo, descricao)` para consolidação por tipo.

#### Parser Clear – Entrada duplicada de Saldo em Conta
- **`_parse_clear_custodia()` em `src/parser.py`**: O parser de custódia também gerava uma entrada para "Saldo em Conta" (Grupo 06 / Código 99), mas só tinha o valor de 2025 (valor_2024 = R$ 0,00), criando uma entrada duplicada e incompleta ao lado da já extraída pelo Informe.
  - **Fix**: Bloco de extração de saldo removido de `_parse_clear_custodia`. A extração canônica (com ambos os valores 2024 e 2025) fica em `parse_xp`.

### ✨ Adicionado

#### Parser Clear – Extração de Saldo em Conta (Bens e Direitos – 06/99)
- **`parse_xp()` em `src/parser.py`**: Adicionado bloco de extração de **Saldo em Conta** imediatamente antes do `return entries`, usando as primeiras 3 páginas do PDF (`pages_text[:min(3, len(pages_text))]`).
  - A página 1 do Informe Clear exibe "Saldo em conta" num formato fragmentado; a **página 3** ("DETALHAMENTO DOS ATIVOS") traz o dado numa linha limpa: `"Saldo em conta - XP Investimentos CCTVM S/A  820,31  7.745,95"`.
  - Extração usa `_xp_summary_rows()` para capturar `(desc, v2024, v2025)` e `_detect_cnpj_in_block()` para associar o CNPJ correto.
  - Gera entry com: `secao='Bens e Direitos'`, `grupo='06'`, `codigo='99'`, `codigo_desc='Outros depósitos à vista'`, com os valores de 31/12/2024 e 31/12/2025 preenchidos.
  - Pipeline validado: 1 entrada de saldo por informe Clear (ex.: v24=820,31 | v25=7.745,95).

### 🔧 Melhorado

#### Higiene de Repositório – `.gitignore` e scripts
- **`.gitignore`** atualizado com entradas que faltavam:
  - `temp_extracted/` — pasta criada por alguns scripts de extração de depuração
  - `*.log` — arquivos de log gerados por redirecionamento de shell (`> output.log`)
  - `.pytest_cache/` — cache do pytest
  - `.venv-1/` — segundo ambiente virtual criado acidentalmente
  - `/debug_*.py` — scripts de depuração temporários na raiz do projeto
- **`scripts/debug_clear.py`**: script de depuração movido da raiz do projeto para `scripts/` (pasta já listada no `.gitignore`).

---

## [1.5.0] - 2026-05-17

### ✨ Adicionado

#### Rótulos de Renda Fixa – Novos Tipos (LCD, LIG, Debêntures)
- **LCD** (Letra de Câmbio), **LIG** (Letra Imobiliária Garantida) e **Debêntures de Infraestrutura** adicionados ao sistema de rótulos de exibição de renda fixa
  - Reconhecidos automaticamente por `irpfDisplayLabel()` no dashboard (JavaScript) e `_renda_fixa_subtype()` em `src/xlsx_writer.py` e `src/parser.py`
  - Afeta a aba "Para IRPF" do dashboard HTML e a aba "Para IRPF" da planilha XLSX exportada
  - Regras de detecção: `LCD` → "LCD – Letra de Câmbio"; `LIG` → "LIG – Letra Imobiliária Garantida"; `DEBENTURE` / `DEBÊNTURE` / prefixo `DEB ` → "Debêntures de Infraestrutura"

#### Parser XP – `_xp_supplement_text()` e Extração de Discriminação
- **`_xp_supplement_text(filename, detail_tables)`** em `src/parser.py`: helper que extrai texto suplementar de tabelas de detalhe presentes em PDFs XP
  - PDFs XP renderizam as páginas 4-5 em layout 2 colunas; `pdfplumber` fragmentava a extração dessas páginas
  - A nova função isola linhas de detalhe imediatamente após o ID do instrumento e monta o campo `discriminacao` completo
  - Campo `discriminacao` das entradas XP de renda fixa agora populado com o nome completo do ativo (ex.: "Tesouro IPCA+ 2029 – Tesouro Direto"), permitindo que `irpfDisplayLabel()` / `_renda_fixa_subtype()` derivem o subtipo corretamente

#### Interface Web – Botão "↺ Nova Sessão"
- **Botão "↺ Nova Sessão"** no hero da página do stepper: permite encerrar a instância atual do servidor e iniciar uma sessão completamente limpa
  - Envia `POST /api/restart` → servidor encerra e reinicia via `os.execv(sys.executable, [sys.executable, '-m', 'src.main'])`
  - Frontend aguarda o servidor cair (1,5 s) e depois faz polling via `pollUntilAlive()` (até 50 tentativas × 1 s)
  - Após reconexão bem-sucedida, redireciona automaticamente para `/`
  - Botão desabilitado durante o processo; exibe "↺ Reiniciando..." enquanto aguarda

- **Endpoint `POST /api/restart`** em `src/main.py`:
  - Dispara o reinício em thread separada (`daemon=False`) para não bloquear a resposta HTTP
  - Retorna `{"ok": true}` antes de encerrar o processo atual

#### Interface Web – Dark Mode do Stepper
- **Dark mode completo** para a página do stepper (`_stepper_html()`):
  - CSS `html.dark-mode { ... }`: variáveis escuras `--bg: #0f1117`, `--card: #1a1d2e`, `--text: #e2e8f0`, `--muted: #94a3b8`, `--border: #2d3748`
  - Overrides específicos para: gradiente do `body`, `.step-index`, `.dropzone`, `.dropzone.active`, `.progress-panel`, `.progress-track`, `.progress-file`, `.result`, `.result.error`, `iframe`
  - Botão **"🌙 Escuro / ☀️ Claro"** no hero, ao lado do botão "↺ Nova Sessão"
  - Preferência persistida em `localStorage('stepper-theme')` e restaurada automaticamente no carregamento da página
  - Independente do dark mode do dashboard (que usa `localStorage('dashboard-theme')`)

---

## [1.4.0] - 2026-05-16

### ✨ Adicionado

#### Dashboard – Ordenação e Filtragem na Tabela de Dados Brutos
- **Cabeçalhos clicáveis** (`↕`) na aba "Dados Brutos": clique em qualquer coluna para ordenar crescente/decrescente, com indicador visual de direção
- **Linha de filtro por coluna**: inputs abaixo do cabeçalho permitem filtrar em tempo real por texto (Arquivo, Instituição, Seção, etc.) ou por expressão numérica (`>1000`, `<500`) nas colunas de valor
- **Coluna Discriminação** adicionada à tabela de Dados Brutos, permitindo filtrar e ordenar pelo campo de discriminação de cada ativo
- **Mensagem de "nenhum resultado"** exibida quando os filtros ativos não retornam linhas
- Estilos adaptativos para modo claro e escuro (dark mode)

#### Dashboard – Linha de Subtotal
- **Linha de subtotal** (`<tfoot>`) ao final da tabela de Dados Brutos: exibe a soma de 2024, 2025 e Rendimento para as linhas atualmente visíveis (respeitando filtros)
- Destaque visual diferenciado (fundo azul translúcido, borda superior em destaque) com suporte a dark mode

#### Rótulos de Exibição para Ativos de Renda Fixa
- **`irpfDisplayLabel(r)`** no dashboard (JavaScript): deriva um rótulo de exibição a partir de `discriminacao` para ativos de Renda Fixa com código 04/02 ou 04/03
  - Tesouro Selic, Tesouro IPCA+, Tesouro Prefixado, Tesouro Direto (genérico)
  - CDB – Certificado de Depósito Bancário
  - RDB – Recibo de Depósito Bancário
  - LCI – Letra de Crédito Imobiliário
  - LCA – Letra de Crédito do Agronegócio
  - CRI – Certificado de Recebíveis Imobiliários
  - CRA – Certificado de Recebíveis do Agronegócio
  - Esses ativos agora aparecem como **linhas separadas** na aba "Para IRPF" do dashboard, em vez de serem consolidados sob o mesmo código

- **`_renda_fixa_subtype(discriminacao)`** em `src/xlsx_writer.py`: mesma lógica de derivação de rótulo aplicada na geração da aba "Para IRPF" do XLSX exportado
  - Agregação na aba Para IRPF agora usa chave `(Grupo, Código, label_derivado)` para renda fixa, mantendo separação por subtipo

#### Stall Timeout no Pipeline de Processamento
- **`stall_timeout` em `_parse_file_map()`** (`src/main.py`): cada arquivo PDF/XLSX é processado com timeout de isolamento via `ThreadPoolExecutor`
  - Se o parsing de um arquivo travar por mais de N segundos sem retornar, ele é ignorado e o pipeline continua com os demais
  - Arquivo problemático registrado em `errors` com mensagem `[timeout]`
  - Configurável via `config.toml` → `[processing].stall_timeout_seconds` (padrão: `60`)
- **Nova seção `[processing]`** em `config.toml`:
  ```toml
  [processing]
  stall_timeout_seconds = 60
  ```

#### Reorganização de Scripts Auxiliares
- Scripts avulsos movidos para a pasta `scripts/`:
  - `explore_pdfs.py`, `process_ana_gloria.py`, `process_pipeline.py`
  - `test_dashboard.py`, `test_dashboard_v2.py`, `test_extraction.py`, `test_pipeline.py`
- `.gitignore` atualizado para refletir nova localização

---

## [1.3.0] - 2026-05-16

### ✨ Adicionado

#### Validação de Contribuinte Único
- **`validate_single_taxpayer(entries)`** em `src/main.py`: Verifica que todas as entradas do processamento pertencem ao mesmo contribuinte
  - Compara `nome_contribuinte` e `cpf_contribuinte` em todas as entradas
  - Retorna `(is_valid: bool, mensagem: str, conflitos: dict)`
  - Integrado ao pipeline principal: exibe aviso ao usuário caso haja inconsistências

- **Campos no modelo `Entry`** (`src/models.py`):
  - `nome_contribuinte: str = ""` — Nome completo do titular do informe
  - `cpf_contribuinte: str = ""` — CPF formatado (`XXX.XXX.XXX-XX`)

#### Extração Automática de Dados do Contribuinte
- **`extract_taxpayer_info(text)`** em `src/normalizer.py`: Extrai nome e CPF do contribuinte a partir do texto de qualquer página de informe
  - Passo 1: localiza CPF (formatado → mascarado → 11 dígitos brutos)
  - Passo 2: busca nome nas primeiras 25 linhas via padrão `Nome :` ou linha com nome + CPF adjacente
  - Passo 3: fallback para linha em maiúsculas sem dígitos (padrão FACHESF)
  - Passo 4: fallback para padrões explícitos de label
  - Todos os 9 parsers de PDF passaram a chamar `extract_taxpayer_info` e popular os campos acima em cada `Entry`

#### Suporte para FACHESF e INSS
- **Parser FACHESF** (`parse_fachesf`): Novo parser para informes da Fundação CHESF de Assistência e Seguridade Social
  - Detectado automaticamente por `fachesf` ou `chesf` no nome do arquivo
  - Extrai Quadro 3 (Rendimentos Tributáveis): total de rendimentos, contribuição à previdência privada, IRRF
  - Extrai Quadro 4 (Rendimentos Isentos): parcela isenta de aposentadoria (65+), 13º isento, aposentadoria por moléstia
  - Extrai Quadro 5 (Tributação Exclusiva): 13º salário/abono anual, outros (PLA/PLR)
  - CNPJ da fonte: `42.160.192/0001-43`

- **Parser INSS** (`parse_inss`): Novo parser para Comprovante de Rendimentos do Fundo do Regime Geral de Previdência Social
  - Detectado automaticamente por `inss` no nome do arquivo ou `regime geral de previdencia` / `frgps` no texto
  - Extrai Quadro 3 (Rendimentos Tributáveis): total de rendimentos (incl. férias), contribuição previdenciária oficial, IRRF
  - Extrai Quadro 4 (Rendimentos Isentos): parcela isenta de aposentadoria/pensão (65+)
  - CNPJ da fonte: `16.727.230/0001-97`

### 🐛 Corrigido

- **`normalizer.py` corrompido**: Arquivo foi completamente reescrito após acumulação de edições incrementais que resultaram em:
  - Definições duplicadas de `extract_taxpayer_info()`
  - Funções `clean()` e `extract_year()` aninhadas dentro de `extract_taxpayer_info()`, tornando-as inacessíveis a outros módulos
  - `NameError: name 'clean' is not defined` ao chamar a segunda definição
  - Solução: reescrita completa com todas as funções no nível de módulo

- **Import incompleto em `parser.py`**: `clean` e `extract_year` eram usados em todo o arquivo mas não estavam no import de `src.normalizer`
  - Corrigido: `from src.normalizer import parse_brl, find_cnpj, extract_taxpayer_info, clean, extract_year`

- **`detect_institution()` sem fallback para novas fontes**: Retornava `'unknown'` para FACHESF e INSS, gerando entradas com `secao='Desconhecido'` que eram filtradas pelo pipeline, causando erro `'Nenhuma entrada válida'`

## [1.2.3] - 2026-05-16

### 🐛 Corrigido

#### Filtragem de Artefatos macOS em ZIPs
- **`_is_metadata_entry()` em `src/extractor.py`**: Nova função que detecta e descarta silenciosamente entradas de ZIP que não são dados reais
  - Diretórios `__MACOSX/` criados pelo macOS ao compactar via Finder
  - Arquivos `._*` (AppleDouble sidecar / resource forks)
  - `.DS_Store` e `Thumbs.db`
  - Qualquer entrada que seja diretório (apenas arquivos são extraídos)

#### Resiliência no Parsing de PDFs
- **Exceções por arquivo não abortam o batch**: Erros em um PDF individual são capturados e registrados, o pipeline continua com os demais arquivos
- **Rastreamento de progresso corrigido**: Progresso agora é contabilizado corretamente para todos os desfechos (sucesso, erro, resultado vazio)
- **Novo teste**: `src/tests/test_zip_and_parse_resilience.py`
  - Testa filtragem de artefatos (8 casos: `__MACOSX`, `._`, `.DS_Store`, etc.)
  - Testa que exceção em um arquivo não interrompe processamento dos demais

## [1.2.2] - 2026-05-15

### ✨ Adicionado

#### Interface Web com Fluxo de Upload (Web-First)
- **Servidor Flask local** (`_run_web_mode()`): `python3 -m src.main` agora abre automaticamente um navegador com UI de arrasta-e-solta
  - Escolha entre processar arquivos de `input/` ou fazer upload manual
  - Drag-and-drop de PDFs individuais ou ZIPs
  - Feedback visual em tempo real durante o processamento
  - Exibe link direto para o dashboard HTML gerado
  - Fallback com mensagem de erro clara se Flask não estiver instalado

- **Modo CLI preservado** (`_run_cli_mode()`): comportamento original acessível via flag `--cli`
  - `python3 -m src.main --cli` processa `input/` imediatamente sem abrir navegador

- **Novas funções auxiliares em `src/main.py`**:
  - `_merge_file_maps(base, extra)`: mescla file maps sem colisão de nomes (renomeia duplicatas)
  - `_collect_upload_file_map(uploaded_paths)`: normaliza lista de uploads (PDFs avulsos + ZIPs) em file map unificado
  - `_parse_file_map(file_map, config)`: extrai lógica de parsing em função reutilizável
  - `_run_pipeline(file_map, config)`: executa pipeline completo e retorna resultado serializável como JSON

- **Dependência adicionada**: `flask` em `requirements.txt`

### 🔧 Melhorado

- **`src/dashboard_generator.py`**: Ajustes de layout e estilo na UI do stepper web

## [1.2.1] - 2026-05-07

### 🐛 Corrigido

- **Aba Para IRPF – duplicatas por instituição**: linhas com a mesma trinca (Grupo, Código, Descrição) mas `discriminacao` distinta (ex.: múltiplos CDBs/fundos individuais da XP) não eram consolidadas, gerando linhas duplicadas para Nubank, Inter e XP.
  - A lógica de mesclagem no dashboard passou a agregar **sempre** por `(grupo, codigo, descricao)`, independentemente de `discriminacao`.
  - Cada trinca é agora exibida como uma única linha com os valores somados, conforme exigido pelo formulário DIRPF.

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
