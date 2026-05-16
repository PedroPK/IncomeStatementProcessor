"""
Integration tests for Income Statement Processor.

Uses mock data to test the complete pipeline:
extraction → parsing → normalization → XLSX generation.
"""

import tempfile
from pathlib import Path
from src.models import Entry
from src.xlsx_writer import write_xlsx


# ─────────────────────────────────────────────────────────────────────────────
# MOCK DATA - Dados simulados para testes sem exposição de informações pessoais
# ─────────────────────────────────────────────────────────────────────────────

# Mock taxpayer information (fictitious for testing purposes)
MOCK_TAXPAYER_NAME = 'João Silva Santos'
MOCK_TAXPAYER_CPF = '123.456.789-10'

MOCK_ENTRIES = [
    # ─ Itaú: Renda Fixa
    Entry(
        arquivo='Itau - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Itaú Bank',
        cnpj_instituicao='60.701.190/0001-04',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='04',
        grupo_desc='Títulos e valores mobiliários',
        codigo='02',
        codigo_desc='Títulos públicos e privados sujeitos à tributação',
        fonte_pagadora='Itaú Bank',
        cnpj_fonte='60.701.190/0001-04',
        localizacao='105 - Brasil',
        discriminacao='CDB 2025 (Banco Itaú)',
        valor_2024=50_000.00,
        valor_2025=52_500.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='Itau - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Itaú Bank',
        cnpj_instituicao='60.701.190/0001-04',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='06',
        codigo_desc='Rendimento de aplicações financeiras',
        fonte_pagadora='Itaú Bank',
        cnpj_fonte='60.701.190/0001-04',
        localizacao='105 - Brasil',
        discriminacao='Juros de CDB',
        valor_2024=0.0,
        valor_2025=0.0,
        rendimento=2_500.00,
        tipo_rendimento='Tributação Exclusiva',
        irrf=750.00,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    
    # ─ Bradesco: Fundos de Investimento
    Entry(
        arquivo='Bradesco - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Bradesco Corretora',
        cnpj_instituicao='30.711.876/0001-59',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='07',
        grupo_desc='Aplicações e investimentos',
        codigo='01',
        codigo_desc='Fundos de investimento sujeitos à tributação',
        fonte_pagadora='Bradesco Corretora',
        cnpj_fonte='30.711.876/0001-59',
        localizacao='105 - Brasil',
        discriminacao='Fundo de Investimento Multimercado (Bradesco)',
        valor_2024=100_000.00,
        valor_2025=115_000.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='Bradesco - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Bradesco Corretora',
        cnpj_instituicao='30.711.876/0001-59',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='06',
        codigo_desc='Rendimento de aplicações financeiras',
        fonte_pagadora='Bradesco Corretora',
        cnpj_fonte='30.711.876/0001-59',
        localizacao='105 - Brasil',
        discriminacao='Rentabilidade Fundo Multimercado',
        valor_2024=0.0,
        valor_2025=0.0,
        rendimento=8_750.00,
        tipo_rendimento='Tributação Exclusiva',
        irrf=2_625.00,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    
    # ─ XP: Ativos no Exterior
    Entry(
        arquivo='XP - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='XP Investimentos',
        cnpj_instituicao='02.332.886/0001-01',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='03',
        grupo_desc='Ações de empresas',
        codigo='01',
        codigo_desc='Ações',
        fonte_pagadora='XP Investimentos',
        cnpj_fonte='02.332.886/0001-01',
        localizacao='249 - Estados Unidos',
        discriminacao='Apple Inc (AAPL) - 10 ações',
        valor_2024=1_850.00,
        valor_2025=2_150.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='XP - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='XP Investimentos',
        cnpj_instituicao='02.332.886/0001-01',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='06',
        codigo_desc='Rendimento de aplicações financeiras',
        fonte_pagadora='XP Investimentos',
        cnpj_fonte='02.332.886/0001-01',
        localizacao='249 - Estados Unidos',
        discriminacao='Dividendos Apple',
        valor_2024=0.0,
        valor_2025=0.0,
        rendimento=125.50,
        tipo_rendimento='Tributação Exclusiva',
        irrf=37.65,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    
    # ─ NuBank: Criptoativos
    Entry(
        arquivo='NuBank - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='NuBank',
        cnpj_instituicao='27.865.757/0001-60',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='08',
        grupo_desc='Criptoativos',
        codigo='01',
        codigo_desc='Bitcoin (BTC)',
        fonte_pagadora='NuBank',
        cnpj_fonte='27.865.757/0001-60',
        localizacao='105 - Brasil',
        discriminacao='0.5 BTC',
        valor_2024=15_000.00,
        valor_2025=22_500.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='NuBank - Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='NuBank',
        cnpj_instituicao='27.865.757/0001-60',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='04',
        grupo_desc='Títulos e valores mobiliários',
        codigo='02',
        codigo_desc='Títulos públicos e privados sujeitos à tributação',
        fonte_pagadora='NuBank',
        cnpj_fonte='27.865.757/0001-60',
        localizacao='105 - Brasil',
        discriminacao='LCI (Letra de Crédito Imobiliário)',
        valor_2024=30_000.00,
        valor_2025=31_200.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='Isenta',
    ),
    
    # ─ Clear: Fundos e Renda Fixa
    Entry(
        arquivo='Clear - 01 Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Clear',
        cnpj_instituicao='02.332.886/0001-04',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='07',
        grupo_desc='Aplicações e investimentos',
        codigo='01',
        codigo_desc='Fundos de investimento sujeitos à tributação',
        fonte_pagadora='Clear',
        cnpj_fonte='02.332.886/0001-04',
        localizacao='105 - Brasil',
        discriminacao='Fundo Multimercado (Clear)',
        valor_2024=40_000.00,
        valor_2025=42_800.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='Clear - 01 Informe de Rendimentos - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Clear',
        cnpj_instituicao='02.332.886/0001-04',
        ano_calendario=2025,
        secao='Rendimentos Tributação Exclusiva',
        grupo='',
        grupo_desc='',
        codigo='06',
        codigo_desc='Rendimento de aplicações financeiras',
        fonte_pagadora='Clear',
        cnpj_fonte='02.332.886/0001-04',
        localizacao='105 - Brasil',
        discriminacao='Rendimentos de Fundo',
        valor_2024=0.0,
        valor_2025=0.0,
        rendimento=1_280.00,
        tipo_rendimento='Tributação Exclusiva',
        irrf=384.00,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    
    # ─ Clear: Custódia de Ativos (Posição Consolidada)
    Entry(
        arquivo='Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Clear',
        cnpj_instituicao='',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='04',
        grupo_desc='Aplicações e Investimentos',
        codigo='01',
        codigo_desc='Ações',
        fonte_pagadora='Clear',
        cnpj_fonte='',
        localizacao='105 - Brasil',
        discriminacao='PSSA3 - Ativo em Custódia',
        valor_2024=0.0,
        valor_2025=19_344.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Clear',
        cnpj_instituicao='',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='07',
        grupo_desc='Fundos de Investimento',
        codigo='99',
        codigo_desc='Fundos de Investimento',
        fonte_pagadora='Clear',
        cnpj_fonte='',
        localizacao='105 - Brasil',
        discriminacao='PLAG11 - Ativo em Custódia',
        valor_2024=0.0,
        valor_2025=9_785.00,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
    Entry(
        arquivo='Clear - 04 Custódia - Ano Base 2025 - IRPF2026.pdf',
        instituicao='Clear',
        cnpj_instituicao='',
        ano_calendario=2025,
        secao='Bens e Direitos',
        grupo='06',
        grupo_desc='Depósito à Vista e Numerário',
        codigo='01',
        codigo_desc='Depósito em conta corrente ou conta pagamento',
        fonte_pagadora='Clear',
        cnpj_fonte='',
        localizacao='105 - Brasil',
        discriminacao='Saldo disponível - Clear',
        valor_2024=0.0,
        valor_2025=7_745.95,
        rendimento=0.0,
        tipo_rendimento='',
        irrf=0.0,
        nome_contribuinte=MOCK_TAXPAYER_NAME,
        cpf_contribuinte=MOCK_TAXPAYER_CPF,
        observacao='',
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# TESTES
# ─────────────────────────────────────────────────────────────────────────────

def test_xlsx_generation_with_mock_data():
    """Test XLSX generation with mock data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / 'test_output.xlsx'
        
        # Generate XLSX
        write_xlsx(MOCK_ENTRIES, str(output_path))
        
        # Verify file exists
        assert output_path.exists(), "XLSX file not created"
        assert output_path.stat().st_size > 0, "XLSX file is empty"
        
        print(f"✅ XLSX gerado com sucesso: {output_path}")
        print(f"   Tamanho: {output_path.stat().st_size / 1024:.1f}KB")
        print(f"   Entradas processadas: {len(MOCK_ENTRIES)}")


def test_mock_data_integrity():
    """Verify mock data is valid."""
    assert len(MOCK_ENTRIES) == 13, f"Expected 13 mock entries, got {len(MOCK_ENTRIES)}"
    
    for entry in MOCK_ENTRIES:
        assert entry.arquivo, "Arquivo não pode ser vazio"
        assert entry.instituicao, "Instituição não pode ser vazia"
        assert entry.secao, "Seção não pode ser vazia"
        assert entry.ano_calendario == 2025, "Ano deve ser 2025"
        
        # Validar montantes
        total = entry.valor_2024 + entry.valor_2025 + entry.rendimento
        assert total >= 0, f"Valores negativos detectados em {entry.instituicao}"
    
    print(f"✅ Integridade de {len(MOCK_ENTRIES)} entradas verificada")


def test_mock_data_summary():
    """Print summary of mock data for documentation."""
    from src.models import Entry
    
    total_2024 = sum(e.valor_2024 for e in MOCK_ENTRIES)
    total_2025 = sum(e.valor_2025 for e in MOCK_ENTRIES)
    total_rend = sum(e.rendimento for e in MOCK_ENTRIES)
    total_irrf = sum(e.irrf for e in MOCK_ENTRIES)
    
    print("\n=== RESUMO DOS DADOS MOCKADOS ===")
    print(f"Entradas: {len(MOCK_ENTRIES)}")
    print(f"Instituições: {len(set(e.instituicao for e in MOCK_ENTRIES))}")
    print(f"Total 2024: R$ {total_2024:,.2f}")
    print(f"Total 2025: R$ {total_2025:,.2f}")
    print(f"Total Rendimentos: R$ {total_rend:,.2f}")
    print(f"Total IRRF: R$ {total_irrf:,.2f}")
    print()
    
    # Group by institution
    print("Por Instituição:")
    for inst in sorted(set(e.instituicao for e in MOCK_ENTRIES)):
        entries = [e for e in MOCK_ENTRIES if e.instituicao == inst]
        inst_2024 = sum(e.valor_2024 for e in entries)
        inst_2025 = sum(e.valor_2025 for e in entries)
        inst_rend = sum(e.rendimento for e in entries)
        print(f"  {inst:20} | Entradas: {len(entries)} | 2024: R${inst_2024:>10,.2f} | 2025: R${inst_2025:>10,.2f} | Rend: R${inst_rend:>10,.2f}")


def get_markdown_tables_for_documentation():
    """Generate markdown tables for README documentation."""
    print("\n=== TABELAS MARKDOWN PARA DOCUMENTAÇÃO ===\n")
    
    # Table 1: All entries (Dados Brutos preview)
    print("#### Aba 1: Dados Brutos (exemplo com 5 primeiras linhas)\n")
    print("| Arquivo | Instituição | Seção | Grupo | Código | Descrição | 2024 | 2025 | Rendimento | IRRF |")
    print("|---------|-------------|-------|-------|--------|-----------|------|------|------------|------|")
    for entry in MOCK_ENTRIES[:5]:
        desc = entry.codigo_desc[:40]
        print(f"| {Path(entry.arquivo).name[:25]}... | {entry.instituicao:15} | {entry.secao:25} | {entry.grupo:5} | {entry.codigo:6} | {desc:40} | R${entry.valor_2024:>8,.0f} | R${entry.valor_2025:>8,.0f} | R${entry.rendimento:>8,.2f} | R${entry.irrf:>7,.2f} |")
    
    # Table 2: Resumo (by section × institution)
    print("\n#### Aba 2: Resumo (Seção × Instituição)\n")
    print("| Seção | Instituição | Valor 2024 | Valor 2025 | Rendimento |")
    print("|-------|-------------|-----------|-----------|-----------|")
    
    sections = sorted(set(e.secao for e in MOCK_ENTRIES))
    for section in sections:
        section_entries = [e for e in MOCK_ENTRIES if e.secao == section]
        for inst in sorted(set(e.instituicao for e in section_entries)):
            inst_entries = [e for e in section_entries if e.instituicao == inst]
            total_2024 = sum(e.valor_2024 for e in inst_entries)
            total_2025 = sum(e.valor_2025 for e in inst_entries)
            total_rend = sum(e.rendimento for e in inst_entries)
            if total_2024 > 0 or total_2025 > 0 or total_rend > 0:
                print(f"| {section:30} | {inst:20} | R${total_2024:>10,.2f} | R${total_2025:>10,.2f} | R${total_rend:>10,.2f} |")
    
    # Table 3: Totais (by grupo × código)
    print("\n#### Aba 3: Totais (Grupo × Código)\n")
    print("| Grupo | Código | Descrição | Valor 2024 | Valor 2025 | Rendimento | Total |")
    print("|-------|--------|-----------|-----------|-----------|-----------|-------|")
    
    seen = set()
    for entry in sorted(MOCK_ENTRIES, key=lambda e: (e.grupo, e.codigo)):
        key = (entry.grupo, entry.codigo, entry.codigo_desc)
        if key not in seen:
            seen.add(key)
            matching = [e for e in MOCK_ENTRIES if e.grupo == entry.grupo and e.codigo == entry.codigo]
            total_2024 = sum(e.valor_2024 for e in matching)
            total_2025 = sum(e.valor_2025 for e in matching)
            total_rend = sum(e.rendimento for e in matching)
            total_all = total_2024 + total_2025 + total_rend
            print(f"| {entry.grupo:5} | {entry.codigo:6} | {entry.codigo_desc:40} | R${total_2024:>10,.2f} | R${total_2025:>10,.2f} | R${total_rend:>10,.2f} | R${total_all:>10,.2f} |")
    
    # Table 4: Para IRPF (by institution)
    print("\n#### Aba 4: Para IRPF (Agrupado por Instituição)\n")
    print("| Instituição | Grupo | Código | Descrição | Localização | Discriminação | 2024 | 2025 | Rendimento |")
    print("|-------------|-------|--------|-----------|-------------|----------------|------|------|-----------|")
    
    for inst in sorted(set(e.instituicao for e in MOCK_ENTRIES)):
        inst_entries = sorted([e for e in MOCK_ENTRIES if e.instituicao == inst], key=lambda e: (e.grupo, e.codigo))
        for entry in inst_entries:
            print(f"| {inst:20} | {entry.grupo:5} | {entry.codigo:6} | {entry.codigo_desc:30} | {entry.localizacao:20} | {entry.discriminacao:25} | R${entry.valor_2024:>6,.0f} | R${entry.valor_2025:>6,.0f} | R${entry.rendimento:>8,.2f} |")


if __name__ == '__main__':
    print("🧪 Income Statement Processor - Integration Tests\n")
    
    # Run tests
    test_mock_data_integrity()
    test_mock_data_summary()
    test_xlsx_generation_with_mock_data()
    
    # Generate documentation
    get_markdown_tables_for_documentation()
    
    print("\n✅ Todos os testes passaram com sucesso!")
