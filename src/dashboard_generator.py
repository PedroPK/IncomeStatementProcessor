"""
Generate interactive HTML dashboard from Income Statement Processor data.

This script creates a bootstrap-based dashboard with charts and tables
from either real XLSX data or mock test data.
"""

import json
from pathlib import Path
from src.models import Entry


def format_currency(value: float) -> str:
    """Format value as Brazilian currency."""
    return f"R$ {value:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')


def generate_dashboard_html(entries: list, output_path: str = 'dashboard.html') -> None:
    """
    Generate interactive dashboard from entries.
    
    Args:
        entries: List of Entry objects
        output_path: Path to write HTML dashboard
    """
    
    # Prepare data for JSON embedding
    data_json = []
    for entry in entries:
        data_json.append({
            'arquivo': Path(entry.arquivo).name[:40],
            'instituicao': entry.instituicao,
            'secao': entry.secao,
            'grupo': entry.grupo,
            'codigo': entry.codigo,
            'descricao': entry.codigo_desc,
            'v2024': entry.valor_2024,
            'v2025': entry.valor_2025,
            'rendimento': entry.rendimento,
            'irrf': entry.irrf
        })
    
    # Calculate metrics
    total_2024 = sum(e.valor_2024 for e in entries)
    total_2025 = sum(e.valor_2025 for e in entries)
    total_rendimento = sum(e.rendimento for e in entries)
    total_irrf = sum(e.irrf for e in entries)
    
    # Generate HTML
    html_content = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Income Statement Processor - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .navbar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}
        .metric-card {{
            border-left: 4px solid #667eea;
            padding: 20px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .nav-tabs .nav-link {{
            color: #667eea;
            border: none;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
        }}
        .nav-tabs .nav-link.active {{
            color: #667eea;
            background-color: transparent;
            border-bottom: 2px solid #667eea;
        }}
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        table {{
            font-size: 13px;
        }}
        thead {{
            background-color: #f0f0f0;
            font-weight: 600;
        }}
        .currency {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}
        .section-header {{
            background-color: #667eea;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin-top: 15px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        .total-row {{
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-dark mb-4">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">📊 Income Statement Processor</span>
            <span class="navbar-text text-white-50">Dashboard - IRPF 2026</span>
        </div>
    </nav>

    <div class="container-fluid">
        <!-- Key Metrics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_2024)}</div>
                    <div class="metric-label">Total 2024</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_2025)}</div>
                    <div class="metric-label">Total 2025</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{format_currency(total_rendimento)}</div>
                    <div class="metric-label">Rendimentos</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{len(entries)}</div>
                    <div class="metric-label">Entradas Processadas</div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="card-title">Distribuição por Instituição (2025)</h6>
                    <div class="chart-container">
                        <canvas id="chartInstitution"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-3">
                    <h6 class="card-title">Evolução 2024 → 2025</h6>
                    <div class="chart-container">
                        <canvas id="chartEvolution"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabs Section -->
        <div class="card">
            <div class="card-body">
                <!-- Tab Navigation -->
                <ul class="nav nav-tabs mb-3" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active" href="#" onclick="switchTab('dados-brutos', event)">📋 Dados Brutos</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('resumo', event)">📈 Resumo</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('totais', event)">💰 Totais</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" onclick="switchTab('para-irpf', event)">📝 Para IRPF</a>
                    </li>
                </ul>

                <!-- Tab 1: Dados Brutos -->
                <div id="dados-brutos" class="tab-content active">
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>Arquivo</th>
                                    <th>Instituição</th>
                                    <th>Seção</th>
                                    <th>Grupo</th>
                                    <th>Código</th>
                                    <th>Descrição</th>
                                    <th class="currency">2024</th>
                                    <th class="currency">2025</th>
                                    <th class="currency">Rendimento</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-brutos"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Tab 2: Resumo -->
                <div id="resumo" class="tab-content">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Seção</th>
                                    <th>Instituição</th>
                                    <th class="currency">Valor 2024</th>
                                    <th class="currency">Valor 2025</th>
                                    <th class="currency">Rendimento</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-resumo"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Tab 3: Totais -->
                <div id="totais" class="tab-content">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Grupo</th>
                                    <th>Código</th>
                                    <th>Descrição</th>
                                    <th class="currency">2024</th>
                                    <th class="currency">2025</th>
                                    <th class="currency">Rendimento</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-totais"></tbody>
                        </table>
                    </div>
                </div>

                <!-- Tab 4: Para IRPF -->
                <div id="para-irpf" class="tab-content">
                    <div id="irpf-content"></div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="text-center mt-5 mb-3 text-muted">
            <small>
                Income Statement Processor v1.0.1 | 
                Gerado em 2026-05-02
            </small>
        </footer>
    </div>

    <script>
        // Data embedded in HTML
        const mockData = {json.dumps(data_json)};

        // Format currency
        function formatCurrency(value) {{
            return new Intl.NumberFormat('pt-BR', {{
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 2
            }}).format(value);
        }}

        // Tab switching
        function switchTab(tabName, event) {{
            event.preventDefault();
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            event.target.classList.add('active');
        }}

        // Populate Dados Brutos
        function populateDadosBrutos() {{
            const tbody = document.getElementById('tbody-brutos');
            mockData.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><small>${{row.arquivo}}</small></td>
                    <td><strong>${{row.instituicao}}</strong></td>
                    <td>${{row.secao}}</td>
                    <td>${{row.grupo || '-'}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.descricao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        // Populate Resumo
        function populateResumo() {{
            const tbody = document.getElementById('tbody-resumo');
            const resumoData = {{}};

            mockData.forEach(row => {{
                const key = `${{row.secao}}|${{row.instituicao}}`;
                if (!resumoData[key]) {{
                    resumoData[key] = {{ secao: row.secao, inst: row.instituicao, v2024: 0, v2025: 0, rend: 0 }};
                }}
                resumoData[key].v2024 += row.v2024;
                resumoData[key].v2025 += row.v2025;
                resumoData[key].rend += row.rendimento;
            }});

            Object.values(resumoData).sort((a, b) => a.secao.localeCompare(b.secao)).forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.secao}}</td>
                    <td>${{row.inst}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rend)}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        // Populate Totais
        function populateTotais() {{
            const tbody = document.getElementById('tbody-totais');
            const totaisData = {{}};

            mockData.forEach(row => {{
                const key = `${{row.grupo}}|${{row.codigo}}|${{row.descricao}}`;
                if (!totaisData[key]) {{
                    totaisData[key] = {{ grupo: row.grupo, codigo: row.codigo, desc: row.descricao, v2024: 0, v2025: 0, rend: 0 }};
                }}
                totaisData[key].v2024 += row.v2024;
                totaisData[key].v2025 += row.v2025;
                totaisData[key].rend += row.rendimento;
            }});

            const sorted = Object.values(totaisData).sort((a, b) => {{
                if (a.grupo !== b.grupo) return (a.grupo || 'zzz').localeCompare(b.grupo || 'zzz');
                return a.codigo.localeCompare(b.codigo);
            }});

            let totalGeral2024 = 0, totalGeral2025 = 0, totalGeralRend = 0;

            sorted.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.grupo || '-'}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.desc}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rend)}}</td>
                `;
                tbody.appendChild(tr);

                totalGeral2024 += row.v2024;
                totalGeral2025 += row.v2025;
                totalGeralRend += row.rend;
            }});

            // Total Row
            const trTotal = document.createElement('tr');
            trTotal.className = 'total-row';
            trTotal.innerHTML = `
                <td colspan="3"><strong>TOTAL GERAL</strong></td>
                <td class="currency"><strong>${{formatCurrency(totalGeral2024)}}</strong></td>
                <td class="currency"><strong>${{formatCurrency(totalGeral2025)}}</strong></td>
                <td class="currency"><strong>${{formatCurrency(totalGeralRend)}}</strong></td>
            `;
            tbody.appendChild(trTotal);
        }}

        // Populate Para IRPF
        function populaParaIRPF() {{
            const container = document.getElementById('irpf-content');
            const irpfData = {{}};

            mockData.forEach(row => {{
                if (!irpfData[row.instituicao]) {{
                    irpfData[row.instituicao] = {{}};
                }}
                if (!irpfData[row.instituicao][row.secao]) {{
                    irpfData[row.instituicao][row.secao] = [];
                }}
                irpfData[row.instituicao][row.secao].push(row);
            }});

            let html = '';
            let totalAllInst2024 = 0, totalAllInst2025 = 0, totalAllInstRend = 0;

            Object.keys(irpfData).sort().forEach(inst => {{
                let instTotal2024 = 0, instTotal2025 = 0, instTotalRend = 0;
                html += `<div class="section-header">${{inst}}</div>`;
                html += '<table class="table table-sm"><thead><tr><th>Seção</th><th>Grupo</th><th>Código</th><th>Descrição</th><th class="currency">2024</th><th class="currency">2025</th><th class="currency">Rendimento</th></tr></thead><tbody>';

                Object.keys(irpfData[inst]).sort().forEach(secao => {{
                    irpfData[inst][secao].forEach(row => {{
                        html += `<tr><td>${{row.secao}}</td><td>${{row.grupo || '-'}}</td><td>${{row.codigo}}</td><td>${{row.descricao}}</td><td class="currency">${{formatCurrency(row.v2024)}}</td><td class="currency">${{formatCurrency(row.v2025)}}</td><td class="currency">${{formatCurrency(row.rendimento)}}</td></tr>`;
                        instTotal2024 += row.v2024;
                        instTotal2025 += row.v2025;
                        instTotalRend += row.rendimento;
                    }});
                }});

                html += `<tr style="background-color: #e8e8e8;"><td colspan="4"><strong>Subtotal ${{inst}}</strong></td><td class="currency">${{formatCurrency(instTotal2024)}}</td><td class="currency">${{formatCurrency(instTotal2025)}}</td><td class="currency">${{formatCurrency(instTotalRend)}}</td></tr>`;
                html += '</tbody></table>';

                totalAllInst2024 += instTotal2024;
                totalAllInst2025 += instTotal2025;
                totalAllInstRend += instTotalRend;
            }});

            html += `<div class="section-header mt-4">TOTAL GERAL</div>`;
            html += `<p><strong>2024:</strong> ${{formatCurrency(totalAllInst2024)}} | <strong>2025:</strong> ${{formatCurrency(totalAllInst2025)}} | <strong>Rendimentos:</strong> ${{formatCurrency(totalAllInstRend)}}</p>`;

            container.innerHTML = html;
        }}

        // Initialize Charts
        function initCharts() {{
            // Chart 1: Distribution by Institution
            const instData = {{}};
            mockData.forEach(row => {{
                if (!instData[row.instituicao]) instData[row.instituicao] = 0;
                instData[row.instituicao] += row.v2025;
            }});

            new Chart(document.getElementById('chartInstitution'), {{
                type: 'pie',
                data: {{
                    labels: Object.keys(instData),
                    datasets: [{{
                        data: Object.values(instData),
                        backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'bottom' }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return formatCurrency(context.parsed);
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Chart 2: Evolution 2024 vs 2025
            const secaoData = {{}};
            mockData.forEach(row => {{
                if (!secaoData[row.instituicao]) secaoData[row.instituicao] = {{ 2024: 0, 2025: 0 }};
                secaoData[row.instituicao]['2024'] += row.v2024;
                secaoData[row.instituicao]['2025'] += row.v2025;
            }});

            new Chart(document.getElementById('chartEvolution'), {{
                type: 'bar',
                data: {{
                    labels: Object.keys(secaoData),
                    datasets: [
                        {{
                            label: '2024',
                            data: Object.values(secaoData).map(d => d['2024']),
                            backgroundColor: '#667eea'
                        }},
                        {{
                            label: '2025',
                            data: Object.values(secaoData).map(d => d['2025']),
                            backgroundColor: '#764ba2'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{ beginAtZero: true, ticks: {{ callback: v => formatCurrency(v) }} }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return formatCurrency(context.parsed.y);
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            populateDadosBrutos();
            populateResumo();
            populateTotais();
            populaParaIRPF();
            initCharts();
        }});
    </script>
</body>
</html>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard gerado: {output_path}")
    print(f"   Entradas: {len(entries)}")
    print(f"   Total 2024: {format_currency(total_2024)}")
    print(f"   Total 2025: {format_currency(total_2025)}")
    print(f"   Total Rendimentos: {format_currency(total_rendimento)}")


if __name__ == '__main__':
    # Example: Generate from test_integration mock data
    from test_integration import MOCK_ENTRIES
    
    generate_dashboard_html(MOCK_ENTRIES, 'dashboard.html')
    print("\n💡 Abra 'dashboard.html' em seu navegador para visualizar o dashboard!")
