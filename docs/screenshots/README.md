# 📸 Dashboard Screenshots

Este diretório contém screenshots de referência do Dashboard Interativo capturados com Playwright.

## 📋 Arquivos

### Visualizações Completas

| Arquivo | Descrição | Tamanho |
|---------|-----------|---------|
| `dashboard_full_light.png` | Dashboard completo em tema claro | 232.6KB |
| `dashboard_full_dark.png` | Dashboard completo em tema escuro | 215.0KB |
| `dashboard_responsive_mobile.png` | Versão mobile (375px de largura) | 179.5KB |

### Seções Específicas

| Arquivo | Descrição | Tamanho |
|---------|-----------|---------|
| `dashboard_charts_light.png` | Seção de gráficos em tema claro | 12.7KB |
| `dashboard_charts_dark.png` | Seção de gráficos em tema escuro | 12.9KB |
| `dashboard_table_light.png` | Tabela de dados brutos | 138.1KB |

### Gráficos Detalhados

| Arquivo | Descrição | Tamanho |
|---------|-----------|---------|
| `dashboard_chart_evolution.png` | Bar chart: Evolução 2024 → 2025 | 20.1KB |
| `dashboard_chart_institution.png` | Pie chart: Distribuição por instituição | 24.8KB |

### Abas de Dados

| Arquivo | Descrição | Tamanho |
|---------|-----------|---------|
| `dashboard_tab_resumo.png` | Aba "Resumo": Dados por seção/instituição | 78.9KB |
| `dashboard_tab_totais.png` | Aba "Totais": Consolidação IRPF | 77.9KB |

## 🔄 Como Regenerar Screenshots

Os screenshots são gerados automaticamente usando **Playwright** e dados de teste mock.

### Pré-requisitos

```bash
pip install playwright
playwright install chromium
```

### Executar Captura

```bash
# Método 1: Executar o módulo de teste
python3 -m src.tests.test_dashboard_screenshots

# Método 2: Importar direto no Python
python3 -c "
import asyncio
from src.tests.test_dashboard_screenshots import take_dashboard_screenshots
asyncio.run(take_dashboard_screenshots())
"
```

### Saída Esperada

```
======================================================================
📸 DASHBOARD SCREENSHOT CAPTURE
======================================================================

🔨 Generating dashboard HTML...
   ✅ Dashboard generated

📱 Opening dashboard...
   ✅ Dashboard loaded and charts rendered

💡 Capturing light mode screenshots...
   ✅ Full page (light)
   ✅ Charts section (light)
   ✅ Table section (light)

🌙 Capturing dark mode screenshots...
   ✅ Full page (dark)
   ✅ Charts section (dark)

📱 Capturing responsive layout...
   ✅ Responsive mobile

📊 Capturing evolution chart detail...
   ✅ Evolution chart detail

🥧 Capturing institution distribution chart...
   ✅ Institution chart detail

📋 Capturing tab views...
   ✅ Tab resumo
   ✅ Tab totais

======================================================================
✅ Screenshots saved to: docs/screenshots
📋 Files created: 10
======================================================================
```

## 🎨 Dados de Teste

Os screenshots são capturados com dados mock definidos em `src/tests/test_dashboard.py`:

- **Instituições**: 6 (Accenture, Avenue, Inter, NuBank, XP Investimentos, XP Previdência)
- **Entradas**: 9 registros diversos
- **Valores**: Simulam dados reais de informes de rendimentos
- **Formato**: HTML com Bootstrap 5.3 + Chart.js + Dark Mode

## 📖 Documentação Relacionada

- **Dashboard**: [docs/DASHBOARD.md](../DASHBOARD.md)
- **Testes**: [src/tests/test_dashboard_screenshots.py](../../src/tests/test_dashboard_screenshots.py)
- **Gerador**: [src/dashboard_generator.py](../../src/dashboard_generator.py)

## 🔧 Troubleshooting

### Problema: "Playwright timeout"
**Solução**: Aumentar timeout em `test_dashboard_screenshots.py` ou reduzir scroll timeout.

### Problema: Imagens parciais/borradas
**Solução**: Verificar se o Chromium foi instalado corretamente:
```bash
playwright install chromium --with-deps
```

### Problema: Dark mode não aparece
**Solução**: Garantir que localStorage tem `theme: dark` antes de capturar.

## 📝 Notas

- Screenshots são capturados em resolução padrão (1280×720)
- Mobile usa viewport 375×667 (iPhone SE)
- Todos os gráficos Chart.js são renderizados antes de capturar
- Fontes são carregadas antes de screenshot (via Playwright `waitForFonts`)
- Tema claro é o padrão; tema escuro é alternado via CSS

## 🚀 Próximas Melhorias

- [ ] Capturar screenshots com dados reais (quando disponível)
- [ ] Adicionar comparação antes/depois em documentação
- [ ] Automatizar regeneração em CI/CD
- [ ] Capturar em múltiplas resoluções (1920×1080, 768×1024, etc.)
