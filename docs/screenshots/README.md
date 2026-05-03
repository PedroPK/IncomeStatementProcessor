# 📸 Dashboard Screenshots

Este diretório contém screenshots de referência do Dashboard Interativo capturado em tempo real com Playwright. Aqui você encontra visualizações de todas as funcionalidades e estados do dashboard.

---

## 🌟 Visualizações Completas

### Dashboard Tema Claro
Dashboard completo em tema claro com todos os gráficos e tabelas renderizados.

![Dashboard Completo - Tema Claro](dashboard_full_light.png)

### Dashboard Tema Escuro
A mesma interface com tema escuro para diferentes preferências de visualização.

![Dashboard Completo - Tema Escuro](dashboard_full_dark.png)

### Dashboard Versão Mobile
Visualização responsiva para dispositivos móveis (375px de largura).

![Dashboard Mobile - Responsivo](dashboard_responsive_mobile.png)

---

## 📊 Seções Específicas do Dashboard

### Gráficos e Visualizações
Detalhe da seção de gráficos em tema claro.

![Seção de Gráficos - Tema Claro](dashboard_charts_light.png)

### Gráficos - Tema Escuro
A mesma seção de gráficos em tema escuro.

![Seção de Gráficos - Tema Escuro](dashboard_charts_dark.png)

### Tabela de Dados Brutos
Visualização completa da tabela com dados estruturados.

![Tabela de Dados Brutos](dashboard_table_light.png)

---

## 📈 Análises Detalhadas

### Gráfico de Evolução (2024 → 2025)
Bar chart mostrando a evolução temporal dos dados entre períodos.

![Gráfico de Evolução Temporal](dashboard_chart_evolution.png)

### Distribuição por Instituição
Pie chart apresentando a distribuição proporcional entre diferentes instituições.

![Distribuição por Instituição](dashboard_chart_institution.png)

---

## 📋 Abas de Navegação

### Aba "Resumo"
Visualização consolidada dos dados organizados por seção e instituição.

![Aba Resumo - Dados Consolidados](dashboard_tab_resumo.png)

### Aba "Totais"
Consolidação e resumo para fins de IRPF (Imposto de Renda Pessoa Física).

![Aba Totais - Consolidação IRPF](dashboard_tab_totais.png)

---

## 🔄 Como Regenerar Screenshots

Os screenshots são gerados automaticamente usando **Playwright** e dados de teste mock. Siga os passos abaixo para capturar novas screenshots após alterações no dashboard.

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
