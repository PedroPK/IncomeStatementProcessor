# Quick Start — Income Statement Processor

## Requisitos

- Python 3.11+
- pip

---

## 1. Ambiente

```bash
# No diretório do projeto
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## 2. Dados de entrada

Coloque um **ZIP** na pasta `input/` contendo os PDFs dos informes de rendimentos.

Os nomes de arquivo são detectados automaticamente:

| Instituição | Padrão esperado |
|---|---|
| Accenture | `Accenture - Informe*.aspx` |
| Avenue | `Avenue*.pdf` |
| Clear (informe) | `Clear - 01 Informe*.pdf` |
| Clear (custódia) | `Clear - 04 Custódia*.pdf` |
| Inter | `Inter*.pdf` |
| NuBank | `NuBank*.pdf` |
| XP Investimentos | `XP - Informe*.pdf` |
| XP Previdência | `XP*Previdência*.pdf` |

> **Custódia de Ativos (opcional):** inclua no ZIP um arquivo `ClearCustodia.xlsx` com colunas: **Ativo**, **Quantidade de Cotas**, **Preço Médio**.

---

## 3. Executar

### Modo Web (padrão — recomendado)

```bash
python3 -m src.main
```

Abre uma interface web local com dois passos:
1. Escolher a origem dos arquivos (`input/` ou upload por drag-and-drop)
2. Visualizar o dashboard gerado após o processamento

### Modo CLI

```bash
python3 -m src.main --cli
```

Processa diretamente os arquivos em `input/` sem interface web.

---

## 4. Saídas

| Arquivo | Descrição |
|---|---|
| `output/informes_rendimentos.xlsx` | Planilha com abas: Dados Brutos, Resumo, Totais, Para IRPF |
| `output/dashboard.html` | Dashboard interativo com gráficos |

---

## 5. Configuração (opcional)

Edite `config.toml` para alterar caminhos de saída ou habilitar Google Sheets:

```toml
[output]
xlsx_path = "output/informes_rendimentos.xlsx"
dashboard_path = "output/dashboard.html"

[google_sheets]
enabled = false   # true para exportar para Sheets
credentials_file = "credentials/credentials.json"
token_file = "credentials/token.json"
```
