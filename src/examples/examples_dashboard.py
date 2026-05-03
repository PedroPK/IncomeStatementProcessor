#!/usr/bin/env python3
"""
Dashboard Generation Examples

Demonstra diferentes formas de usar o dashboard generator:
1. Com dados mockados (teste)
2. Com dados reais processados
3. Customização de path de saída
"""

from pathlib import Path
from src.dashboard_generator import generate_dashboard_html
from src.models import Entry
from src.tests.test_integration import MOCK_ENTRIES


def example_1_mock_data():
    """Exemplo 1: Gerar dashboard com dados mockados."""
    print("=" * 70)
    print("EXEMPLO 1: Dashboard com Dados Mockados")
    print("=" * 70)

    # Use dados mockados diretos
    generate_dashboard_html(MOCK_ENTRIES, 'examples/dashboard_mock.html')
    print("✅ Dashboard mockado criado: examples/dashboard_mock.html\n")


def example_2_real_data():
    """Exemplo 2: Gerar dashboard após processar PDFs reais."""
    print("=" * 70)
    print("EXEMPLO 2: Dashboard com Dados Reais (Pipeline Completo)")
    print("=" * 70)

    # Este exemplo simula o fluxo real do pipeline
    from src.extractor import extract_zip, find_zip
    from src.parser import parse_file

    zip_path = find_zip('input')
    if not zip_path:
        print("[aviso] Nenhum ZIP encontrado em input/")
        print("        Pulando exemplo 2. Para testar, adicione um ZIP em input/")
        return

    print(f"ZIP encontrado: {zip_path}")
    file_map = extract_zip(zip_path)
    print(f"  {len(file_map)} arquivo(s) extraído(s)")

    # Parse each file
    all_entries = []
    for filename, filepath in sorted(file_map.items()):
        ext = Path(filename).suffix.lower()
        if ext not in {'.pdf', '.aspx', '.asp'}:
            continue

        print(f"  Processando: {filename}")
        entries = parse_file(filepath)

        ok_entries = [e for e in entries if e.secao not in ('Erro', 'Desconhecido')]
        print(f"    → {len(ok_entries)} entradas extraídas")
        all_entries.extend(ok_entries)

    # Generate dashboard
    print(f"\nTotal: {len(all_entries)} entradas processadas")
    generate_dashboard_html(all_entries, 'examples/dashboard_real.html')
    print("✅ Dashboard com dados reais criado: examples/dashboard_real.html\n")


def example_3_custom_filter():
    """Exemplo 3: Gerar dashboard com filtro customizado."""
    print("=" * 70)
    print("EXEMPLO 3: Dashboard Filtrado (Apenas XP)")
    print("=" * 70)

    # Filtre apenas entradas de XP
    xp_entries = [e for e in MOCK_ENTRIES if 'XP' in e.instituicao.upper()]

    print(f"Entradas de XP: {len(xp_entries)} de {len(MOCK_ENTRIES)}")
    generate_dashboard_html(xp_entries, 'examples/dashboard_xp_only.html')
    print("✅ Dashboard filtrado (XP) criado: examples/dashboard_xp_only.html\n")


def example_4_period_comparison():
    """Exemplo 4: Dashboard comparativo (2024 vs 2025)."""
    print("=" * 70)
    print("EXEMPLO 4: Dashboard Comparativo")
    print("=" * 70)

    # Filtre apenas entradas com crescimento positivo
    growing_entries = [
        e for e in MOCK_ENTRIES
        if e.valor_2025 > e.valor_2024 * 1.1  # Crescimento > 10%
    ]

    print(f"Ativos em crescimento (>10%): {len(growing_entries)}")
    for e in growing_entries:
        growth = ((e.valor_2025 - e.valor_2024) / e.valor_2024 * 100) if e.valor_2024 > 0 else 0
        print(f"  - {e.codigo_desc}: {growth:+.1f}% ({e.valor_2024:.2f} → {e.valor_2025:.2f})")

    generate_dashboard_html(growing_entries, 'examples/dashboard_growing.html')
    print("\n✅ Dashboard de ativos em crescimento criado: examples/dashboard_growing.html\n")


def example_5_top_institutions():
    """Exemplo 5: Dashboard das principais instituições."""
    print("=" * 70)
    print("EXEMPLO 5: Dashboard Top Instituições")
    print("=" * 70)

    # Agrupe e calcule top 3 instituições
    inst_totals = {}
    for e in MOCK_ENTRIES:
        if e.instituicao not in inst_totals:
            inst_totals[e.instituicao] = 0
        inst_totals[e.instituicao] += e.valor_2025

    top_insts = sorted(inst_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    top_names = [name for name, _ in top_insts]

    print("Top 3 instituições (2025):")
    for i, (name, total) in enumerate(top_insts, 1):
        print(f"  {i}. {name}: R$ {total:,.2f}")

    top_entries = [e for e in MOCK_ENTRIES if e.instituicao in top_names]
    generate_dashboard_html(top_entries, 'examples/dashboard_top3.html')
    print(f"\n✅ Dashboard top 3 instituições criado: examples/dashboard_top3.html")
    print(f"   Entradas: {len(top_entries)}\n")


def main():
    """Execute todos os exemplos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Dashboard Generator — Exemplos" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Create examples directory
    Path('examples').mkdir(exist_ok=True)

    # Run examples
    example_1_mock_data()
    example_2_real_data()
    example_3_custom_filter()
    example_4_period_comparison()
    example_5_top_institutions()

    print("=" * 70)
    print("✅ TODOS OS EXEMPLOS CONCLUÍDOS!")
    print("=" * 70)
    print("\nArquivos gerados em: examples/")
    print("  - dashboard_mock.html          (dados mockados)")
    print("  - dashboard_real.html          (dados reais, se ZIP disponível)")
    print("  - dashboard_xp_only.html       (filtrado por instituição)")
    print("  - dashboard_growing.html       (ativos em crescimento)")
    print("  - dashboard_top3.html          (top 3 instituições)")
    print("\nAbra qualquer arquivo em seu navegador para visualizar.")
    print()


if __name__ == '__main__':
    main()
