"""Optional Google Sheets export.

Only imported/used when ``google_sheets.enabled = true`` in config.toml.
Requires: gspread, google-auth-oauthlib
"""
from __future__ import annotations

from typing import Any
import pandas as pd


def push_to_sheets(entries: list[Any], config: dict) -> None:
    """Upload the same 4 tabs to a Google Sheets spreadsheet.

    Authentication is performed via OAuth2 (desktop flow).  On the first run
    a browser window opens for consent; the token is cached in
    ``config['token_file']`` for subsequent runs.
    """
    try:
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise RuntimeError(
            'Dependências do Google Sheets não instaladas.\n'
            'Execute: pip install gspread google-auth-oauthlib'
        ) from exc

    import os
    import json

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive.file']

    creds_file  = config.get('credentials_file', 'credentials/credentials.json')
    token_file  = config.get('token_file',        'credentials/token.json')
    sheet_name  = config.get('spreadsheet_name',  'Informes de Rendimentos')

    # ── Authenticate ──────────────────────────────────────────────────────────
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_file):
                raise FileNotFoundError(
                    f'Arquivo de credenciais não encontrado: {creds_file}\n'
                    'Consulte setup_guide.md para configurar o acesso ao Google Sheets.'
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as fh:
            fh.write(creds.to_json())

    gc = gspread.authorize(creds)

    # ── Open or create spreadsheet ────────────────────────────────────────────
    try:
        sh = gc.open(sheet_name)
        print(f'  Planilha "{sheet_name}" encontrada no Google Drive.')
    except gspread.SpreadsheetNotFound:
        sh = gc.create(sheet_name)
        print(f'  Planilha "{sheet_name}" criada no Google Drive.')

    # ── Build DataFrames (same logic as xlsx_writer) ──────────────────────────
    from src.xlsx_writer import _entries_to_df, _COL_LABELS

    df = _entries_to_df(entries)

    tab_configs = [
        ('Dados Brutos',  df),
        ('Resumo',        _build_resumo_df(df)),
        ('Totais',        _build_totais_df(df)),
        ('Para IRPF',     _build_para_irpf_df(df)),
    ]

    existing_titles = {ws.title for ws in sh.worksheets()}

    for tab_name, tab_df in tab_configs:
        if tab_name in existing_titles:
            ws = sh.worksheet(tab_name)
            ws.clear()
        else:
            ws = sh.add_worksheet(title=tab_name, rows=max(len(tab_df) + 10, 50), cols=30)

        # Write header + data
        data = [tab_df.columns.tolist()] + tab_df.fillna('').values.tolist()
        ws.update(data, value_input_option='USER_ENTERED')
        print(f'  Aba "{tab_name}" atualizada ({len(tab_df)} linhas).')

    # Remove default "Sheet1" if it was created
    for ws in sh.worksheets():
        if ws.title in ('Sheet1', 'Página1'):
            try:
                sh.del_worksheet(ws)
            except Exception:
                pass

    print(f'  URL: {sh.url}')


# ── DataFrame builders (mirrors xlsx_writer logic) ────────────────────────────

def _build_resumo_df(df: pd.DataFrame) -> pd.DataFrame:
    institutions = sorted(df['Instituição'].dropna().unique())
    rows = []
    for key, grp in df.groupby(['Seção', 'Grupo', 'Código Descrição']):
        row = {'Seção': key[0], 'Grupo/Código': key[1], 'Descrição': key[2]}
        for inst in institutions:
            sub = grp[grp['Instituição'] == inst]
            row[f'{inst} – 2024']       = sub['Valor 31/12/2024'].sum()
            row[f'{inst} – 2025']       = sub['Valor 31/12/2025'].sum()
            row[f'{inst} – Rendimento'] = sub['Rendimento'].sum()
        row['TOTAL 2024']        = grp['Valor 31/12/2024'].sum()
        row['TOTAL 2025']        = grp['Valor 31/12/2025'].sum()
        row['TOTAL Rendimentos'] = grp['Rendimento'].sum()
        rows.append(row)
    return pd.DataFrame(rows)


def _build_totais_df(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby(['Seção', 'Grupo', 'Grupo Descrição', 'Código', 'Código Descrição'],
                   as_index=False)
        .agg({'Valor 31/12/2024': 'sum', 'Valor 31/12/2025': 'sum',
              'Rendimento': 'sum', 'IRRF': 'sum'})
        .sort_values(['Seção', 'Grupo', 'Código'])
    )
    agg.columns = ['Seção', 'Grupo', 'Grupo Descrição', 'Código', 'Código Descrição',
                   'Total 31/12/2024', 'Total 31/12/2025', 'Total Rendimentos', 'Total IRRF']
    return agg


def _build_para_irpf_df(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for inst in sorted(df['Instituição'].unique()):
        inst_df = df[df['Instituição'] == inst]
        for _, r in inst_df.iterrows():
            rows.append({
                'Instituição':     inst,
                'Seção':           r['Seção'],
                'Grupo':           r['Grupo'],
                'Código':          r['Código'],
                'Descrição':       r['Código Descrição'],
                'Valor 31/12/2024': r['Valor 31/12/2024'],
                'Valor 31/12/2025': r['Valor 31/12/2025'],
                'Rendimento':       r['Rendimento'],
                'IRRF':             r['IRRF'],
            })
    return pd.DataFrame(rows)
