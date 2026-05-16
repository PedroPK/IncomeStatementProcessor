"""
Generate interactive HTML dashboard from Income Statement Processor data.

This script creates a bootstrap-based dashboard with charts and tables
from either real XLSX data or mock test data, with light/dark mode support.
"""

import json
import tomllib
from datetime import datetime
from pathlib import Path
from src.models import Entry


def load_dashboard_config() -> dict:
    """Load dashboard configuration from config.toml."""
    config_path = Path('config.toml')
    if config_path.exists():
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
            return config.get('dashboard', {})
    return {}


def truncate_label(label: str, config: dict) -> str:
    """
    Truncate label based on configuration.
    
    Args:
        label: Original label text
        config: Dashboard configuration dictionary
        
    Returns:
        Truncated label
    """
    mode = config.get('label_truncation_mode', 'separator')
    value = config.get('label_truncation_value', 'LTDA')
    add_ellipsis = config.get('label_add_ellipsis', True)
    
    truncated = label
    
    if mode == 'max_length':
        # Truncate by maximum length
        max_len = int(value) if isinstance(value, (int, str)) else 30
        if len(label) > max_len:
            truncated = label[:max_len]
    elif mode == 'separator':
        # Truncate at separator
        if value in label:
            truncated = label[:label.index(value) + len(value)].strip()
    
    # Add ellipsis if truncated and configured
    if add_ellipsis and truncated != label:
        truncated += '...'
    
    return truncated


def format_currency(value: float) -> str:
    """Format value as Brazilian currency."""
    return f"R$ {value:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')


def generate_dashboard_html(entries: list, output_path: str = 'dashboard.html') -> None:
    """
    Generate interactive dashboard from entries with dark mode support.
    
    Args:
        entries: List of Entry objects
        output_path: Path to write HTML dashboard
    """
    
    # Load dashboard configuration
    dashboard_config = load_dashboard_config()
    
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
            'discriminacao': entry.discriminacao,
            'v2024': entry.valor_2024,
            'v2025': entry.valor_2025,
            'rendimento': entry.rendimento,
            'irrf': entry.irrf
        })
    
    # Generate timestamp
    generated_at = datetime.now().strftime('%d/%m/%Y às %H:%M')

    # Extract taxpayer information (should be the same for all entries)
    nome_contribuinte = ""
    cpf_contribuinte = ""
    for entry in entries:
        if entry.nome_contribuinte or entry.cpf_contribuinte:
            nome_contribuinte = entry.nome_contribuinte or ""
            cpf_contribuinte = entry.cpf_contribuinte or ""
            break

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
        :root {{
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --bg-light: #f8f9fa;
            --bg-light-card: #ffffff;
            --text-light: #333333;
            --text-muted: #999999;
            --border-light: #e9ecef;
            --table-header-light: #f0f0f0;
        }}
        
        html.dark-mode {{
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --bg-light: #1a1a1a;
            --bg-light-card: #2d2d2d;
            --text-light: #e0e0e0;
            --text-muted: #999999;
            --border-light: #3d3d3d;
            --table-header-light: #3d3d3d;
        }}
        
        * {{
            transition: background-color 0.3s, color 0.3s;
        }}
        
        body {{
            background-color: var(--bg-light);
            color: var(--text-light);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .navbar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            background-color: #667eea !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .navbar-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            padding: 0 15px;
        }}
        
        .navbar-title {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .theme-toggle {{
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.3);
            box-shadow: 0 0 10px rgba(255,255,255,0.2);
        }}
        
        .card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            background-color: var(--bg-light-card);
            color: var(--text-light);
            border: 1px solid var(--border-light);
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}
        
        .metric-card {{
            border-left: 4px solid var(--primary-color);
            padding: 20px;
        }}
        
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: var(--primary-color);
        }}
        
        .metric-label {{
            font-size: 12px;
            color: var(--text-muted);
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
            color: var(--text-muted);
            border: none;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
        }}
        
        .nav-tabs .nav-link.active {{
            color: var(--primary-color);
            background-color: transparent;
            border-bottom: 2px solid var(--primary-color);
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        
        #chartInstitution {{
            min-height: 350px !important;
        }}
        
        table {{
            font-size: 13px;
            background-color: var(--bg-light-card);
            color: var(--text-light);
        }}
        
        thead {{
            background-color: var(--table-header-light) !important;
            font-weight: 600;
            color: var(--text-light) !important;
            border-color: var(--border-light) !important;
        }}
        
        tbody tr {{
            background-color: var(--bg-light-card) !important;
            color: var(--text-light) !important;
            border-color: var(--border-light) !important;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: var(--bg-light-card) !important;
        }}
        
        html.dark-mode tbody tr {{
            background-color: #2d2d2d !important;
        }}
        
        html.dark-mode tbody tr:nth-child(even) {{
            background-color: #353535 !important;
        }}
        
        tbody tr:hover {{
            background-color: var(--border-light) !important;
            cursor: pointer;
        }}
        
        tbody td {{
            border-color: var(--border-light) !important;
            color: var(--text-light) !important;
        }}
        
        table.table-striped tbody tr:nth-child(odd) td {{
            background-color: var(--bg-light-card) !important;
        }}
        
        table.table-striped tbody tr:nth-child(even) td {{
            background-color: var(--bg-light-card) !important;
        }}
        
        html.dark-mode table.table-striped tbody tr:nth-child(odd) td {{
            background-color: #2d2d2d !important;
        }}
        
        html.dark-mode table.table-striped tbody tr:nth-child(even) td {{
            background-color: #353535 !important;
        }}
        
        .currency {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}
        
        .section-header {{
            background-color: var(--primary-color);
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin-top: 15px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .total-row {{
            background-color: var(--primary-color);
            color: white;
            font-weight: bold;
        }}
        
        .navbar-brand {{
            color: white !important;
            font-weight: bold;
            margin: 0;
        }}
        
        .navbar-text {{
            color: rgba(255,255,255,0.8) !important;
            margin: 0;
        }}
        
        .generated-at {{
            font-size: 0.82rem;
            text-align: right;
            color: #666666;
        }}
        
        html.dark-mode .generated-at {{
            color: #aaaaaa;
        }}
        
        .container-fluid {{
            background-color: var(--bg-light);
        }}
        
        footer {{
            color: var(--text-muted);
            border-top: 1px solid var(--border-light);
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <!-- Navigation -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.2); padding: 12px 0 6px 0; margin-bottom: 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; padding: 0 20px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="color:#ffffff; font-weight:bold; font-size:1.5rem;">📊 Income Statement Processor</span>
                <span style="color:rgba(255,255,255,0.85); font-size:1rem;">Dashboard - IRPF 2026</span>
            </div>
            <button class="theme-toggle" onclick="toggleTheme()">
                <span id="theme-icon">🌙 Dark Mode</span>
            </button>
        </div>
        <div style="text-align:right; padding: 4px 20px 0 20px;">
            <span style="font-size:0.78rem; color:rgba(255,255,255,0.75);">Gerado em {generated_at}</span>
        </div>
    </div>

    <div class="container-fluid mt-2">

        <!-- Taxpayer Information Card -->
        {f'''
        <div class="row mb-4">
            <div class="col-12">
                <div class="card p-3" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-left: 4px solid #667eea;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h5 style="margin: 0; color: var(--primary-color); font-weight: 600;">
                                👤 Contribuinte
                            </h5>
                            <div style="margin-top: 12px; display: flex; gap: 30px;">
                                <div>
                                    <p style="margin: 0; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase;">Nome</p>
                                    <p style="margin: 5px 0 0 0; font-size: 1rem; font-weight: 500; color: var(--text-light);">
                                        {nome_contribuinte or "Não informado"}
                                    </p>
                                </div>
                                <div>
                                    <p style="margin: 0; font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase;">CPF</p>
                                    <p style="margin: 5px 0 0 0; font-size: 1rem; font-weight: 500; color: var(--text-light); font-family: 'Courier New', monospace;">
                                        {cpf_contribuinte or "Não informado"}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div style="text-align: right; padding-right: 10px;">
                            <div style="font-size: 3rem; opacity: 0.3;">📋</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        ''' if nome_contribuinte or cpf_contribuinte else ''}

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
        <footer class="text-center mt-5 mb-3">
            <small>
                Income Statement Processor v1.1.0 | 
                Gerado em 2026-05-02 | 
                Com suporte a Dark Mode 🌙
            </small>
        </footer>
    </div>

    <script>
        // Data embedded in HTML
        const mockData = {json.dumps(data_json)};
        const dashboardConfig = {json.dumps(dashboard_config)};

        // Utility function to truncate labels based on configuration
        function truncateLabel(label, config) {{
            const mode = config.label_truncation_mode || 'separator';
            const value = config.label_truncation_value || 'LTDA';
            const addEllipsis = config.label_add_ellipsis !== false;
            
            let truncated = label;
            
            if (mode === 'max_length') {{
                const maxLen = parseInt(value) || 30;
                if (label.length > maxLen) {{
                    truncated = label.substring(0, maxLen);
                }}
            }} else if (mode === 'separator') {{
                const idx = label.indexOf(value);
                if (idx !== -1) {{
                    truncated = label.substring(0, idx + value.length).trim();
                }}
            }}
            
            if (addEllipsis && truncated !== label) {{
                truncated += '...';
            }}
            
            return truncated;
        }}

        // Theme Management
        window.appTheme = 'light'; // In-memory theme tracker for file:// URLs
        
        function initializeTheme() {{
            let savedTheme = 'light';
            try {{
                savedTheme = localStorage.getItem('dashboard-theme') || 'light';
            }} catch(e) {{
                console.log('localStorage not available, using in-memory theme');
            }}
            window.appTheme = savedTheme;
            if (savedTheme === 'dark') {{
                document.documentElement.classList.add('dark-mode');
                document.getElementById('theme-icon').textContent = '☀️ Light Mode';
            }}
        }}
        
        function toggleTheme() {{
            const html = document.documentElement;
            const isDark = html.classList.contains('dark-mode');
            
            if (isDark) {{
                html.classList.remove('dark-mode');
                window.appTheme = 'light';
                try {{
                    localStorage.setItem('dashboard-theme', 'light');
                }} catch(e) {{}}
                document.getElementById('theme-icon').textContent = '🌙 Dark Mode';
                updateCharts('light');
            }} else {{
                html.classList.add('dark-mode');
                window.appTheme = 'dark';
                try {{
                    localStorage.setItem('dashboard-theme', 'dark');
                }} catch(e) {{}}
                document.getElementById('theme-icon').textContent = '☀️ Light Mode';
                updateCharts('dark');
            }}
        }}

        // Format currency
        function formatCurrency(value) {{
            return new Intl.NumberFormat('pt-BR', {{
                style: 'currency',
                currency: 'BRL'
            }}).format(value);
        }}

        // Tab Switching
        function switchTab(tabName, event) {{
            event.preventDefault();
            
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Remove active from all links
            const links = document.querySelectorAll('.nav-link');
            links.forEach(link => link.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}

        // Populate tabs
        function populateTabs() {{
            // Tab 1: Dados Brutos
            const tbody = document.getElementById('tbody-brutos');
            mockData.forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.arquivo}}</td>
                    <td>${{row.instituicao}}</td>
                    <td>${{row.secao}}</td>
                    <td>${{row.grupo}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.descricao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbody.appendChild(tr);
            }});

            // Tab 2: Resumo
            const resumo = {{}};
            mockData.forEach(row => {{
                const key = row.secao + '|' + row.instituicao;
                if (!resumo[key]) {{
                    resumo[key] = {{
                        secao: row.secao,
                        instituicao: row.instituicao,
                        v2024: 0,
                        v2025: 0,
                        rendimento: 0
                    }};
                }}
                resumo[key].v2024 += row.v2024;
                resumo[key].v2025 += row.v2025;
                resumo[key].rendimento += row.rendimento;
            }});
            
            const tbodyResumo = document.getElementById('tbody-resumo');
            Object.values(resumo).forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.secao}}</td>
                    <td>${{row.instituicao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbodyResumo.appendChild(tr);
            }});

            // Tab 3: Totais
            const totais = {{}};
            mockData.forEach(row => {{
                const key = row.grupo + '|' + row.codigo;
                if (!totais[key]) {{
                    totais[key] = {{
                        grupo: row.grupo,
                        codigo: row.codigo,
                        descricao: row.descricao,
                        v2024: 0,
                        v2025: 0,
                        rendimento: 0
                    }};
                }}
                totais[key].v2024 += row.v2024;
                totais[key].v2025 += row.v2025;
                totais[key].rendimento += row.rendimento;
            }});
            
            const tbodyTotais = document.getElementById('tbody-totais');
            Object.values(totais).forEach(row => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${{row.grupo || '-'}}</td>
                    <td>${{row.codigo}}</td>
                    <td>${{row.descricao}}</td>
                    <td class="currency">${{formatCurrency(row.v2024)}}</td>
                    <td class="currency">${{formatCurrency(row.v2025)}}</td>
                    <td class="currency">${{formatCurrency(row.rendimento)}}</td>
                `;
                tbodyTotais.appendChild(tr);
            }});

            // Tab 4: Para IRPF
            gerarTabelasIRPF();
        }}

        // Chart Configuration based on theme
        let chartInstance1 = null;
        let chartInstance2 = null;

        function getChartColors(isDark) {{
            return {{
                text: isDark ? '#e0e0e0' : '#333333',
                grid: isDark ? '#3d3d3d' : '#e9ecef',
                primary: '#667eea',
                secondary: '#764ba2'
            }};
        }}

        function updateCharts(theme) {{
            const isDark = theme === 'dark';
            const colors = getChartColors(isDark);
            
            if (chartInstance1) {{
                chartInstance1.options.plugins.legend.labels.color = colors.text;
                chartInstance1.options.plugins.tooltip.bodyColor = colors.text;
                chartInstance1.update();
            }}
            
            if (chartInstance2) {{
                chartInstance2.options.scales.y.ticks.color = colors.text;
                chartInstance2.options.scales.x.ticks.color = colors.text;
                chartInstance2.options.scales.y.grid.color = colors.grid;
                chartInstance2.options.plugins.legend.labels.color = colors.text;
                chartInstance2.update();
            }}
        }}

        function createCharts() {{
            const isDark = document.documentElement.classList.contains('dark-mode');
            const colors = getChartColors(isDark);

            // Prepare data
            const institutions = {{}};
            mockData.forEach(row => {{
                if (!institutions[row.instituicao]) {{
                    institutions[row.instituicao] = 0;
                }}
                institutions[row.instituicao] += row.v2025;
            }});

            // Truncate institution labels
            const truncatedInstitutions = {{}};
            const institutionLabels = [];
            Object.keys(institutions).forEach(inst => {{
                const truncated = truncateLabel(inst, dashboardConfig);
                truncatedInstitutions[truncated] = institutions[inst];
                institutionLabels.push(truncated);
            }});

            // Chart 1: Institution Distribution
            const ctx1 = document.getElementById('chartInstitution').getContext('2d');
            chartInstance1 = new Chart(ctx1, {{
                type: 'doughnut',
                data: {{
                    labels: institutionLabels,
                    datasets: [{{
                        data: Object.values(truncatedInstitutions),
                        backgroundColor: [
                            '#667eea', '#764ba2', '#f093fb', '#4facfe',
                            '#43e97b', '#fa709a', '#30cfd0', '#a8edea'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ 
                                color: colors.text,
                                padding: 15,
                                font: {{ size: 12 }}
                            }}
                        }},
                        tooltip: {{
                            bodyColor: colors.text,
                            backgroundColor: isDark ? '#2d2d2d' : '#ffffff'
                        }}
                    }}
                }}
            }});

            // Chart 2: Evolution
            const ctx2 = document.getElementById('chartEvolution').getContext('2d');
            const evolution = {{}};
            mockData.forEach(row => {{
                if (!evolution[row.instituicao]) {{
                    evolution[row.instituicao] = {{ v2024: 0, v2025: 0 }};
                }}
                evolution[row.instituicao].v2024 += row.v2024;
                evolution[row.instituicao].v2025 += row.v2025;
            }});

            // Truncate evolution labels
            const truncatedEvolution = {{}};
            const evolutionLabels = [];
            Object.keys(evolution).forEach(inst => {{
                const truncated = truncateLabel(inst, dashboardConfig);
                truncatedEvolution[truncated] = evolution[inst];
                evolutionLabels.push(truncated);
            }});

            chartInstance2 = new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: evolutionLabels,
                    datasets: [
                        {{
                            label: '2024',
                            data: Object.values(truncatedEvolution).map(e => e.v2024),
                            backgroundColor: '#667eea'
                        }},
                        {{
                            label: '2025',
                            data: Object.values(truncatedEvolution).map(e => e.v2025),
                            backgroundColor: '#764ba2'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {{
                        y: {{
                            ticks: {{ color: colors.text }},
                            grid: {{ color: colors.grid }}
                        }},
                        x: {{
                            ticks: {{ 
                                color: colors.text,
                                maxRotation: {dashboard_config.get('chart_label_rotation', 45)},
                                minRotation: {dashboard_config.get('chart_label_rotation', 45)}
                            }},
                            grid: {{ color: colors.grid }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            labels: {{ color: colors.text }}
                        }},
                        tooltip: {{
                            bodyColor: colors.text,
                            backgroundColor: isDark ? '#2d2d2d' : '#ffffff'
                        }}
                    }}
                }}
            }});
        }}

        // Derive a display label for renda fixa assets from the discriminacao,
        // so that Tesouro Selic/Prefixado/IPCA+ and CDB/RDB appear as separate
        // lines in the IRPF tab instead of being merged under the same code.
        function irpfDisplayLabel(r) {{
            if (r.grupo === '04' && (r.codigo === '02' || r.codigo === '03')) {{
                const d = (r.discriminacao || '').toUpperCase();
                if (d.includes('TESOURO')) {{
                    if (d.includes('SELIC'))     return 'Tesouro Selic';
                    if (d.includes('IPCA'))      return 'Tesouro IPCA+';
                    if (d.includes('PREFIXADO')) return 'Tesouro Prefixado';
                    return 'Tesouro Direto';
                }}
                if (d.includes('CDB')) return 'CDB \u2013 Certificado de Dep\u00f3sito Banc\u00e1rio';
                if (d.includes('RDB')) return 'RDB \u2013 Recibo de Dep\u00f3sito Banc\u00e1rio';
                if (d.includes('LCI')) return 'LCI \u2013 Letra de Cr\u00e9dito Imobili\u00e1rio';
                if (d.includes('LCA')) return 'LCA \u2013 Letra de Cr\u00e9dito do Agroneg\u00f3cio';
                if (d.includes('CRI')) return 'CRI \u2013 Certificado de Receb\u00edveis Imobili\u00e1rios';
                if (d.includes('CRA')) return 'CRA \u2013 Certificado de Receb\u00edveis do Agroneg\u00f3cio';
                // Fallback for code 02: unidentified entries are generic Tesouro Direto
                if (r.codigo === '02') return 'Tesouro Direto';
            }}
            return r.descricao;
        }}

        // Generate IRPF Tables grouped by Instituição (Broker)
        function gerarTabelasIRPF() {{
            const irpfContent = document.getElementById('irpf-content');
            
            // Group by Instituição, then by Seção
            const instituicoes = {{}};
            let totalGeral = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
            
            mockData.forEach(row => {{
                if (!instituicoes[row.instituicao]) {{
                    instituicoes[row.instituicao] = {{}};
                }}
                if (!instituicoes[row.instituicao][row.secao]) {{
                    instituicoes[row.instituicao][row.secao] = [];
                }}
                instituicoes[row.instituicao][row.secao].push(row);
                
                // Accumulate totals
                totalGeral.v2024 += row.v2024 || 0;
                totalGeral.v2025 += row.v2025 || 0;
                totalGeral.rendimento += row.rendimento || 0;
                totalGeral.irrf += row.irrf || 0;
            }});

            // Sort instituições alphabetically
            const sortedInstitucoes = Object.keys(instituicoes).sort();
            
            sortedInstitucoes.forEach(instituicao => {{
                // Institution header
                const instDiv = document.createElement('div');
                instDiv.className = 'institution-header';
                instDiv.style.marginTop = '20px';
                instDiv.style.marginBottom = '10px';
                instDiv.style.fontSize = '18px';
                instDiv.style.fontWeight = 'bold';
                instDiv.style.color = 'var(--primary-color)';
                instDiv.style.borderBottom = '2px solid var(--primary-color)';
                instDiv.style.paddingBottom = '5px';
                instDiv.textContent = instituicao.toUpperCase();
                irpfContent.appendChild(instDiv);

                const instData = instituicoes[instituicao];
                const sortedSecoes = Object.keys(instData).sort();
                let instTotal = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
                
                // For each seção within this instituição
                sortedSecoes.forEach(secao => {{
                    const rawRows = instData[secao];

                    // Aggregate by (grupo, codigo, display_label). For renda fixa
                    // (04/02 and 04/03) the label is derived from discriminacao so
                    // Tesouro Selic/Prefixado/IPCA+ and CDB appear as separate lines.
                    const mergedRows = [];
                    const seenKey   = {{}};
                    rawRows.forEach(r => {{
                        const displayLabel = irpfDisplayLabel(r);
                        const key = `${{r.grupo || ''}}|${{r.codigo}}|${{displayLabel}}`;
                        if (seenKey[key] !== undefined) {{
                            mergedRows[seenKey[key]].v2024      += r.v2024      || 0;
                            mergedRows[seenKey[key]].v2025      += r.v2025      || 0;
                            mergedRows[seenKey[key]].rendimento += r.rendimento || 0;
                            mergedRows[seenKey[key]].irrf       += r.irrf       || 0;
                        }} else {{
                            seenKey[key] = mergedRows.length;
                            const merged = Object.assign({{}}, r);
                            merged.descricao = displayLabel;
                            mergedRows.push(merged);
                        }}
                    }});
                    const secaoRows = mergedRows;

                    // Section subheader
                    const secaoDiv = document.createElement('div');
                    secaoDiv.style.marginTop = '10px';
                    secaoDiv.style.marginBottom = '5px';
                    secaoDiv.style.fontSize = '14px';
                    secaoDiv.style.fontWeight = '600';
                    secaoDiv.style.color = 'var(--secondary-color)';
                    secaoDiv.textContent = secao;
                    irpfContent.appendChild(secaoDiv);

                    // Accumulate section and institution totals before rendering
                    const secaoTotal = {{ v2024: 0, v2025: 0, rendimento: 0, irrf: 0 }};
                    secaoRows.forEach(r => {{
                        secaoTotal.v2024      += r.v2024      || 0;
                        secaoTotal.v2025      += r.v2025      || 0;
                        secaoTotal.rendimento += r.rendimento || 0;
                        secaoTotal.irrf       += r.irrf       || 0;
                        instTotal.v2024       += r.v2024      || 0;
                        instTotal.v2025       += r.v2025      || 0;
                        instTotal.rendimento  += r.rendimento || 0;
                        instTotal.irrf        += r.irrf       || 0;
                    }});

                    const table = document.createElement('table');
                    table.className = 'table table-sm table-striped';
                    table.style.marginBottom = '15px';
                    table.innerHTML = `
                        <thead>
                            <tr style="background-color: var(--table-header-light);">
                                <th>Grupo</th>
                                <th>Código</th>
                                <th>Descrição</th>
                                <th class="currency">2024 (R$)</th>
                                <th class="currency">2025 (R$)</th>
                                <th class="currency">Rendimento (R$)</th>
                                <th class="currency">IRRF (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${{secaoRows.map(r => {{
                                const tickerMatch = r.discriminacao && r.discriminacao.match(/^([A-Z0-9]{{3,7}})\s*[\u2013-]/);
                                const ticker = tickerMatch ? tickerMatch[1] : null;
                                const descDisplay = ticker ? `<strong>${{ticker}}</strong> — ${{r.descricao}}` : r.descricao;
                                return `
                                    <tr>
                                        <td>${{r.grupo || '-'}}</td>
                                        <td>${{r.codigo}}</td>
                                        <td>${{descDisplay}}</td>
                                        <td class="currency">${{formatCurrency(r.v2024)}}</td>
                                        <td class="currency">${{formatCurrency(r.v2025)}}</td>
                                        <td class="currency">${{formatCurrency(r.rendimento)}}</td>
                                        <td class="currency">${{formatCurrency(r.irrf)}}</td>
                                    </tr>
                                `;
                            }}).join('')}}
                        </tbody>
                        <tfoot>
                            <tr style="font-weight: bold; background-color: var(--bg-light-card); border-top: 2px solid var(--border-light);">
                                <td colspan="3">SubTotal ${{secao}}</td>
                                <td class="currency">${{formatCurrency(secaoTotal.v2024)}}</td>
                                <td class="currency">${{formatCurrency(secaoTotal.v2025)}}</td>
                                <td class="currency">${{formatCurrency(secaoTotal.rendimento)}}</td>
                                <td class="currency">${{formatCurrency(secaoTotal.irrf)}}</td>
                            </tr>
                        </tfoot>
                    `;
                    irpfContent.appendChild(table);
                }});
                
                // Institution subtotal
                const instSubtotalDiv = document.createElement('div');
                instSubtotalDiv.style.display = 'grid';
                instSubtotalDiv.style.gridTemplateColumns = 'repeat(7, 1fr)';
                instSubtotalDiv.style.gap = '5px';
                instSubtotalDiv.style.marginBottom = '20px';
                instSubtotalDiv.style.fontWeight = 'bold';
                instSubtotalDiv.style.padding = '10px';
                instSubtotalDiv.style.backgroundColor = 'var(--bg-light-card)';
                instSubtotalDiv.style.border = '1px solid var(--border-light)';
                instSubtotalDiv.innerHTML = `
                    <div style="grid-column: 1/4;">Subtotal ${{instituicao}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.v2024)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.v2025)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.rendimento)}}</div>
                    <div class="currency" style="textAlign: right;">${{formatCurrency(instTotal.irrf)}}</div>
                `;
                irpfContent.appendChild(instSubtotalDiv);
            }});
            
            // Grand Total
            const grandTotalDiv = document.createElement('div');
            grandTotalDiv.style.display = 'grid';
            grandTotalDiv.style.gridTemplateColumns = 'repeat(7, 1fr)';
            grandTotalDiv.style.gap = '5px';
            grandTotalDiv.style.marginTop = '30px';
            grandTotalDiv.style.fontWeight = 'bold';
            grandTotalDiv.style.fontSize = '16px';
            grandTotalDiv.style.padding = '10px';
            grandTotalDiv.style.backgroundColor = 'var(--primary-color)';
            grandTotalDiv.style.color = 'white';
            grandTotalDiv.style.border = '2px solid var(--secondary-color)';
            grandTotalDiv.innerHTML = `
                <div style="grid-column: 1/4;">TOTAL GERAL</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.v2024)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.v2025)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.rendimento)}}</div>
                <div class="currency" style="textAlign: right;">${{formatCurrency(totalGeral.irrf)}}</div>
            `;
            irpfContent.appendChild(grandTotalDiv);
        }}

        // Initialize
        window.addEventListener('DOMContentLoaded', function() {{
            initializeTheme();
            populateTabs();
            createCharts();
        }});
    </script>
</body>
</html>
'''
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'  Dashboard gerado em: {output_path} (com Dark Mode 🌙)')
