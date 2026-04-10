"""
IPAJM Analytics Institucional — app.py
Green Institutional Theme | Plus Jakarta Sans + DM Serif Display
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from datetime import date

# ──────────────────────────────────────────────────────────────
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="IPAJM · Analytics Institucional",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

server = app.server

df = pd.read_parquet(os.path.join(BASE_PATH, 'data_processed.parquet'))
UPDATE_DATE = date.today().strftime("%d/%m/%Y")

# Lista de todos os órgãos (77) ordenados, sem 'nan'
ALL_ORGAOS = sorted([o for o in df['NO_ORGAO'].dropna().unique() if str(o) != 'nan'])

# ── Plotly base layout (sem legend — aplicamos por figura) ────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#6b8e69", size=11),
    colorway=["#175414","#2a8a24","#3db836","#72d96a","#b5e4b2","#c8a84b"],
    xaxis=dict(showgrid=False, zeroline=False, showline=False,
               tickcolor="#9ab898", tickfont=dict(size=10, color="#6b8e69")),
    yaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)", zeroline=False,
               showline=False, tickcolor="#9ab898", tickfont=dict(size=10, color="#6b8e69")),
    margin=dict(t=10, b=10, l=10, r=10),
    hoverlabel=dict(bgcolor="#ffffff", bordercolor="#b0ccae",
                    font=dict(color="#0f2e0d", family="Plus Jakarta Sans, sans-serif"))
)
LEGEND_BASE = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b8e69"))

# ── Helpers ───────────────────────────────────────────────────
def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",","X").replace(".","," ).replace("X",".")

def fmt_mil(v):
    if v >= 1e9:
        s = f"{v/1e9:.1f}".replace(".",","); return f"R$ {s}B"
    s = f"{v/1e6:.1f}".replace(".",","); return f"R$ {s}M"

def fmt_int(v):
    return f"{int(v):,}".replace(",",".")

def kpi_card(value, label, delta=None):
    ch = [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value")]
    if delta: ch.append(html.Div(delta, className="kpi-delta"))
    return html.Div(ch, className="kpi-card")

def chart_card(title, gid):
    return html.Div([
        html.Div(html.Span(title, className="chart-card-title"), className="chart-card-header"),
        dcc.Graph(id=gid, config={"displayModeBar": False, "responsive": True}, style={"height":"320px"})
    ], className="chart-card h-100")

# ── Dropdown estilo "select" simples ─────────────────────────
DROP_STYLE = {
    "fontFamily": "Plus Jakarta Sans, sans-serif",
    "fontSize": "0.88rem",
    "minWidth": "180px",
}

# ── Layout ────────────────────────────────────────────────────
app.layout = html.Div([
    html.Header([
        html.Div(html.Img(src='/assets/logo-ipajm.png', alt='IPAJM'), className="header-logo-wrap"),
        html.Div([
            html.Div([
                html.Img(src='/assets/Brasao_Governo.png', alt='Governo do ES',
                         style={"height":"56px","width":"auto",
                                "filter":"brightness(0) invert(1)","opacity":"0.88"}),
                html.Span(f"Atualizado em {UPDATE_DATE}", className="header-date-pill"),
            ], style={"display":"flex","alignItems":"center","gap":"14px"}),
            html.Button([html.Span("↓ "), html.Span("Exportar Relatório")],
                        id="btn-export-pdf", className="btn-export-pdf", n_clicks=0),
        ], className="header-right")
    ], className="ipajm-header"),

    html.Div([
        html.Div("Filtros de Análise", className="section-label"),
        html.Div([
            # ── Categoria
            html.Div([
                html.Label("Categoria", className="sel-label"),
                dcc.Dropdown(
                    id='filter-category',
                    options=[{"label": "Todas as categorias", "value": "__all__"}] +
                            [{"label": i, "value": i} for i in sorted(df['CATEGORIA'].unique())],
                    value="__all__",
                    clearable=False,
                    searchable=False,
                    className="drop-select",
                    style=DROP_STYLE,
                )
            ], className="filter-group", style={"flex":"1"}),

            # ── Sexo
            html.Div([
                html.Label("Sexo", className="sel-label"),
                dcc.Dropdown(
                    id='filter-sex',
                    options=[{"label": "Todos", "value": "__all__"}] +
                            [{"label": i, "value": i} for i in
                             sorted([s for s in df['SEXO_DESC'].unique() if s != 'Não Informado']) + ['Não Informado']],
                    value="__all__",
                    clearable=False,
                    searchable=False,
                    className="drop-select",
                    style=DROP_STYLE,
                )
            ], className="filter-group", style={"flex":"1"}),

            # ── Órgão — todos os 77
            html.Div([
                html.Label("Órgão", className="sel-label"),
                dcc.Dropdown(
                    id='filter-orgao',
                    options=[{"label": "Todos os órgãos", "value": "__all__"}] +
                            [{"label": i, "value": i} for i in ALL_ORGAOS],
                    value="__all__",
                    clearable=False,
                    searchable=True,
                    className="drop-select",
                    style=DROP_STYLE,
                    placeholder="Todos os órgãos",
                    optionHeight=36,
                )
            ], className="filter-group", style={"flex":"1.5"}),
        ], className="filter-bar"),

        html.Div("Indicadores-Chave", className="section-label"),
        html.Div(id='kpi-row', className="kpi-grid"),

        html.Div("Distribuições", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Distribuição por Categoria",    "graph-cat"),  md=4, className="mb-4"),
            dbc.Col(chart_card("Distribuição por Faixa Etária", "graph-age"),  md=8, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(chart_card("Remuneração Média por Órgão (Top 10)", "graph-salary"), md=8, className="mb-4"),
            dbc.Col(chart_card("Distribuição por Sexo",                "graph-sex"),    md=4, className="mb-4"),
        ]),

        html.Div("Análises Avançadas", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Top 10 Cargos por Remuneração Média (Ativos)", "graph-top-cargos"), md=7, className="mb-4"),
            dbc.Col(chart_card("Remuneração Média por Categoria",               "graph-contrib"),    md=5, className="mb-4"),
        ]),

        html.Div("Detalhamento de Cargos", className="section-label"),
        html.Div([
            html.Div(html.Span("Principais Cargos", className="chart-card-title"), className="chart-card-header"),
            html.Div(id='table-output')
        ], className="chart-card mb-5"),
    ], className="page-body"),

    html.Footer([
        html.Span("IPAJM · Instituto de Previdência dos Servidores do Estado do Espírito Santo"),
        html.Span(f"Dados referentes ao exercício 2026 · Build {UPDATE_DATE}")
    ], className="ipajm-footer"),

    dcc.Store(id='store-report-data'),
    html.Div(id='pdf-modal-container'),
], style={"minHeight":"100vh","backgroundColor":"#f0f4f0"})


# ── Callback principal ────────────────────────────────────────
@app.callback(
    [Output('kpi-row','children'),
     Output('graph-cat','figure'),
     Output('graph-age','figure'),
     Output('graph-salary','figure'),
     Output('graph-sex','figure'),
     Output('graph-top-cargos','figure'),
     Output('graph-contrib','figure'),
     Output('table-output','children'),
     Output('store-report-data','data')],
    [Input('filter-category','value'),
     Input('filter-sex','value'),
     Input('filter-orgao','value')]
)
def update_dashboard(categories, sexes, orgaos):
    # Dropdowns retornam string única (não-multi)
    cat_filter = None if (not categories or categories == "__all__") else [categories]
    sex_filter = None if (not sexes      or sexes      == "__all__") else [sexes]
    org_filter = None if (not orgaos     or orgaos     == "__all__") else [orgaos]

    dff = df[df['CATEGORIA'].isin(cat_filter or df['CATEGORIA'].unique())]
    dff = dff[dff['SEXO_DESC'].isin(sex_filter or df['SEXO_DESC'].unique())]
    if org_filter:
        dff = dff[dff['NO_ORGAO'].isin(org_filter)]

    total       = len(dff)
    media_sal   = dff['VL_REMUNERACAO'].mean()
    media_idade = dff['IDADE'].mean()
    contrib     = dff['VL_CONTRIBUICAO'].sum()

    kpis = [
        kpi_card(fmt_int(total),            "Total de Servidores",  "base completa"),
        kpi_card(fmt_brl(media_sal),        "Remuneração Média",    None),
        kpi_card(f"{media_idade:.1f} anos", "Idade Média",          None),
        kpi_card(fmt_mil(contrib),          "Contribuição Total",   None),
    ]

    greens = ["#175414","#1e6e19","#2a8a24","#3db836","#72d96a","#b5e4b2","#e8f5e6"]

    # ── 1 Donut Categoria
    cc = dff['CATEGORIA'].value_counts().reset_index()
    fig_cat = go.Figure(go.Pie(
        labels=cc['CATEGORIA'], values=cc['count'], hole=0.6, textinfo='percent',
        marker=dict(colors=greens, line=dict(color="#ffffff", width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,} servidores<extra></extra>"
    ))
    fig_cat.update_layout(**BASE_LAYOUT,
                          showlegend=True,
                          legend=dict(**LEGEND_BASE, orientation="v"))

    # ── 2 Faixa Etária
    age_order = ['<18','18-25','26-35','36-45','46-55','56-65','66-75','>75']
    ac = dff['FAIXA_ETARIA'].value_counts().reindex(age_order).fillna(0).reset_index()
    ac['txt'] = ac['count'].apply(lambda x: fmt_int(int(x)))
    fig_age = go.Figure(go.Bar(
        x=ac['count'], y=ac['FAIXA_ETARIA'], orientation='h',
        text=ac['txt'], textposition='outside', textfont=dict(size=10, color="#2d4a2b"),
        marker=dict(color=ac['count'], colorscale=[[0,"#b5e4b2"],[0.5,"#2a8a24"],[1,"#175414"]], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,} servidores<extra></extra>"
    ))
    fig_age.update_layout(**BASE_LAYOUT)
    fig_age.update_layout(
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)", tickformat=",")
    )
    fig_age.update_traces(width=0.65)

    # ── 3 Salário por Órgão
    so = dff.groupby('NO_ORGAO')['VL_REMUNERACAO'].mean().sort_values(ascending=True).tail(10).reset_index()
    so['txt'] = so['VL_REMUNERACAO'].apply(fmt_brl)
    fig_sal = go.Figure(go.Bar(
        x=so['VL_REMUNERACAO'], y=so['NO_ORGAO'], orientation='h',
        text=so['txt'], textposition='outside', textfont=dict(size=9, color="#2d4a2b"),
        marker=dict(color=so['VL_REMUNERACAO'], colorscale=[[0,"#b5e4b2"],[1,"#175414"]], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>"
    ))
    fig_sal.update_layout(**BASE_LAYOUT)
    fig_sal.update_layout(yaxis=dict(showgrid=False),
                          xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)"))

    # ── 4 Sexo donut
    sc = dff['SEXO_DESC'].value_counts().reset_index()
    fig_sex = go.Figure(go.Pie(
        labels=sc['SEXO_DESC'], values=sc['count'], hole=0.6, textinfo='percent',
        marker=dict(colors=greens, line=dict(color="#ffffff", width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>"
    ))
    fig_sex.update_layout(**BASE_LAYOUT,
                          showlegend=True,
                          legend=dict(**LEGEND_BASE, orientation="v"))

    # ── 5 Top Cargos (apenas Ativos)
    ativos_df = dff[dff['CATEGORIA']=='ATIVOS']
    tc = (ativos_df.groupby('NO_CARGO')['VL_REMUNERACAO']
          .mean().sort_values(ascending=True).tail(10).reset_index())
    tc['lbl'] = tc['NO_CARGO'].apply(lambda x: str(x)[:35]+"…" if len(str(x))>35 else str(x))
    tc['txt'] = tc['VL_REMUNERACAO'].apply(fmt_brl)
    fig_tc = go.Figure(go.Bar(
        x=tc['VL_REMUNERACAO'], y=tc['lbl'], orientation='h',
        text=tc['txt'], textposition='outside', textfont=dict(size=9, color="#2d4a2b"),
        marker=dict(color="#1e6e19", opacity=0.85, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>"
    ))
    fig_tc.update_layout(**BASE_LAYOUT)
    fig_tc.update_layout(yaxis=dict(showgrid=False))

    # ── 6 Remuneração Média por Categoria
    rm_cat = dff.groupby('CATEGORIA')['VL_REMUNERACAO'].mean().reset_index()
    rm_cat['txt'] = rm_cat['VL_REMUNERACAO'].apply(fmt_brl)
    fig_contrib = go.Figure(go.Bar(
        x=rm_cat['CATEGORIA'], y=rm_cat['VL_REMUNERACAO'],
        text=rm_cat['txt'], textposition='outside', textfont=dict(size=10, color="#2d4a2b"),
        marker=dict(color=rm_cat['VL_REMUNERACAO'],
                    colorscale=[[0,"#b5e4b2"],[1,"#175414"]], line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>"
    ))
    fig_contrib.update_layout(**BASE_LAYOUT)
    fig_contrib.update_traces(width=0.4)

    # ── Tabela
    tdf = (dff.groupby('NO_CARGO')
              .agg(Servidores=('VL_REMUNERACAO','count'),
                   Rem_Media=('VL_REMUNERACAO','mean'),
                   Idade_Media=('IDADE','mean'))
              .reset_index()
              .sort_values('Servidores', ascending=False)
              .head(15))
    tdf['Servidores']  = tdf['Servidores'].apply(fmt_int)
    tdf['Rem_Media']   = tdf['Rem_Media'].apply(fmt_brl)
    tdf['Idade_Media'] = tdf['Idade_Media'].apply(lambda x: f"{x:.1f}")
    tdf.columns = ['Cargo','Servidores','Rem. Média','Idade Média']

    table = dash_table.DataTable(
        data=tdf.to_dict('records'),
        columns=[{"name": c,"id": c} for c in tdf.columns],
        style_as_list_view=True, page_size=10,
        style_header={
            'backgroundColor':'#f2faf1','color':'#175414','fontWeight':'700',
            'fontSize':'0.67rem','letterSpacing':'0.1em','textTransform':'uppercase',
            'borderBottom':'2px solid #b0ccae','padding':'12px 16px','textAlign':'center',
        },
        style_cell={
            'backgroundColor':'#ffffff','color':'#2d4a2b',
            'fontFamily':'Plus Jakarta Sans, sans-serif','fontSize':'0.83rem',
            'padding':'11px 16px','border':'none','borderBottom':'1px solid #d4e6d2',
            'textAlign':'center',
        },
        style_cell_conditional=[{'if':{'column_id':'Cargo'},'textAlign':'left','paddingLeft':'20px'}],
        style_data_conditional=[
            {'if':{'row_index':'odd'},'backgroundColor':'#fafcfa'},
            {'if':{'state':'active'},'backgroundColor':'#e8f5e6','color':'#175414'},
        ],
    )

    report_data = {
        'total': fmt_int(total), 'media_sal': fmt_brl(media_sal),
        'media_idade': f"{media_idade:.1f}", 'contrib': fmt_mil(contrib),
        'update_date': UPDATE_DATE,
        'categorias': dff['CATEGORIA'].value_counts().to_dict(),
        'top_orgaos': so[['NO_ORGAO','VL_REMUNERACAO']].to_dict('records'),
        'top_cargos': (tc[['lbl','VL_REMUNERACAO']].to_dict('records') if not tc.empty else []),
        'dist_sexo': sc.rename(columns={'SEXO_DESC':'label','count':'value'}).to_dict('records'),
        'faixa_etaria': ac.to_dict('records'),
        'rem_cat': rm_cat.to_dict('records'),
        'table': tdf.to_dict('records'),
    }

    return kpis, fig_cat, fig_age, fig_sal, fig_sex, fig_tc, fig_contrib, table, report_data


# ── PDF Modal ─────────────────────────────────────────────────
@app.callback(
    Output('pdf-modal-container','children'),
    Input('btn-export-pdf','n_clicks'),
    State('store-report-data','data'),
    prevent_initial_call=True
)
def open_pdf_modal(n, rd):
    if not n or not rd:
        return []

    cats      = rd.get('categorias', {})
    cat_lines = " | ".join([f"{k}: {fmt_int(v)}" for k, v in cats.items()])

    dist_sexo = {r['label']: r['value'] for r in rd.get('dist_sexo', [])}
    fem       = dist_sexo.get('Feminino', 0)
    masc      = dist_sexo.get('Masculino', 0)
    total_sx  = fem + masc
    pct_fem   = (fem/total_sx*100) if total_sx else 0
    pct_masc  = (masc/total_sx*100) if total_sx else 0

    fe_data    = {r['FAIXA_ETARIA']: int(r['count']) for r in rd.get('faixa_etaria', [])}
    peak_faixa = max(fe_data, key=fe_data.get) if fe_data else "N/D"
    peak_count = fmt_int(fe_data.get(peak_faixa, 0))

    tc_top = rd['top_cargos'][0] if rd.get('top_cargos') else {}
    to_top = rd['top_orgaos'][-1] if rd.get('top_orgaos') else {}

    cc_data       = {r['CATEGORIA']: r['VL_REMUNERACAO'] for r in rd.get('rem_cat', [])}
    maior_rem_cat = max(cc_data, key=cc_data.get) if cc_data else "N/D"

    # ── Estilos reutilizáveis para o relatório ──
    _TH = {"background":"#175414","color":"white","padding":"7px 12px",
           "fontSize":"0.6rem","textTransform":"uppercase","letterSpacing":"0.06em",
           "textAlign":"center","fontFamily":"Plus Jakarta Sans,sans-serif","fontWeight":"700"}
    _TD = {"padding":"6px 12px","fontSize":"0.78rem","color":"#2d4a2b","textAlign":"center"}
    _TD_L = {**_TD, "textAlign":"left"}
    _TBOX = {"width":"100%","borderCollapse":"collapse","border":"1px solid #c8ddc6",
             "overflow":"hidden","marginTop":"10px"}
    _SEC = {"background":"#f8fbf8","border":"1px solid #d4e6d2","borderLeft":"4px solid #175414",
            "borderRadius":"10px","padding":"20px 24px","marginBottom":"14px",
            "pageBreakInside":"avoid","breakInside":"avoid"}
    _H3 = {"fontFamily":"'DM Serif Display',serif","fontSize":"1.15rem","color":"#175414",
           "margin":"0 0 10px","paddingBottom":"8px","borderBottom":"2px solid #c8ddc6"}
    _P = {"margin":"0 0 12px","lineHeight":"1.85","fontSize":"0.85rem","color":"#2d4a2b"}

    def rpt_hdr():
        return html.Div([
            html.Div([
                html.Img(src='/assets/logo-ipajm.png', style={"height":"34px","width":"auto"}),
                html.Div([
                    html.Div("IPAJM — Instituto de Previdência dos Servidores do Estado do Espírito Santo",
                             style={"fontSize":"0.65rem","fontWeight":"700","color":"#175414",
                                    "letterSpacing":"0.03em"}),
                    html.Div(f"Relatório de Análise de Indicadores · {rd['update_date']}",
                             style={"fontSize":"0.58rem","color":"#6b8e69",
                                    "fontFamily":"'JetBrains Mono',monospace","marginTop":"2px"}),
                ], style={"flex":"1"}),
                html.Div(html.Img(src='/assets/Brasao_Governo.png', style={"height":"50px","width":"auto","filter":"brightness(0) invert(1)"}), style={"background":"#175414","borderRadius":"8px","padding":"8px 10px","display":"flex","alignItems":"center","justifyContent":"center"}),
            ], style={"display":"flex","alignItems":"center","gap":"16px",
                      "padding":"14px 0 10px","marginBottom":"18px",
                      "borderBottom":"2px solid #175414"}),
        ], className="report-page-header")

    def mini_tbl(headers, rows):
        return html.Table([
            html.Thead(html.Tr([html.Th(h, style=_TH) for h in headers])),
            html.Tbody([
                html.Tr([html.Td(c, style=_TD_L if j == 0 else _TD) for j, c in enumerate(r)],
                         style={"background":"#fff" if i % 2 == 0 else "#f8fbf8",
                                "borderBottom":"1px solid #d4e6d2"})
                for i, r in enumerate(rows)
            ])
        ], style=_TBOX)

    # ── Mini-tabelas de apoio ──
    cat_rows = [[k, fmt_int(v)] for k, v in cats.items()]
    tbl_cat = mini_tbl(["Categoria", "Servidores"], cat_rows)

    fe_rows = [[r['FAIXA_ETARIA'], fmt_int(int(r['count']))]
               for r in rd.get('faixa_etaria', []) if int(r['count']) > 0]
    tbl_fe = mini_tbl(["Faixa Etária", "Servidores"], fe_rows)

    gen_rows = [[r['label'], fmt_int(int(r['value'])),
                 f"{r['value']/total_sx*100:.1f}%" if total_sx else "—"]
                for r in rd.get('dist_sexo', [])]
    tbl_gen = mini_tbl(["Sexo", "Servidores", "%"], gen_rows)

    org_rows = [[r['NO_ORGAO'], fmt_brl(r['VL_REMUNERACAO'])]
                for r in reversed(rd.get('top_orgaos', []))]
    tbl_org = mini_tbl(["Órgão (Top 10)", "Rem. Média"], org_rows)

    cargo_rows = [[r['lbl'], fmt_brl(r['VL_REMUNERACAO'])]
                  for r in reversed(rd.get('top_cargos', []))]
    tbl_cargo = mini_tbl(["Cargo — Ativos (Top 10)", "Rem. Média"], cargo_rows)

    rc_rows = [[r['CATEGORIA'], fmt_brl(r['VL_REMUNERACAO'])] for r in rd.get('rem_cat', [])]
    tbl_rc = mini_tbl(["Categoria", "Rem. Média"], rc_rows)

    # ── Seções de análise (com html.Strong em vez de <strong>) ──
    sec_composicao = html.Div([
        html.H3("1. Composição da Força de Trabalho", style=_H3),
        html.P([
            "O universo analisado abrange ", html.Strong(rd['total']),
            " servidores vinculados ao RPPS do Estado do Espírito Santo, distribuídos nas categorias: ",
            cat_lines, ". Este contingente representa a massa segurada sob gestão do IPAJM, constituindo "
            "a base fundamental para as projeções atuariais de curto, médio e longo prazo. A proporção "
            "entre ativos e inativos é indicador crítico do equilíbrio financeiro-atuarial do plano de "
            "benefícios, devendo ser monitorada trimestralmente."
        ], style=_P),
        tbl_cat,
    ], style=_SEC)

    sec_demografico = html.Div([
        html.H3("2. Perfil Demográfico e Envelhecimento", style=_H3),
        html.P([
            "A idade média da força de trabalho é de ", html.Strong(f"{rd['media_idade']} anos"),
            ", com maior concentração na faixa etária ", html.Strong(peak_faixa),
            ", que reúne ", html.Strong(f"{peak_count} servidores"), ". Este perfil etário aponta para "
            "uma força de trabalho madura, com impacto direto nas projeções de aposentadorias e na "
            "necessidade de reposição de quadros nos próximos exercícios. Do ponto de vista atuarial, a "
            "concentração etária elevada reforça a urgência de políticas de equilíbrio entre entradas e "
            "saídas do sistema previdenciário."
        ], style=_P),
        tbl_fe,
    ], style=_SEC)

    sec_genero = html.Div([
        html.H3("3. Análise de Gênero e Longevidade", style=_H3),
        html.P([
            "A distribuição por sexo revela ",
            html.Strong(f"{pct_fem:.1f}% de servidoras do sexo feminino"),
            f" ({fmt_int(int(fem))} servidoras) e ",
            html.Strong(f"{pct_masc:.1f}% do sexo masculino"),
            f" ({fmt_int(int(masc))} servidores) sobre a base informada. Esta distribuição tem "
            "implicações atuariais relevantes, uma vez que tábuas de mortalidade e sobrevivência "
            "diferenciam longevidade por sexo. A maior presença feminina em carreiras como educação "
            "e saúde impacta o tempo médio de benefício e as projeções de pensão por morte, exigindo "
            "modelagem específica por segmento."
        ], style=_P),
        tbl_gen,
    ], style=_SEC)

    sec_remuneracao = html.Div([
        html.H3("4. Remuneração, Cargos e Impacto Financeiro", style=_H3),
        html.P([
            "A remuneração média geral do funcionalismo é de ", html.Strong(rd['media_sal']),
            ". A categoria ", html.Strong(maior_rem_cat),
            " registra a maior remuneração média entre as analisadas. O órgão com maior média salarial é ",
            html.Strong(to_top.get('NO_ORGAO', 'N/D')),
            f" ({fmt_brl(to_top.get('VL_REMUNERACAO', 0))}). O cargo de maior remuneração média "
            "identificado é ", html.Strong(tc_top.get('lbl', 'N/D')),
            f" ({fmt_brl(tc_top.get('VL_REMUNERACAO', 0))}). A massa salarial total é indicador "
            "fundamental para o cálculo da alíquota de equilíbrio do plano, devendo ser monitorada "
            "continuamente em face de reajustes e reestruturações de carreiras."
        ], style=_P),
        tbl_org,
        html.Div(style={"height":"10px"}),
        tbl_cargo,
    ], style=_SEC)

    sec_contribuicao = html.Div([
        html.H3("5. Contribuições Previdenciárias e Sustentabilidade", style=_H3),
        html.P([
            "O volume total de contribuições previdenciárias no período analisado alcança ",
            html.Strong(rd['contrib']),
            ". A sustentabilidade do regime de repartição depende diretamente da relação entre o fluxo "
            "de contribuições arrecadadas e o montante de benefícios pagos. Variações nessa relação "
            "exigem reavaliação periódica das hipóteses atuariais e, eventualmente, ajustes paramétricos "
            "no plano de custeio. Recomenda-se a realização de avaliação atuarial anual para verificação "
            "do equilíbrio financeiro de longo prazo do RPPS estadual."
        ], style=_P),
        tbl_rc,
    ], style=_SEC)

    # ── Conteúdo do relatório para impressão ──
    print_content = html.Div(id="print-report-content", children=[

        # ═══ CAPA ═══
        html.Div([
            html.Div(style={"height":"60px"}),
            html.Div([
                html.Img(src='/assets/logo-ipajm.png', style={
                    "height":"80px","filter":"brightness(0) invert(1)","display":"block","margin":"0 auto 28px"
                }),
                html.H1("Relatório de Análise de Indicadores", style={
                    "fontFamily":"'DM Serif Display',serif","fontSize":"2.4rem","color":"#fff",
                    "textAlign":"center","margin":"0 0 8px"
                }),
                html.H2("Servidores do Estado do Espírito Santo", style={
                    "fontFamily":"'DM Serif Display',serif","fontSize":"1.35rem",
                    "color":"rgba(255,255,255,0.75)","textAlign":"center","fontWeight":"normal","margin":"0 0 40px"
                }),
                html.Div([
                    *[html.Div([
                        html.Div(l, style={"fontSize":"0.58rem","color":"rgba(255,255,255,0.50)",
                                           "textTransform":"uppercase","letterSpacing":"0.1em",
                                           "marginBottom":"6px"}),
                        html.Div(v, style={"fontSize":"1.8rem","fontFamily":"'DM Serif Display',serif",
                                           "color":"#fff","lineHeight":"1","whiteSpace":"nowrap"}),
                    ], style={"textAlign":"center","padding":"18px 28px","flex":"1",
                              "display":"flex","flexDirection":"column","justifyContent":"center","alignItems":"center",
                              "borderRight":"1px solid rgba(255,255,255,0.18)" if i < 3 else "none"})
                    for i, (v, l) in enumerate([
                        (rd['total'], "Total Servidores"),
                        (rd['media_sal'], "Remuneração Média"),
                        (f"{rd['media_idade']} anos", "Idade Média"),
                        (rd['contrib'], "Contribuição Total"),
                    ])]
                ], style={"display":"flex","justifyContent":"center","alignItems":"stretch",
                          "background":"rgba(255,255,255,0.08)",
                          "border":"1px solid rgba(255,255,255,0.15)","borderRadius":"12px"}),
                html.Div([
                    html.Div("Instituto de Previdência dos Servidores do Estado do Espírito Santo — IPAJM",
                             style={"color":"rgba(255,255,255,0.55)","fontSize":"0.78rem"}),
                    html.Div(f"Data de Geração: {rd['update_date']}",
                             style={"color":"rgba(255,255,255,0.4)","fontSize":"0.72rem",
                                    "fontFamily":"'JetBrains Mono',monospace","marginTop":"6px"}),
                ], style={"textAlign":"center","marginTop":"36px"}),
            ]),
        ], className="report-cover"),

        # ═══ PÁGINA 2 — Composição + Perfil Demográfico ═══
        html.Div([
            rpt_hdr(),
            sec_composicao,
            sec_demografico,
        ], className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),

        # ═══ PÁGINA 3 — Gênero + Remuneração ═══
        html.Div([
            rpt_hdr(),
            sec_genero,
            sec_remuneracao,
        ], className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),

        # ═══ PÁGINA 4 — Contribuições + Tabela de Cargos ═══
        html.Div([
            rpt_hdr(),
            sec_contribuicao,
            html.H3("Detalhamento dos Principais Cargos", style={
                "fontFamily":"'DM Serif Display',serif","fontSize":"1.15rem","color":"#175414",
                "marginTop":"20px","marginBottom":"12px","paddingBottom":"8px",
                "borderBottom":"2px solid #c8ddc6"
            }),
            html.Table([
                html.Thead(html.Tr([
                    html.Th(c, style=_TH) for c in ['Cargo', 'Servidores', 'Rem. Média', 'Idade Média']
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(row.get('Cargo', ''),       style={**_TD, "textAlign":"left"}),
                        html.Td(row.get('Servidores', ''),   style=_TD),
                        html.Td(row.get('Rem. Média', ''),   style=_TD),
                        html.Td(row.get('Idade Média', ''),  style=_TD),
                    ], style={"background":"#fff" if i % 2 == 0 else "#f8fbf8",
                              "borderBottom":"1px solid #d4e6d2"})
                    for i, row in enumerate(rd.get('table', []))
                ])
            ], style={"width":"100%","borderCollapse":"collapse","border":"1px solid #c8ddc6",
                      "overflow":"hidden"}),
        ], className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),

        # ═══ RODAPÉ ═══
        html.Div([
            html.Hr(style={"border":"none","borderTop":"1px solid #c8ddc6","margin":"28px 0 14px"}),
            html.Div([
                html.Span("IPAJM — Instituto de Previdência dos Servidores do Estado do Espírito Santo",
                          style={"fontSize":"0.68rem","color":"#9ab898"}),
                html.Span(f"Gerado em {rd['update_date']} · Documento analítico e informativo.",
                          style={"fontSize":"0.68rem","color":"#9ab898"}),
            ], style={"display":"flex","justifyContent":"space-between","flexWrap":"wrap","gap":"8px"}),
        ], style={"padding":"0 40px"}),
    ])

    modal = html.Div([
        html.Div(id='pdf-overlay', style={
            "position":"fixed","top":0,"left":0,"width":"100vw","height":"100vh",
            "backgroundColor":"rgba(0,0,0,0.62)","zIndex":9000,
            "display":"flex","alignItems":"center","justifyContent":"center",
        }, children=[
            html.Div([
                html.Div([
                    html.Div([
                        html.Img(src='/assets/logo-ipajm.png', style={"height":"28px","filter":"invert(25%) sepia(60%) saturate(700%) hue-rotate(100deg)"}),
                        html.Span("Exportar Relatório PDF", style={"fontWeight":"700","fontSize":"1rem","color":"#0f2e0d","marginLeft":"10px"}),
                    ], style={"display":"flex","alignItems":"center"}),
                    html.Button("✕", id="btn-close-pdf-modal", style={
                        "background":"none","border":"none","fontSize":"1.1rem",
                        "color":"#6b8e69","cursor":"pointer","padding":"0 4px"
                    })
                ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                          "marginBottom":"16px","paddingBottom":"12px","borderBottom":"1px solid #c8ddc6"}),
                html.Div([
                    html.Div("📋", style={"fontSize":"2.5rem","textAlign":"center","marginBottom":"12px"}),
                    html.P([
                        "O relatório inclui ", html.Strong("capa institucional"), ", ",
                        html.Strong("indicadores-chave"), ", ",
                        html.Strong("5 análises interpretativas automáticas"), " e ",
                        html.Strong("tabela de cargos"), ". Clique em 'Imprimir' para abrir o diálogo de impressão/PDF do navegador."
                    ], style={"fontSize":"0.85rem","color":"#6b8e69","textAlign":"center","lineHeight":"1.65","marginBottom":"20px"}),
                    html.Button([html.Span("🖨 "), html.Span("Abrir Diálogo de Impressão")],
                        id="btn-print-pdf", n_clicks=0, style={
                            "width":"100%","padding":"13px","background":"#175414","color":"white",
                            "border":"none","borderRadius":"8px","fontWeight":"700","fontSize":"0.92rem",
                            "cursor":"pointer","fontFamily":"Plus Jakarta Sans,sans-serif",
                        }),
                ]),
            ], style={
                "background":"#ffffff","borderRadius":"16px","padding":"28px 32px",
                "width":"440px","boxShadow":"0 12px 48px rgba(0,0,0,0.28)","zIndex":9001,
                "fontFamily":"Plus Jakarta Sans,sans-serif",
            })
        ]),
        print_content,
    ])

    return modal


# ── Clientside callbacks ──────────────────────────────────────
app.clientside_callback(
    """
    function(n) {
        if (n > 0) {
            var overlay = document.getElementById('pdf-overlay');
            if (overlay) overlay.style.display = 'none';
            setTimeout(function(){ window.print(); }, 200);
        }
        return false;
    }
    """,
    Output('btn-print-pdf', 'disabled'),
    Input('btn-print-pdf', 'n_clicks'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n) {
        if (n > 0) {
            var c = document.getElementById('pdf-modal-container');
            if (c) c.innerHTML = '';
        }
        return {};
    }
    """,
    Output('pdf-modal-container', 'style'),
    Input('btn-close-pdf-modal', 'n_clicks'),
    prevent_initial_call=True
)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
