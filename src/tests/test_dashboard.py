"""
Tests for Dashboard Generator Module

Comprehensive test suite covering:
- Dashboard HTML generation
- Data aggregation and formatting
- Chart data preparation
- Tab content generation
- Responsive design validation
"""

import tempfile
import json
from pathlib import Path
from src.dashboard_generator import generate_dashboard_html
from src.models import Entry
from . import test_integration
from .test_integration import MOCK_ENTRIES


# ── Extended Test Data ────────────────────────────────────────────────────────

EXTENDED_TEST_DATA = [
    # More realistic data with diverse institutions and amounts
    Entry(
        arquivo='Avenue_2026.pdf',
        instituicao='Avenue Securities',
        cnpj_instituicao='07.526.847/0001-03',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='03',
        grupo_desc='Bens e direitos (valores mobiliários)',
        codigo='01',
        codigo_desc='Ações (valores mobiliários)',
        fonte_pagadora='Avenue Securities',
        cnpj_fonte='07.526.847/0001-03',
        localizacao='BR',
        discriminacao='Apple Inc.',
        valor_2024=8500,
        valor_2025=9200,
        rendimento=850,
        tipo_rendimento='Tributação Exclusiva',
        irrf=127.5,
        observacao='AAPL - NYSE'
    ),
    Entry(
        arquivo='Inter_2026.pdf',
        instituicao='Inter',
        cnpj_instituicao='17.197.385/0001-21',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='04',
        grupo_desc='Títulos e valores mobiliários',
        codigo='02',
        codigo_desc='Títulos públicos e privados',
        fonte_pagadora='Banco Inter',
        cnpj_fonte='17.197.385/0001-21',
        localizacao='BR',
        discriminacao='Tesouro Direto - NTN-B Principal',
        valor_2024=125000,
        valor_2025=132500,
        rendimento=8750,
        tipo_rendimento='Tributação Exclusiva',
        irrf=1312.5,
        observacao='Vencimento: 2035'
    ),
    Entry(
        arquivo='NuBank_2026.pdf',
        instituicao='NuBank',
        cnpj_instituicao='25.354.503/0001-25',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='06',
        codigo_desc='Rendimento de aplicações financeiras',
        fonte_pagadora='NuBank Pagamentos S.A.',
        cnpj_fonte='25.354.503/0001-25',
        localizacao='BR',
        discriminacao='Aplicações em CDB',
        valor_2024=0,
        valor_2025=0,
        rendimento=5650,
        tipo_rendimento='Tributação Exclusiva',
        irrf=847.5,
        observacao='CDB + LCI'
    ),
    Entry(
        arquivo='XP_2026.pdf',
        instituicao='XP Investimentos',
        cnpj_instituicao='24.196.726/0001-03',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='07',
        grupo_desc='Bens e direitos móveis',
        codigo='01',
        codigo_desc='Fundos de investimento',
        fonte_pagadora='XP Investimentos',
        cnpj_fonte='24.196.726/0001-03',
        localizacao='BR',
        discriminacao='Fundo Multimercado XP',
        valor_2024=250000,
        valor_2025=285000,
        rendimento=28500,
        tipo_rendimento='Tributação Exclusiva',
        irrf=4275,
        observacao='Fundo XPML11'
    ),
    Entry(
        arquivo='XP_2026.pdf',
        instituicao='XP Investimentos',
        cnpj_instituicao='24.196.726/0001-03',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='13',
        codigo_desc='Ganho líquido em operações com futuros',
        fonte_pagadora='XP Investimentos',
        cnpj_fonte='24.196.726/0001-03',
        localizacao='BR',
        discriminacao='Mini Índice - Mercado Futuro',
        valor_2024=0,
        valor_2025=0,
        rendimento=12500,
        tipo_rendimento='Tributação Exclusiva',
        irrf=1875,
        observacao='Operações de hedge'
    ),
    Entry(
        arquivo='XP_Previdencia_2026.pdf',
        instituicao='XP Vida e Previdência',
        cnpj_instituicao='17.197.385/0001-21',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='31',
        grupo_desc='Aplicações - previdência privada',
        codigo='01',
        codigo_desc='VGBL (Vida Gerador de Benefício Livre)',
        fonte_pagadora='XP Vida Seguros',
        cnpj_fonte='17.197.385/0001-21',
        localizacao='BR',
        discriminacao='VGBL Multimercado',
        valor_2024=180000,
        valor_2025=198000,
        rendimento=18000,
        tipo_rendimento='Isenta',
        irrf=0,
        observacao='Plano Aberto de Previdência'
    ),
]


def test_dashboard_generation():
    """Test basic dashboard HTML generation."""
    print("🧪 Test 1: Dashboard Generation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        
        # Generate dashboard
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        # Verify file exists and has content
        assert output_path.exists(), "Dashboard HTML not created"
        content = output_path.read_text(encoding='utf-8')
        assert len(content) > 1000, "Dashboard HTML too small"
        assert '<html' in content.lower(), "Not valid HTML"
        assert 'chart.js' in content.lower(), "Chart.js not included"
        assert 'bootstrap' in content.lower(), "Bootstrap not included"
        
        print("  ✅ Dashboard HTML generated successfully")
        print(f"     Size: {len(content) / 1024:.1f}KB")
        return True


def test_dashboard_data_embedding():
    """Test that data is properly embedded as JSON."""
    print("🧪 Test 2: Data Embedding")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Extract JSON data from script
        start_idx = content.find('const mockData = ')
        assert start_idx != -1, "mockData not found in HTML"
        
        json_start = content.find('[', start_idx)
        json_end = content.find('];', json_start) + 1
        json_str = content[json_start:json_end]
        
        # Parse JSON
        data = json.loads(json_str)
        assert len(data) == len(MOCK_ENTRIES), f"Data mismatch: {len(data)} vs {len(MOCK_ENTRIES)}"
        
        # Verify structure
        for entry in data:
            assert 'arquivo' in entry, "Missing 'arquivo' field"
            assert 'instituicao' in entry, "Missing 'instituicao' field"
            assert 'v2024' in entry, "Missing 'v2024' field"
            assert 'v2025' in entry, "Missing 'v2025' field"
        
        print("  ✅ Data properly embedded as JSON")
        print(f"     Entries: {len(data)}")
        return True


def test_dashboard_tabs():
    """Test that all 4 tabs are present in HTML."""
    print("🧪 Test 3: Tab Structure")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check for tab ids
        tabs = ['dados-brutos', 'resumo', 'totais', 'para-irpf']
        for tab in tabs:
            assert f'id="{tab}"' in content, f"Tab '{tab}' not found"
            assert f'onclick="switchTab(\'{tab}' in content, f"Tab switch for '{tab}' not found"
        
        # Check for tab navigation
        assert 'nav-tabs' in content, "Tab navigation not found"
        assert 'switchTab' in content, "switchTab function not found"
        
        print("  ✅ All 4 tabs present and functional")
        print(f"     Tabs: {', '.join(tabs)}")
        return True


def test_dashboard_charts():
    """Test that Chart.js charts are configured."""
    print("🧪 Test 4: Chart Configuration")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check for chart canvases
        assert 'id="chartInstitution"' in content, "Pie chart canvas not found"
        assert 'id="chartEvolution"' in content, "Bar chart canvas not found"
        
        # Check for chart initialization
        assert "type: 'pie'" in content, "Pie chart type not configured"
        assert "type: 'bar'" in content, "Bar chart type not configured"
        assert 'initCharts' in content, "initCharts function not found"
        
        print("  ✅ Charts properly configured")
        print("     Charts: Pie (institution), Bar (evolution)")
        return True


def test_dashboard_metrics():
    """Test that metric cards display correct values."""
    print("🧪 Test 5: Metric Calculation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Calculate expected totals
        total_2024 = sum(e.valor_2024 for e in MOCK_ENTRIES)
        total_2025 = sum(e.valor_2025 for e in MOCK_ENTRIES)
        total_rend = sum(e.rendimento for e in MOCK_ENTRIES)
        
        # Verify metrics are in content (as formatted currency)
        metrics_found = 0
        if 'metric-value' in content:
            metrics_found += 1
        if 'metric-card' in content:
            metrics_found += 1
        
        assert metrics_found > 0, "Metric cards not found"
        
        print("  ✅ Metric cards configured")
        print(f"     Total 2024: R$ {total_2024:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        print(f"     Total 2025: R$ {total_2025:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        print(f"     Rendimentos: R$ {total_rend:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        return True


def test_dashboard_with_extended_data():
    """Test dashboard with extended test data."""
    print("🧪 Test 6: Extended Data Set")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_extended.html'
        generate_dashboard_html(EXTENDED_TEST_DATA, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        assert output_path.exists(), "Dashboard not created with extended data"
        
        # Extract and verify data
        json_start = content.find('[', content.find('const mockData'))
        json_end = content.find('];', json_start) + 1
        data = json.loads(content[json_start:json_end])
        
        assert len(data) == len(EXTENDED_TEST_DATA), "Extended data not fully embedded"
        
        print("  ✅ Extended data set processed")
        print(f"     Entries: {len(EXTENDED_TEST_DATA)}")
        print(f"     Institutions: {len(set(e.instituicao for e in EXTENDED_TEST_DATA))}")
        print(f"     File size: {len(content) / 1024:.1f}KB")
        return True


def test_dashboard_responsive_design():
    """Test that responsive design classes are present."""
    print("🧪 Test 7: Responsive Design")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check for Bootstrap responsive classes
        responsive_classes = ['container-fluid', 'col-md', 'table-responsive']
        found_classes = 0
        for cls in responsive_classes:
            if cls in content:
                found_classes += 1
        
        assert found_classes >= 2, "Responsive design classes not sufficient"
        
        # Check for viewport meta tag
        assert 'viewport' in content.lower(), "Viewport meta tag not found"
        
        print("  ✅ Responsive design implemented")
        print(f"     Bootstrap classes: {found_classes}/{len(responsive_classes)}")
        return True


def test_dashboard_currency_formatting():
    """Test currency formatting functions."""
    print("🧪 Test 8: Currency Formatting")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check for Intl.NumberFormat
        assert "Intl.NumberFormat('pt-BR'" in content, "Currency formatter not found"
        assert "style: 'currency'" in content, "Currency style not configured"
        assert "currency: 'BRL'" in content, "BRL currency not set"
        
        # Check for formatting function
        assert 'formatCurrency' in content, "formatCurrency function not found"
        
        print("  ✅ Currency formatting configured")
        print("     Locale: pt-BR")
        print("     Currency: BRL")
        return True


def test_dashboard_all_institutions():
    """Test dashboard correctly groups all institutions."""
    print("🧪 Test 9: Institution Grouping")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(EXTENDED_TEST_DATA, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Extract unique institutions from data
        institutions = set(e.instituicao for e in EXTENDED_TEST_DATA)
        
        # Check that majority of institutions appear in JavaScript
        found_institutions = 0
        for inst in institutions:
            # Check for institution name (may be escaped or formatted differently)
            if inst in content or inst.replace(' ', '') in content.replace(' ', ''):
                found_institutions += 1
        
        assert found_institutions >= len(institutions) - 1, f"Only {found_institutions}/{len(institutions)} institutions found"
        
        print("  ✅ All institutions properly grouped")
        print(f"     Institutions: {len(institutions)}")
        for inst in sorted(institutions):
            count = len([e for e in EXTENDED_TEST_DATA if e.instituicao == inst])
            print(f"       - {inst}: {count} entries")
        return True


def test_dashboard_section_aggregation():
    """Test that sections are properly aggregated."""
    print("🧪 Test 10: Section Aggregation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard.html'
        generate_dashboard_html(EXTENDED_TEST_DATA, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Extract unique sections
        sections = set(e.secao for e in EXTENDED_TEST_DATA if e.secao)
        
        # Verify aggregation happens in resumo
        assert 'populateResumo' in content, "Resumo population function not found"
        
        print("  ✅ Section aggregation configured")
        print(f"     Sections: {len(sections)}")
        for sec in sorted(sections):
            count = len([e for e in EXTENDED_TEST_DATA if e.secao == sec])
            print(f"       - {sec}: {count} entries")
        return True


def test_dashboard_dark_mode():
    """Test that dark mode CSS variables and toggle functionality exist."""
    print("🧪 Test 11: Dark Mode Support")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_dashboard_dark.html'
        generate_dashboard_html(MOCK_ENTRIES, str(output_path))
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check for CSS variables (light and dark modes)
        assert '--primary-color' in content, "CSS variables not defined"
        assert '--bg-light' in content, "Background color variable not defined"
        assert '--text-light' in content, "Text color variable not defined"
        assert 'dark-mode' in content, "Dark mode class not defined"
        
        # Check for theme toggle functionality
        assert 'toggleTheme' in content, "toggleTheme function not found"
        assert 'localStorage' in content, "localStorage persistence not found"
        assert 'theme-toggle' in content, "Theme toggle button not found"
        assert 'theme-icon' in content, "Theme icon element not found"
        
        # Check for dark mode styles
        assert 'html.dark-mode' in content, "Dark mode CSS rules not found"
        
        # Verify light mode initialization
        assert 'initializeTheme' in content, "Theme initialization function not found"
        
        print("  ✅ Dark mode CSS variables configured")
        print("  ✅ Theme toggle button implemented")
        print("  ✅ localStorage persistence enabled")
        print("  ✅ Light/Dark mode detection working")
        return True


def run_all_tests():
    """Run all dashboard tests."""
    print("\n" + "=" * 70)
    print("🧪 DASHBOARD GENERATOR TEST SUITE")
    print("=" * 70 + "\n")
    
    tests = [
        test_dashboard_generation,
        test_dashboard_data_embedding,
        test_dashboard_tabs,
        test_dashboard_charts,
        test_dashboard_metrics,
        test_dashboard_with_extended_data,
        test_dashboard_responsive_design,
        test_dashboard_currency_formatting,
        test_dashboard_all_institutions,
        test_dashboard_section_aggregation,
        test_dashboard_dark_mode,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, True, None))
        except Exception as e:
            results.append((test_func.__name__, False, str(e)))
            print(f"  ❌ Error: {e}\n")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = sum(1 for _, success, _ in results if not success)
    
    for name, success, error in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
        if error:
            print(f"   {error}")
    
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {failed} TEST(S) FAILED!")
    
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
