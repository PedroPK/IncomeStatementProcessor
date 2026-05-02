# Dashboard Examples

Esta pasta contém exemplos de dashboards HTML gerados automaticamente pelo `examples_dashboard.py`.

## 📋 Como Usar

### Gerar Todos os Exemplos

```bash
python3 examples_dashboard.py
```

Isso gera 5 dashboards diferentes demonstrando vários cenários:

### 1️⃣ `dashboard_mock.html`

**Descrição**: Dashboard com dados mockados de teste (10 entradas)

**Uso**: Para testes rápidos sem precisar processar PDFs reais

**Dados**: 5 instituições (Accenture, Itaú, Bradesco, XP, NuBank)

```
Total 2024: R$ 196,850.00
Total 2025: R$ 268,350.00
Rendimentos: R$ 23,875.50
```

### 2️⃣ `dashboard_real.html`

**Descrição**: Dashboard com todos os dados reais processados do ZIP (59 entradas)

**Uso**: Visualização completa após processar `input/*.zip`

**Requer**: ZIP com PDFs de 6 instituições em `input/`

```
Total 2024: R$ 466,311.07
Total 2025: R$ 651,499.50
Rendimentos: R$ 55,792.97
```

### 3️⃣ `dashboard_xp_only.html`

**Descrição**: Dashboard filtrado com apenas entradas XP (2 entradas)

**Uso**: Analisar ativos de uma instituição específica

**Filtro**: `instituicao like '%XP%'`

```
Total 2024: R$ 1,850.00
Total 2025: R$ 2,150.00
Rendimentos: R$ 125.50
```

### 4️⃣ `dashboard_growing.html`

**Descrição**: Dashboard com ativos em crescimento > 10% (4 entradas)

**Uso**: Identificar melhores performers

**Critério**: `(valor_2025 - valor_2024) / valor_2024 > 10%`

```
Ativos com crescimento:
- Bitcoin (BTC):              +50.0%
- Fundos de investimento:     +15.0%
- Ações:                      +16.2%
- Rendimentos PJ:             +∞ (novo em 2025)
```

### 5️⃣ `dashboard_top3.html`

**Descrição**: Dashboard das 3 principais instituições (6 entradas)

**Uso**: Comparar maior parte dos investimentos

**Top 3 (2025)**:
1. Bradesco Corretora: R$ 115,000.00
2. NuBank: R$ 53,700.00
3. Itaú Bank: R$ 52,500.00

## 🎯 Casos de Uso

### Análise Rápida
```bash
# Abra o dashboard mockado para ver estrutura
open dashboard_mock.html
```

### Auditoria Completa
```bash
# Após colocar ZIP em input/, execute:
python3 examples_dashboard.py
open dashboard_real.html  # visualizar todos os 59 dados
```

### Análise por Instituição
```bash
# Customizar o filtro em examples_dashboard.py:
# xp_entries = [e for e in MOCK_ENTRIES if 'OUTRA_INST' in e.instituicao]
open dashboard_xp_only.html
```

### Performance Analysis
```bash
# Identificar crescimento de ativos
open dashboard_growing.html
```

### Portfólio Focus
```bash
# Concentração nos maiores ativos
open dashboard_top3.html
```

## 🔧 Customizando Exemplos

### Adicionar Novo Exemplo

Edite `examples_dashboard.py`:

```python
def example_6_my_filter():
    """Exemplo 6: Dashboard customizado."""
    print("=" * 70)
    print("EXEMPLO 6: Meu Filtro")
    print("=" * 70)

    # Seu filtro aqui
    my_entries = [e for e in MOCK_ENTRIES if e.rendimento > 5000]

    generate_dashboard_html(my_entries, 'examples/dashboard_custom.html')
    print(f"✅ Dashboard customizado: {len(my_entries)} entradas")
```

Adicione ao `main()`:
```python
def main():
    # ... outros exemplos ...
    example_6_my_filter()  # novo
```

### Filtros Úteis

```python
# Por instituição
entries = [e for e in MOCK_ENTRIES if e.instituicao == 'XP']

# Por rendimento mínimo
entries = [e for e in MOCK_ENTRIES if e.rendimento > 1000]

# Por seção
entries = [e for e in MOCK_ENTRIES if 'Bens' in e.secao]

# Por período (2025 > 2024)
entries = [e for e in MOCK_ENTRIES if e.valor_2025 > e.valor_2024]

# Combinado
entries = [
    e for e in MOCK_ENTRIES
    if e.instituicao == 'NuBank' and e.rendimento > 0
]
```

## 📊 Navegação dos Dashboards

### Todas as abas suportam:

1. **Dados Brutos** — Tabela com todas as entradas
2. **Resumo** — Pivot por Seção × Instituição
3. **Totais** — Agregação por Grupo/Código
4. **Para IRPF** — Formatação para preenchimento IRPF

### Recursos Interativos:

- ✅ Gráficos interativos (Pie + Bar) via Chart.js
- ✅ Tabelas responsivas com scroll horizontal
- ✅ Formatação de moeda em tempo real
- ✅ Hover effects e alternating rows
- ✅ Navegação por tabs sem recarregar página

## 📱 Compatibilidade

| Navegador | Suporte |
|-----------|---------|
| Chrome 90+ | ✅ Completo |
| Firefox 88+ | ✅ Completo |
| Safari 14+ | ✅ Completo |
| Edge 90+ | ✅ Completo |
| Mobile Safari (iOS) | ✅ Com responsividade |
| Chrome Mobile | ✅ Com responsividade |

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| Gráficos não aparecem | Verifique conexão CDN (Chart.js) |
| Tabelas distorcidas em mobile | Use modo landscape |
| Valores não formatados | Navegador antigo, atualize |
| Dashboard vazio | Verifique se há entradas no filtro |

## 📈 Próximas Melhorias

- [ ] Exportar para PDF (via print CSS)
- [ ] Exportar para CSV/Excel
- [ ] Adicionar temas (dark mode)
- [ ] Filtros dinâmicos via UI
- [ ] Gráficos adicionais (treemap, waterfall)

## 📚 Referências

- [Dashboard.md](../DASHBOARD.md) — Documentação completa
- [src/dashboard_generator.py](../src/dashboard_generator.py) — Código gerador
- [test_integration.py](../test_integration.py) — Dados mockados
- [README.md](../README.md) — Guia principal

---

**Versão**: 1.0.1  
**Data**: 2026-05-02  
**Autor**: Pedro Carlos Ferreira Santos
