# 📊 Dashboard Interativo — Documentação Visual

## Visão Geral

O Dashboard Interativo oferece uma visualização completa dos dados de Informes de Rendimentos com:
- ✅ 4 abas interativas (Dados Brutos, Resumo, Totais, Para IRPF)
- ✅ 2 gráficos dinâmicos (Pizza e Barras)
- ✅ 4 cards de métricas-chave
- ✅ Design responsivo (mobile-friendly)
- ✅ Formatação automática de moeda

---

## 🎯 Métricas Principais

O dashboard destaca 4 métricas principais em cards interativos:

```
┌─────────────────────┬──────────────────────┬─────────────────────┬──────────────┐
│  Total 2024         │   Total 2025         │   Rendimentos       │  Entradas    │
├─────────────────────┼──────────────────────┼─────────────────────┼──────────────┤
│  R$ 196.850,00      │   R$ 268.350,00      │   R$ 23.875,50      │      10      │
│  (Dados Mockados)   │   (Dados Mockados)   │   (Dados Mockados)  │ (Mockados)   │
└─────────────────────┴──────────────────────┴─────────────────────┴──────────────┘
```

### Com Dados Reais (59 entradas):

```
┌─────────────────────┬──────────────────────┬─────────────────────┬──────────────┐
│  Total 2024         │   Total 2025         │   Rendimentos       │  Entradas    │
├─────────────────────┼──────────────────────┼─────────────────────┼──────────────┤
│  R$ 466.311,07      │   R$ 651.499,50      │   R$ 55.792,97      │      59      │
│  (Dados Reais)      │   (Dados Reais)      │   (Dados Reais)     │ (Reais)      │
└─────────────────────┴──────────────────────┴─────────────────────┴──────────────┘
```

---

## 📈 Gráficos Dinâmicos

### Gráfico 1: Distribuição por Instituição (Pizza)

**O que mostra**: Proporção de cada instituição no total de ativos em 2025

**Dados de exemplo (Mockados - 10 entradas)**:
```
Accenture                   18.5% (R$ 49.650)
Bradesco Corretora          42.8% (R$ 115.000)
Itaú Bank                   19.5% (R$ 52.500)
NuBank                      20.1% (R$ 53.700)
XP Investimentos             0.8% (R$ 2.150)
                           ─────────────────
Total                      100.0% (R$ 268.350)
```

**Dados de exemplo (Estendidos - 7 entradas)**:
```
Accenture                   12.0% (R$ 85.000)
Avenue Securities            1.3% (R$ 9.200)
Inter                       18.7% (R$ 132.500)
NuBank                       0.0% (R$ 0)
XP Investimentos            47.6% (R$ 337.500)
XP Vida e Previdência       20.4% (R$ 144.500)
                           ─────────────────
Total                      100.0% (R$ 709.700)
```

### Gráfico 2: Evolução 2024 vs 2025 (Barras)

**O que mostra**: Comparação de valores entre 2024 e 2025 por instituição

**Dados de exemplo (Mockados)**:
```
                2024          2025         Crescimento
Accenture         R$ 0     R$ 45.000       +∞ (novo)
Bradesco    R$ 100.000    R$ 115.000       +15%
Itaú Bank   R$ 50.000     R$ 52.500        +5%
NuBank      R$ 52.500     R$ 53.700        +2.3%
XP           R$ 1.850      R$ 2.150        +16.2%
             ──────────    ──────────
Total      R$ 196.850    R$ 268.350        +36.2%
```

**Interpretação**:
- Bradesco e XP mostram crescimento significativo
- Instituições menores crescem proporcionalistas
- Crescimento total de 36% no período

---

## 📋 Aba 1: Dados Brutos

Contém **todas as entradas** com 9 colunas principais, formatada como tabela interativa com:
- ✅ Linhas com cores alternadas (hover effect)
- ✅ Moeda formatada em BRL
- ✅ Scroll horizontal em mobile
- ✅ Classificação por instituição

### Amostra com Dados Mockados:

| Arquivo | Instituição | Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|---------|-------------|-------|-------|--------|-----------|------|------|-----------|
| Accenture... | Accenture | Rendimentos Tributáveis PJ | — | 01 | Rendimentos de PJ | R$ 0 | R$ 45.000 | R$ 0 |
| Accenture... | Accenture | Rendimentos Tributação Exclusiva | — | 11 | PLR 2025 | R$ 0 | R$ 0 | R$ 12.500 |
| Itau... | Itaú Bank | Bens e Direitos | 04 | 02 | Títulos públicos | R$ 50.000 | R$ 52.500 | R$ 0 |
| Itau... | Itaú Bank | Rendimentos Tributação Exclusiva | — | 06 | Rendimentos financeiros | R$ 0 | R$ 0 | R$ 2.500 |
| Bradesco... | Bradesco Corretora | Bens e Direitos | 07 | 01 | Fundos de investimento | R$ 100.000 | R$ 115.000 | R$ 0 |
| Bradesco... | Bradesco Corretora | Rendimentos Tributação Exclusiva | — | 06 | Rendimentos FII | R$ 0 | R$ 0 | R$ 8.750 |
| XP... | XP Investimentos | Bens e Direitos | 03 | 01 | Ações | R$ 1.850 | R$ 2.150 | R$ 0 |
| XP... | XP Investimentos | Rendimentos Tributação Exclusiva | — | 06 | Dividendos | R$ 0 | R$ 0 | R$ 125.50 |
| NuBank... | NuBank | Bens e Direitos | 08 | 01 | Criptomoedas | R$ 52.500 | R$ 53.700 | R$ 0 |
| NuBank... | NuBank | Rendimentos Tributação Exclusiva | — | 06 | Juro do CDB | R$ 0 | R$ 0 | R$ 0 |

---

## 📈 Aba 2: Resumo (Pivot Seção × Instituição)

Agrupa dados por **seção e instituição** para visão consolidada por categoria:

### Exemplo com Dados Mockados:

| Seção | Instituição | 2024 | 2025 | Rendimento |
|-------|-------------|------|------|-----------|
| **Bens e Direitos** | | | | |
| | Bradesco Corretora | R$ 100.000 | R$ 115.000 | R$ 0 |
| | Itaú Bank | R$ 50.000 | R$ 52.500 | R$ 0 |
| | NuBank | R$ 52.500 | R$ 53.700 | R$ 0 |
| | XP Investimentos | R$ 1.850 | R$ 2.150 | R$ 0 |
| *Subtotal Bens* | | **R$ 204.350** | **R$ 223.350** | **R$ 0** |
| | | | | |
| **Rendimentos Tributação Exclusiva** | | | | |
| | Accenture | R$ 0 | R$ 0 | R$ 12.500 |
| | Bradesco Corretora | R$ 0 | R$ 0 | R$ 8.750 |
| | Itaú Bank | R$ 0 | R$ 0 | R$ 2.500 |
| | XP Investimentos | R$ 0 | R$ 0 | R$ 125.50 |
| *Subtotal Rendimentos* | | **R$ 0** | **R$ 0** | **R$ 23.875,50** |
| | | | | |
| **Rendimentos Tributáveis PJ** | | | | |
| | Accenture | R$ 0 | R$ 45.000 | R$ 0 |
| *Subtotal PJ* | | **R$ 0** | **R$ 45.000** | **R$ 0** |
| | | | | |
| **TOTAL GERAL** | | **R$ 204.350** | **R$ 268.350** | **R$ 23.875,50** |

---

## 💰 Aba 3: Totais (Agregação por Grupo/Código)

Consolida por **grupo e código IRPF** com linha de total destacada:

### Exemplo com Dados Mockados:

| Grupo | Código | Descrição | 2024 | 2025 | Rendimento | Total |
|-------|--------|-----------|------|------|-----------|-------|
| — | 01 | Rendimentos de PJ | R$ 0 | R$ 45.000 | R$ 0 | R$ 45.000 |
| — | 06 | Rendimentos de aplicações | R$ 0 | R$ 0 | R$ 11.375,50 | R$ 11.375,50 |
| — | 11 | PLR/Participação nos lucros | R$ 0 | R$ 0 | R$ 12.500 | R$ 12.500 |
| **03** | **01** | **Ações** | **R$ 1.850** | **R$ 2.150** | **R$ 0** | **R$ 4.000** |
| **04** | **02** | **Títulos públicos/privados** | **R$ 50.000** | **R$ 52.500** | **R$ 0** | **R$ 102.500** |
| **07** | **01** | **Fundos de investimento** | **R$ 100.000** | **R$ 115.000** | **R$ 0** | **R$ 215.000** |
| **08** | **01** | **Criptomoedas** | **R$ 52.500** | **R$ 53.700** | **R$ 0** | **R$ 106.200** |
| | | | | | | |
| **TOTAL GERAL** | | | **R$ 204.350** | **R$ 268.350** | **R$ 23.875,50** | **R$ 496.575,50** |

---

## 📝 Aba 4: Para IRPF (Agrupado por Instituição)

Formatado especificamente para facilitar preenchimento da DIRPF, com:
- ✅ Agrupamento por instituição (alfabético)
- ✅ Separadores de seção
- ✅ Subtotal por instituição
- ✅ Total geral consolidado

### Exemplo com Dados Mockados:

#### **ACCENTURE**

| Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|-------|-------|--------|-----------|------|------|-----------|
| Rendimentos Tributáveis PJ | — | 01 | Rendimentos de PJ | R$ 0 | R$ 45.000 | R$ 0 |
| Rendimentos Tributação Exclusiva | — | 11 | PLR 2025 | R$ 0 | R$ 0 | R$ 12.500 |
| *Subtotal Accenture* | | | | **R$ 0** | **R$ 45.000** | **R$ 12.500** |

#### **BRADESCO CORRETORA**

| Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|-------|-------|--------|-----------|------|------|-----------|
| Bens e Direitos | 07 | 01 | Fundos de investimento | R$ 100.000 | R$ 115.000 | R$ 0 |
| Rendimentos Tributação Exclusiva | — | 06 | Rendimentos FII | R$ 0 | R$ 0 | R$ 8.750 |
| *Subtotal Bradesco* | | | | **R$ 100.000** | **R$ 115.000** | **R$ 8.750** |

#### **ITAÚ BANK**

| Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|-------|-------|--------|-----------|------|------|-----------|
| Bens e Direitos | 04 | 02 | Títulos públicos | R$ 50.000 | R$ 52.500 | R$ 0 |
| Rendimentos Tributação Exclusiva | — | 06 | Rendimentos financeiros | R$ 0 | R$ 0 | R$ 2.500 |
| *Subtotal Itaú* | | | | **R$ 50.000** | **R$ 52.500** | **R$ 2.500** |

#### **NUBANK**

| Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|-------|-------|--------|-----------|------|------|-----------|
| Bens e Direitos | 08 | 01 | Criptomoedas | R$ 52.500 | R$ 53.700 | R$ 0 |
| *Subtotal NuBank* | | | | **R$ 52.500** | **R$ 53.700** | **R$ 0** |

#### **XP INVESTIMENTOS**

| Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento |
|-------|-------|--------|-----------|------|------|-----------|
| Bens e Direitos | 03 | 01 | Ações | R$ 1.850 | R$ 2.150 | R$ 0 |
| Rendimentos Tributação Exclusiva | — | 06 | Dividendos | R$ 0 | R$ 0 | R$ 125.50 |
| *Subtotal XP* | | | | **R$ 1.850** | **R$ 2.150** | **R$ 125.50** |

---

#### **RESUMO GERAL PARA IRPF**

```
Accenture:               2024: R$ 0          2025: R$ 45.000         Rend: R$ 12.500
Bradesco Corretora:      2024: R$ 100.000    2025: R$ 115.000        Rend: R$ 8.750
Itaú Bank:               2024: R$ 50.000     2025: R$ 52.500         Rend: R$ 2.500
NuBank:                  2024: R$ 52.500     2025: R$ 53.700         Rend: R$ 0
XP Investimentos:        2024: R$ 1.850      2025: R$ 2.150          Rend: R$ 125.50
                        ──────────────      ──────────────       ───────────────
TOTAL:                   2024: R$ 204.350    2025: R$ 268.350        Rend: R$ 23.875,50
```

---

## 🎨 Recursos de Design

### Cores e Tema

- **Primária**: `#667eea` (azul roxo) — usado em títulos, métricas, bordas
- **Secundária**: `#764ba2` (roxo) — usado em gráficos, hover effects
- **Destaques**: `#f093fb` (rosa), `#4facfe` (azul claro), `#43e97b` (verde)
- **Fundo**: `#f8f9fa` (cinza claro)
- **Cards**: Branco com sombra suave, borda esquerda roxo

### Responsividade

| Dispositivo | Width | Layout |
|------------|-------|--------|
| Mobile | < 576px | 1 coluna, tabelas com scroll |
| Tablet | 576-992px | 2 colunas |
| Desktop | > 992px | 4 cards + 2 charts em 2 colunas |

---

## 📦 Dados de Teste Disponíveis

### Conjunto 1: Mock Data (10 entradas, 5 instituições)
- **Arquivo**: `test_integration.py` → `MOCK_ENTRIES`
- **Total 2024**: R$ 196.850,00
- **Total 2025**: R$ 268.350,00
- **Rendimentos**: R$ 23.875,50
- **Uso**: Testes rápidos, demonstração, documentação

### Conjunto 2: Extended Test Data (7 entradas, 6 instituições)
- **Arquivo**: `test_dashboard.py` → `EXTENDED_TEST_DATA`
- **Total 2024**: R$ 563.500,00
- **Total 2025**: R$ 709.700,00
- **Rendimentos**: R$ 74.250,00
- **Novidades**: Dados mais realistas com valores maiores
- **Uso**: Testes abrangentes, cenários complexos

### Conjunto 3: Dados Reais (59 entradas, 6 instituições)
- **Arquivo**: `input/drive-download-*.zip` (quando disponível)
- **Total 2024**: R$ 466.311,07
- **Total 2025**: R$ 651.499,50
- **Rendimentos**: R$ 55.792,97
- **Uso**: Produção, cenários reais

---

## 🧪 Testes Automatizados

O dashboard possui suite completa de testes em `test_dashboard.py`:

```bash
python3 test_dashboard.py
```

### Testes Incluídos

1. ✅ `test_dashboard_generation` — Gera HTML com sucesso
2. ✅ `test_dashboard_data_embedding` — JSON embedded corretamente
3. ✅ `test_dashboard_tabs` — 4 abas presentes e funcionais
4. ✅ `test_dashboard_charts` — Charts Chart.js configurados
5. ✅ `test_dashboard_metrics` — Cards de métricas corretos
6. ✅ `test_dashboard_with_extended_data` — Funciona com dados estendidos
7. ✅ `test_dashboard_responsive_design` — Classes Bootstrap presentes
8. ✅ `test_dashboard_currency_formatting` — Formatação de moeda OK
9. ✅ `test_dashboard_all_institutions` — Todas as instituições aparecem
10. ✅ `test_dashboard_section_aggregation` — Seções agregadas corretamente

**Resultado**: ✅ 10/10 testes passando

---

## 🚀 Como Usar

### Gerar Dashboard Automaticamente

```bash
python3 -m src.main
# Outputs:
#  - output/informes_rendimentos.xlsx
#  - output/dashboard.html
```

### Gerar Exemplos

```bash
python3 examples_dashboard.py
# Gera 5 dashboards em examples/:
#  - dashboard_mock.html
#  - dashboard_real.html
#  - dashboard_xp_only.html
#  - dashboard_growing.html
#  - dashboard_top3.html
```

### Abrir no Navegador

```bash
# macOS
open output/dashboard.html

# Linux
firefox output/dashboard.html

# Windows
start output/dashboard.html
```

---

## 📊 Comparação de Volumes

| Métrica | Mock | Extended | Real |
|---------|------|----------|------|
| Entradas | 10 | 7 | 59 |
| Instituições | 5 | 6 | 6 |
| Total 2024 | R$ 196.850 | R$ 563.500 | R$ 466.311 |
| Total 2025 | R$ 268.350 | R$ 709.700 | R$ 651.500 |
| Rendimentos | R$ 23.875,50 | R$ 74.250 | R$ 55.792,97 |
| Tamanho HTML | 22.7KB | 21.6KB | 37KB |

---

**Versão**: 1.0.1  
**Data**: 2026-05-02  
**Status**: ✅ Completo
