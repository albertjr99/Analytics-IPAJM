"""
IPAJM Analytics 360° — Dashboard Estratégico
Conforme Especificação Técnica e Funcional do IPAJM
Eixos: Nossa Gente | Como nos Mantemos | Prova de Vida
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
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
    title="IPAJM · Analytics 360°",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
server = app.server

# ── Dados ─────────────────────────────────────────────────────
df = pd.read_parquet(os.path.join(BASE_PATH, 'data_processed.parquet'))
recad_path = os.path.join(BASE_PATH, 'data_recadastramento.parquet')
df_recad = pd.read_parquet(recad_path) if os.path.exists(recad_path) else pd.DataFrame()

UPDATE_DATE = date.today().strftime("%d/%m/%Y")
ALL_ORGAOS = sorted([o for o in df['NO_ORGAO'].dropna().unique() if str(o) != 'nan'])

# ── Plotly base ───────────────────────────────────────────────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
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
GREENS = ["#175414","#1e6e19","#2a8a24","#3db836","#72d96a","#b5e4b2","#e8f5e6"]

# ── Helpers ───────────────────────────────────────────────────
def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def fmt_mil(v):
    if v >= 1e9:
        s = f"{v/1e9:.1f}".replace(".",","); return f"R$ {s}B"
    s = f"{v/1e6:.1f}".replace(".",","); return f"R$ {s}M"

def fmt_int(v):
    return f"{int(v):,}".replace(",",".")

def kpi_card(value, label, delta=None, icon=None):
    ch = [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value")]
    if delta:
        ch.append(html.Div(delta, className="kpi-delta"))
    return html.Div(ch, className="kpi-card")

def chart_card(title, gid, tooltip=None):
    header_children = [html.Span(title, className="chart-card-title")]
    if tooltip:
        header_children.append(html.Span("ⓘ", title=tooltip,
            style={"cursor":"help","marginLeft":"8px","color":"#9ab898","fontSize":"0.85rem"}))
    return html.Div([
        html.Div(header_children, className="chart-card-header"),
        dcc.Graph(id=gid, config={"displayModeBar": False, "responsive": True},
                  style={"height":"320px"})
    ], className="chart-card h-100")

DROP_STYLE = {"fontFamily":"Plus Jakarta Sans,sans-serif","fontSize":"0.88rem","minWidth":"180px"}

# ── Tooltip texts (linguagem cidadã) ─────────────────────────
TIP_CONTRIB_SEG = "Contribuição do Segurado: valor descontado do salário do servidor para financiar sua aposentadoria."
TIP_CONTRIB_PAT = "Contribuição Patronal: valor que o Estado, como empregador, deposita no fundo previdenciário."
TIP_RECAD = "Prova de Vida: recadastramento anual obrigatório para manutenção do benefício previdenciário."

# ══════════════════════════════════════════════════════════════
#  LAYOUT — Navegação por Abas (4 Eixos)
# ══════════════════════════════════════════════════════════════
def build_tab_label(icon, text):
    return html.Div([html.Span(icon, style={"marginRight":"6px"}), text],
                     style={"display":"flex","alignItems":"center"})

app.layout = html.Div([
    # ── Header
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

    # ── Tabs de navegação
    html.Div([
        dcc.Tabs(id='main-tabs', value='tab-gente', children=[
            dcc.Tab(label='👥 Nossa Gente', value='tab-gente',
                    className='nav-tab', selected_className='nav-tab--selected'),
            dcc.Tab(label='💰 Como nos Mantemos', value='tab-receitas',
                    className='nav-tab', selected_className='nav-tab--selected'),
            dcc.Tab(label='✅ Prova de Vida', value='tab-recad',
                    className='nav-tab', selected_className='nav-tab--selected'),
        ], className='nav-tabs-bar'),
    ], className="tabs-wrapper"),

    # ── Conteúdo dinâmico
    html.Div(id='tab-content'),

    # ── Footer
    html.Footer([
        html.Span("IPAJM · Instituto de Previdência dos Servidores do Estado do Espírito Santo"),
        html.Span(f"Dados referentes ao exercício 2026 · Build {UPDATE_DATE}")
    ], className="ipajm-footer"),

    dcc.Store(id='store-report-data'),
    html.Div(id='pdf-modal-container'),
], style={"minHeight":"100vh","backgroundColor":"#f0f4f0"})


# ══════════════════════════════════════════════════════════════
#  CALLBACK — Renderizar aba selecionada
# ══════════════════════════════════════════════════════════════
@app.callback(Output('tab-content','children'), Input('main-tabs','value'))
def render_tab(tab):
    if tab == 'tab-gente':
        return build_tab_gente()
    elif tab == 'tab-receitas':
        return build_tab_receitas()
    elif tab == 'tab-recad':
        return build_tab_recad()
    return html.Div("Selecione uma aba.")


# ══════════════════════════════════════════════════════════════
#  ABA 1 — NOSSA GENTE (Módulo Demográfico)
# ══════════════════════════════════════════════════════════════
def build_tab_gente():
    return html.Div([
        html.Div("Filtros de Análise", className="section-label"),
        html.Div([
            html.Div([
                html.Label("Categoria", className="sel-label"),
                dcc.Dropdown(id='filter-category',
                    options=[{"label":"Todas as categorias","value":"__all__"}] +
                            [{"label":i,"value":i} for i in sorted(df['CATEGORIA'].unique())],
                    value="__all__", clearable=False, searchable=False,
                    className="drop-select", style=DROP_STYLE)
            ], className="filter-group", style={"flex":"1"}),
            html.Div([
                html.Label("Sexo", className="sel-label"),
                dcc.Dropdown(id='filter-sex',
                    options=[{"label":"Todos","value":"__all__"}] +
                            [{"label":i,"value":i} for i in
                             sorted([s for s in df['SEXO_DESC'].unique() if s != 'Não Informado']) + ['Não Informado']],
                    value="__all__", clearable=False, searchable=False,
                    className="drop-select", style=DROP_STYLE)
            ], className="filter-group", style={"flex":"1"}),
            html.Div([
                html.Label("Órgão", className="sel-label"),
                dcc.Dropdown(id='filter-orgao',
                    options=[{"label":"Todos os órgãos","value":"__all__"}] +
                            [{"label":i,"value":i} for i in ALL_ORGAOS],
                    value="__all__", clearable=False, searchable=True,
                    className="drop-select", style=DROP_STYLE,
                    placeholder="Todos os órgãos", optionHeight=36)
            ], className="filter-group", style={"flex":"1.5"}),
        ], className="filter-bar"),

        html.Div("Indicadores-Chave", className="section-label"),
        html.Div(id='kpi-row', className="kpi-grid"),

        html.Div("Distribuições", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Distribuição por Categoria","graph-cat"), md=4, className="mb-4"),
            dbc.Col(chart_card("Pirâmide Etária","graph-age",
                               tooltip="Distribuição dos servidores por faixa de idade"), md=8, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(chart_card("Remuneração Média por Órgão (Top 10)","graph-salary",
                               tooltip="Média salarial dos 10 órgãos com maior remuneração"), md=8, className="mb-4"),
            dbc.Col(chart_card("Distribuição por Sexo","graph-sex"), md=4, className="mb-4"),
        ]),

        html.Div("Análises Avançadas", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Top 10 Cargos por Remuneração Média (Ativos)","graph-top-cargos"), md=7, className="mb-4"),
            dbc.Col(chart_card("Remuneração Média por Categoria","graph-contrib"), md=5, className="mb-4"),
        ]),

        html.Div("Detalhamento de Cargos", className="section-label"),
        html.Div([
            html.Div(html.Span("Principais Cargos", className="chart-card-title"), className="chart-card-header"),
            html.Div(id='table-output')
        ], className="chart-card mb-5"),
    ], className="page-body")


# ══════════════════════════════════════════════════════════════
#  ABA 2 — COMO NOS MANTEMOS (Receitas / Contribuições)
# ══════════════════════════════════════════════════════════════
def build_tab_receitas():
    return html.Div([
        html.Div("Indicadores de Custeio", className="section-label"),
        html.Div(id='kpi-receitas', className="kpi-grid"),

        html.Div("Contribuições por Categoria", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Contribuição do Segurado vs Base de Cálculo por Categoria",
                               "graph-contrib-cat",
                               tooltip=TIP_CONTRIB_SEG), md=6, className="mb-4"),
            dbc.Col(chart_card("Volume de Contribuição por Categoria",
                               "graph-contrib-vol",
                               tooltip="Total arrecadado em contribuições por categoria de servidor"), md=6, className="mb-4"),
        ]),

        html.Div("Análise por Órgão", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Top 10 Órgãos — Contribuição Total",
                               "graph-contrib-orgao",
                               tooltip=TIP_CONTRIB_PAT), md=7, className="mb-4"),
            dbc.Col(chart_card("Relação Contribuição / Remuneração por Categoria",
                               "graph-contrib-ratio",
                               tooltip="Percentual da remuneração destinado à contribuição previdenciária"), md=5, className="mb-4"),
        ]),

        html.Div("Detalhamento", className="section-label"),
        html.Div([
            html.Div(html.Span("Contribuições por Órgão (Top 15)", className="chart-card-title"),
                     className="chart-card-header"),
            html.Div(id='table-receitas')
        ], className="chart-card mb-5"),
    ], className="page-body")


# ══════════════════════════════════════════════════════════════
#  ABA 3 — PROVA DE VIDA (Recadastramento)
# ══════════════════════════════════════════════════════════════
def build_tab_recad():
    if df_recad.empty:
        return html.Div([
            html.Div("Dados de recadastramento não disponíveis.",
                     style={"padding":"60px","textAlign":"center","color":"#6b8e69","fontSize":"1.1rem"})
        ], className="page-body")

    return html.Div([
        html.Div("Indicadores de Recadastramento — Prova de Vida 2025", className="section-label"),
        html.Div(id='kpi-recad', className="kpi-grid"),

        html.Div("Visão Geral", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Status do Recadastramento","graph-recad-status",
                               tooltip=TIP_RECAD), md=4, className="mb-4"),
            dbc.Col(chart_card("Recadastramento por Modalidade","graph-recad-modal",
                               tooltip="Gov.br = recadastramento digital | Sisprev Web = sistema próprio do IPAJM"), md=4, className="mb-4"),
            dbc.Col(chart_card("Recadastramento por Categoria","graph-recad-cat"), md=4, className="mb-4"),
        ]),

        html.Div("Análise Temporal e Demográfica", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Volume por Mês de Aniversário","graph-recad-mes"), md=6, className="mb-4"),
            dbc.Col(chart_card("Distribuição por Faixa Etária","graph-recad-age"), md=6, className="mb-4"),
        ]),

        html.Div("Análise por Órgão e Sexo", className="section-label"),
        dbc.Row([
            dbc.Col(chart_card("Top 10 Órgãos — Não Recadastrados","graph-recad-orgao",
                               tooltip="Órgãos com maior número de beneficiários pendentes de prova de vida"), md=7, className="mb-4"),
            dbc.Col(chart_card("Recadastramento por Sexo","graph-recad-sexo"), md=5, className="mb-4"),
        ]),

        html.Div("Detalhamento", className="section-label"),
        html.Div([
            html.Div(html.Span("Situação por Órgão", className="chart-card-title"),
                     className="chart-card-header"),
            html.Div(id='table-recad')
        ], className="chart-card mb-5"),
    ], className="page-body")


# ══════════════════════════════════════════════════════════════
#  CALLBACK — ABA 1: Nossa Gente
# ══════════════════════════════════════════════════════════════
@app.callback(
    [Output('kpi-row','children'),
     Output('graph-cat','figure'), Output('graph-age','figure'),
     Output('graph-salary','figure'), Output('graph-sex','figure'),
     Output('graph-top-cargos','figure'), Output('graph-contrib','figure'),
     Output('table-output','children'),
     Output('store-report-data','data')],
    [Input('filter-category','value'),
     Input('filter-sex','value'),
     Input('filter-orgao','value')]
)
def update_dashboard(categories, sexes, orgaos):
    cat_filter = None if (not categories or categories == "__all__") else [categories]
    sex_filter = None if (not sexes or sexes == "__all__") else [sexes]
    org_filter = None if (not orgaos or orgaos == "__all__") else [orgaos]

    dff = df[df['CATEGORIA'].isin(cat_filter or df['CATEGORIA'].unique())]
    dff = dff[dff['SEXO_DESC'].isin(sex_filter or df['SEXO_DESC'].unique())]
    if org_filter:
        dff = dff[dff['NO_ORGAO'].isin(org_filter)]

    total = len(dff)
    media_sal = dff['VL_REMUNERACAO'].mean()
    media_idade = dff['IDADE'].mean()
    contrib = dff['VL_CONTRIBUICAO'].sum()

    # Recadastramento cruzado
    total_recad = len(df_recad) if not df_recad.empty else 0
    recad_ok = len(df_recad[df_recad['STATUS_RECAD']=='RECADASTRADO']) if not df_recad.empty else 0
    pct_recad = f"{recad_ok/total_recad*100:.1f}%" if total_recad else "N/D"

    kpis = [
        kpi_card(fmt_int(total), "Total de Servidores", "base completa"),
        kpi_card(fmt_brl(media_sal), "Remuneração Média"),
        kpi_card(f"{media_idade:.1f} anos", "Idade Média"),
        kpi_card(fmt_mil(contrib), "Contribuição Total"),
    ]

    # 1 — Donut Categoria
    cc = dff['CATEGORIA'].value_counts().reset_index()
    fig_cat = go.Figure(go.Pie(labels=cc['CATEGORIA'], values=cc['count'], hole=0.6,
        textinfo='percent', marker=dict(colors=GREENS, line=dict(color="#ffffff",width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,} servidores<extra></extra>"))
    fig_cat.update_layout(**BASE_LAYOUT, showlegend=True, legend=dict(**LEGEND_BASE, orientation="v"))

    # 2 — Faixa Etária
    age_order = ['<18','18-25','26-35','36-45','46-55','56-65','66-75','>75']
    ac = dff['FAIXA_ETARIA'].value_counts().reindex(age_order).fillna(0).reset_index()
    ac['txt'] = ac['count'].apply(lambda x: fmt_int(int(x)))
    fig_age = go.Figure(go.Bar(
        x=ac['count'], y=ac['FAIXA_ETARIA'], orientation='h',
        text=ac['txt'], textposition='outside', textfont=dict(size=10,color="#2d4a2b"),
        marker=dict(color=ac['count'],colorscale=[[0,"#b5e4b2"],[0.5,"#2a8a24"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,} servidores<extra></extra>"))
    fig_age.update_layout(**BASE_LAYOUT)
    fig_age.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True,gridcolor="rgba(180,210,178,.35)",tickformat=","))
    fig_age.update_traces(width=0.65)

    # 3 — Salário por Órgão
    so = dff.groupby('NO_ORGAO')['VL_REMUNERACAO'].mean().sort_values(ascending=True).tail(10).reset_index()
    so['txt'] = so['VL_REMUNERACAO'].apply(fmt_brl)
    fig_sal = go.Figure(go.Bar(
        x=so['VL_REMUNERACAO'], y=so['NO_ORGAO'], orientation='h',
        text=so['txt'], textposition='outside', textfont=dict(size=9,color="#2d4a2b"),
        marker=dict(color=so['VL_REMUNERACAO'],colorscale=[[0,"#b5e4b2"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>"))
    fig_sal.update_layout(**BASE_LAYOUT)
    fig_sal.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True,gridcolor="rgba(180,210,178,.35)"))

    # 4 — Sexo donut
    sc = dff['SEXO_DESC'].value_counts().reset_index()
    fig_sex = go.Figure(go.Pie(labels=sc['SEXO_DESC'], values=sc['count'], hole=0.6,
        textinfo='percent', marker=dict(colors=GREENS, line=dict(color="#ffffff",width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>"))
    fig_sex.update_layout(**BASE_LAYOUT, showlegend=True, legend=dict(**LEGEND_BASE, orientation="v"))

    # 5 — Top Cargos
    ativos_df = dff[dff['CATEGORIA']=='ATIVOS']
    tc = ativos_df.groupby('NO_CARGO')['VL_REMUNERACAO'].mean().sort_values(ascending=True).tail(10).reset_index()
    tc['lbl'] = tc['NO_CARGO'].apply(lambda x: str(x)[:35]+"…" if len(str(x))>35 else str(x))
    tc['txt'] = tc['VL_REMUNERACAO'].apply(fmt_brl)
    fig_tc = go.Figure(go.Bar(
        x=tc['VL_REMUNERACAO'], y=tc['lbl'], orientation='h',
        text=tc['txt'], textposition='outside', textfont=dict(size=9,color="#2d4a2b"),
        marker=dict(color="#1e6e19", opacity=0.85, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>"))
    fig_tc.update_layout(**BASE_LAYOUT)
    fig_tc.update_layout(yaxis=dict(showgrid=False))

    # 6 — Remuneração por Categoria
    rm_cat = dff.groupby('CATEGORIA')['VL_REMUNERACAO'].mean().reset_index()
    rm_cat['txt'] = rm_cat['VL_REMUNERACAO'].apply(fmt_brl)
    fig_contrib = go.Figure(go.Bar(
        x=rm_cat['CATEGORIA'], y=rm_cat['VL_REMUNERACAO'],
        text=rm_cat['txt'], textposition='outside', textfont=dict(size=10,color="#2d4a2b"),
        marker=dict(color=rm_cat['VL_REMUNERACAO'],colorscale=[[0,"#b5e4b2"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>"))
    fig_contrib.update_layout(**BASE_LAYOUT)
    fig_contrib.update_traces(width=0.4)

    # Tabela
    tdf = (dff.groupby('NO_CARGO')
              .agg(Servidores=('VL_REMUNERACAO','count'),
                   Rem_Media=('VL_REMUNERACAO','mean'),
                   Idade_Media=('IDADE','mean'))
              .reset_index().sort_values('Servidores',ascending=False).head(15))
    tdf['Servidores'] = tdf['Servidores'].apply(fmt_int)
    tdf['Rem_Media'] = tdf['Rem_Media'].apply(fmt_brl)
    tdf['Idade_Media'] = tdf['Idade_Media'].apply(lambda x: f"{x:.1f}")
    tdf.columns = ['Cargo','Servidores','Rem. Média','Idade Média']

    table = dash_table.DataTable(
        data=tdf.to_dict('records'),
        columns=[{"name":c,"id":c} for c in tdf.columns],
        style_as_list_view=True, page_size=10,
        style_header={'backgroundColor':'#f2faf1','color':'#175414','fontWeight':'700',
                      'fontSize':'0.67rem','letterSpacing':'0.1em','textTransform':'uppercase',
                      'borderBottom':'2px solid #b0ccae','padding':'12px 16px','textAlign':'center'},
        style_cell={'backgroundColor':'#ffffff','color':'#2d4a2b',
                    'fontFamily':'Plus Jakarta Sans,sans-serif','fontSize':'0.83rem',
                    'padding':'11px 16px','border':'none','borderBottom':'1px solid #d4e6d2','textAlign':'center'},
        style_cell_conditional=[{'if':{'column_id':'Cargo'},'textAlign':'left','paddingLeft':'20px'}],
        style_data_conditional=[
            {'if':{'row_index':'odd'},'backgroundColor':'#fafcfa'},
            {'if':{'state':'active'},'backgroundColor':'#e8f5e6','color':'#175414'}])

    # Report data
    report_data = {
        'total': fmt_int(total), 'media_sal': fmt_brl(media_sal),
        'media_idade': f"{media_idade:.1f}", 'contrib': fmt_mil(contrib),
        'update_date': UPDATE_DATE,
        'categorias': dff['CATEGORIA'].value_counts().to_dict(),
        'top_orgaos': so[['NO_ORGAO','VL_REMUNERACAO']].to_dict('records'),
        'top_cargos': tc[['lbl','VL_REMUNERACAO']].to_dict('records') if not tc.empty else [],
        'dist_sexo': sc.rename(columns={'SEXO_DESC':'label','count':'value'}).to_dict('records'),
        'faixa_etaria': ac.to_dict('records'),
        'rem_cat': rm_cat.to_dict('records'),
        'table': tdf.to_dict('records'),
        'pct_recad': pct_recad,
        'total_recad': fmt_int(total_recad),
        'recad_ok': fmt_int(recad_ok),
        'recad_pendente': fmt_int(total_recad - recad_ok),
    }

    return kpis, fig_cat, fig_age, fig_sal, fig_sex, fig_tc, fig_contrib, table, report_data


# ══════════════════════════════════════════════════════════════
#  CALLBACK — ABA 2: Receitas
# ══════════════════════════════════════════════════════════════
@app.callback(
    [Output('kpi-receitas','children'),
     Output('graph-contrib-cat','figure'), Output('graph-contrib-vol','figure'),
     Output('graph-contrib-orgao','figure'), Output('graph-contrib-ratio','figure'),
     Output('table-receitas','children')],
    Input('main-tabs','value')
)
def update_receitas(tab):
    if tab != 'tab-receitas':
        empty = go.Figure()
        empty.update_layout(**BASE_LAYOUT)
        return [], empty, empty, empty, empty, html.Div()

    contrib_total = df['VL_CONTRIBUICAO'].sum()
    base_total = df['VL_BASE_CALCULO'].sum()
    rem_total = df['VL_REMUNERACAO'].sum()
    aliq_media = (contrib_total / base_total * 100) if base_total else 0

    kpis = [
        kpi_card(fmt_mil(contrib_total), "Contribuição Total do Segurado",
                 TIP_CONTRIB_SEG[:30]+"…"),
        kpi_card(fmt_mil(rem_total), "Massa Salarial Total"),
        kpi_card(fmt_mil(base_total), "Base de Cálculo Total"),
        kpi_card(f"{aliq_media:.2f}%", "Alíquota Média Efetiva",
                 "Contribuição / Base de Cálculo"),
    ]

    # Contrib vs Base por Categoria
    cat_agg = df.groupby('CATEGORIA').agg(
        Contribuicao=('VL_CONTRIBUICAO','sum'),
        Base=('VL_BASE_CALCULO','sum')).reset_index()
    fig_cc = go.Figure()
    fig_cc.add_trace(go.Bar(name='Contribuição', x=cat_agg['CATEGORIA'], y=cat_agg['Contribuicao'],
                            marker_color="#175414",
                            text=cat_agg['Contribuicao'].apply(fmt_mil), textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Contribuição: R$ %{y:,.2f}<extra></extra>"))
    fig_cc.add_trace(go.Bar(name='Base de Cálculo', x=cat_agg['CATEGORIA'], y=cat_agg['Base'],
                            marker_color="#b5e4b2",
                            text=cat_agg['Base'].apply(fmt_mil), textposition='outside',
                            hovertemplate="<b>%{x}</b><br>Base: R$ %{y:,.2f}<extra></extra>"))
    fig_cc.update_layout(**BASE_LAYOUT, barmode='group', showlegend=True,
                         legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    # Volume de Contribuição por Categoria (donut)
    fig_cv = go.Figure(go.Pie(labels=cat_agg['CATEGORIA'], values=cat_agg['Contribuicao'], hole=0.55,
        textinfo='percent+label',
        marker=dict(colors=GREENS, line=dict(color="#ffffff",width=2)),
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"))
    fig_cv.update_layout(**BASE_LAYOUT, showlegend=False)

    # Top 10 Órgãos por Contribuição
    org_c = df.groupby('NO_ORGAO')['VL_CONTRIBUICAO'].sum().sort_values(ascending=True).tail(10).reset_index()
    org_c['txt'] = org_c['VL_CONTRIBUICAO'].apply(fmt_mil)
    fig_co = go.Figure(go.Bar(
        x=org_c['VL_CONTRIBUICAO'], y=org_c['NO_ORGAO'], orientation='h',
        text=org_c['txt'], textposition='outside', textfont=dict(size=9,color="#2d4a2b"),
        marker=dict(color=org_c['VL_CONTRIBUICAO'],colorscale=[[0,"#b5e4b2"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"))
    fig_co.update_layout(**BASE_LAYOUT)
    fig_co.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True,gridcolor="rgba(180,210,178,.35)"))

    # Relação Contrib / Remuneração
    cat_ratio = df.groupby('CATEGORIA').agg(
        C=('VL_CONTRIBUICAO','sum'), R=('VL_REMUNERACAO','sum')).reset_index()
    cat_ratio['pct'] = (cat_ratio['C'] / cat_ratio['R'] * 100).round(2)
    cat_ratio['txt'] = cat_ratio['pct'].apply(lambda x: f"{x:.1f}%")
    fig_cr = go.Figure(go.Bar(
        x=cat_ratio['CATEGORIA'], y=cat_ratio['pct'],
        text=cat_ratio['txt'], textposition='outside', textfont=dict(size=11,color="#2d4a2b"),
        marker=dict(color=cat_ratio['pct'],colorscale=[[0,"#b5e4b2"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"))
    fig_cr.update_layout(**BASE_LAYOUT)
    fig_cr.update_traces(width=0.4)

    # Tabela
    tbl = (df.groupby('NO_ORGAO').agg(
        Servidores=('VL_REMUNERACAO','count'),
        Contrib_Total=('VL_CONTRIBUICAO','sum'),
        Rem_Media=('VL_REMUNERACAO','mean'),
        Base_Media=('VL_BASE_CALCULO','mean'))
        .reset_index().sort_values('Contrib_Total',ascending=False).head(15))
    tbl['Servidores'] = tbl['Servidores'].apply(fmt_int)
    tbl['Contrib_Total'] = tbl['Contrib_Total'].apply(fmt_mil)
    tbl['Rem_Media'] = tbl['Rem_Media'].apply(fmt_brl)
    tbl['Base_Media'] = tbl['Base_Media'].apply(fmt_brl)
    tbl.columns = ['Órgão','Servidores','Contrib. Total','Rem. Média','Base Média']

    table_r = dash_table.DataTable(
        data=tbl.to_dict('records'),
        columns=[{"name":c,"id":c} for c in tbl.columns],
        style_as_list_view=True, page_size=10,
        style_header={'backgroundColor':'#f2faf1','color':'#175414','fontWeight':'700',
                      'fontSize':'0.67rem','letterSpacing':'0.1em','textTransform':'uppercase',
                      'borderBottom':'2px solid #b0ccae','padding':'12px 16px','textAlign':'center'},
        style_cell={'backgroundColor':'#ffffff','color':'#2d4a2b',
                    'fontFamily':'Plus Jakarta Sans,sans-serif','fontSize':'0.83rem',
                    'padding':'11px 16px','border':'none','borderBottom':'1px solid #d4e6d2','textAlign':'center'},
        style_cell_conditional=[{'if':{'column_id':'Órgão'},'textAlign':'left','paddingLeft':'20px'}],
        style_data_conditional=[
            {'if':{'row_index':'odd'},'backgroundColor':'#fafcfa'},
            {'if':{'state':'active'},'backgroundColor':'#e8f5e6','color':'#175414'}])

    return kpis, fig_cc, fig_cv, fig_co, fig_cr, table_r


# ══════════════════════════════════════════════════════════════
#  CALLBACK — ABA 3: Prova de Vida
# ══════════════════════════════════════════════════════════════
@app.callback(
    [Output('kpi-recad','children'),
     Output('graph-recad-status','figure'), Output('graph-recad-modal','figure'),
     Output('graph-recad-cat','figure'), Output('graph-recad-mes','figure'),
     Output('graph-recad-age','figure'), Output('graph-recad-orgao','figure'),
     Output('graph-recad-sexo','figure'), Output('table-recad','children')],
    Input('main-tabs','value')
)
def update_recad(tab):
    empty = go.Figure()
    empty.update_layout(**BASE_LAYOUT)
    if tab != 'tab-recad' or df_recad.empty:
        return [], empty, empty, empty, empty, empty, empty, empty, html.Div()

    rdf = df_recad
    total = len(rdf)
    recad = len(rdf[rdf['STATUS_RECAD']=='RECADASTRADO'])
    pendente = total - recad
    pct = recad/total*100 if total else 0

    # Modalidades (apenas recadastrados)
    rec_only = rdf[rdf['STATUS_RECAD']=='RECADASTRADO']
    gov_br = len(rec_only[rec_only['MODALIDADE_RECAD']=='GOV BR'])
    sisprev = len(rec_only[rec_only['MODALIDADE_RECAD']=='SISPREV WEB'])
    pct_digital = gov_br/recad*100 if recad else 0

    kpis = [
        kpi_card(fmt_int(total), "Total Segurados", "universo prova de vida"),
        kpi_card(f"{pct:.1f}%", "Taxa de Recadastramento", f"{fmt_int(recad)} recadastrados"),
        kpi_card(fmt_int(pendente), "Pendentes", "não recadastrados"),
        kpi_card(f"{pct_digital:.1f}%", "Recad. Digital (Gov.br)", f"{fmt_int(gov_br)} via Gov.br"),
    ]

    # 1 — Status donut
    st = rdf['STATUS_RECAD'].value_counts().reset_index()
    colors_st = ["#175414", "#e74c3c"]
    fig_st = go.Figure(go.Pie(labels=st['STATUS_RECAD'], values=st['count'], hole=0.6,
        textinfo='percent+label', marker=dict(colors=colors_st, line=dict(color="#fff",width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>"))
    fig_st.update_layout(**BASE_LAYOUT, showlegend=False)

    # 2 — Modalidade
    mod = rec_only['MODALIDADE_RECAD'].value_counts().reset_index()
    fig_mod = go.Figure(go.Bar(
        x=mod['MODALIDADE_RECAD'], y=mod['count'],
        text=mod['count'].apply(fmt_int), textposition='outside',
        textfont=dict(size=10,color="#2d4a2b"),
        marker=dict(color=["#175414","#2a8a24","#72d96a"][:len(mod)], line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>"))
    fig_mod.update_layout(**BASE_LAYOUT)
    fig_mod.update_traces(width=0.5)

    # 3 — Por Categoria
    cat_r = rdf.groupby(['RECAD_CAT_SIMPLES','STATUS_RECAD']).size().reset_index(name='count')
    cats_uni = cat_r['RECAD_CAT_SIMPLES'].unique()
    fig_cat_r = go.Figure()
    for i, st_name in enumerate(['RECADASTRADO','NÃO RECADASTRADO']):
        sub = cat_r[cat_r['STATUS_RECAD']==st_name]
        fig_cat_r.add_trace(go.Bar(
            name=st_name.title(), x=sub['RECAD_CAT_SIMPLES'], y=sub['count'],
            marker_color=["#175414","#e74c3c"][i],
            text=sub['count'].apply(fmt_int), textposition='outside',
            hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>"))
    fig_cat_r.update_layout(**BASE_LAYOUT, barmode='group',
                            showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    # 4 — Por mês de aniversário
    mes_order = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    mes_r = rdf.groupby(['MES_ANIV_DESC','STATUS_RECAD']).size().reset_index(name='count')
    fig_mes = go.Figure()
    for i, st_name in enumerate(['RECADASTRADO','NÃO RECADASTRADO']):
        sub = mes_r[mes_r['STATUS_RECAD']==st_name]
        sub = sub.set_index('MES_ANIV_DESC').reindex(mes_order).fillna(0).reset_index()
        fig_mes.add_trace(go.Bar(
            name=st_name.title(), x=sub['MES_ANIV_DESC'], y=sub['count'],
            marker_color=["#175414","#e74c3c"][i],
            hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>"))
    fig_mes.update_layout(**BASE_LAYOUT, barmode='stack',
                          showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    # 5 — Faixa etária
    fe_order = ['<50','50-60','61-70','71-80','80+']
    fe = rdf['FAIXA_ETARIA_RECAD'].value_counts().reindex(fe_order).fillna(0).reset_index()
    fe['txt'] = fe['count'].apply(lambda x: fmt_int(int(x)))
    fig_fe = go.Figure(go.Bar(
        x=fe['count'], y=fe['FAIXA_ETARIA_RECAD'], orientation='h',
        text=fe['txt'], textposition='outside', textfont=dict(size=10,color="#2d4a2b"),
        marker=dict(color=fe['count'],colorscale=[[0,"#b5e4b2"],[0.5,"#2a8a24"],[1,"#175414"]],line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>"))
    fig_fe.update_layout(**BASE_LAYOUT)
    fig_fe.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True,gridcolor="rgba(180,210,178,.35)"))

    # 6 — Top órgãos não recadastrados
    nao = rdf[rdf['STATUS_RECAD']=='NÃO RECADASTRADO']
    org_nao = nao['RECAD_ORGAO'].value_counts().head(10).sort_values(ascending=True).reset_index()
    org_nao.columns = ['ORGAO','count']
    org_nao['txt'] = org_nao['count'].apply(fmt_int)
    fig_org = go.Figure(go.Bar(
        x=org_nao['count'], y=org_nao['ORGAO'], orientation='h',
        text=org_nao['txt'], textposition='outside', textfont=dict(size=9,color="#2d4a2b"),
        marker=dict(color="#e74c3c", opacity=0.85, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,} pendentes<extra></extra>"))
    fig_org.update_layout(**BASE_LAYOUT)
    fig_org.update_layout(yaxis=dict(showgrid=False))

    # 7 — Sexo
    sx = rdf.groupby(['SEXO_DESC','STATUS_RECAD']).size().reset_index(name='count')
    fig_sx = go.Figure()
    for i, st_name in enumerate(['RECADASTRADO','NÃO RECADASTRADO']):
        sub = sx[sx['STATUS_RECAD']==st_name]
        fig_sx.add_trace(go.Bar(
            name=st_name.title(), x=sub['SEXO_DESC'], y=sub['count'],
            marker_color=["#175414","#e74c3c"][i],
            text=sub['count'].apply(fmt_int), textposition='outside',
            hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>"))
    fig_sx.update_layout(**BASE_LAYOUT, barmode='group',
                         showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    # Tabela por órgão
    tbl = rdf.groupby('RECAD_ORGAO').agg(
        Total=('STATUS_RECAD','count'),
        Recadastrados=('STATUS_RECAD', lambda x: (x=='RECADASTRADO').sum()),
    ).reset_index()
    tbl['Pendentes'] = tbl['Total'] - tbl['Recadastrados']
    tbl['Taxa'] = (tbl['Recadastrados'] / tbl['Total'] * 100).round(1)
    tbl = tbl.sort_values('Total', ascending=False).head(15)
    tbl['Total'] = tbl['Total'].apply(fmt_int)
    tbl['Recadastrados'] = tbl['Recadastrados'].apply(fmt_int)
    tbl['Pendentes'] = tbl['Pendentes'].apply(fmt_int)
    tbl['Taxa'] = tbl['Taxa'].apply(lambda x: f"{x}%")
    tbl.columns = ['Órgão','Total','Recadastrados','Pendentes','Taxa']

    table_rc = dash_table.DataTable(
        data=tbl.to_dict('records'),
        columns=[{"name":c,"id":c} for c in tbl.columns],
        style_as_list_view=True, page_size=10,
        style_header={'backgroundColor':'#f2faf1','color':'#175414','fontWeight':'700',
                      'fontSize':'0.67rem','letterSpacing':'0.1em','textTransform':'uppercase',
                      'borderBottom':'2px solid #b0ccae','padding':'12px 16px','textAlign':'center'},
        style_cell={'backgroundColor':'#ffffff','color':'#2d4a2b',
                    'fontFamily':'Plus Jakarta Sans,sans-serif','fontSize':'0.83rem',
                    'padding':'11px 16px','border':'none','borderBottom':'1px solid #d4e6d2','textAlign':'center'},
        style_cell_conditional=[{'if':{'column_id':'Órgão'},'textAlign':'left','paddingLeft':'20px'}],
        style_data_conditional=[
            {'if':{'row_index':'odd'},'backgroundColor':'#fafcfa'},
            {'if':{'state':'active'},'backgroundColor':'#e8f5e6','color':'#175414'}])

    return kpis, fig_st, fig_mod, fig_cat_r, fig_mes, fig_fe, fig_org, fig_sx, table_rc


# ══════════════════════════════════════════════════════════════
#  PDF Modal + Relatório
# ══════════════════════════════════════════════════════════════
@app.callback(
    Output('pdf-modal-container','children'),
    Input('btn-export-pdf','n_clicks'),
    State('store-report-data','data'),
    prevent_initial_call=True
)
def open_pdf_modal(n, rd):
    if not n or not rd:
        return []

    cats = rd.get('categorias', {})
    cat_lines = " | ".join([f"{k}: {fmt_int(v)}" for k, v in cats.items()])

    dist_sexo = {r['label']: r['value'] for r in rd.get('dist_sexo', [])}
    fem = dist_sexo.get('Feminino', 0)
    masc = dist_sexo.get('Masculino', 0)
    total_sx = fem + masc
    pct_fem = (fem/total_sx*100) if total_sx else 0
    pct_masc = (masc/total_sx*100) if total_sx else 0

    fe_data = {r['FAIXA_ETARIA']: int(r['count']) for r in rd.get('faixa_etaria', [])}
    peak_faixa = max(fe_data, key=fe_data.get) if fe_data else "N/D"
    peak_count = fmt_int(fe_data.get(peak_faixa, 0))

    tc_top = rd['top_cargos'][0] if rd.get('top_cargos') else {}
    to_top = rd['top_orgaos'][-1] if rd.get('top_orgaos') else {}

    cc_data = {r['CATEGORIA']: r['VL_REMUNERACAO'] for r in rd.get('rem_cat', [])}
    maior_rem_cat = max(cc_data, key=cc_data.get) if cc_data else "N/D"

    # ── Estilos
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
                             style={"fontSize":"0.65rem","fontWeight":"700","color":"#175414","letterSpacing":"0.03em"}),
                    html.Div(f"Relatório de Análise de Indicadores · {rd['update_date']}",
                             style={"fontSize":"0.58rem","color":"#6b8e69",
                                    "fontFamily":"'JetBrains Mono',monospace","marginTop":"2px"}),
                ], style={"flex":"1"}),
                html.Div(html.Img(src='/assets/Brasao_Governo.png',
                    style={"height":"38px","width":"auto","filter":"brightness(0) invert(1)"}),
                    style={"background":"#175414","borderRadius":"8px","padding":"8px 10px",
                           "display":"flex","alignItems":"center","justifyContent":"center"}),
            ], style={"display":"flex","alignItems":"center","gap":"16px",
                      "padding":"14px 0 10px","marginBottom":"18px","borderBottom":"2px solid #175414"}),
        ], className="report-page-header")

    def mini_tbl(headers, rows):
        return html.Table([
            html.Thead(html.Tr([html.Th(h, style=_TH) for h in headers])),
            html.Tbody([
                html.Tr([html.Td(c, style=_TD_L if j==0 else _TD) for j,c in enumerate(r)],
                         style={"background":"#fff" if i%2==0 else "#f8fbf8","borderBottom":"1px solid #d4e6d2"})
                for i,r in enumerate(rows)])
        ], style=_TBOX)

    cat_rows = [[k, fmt_int(v)] for k, v in cats.items()]
    tbl_cat = mini_tbl(["Categoria","Servidores"], cat_rows)

    fe_rows = [[r['FAIXA_ETARIA'], fmt_int(int(r['count']))]
               for r in rd.get('faixa_etaria',[]) if int(r['count'])>0]
    tbl_fe = mini_tbl(["Faixa Etária","Servidores"], fe_rows)

    gen_rows = [[r['label'], fmt_int(int(r['value'])),
                 f"{r['value']/total_sx*100:.1f}%" if total_sx else "—"]
                for r in rd.get('dist_sexo',[])]
    tbl_gen = mini_tbl(["Sexo","Servidores","%"], gen_rows)

    org_rows = [[r['NO_ORGAO'], fmt_brl(r['VL_REMUNERACAO'])]
                for r in reversed(rd.get('top_orgaos',[]))]
    tbl_org = mini_tbl(["Órgão (Top 10)","Rem. Média"], org_rows)

    cargo_rows = [[r['lbl'], fmt_brl(r['VL_REMUNERACAO'])]
                  for r in reversed(rd.get('top_cargos',[]))]
    tbl_cargo = mini_tbl(["Cargo — Ativos (Top 10)","Rem. Média"], cargo_rows)

    rc_rows = [[r['CATEGORIA'], fmt_brl(r['VL_REMUNERACAO'])] for r in rd.get('rem_cat',[])]
    tbl_rc = mini_tbl(["Categoria","Rem. Média"], rc_rows)

    # ── Seções de análise
    sec1 = html.Div([
        html.H3("1. Composição da Força de Trabalho", style=_H3),
        html.P([
            "O universo analisado abrange ", html.Strong(rd['total']),
            " servidores vinculados ao RPPS do Estado do Espírito Santo, distribuídos nas categorias: ",
            cat_lines, ". Este contingente representa a massa segurada sob gestão do IPAJM."
        ], style=_P),
        tbl_cat,
    ], style=_SEC)

    sec2 = html.Div([
        html.H3("2. Perfil Demográfico e Envelhecimento", style=_H3),
        html.P([
            "A idade média é de ", html.Strong(f"{rd['media_idade']} anos"),
            ", com maior concentração na faixa ", html.Strong(peak_faixa),
            " (", html.Strong(f"{peak_count} servidores"), ")."
        ], style=_P),
        tbl_fe,
    ], style=_SEC)

    sec3 = html.Div([
        html.H3("3. Análise de Gênero", style=_H3),
        html.P([
            html.Strong(f"{pct_fem:.1f}% feminino"), f" ({fmt_int(int(fem))}) e ",
            html.Strong(f"{pct_masc:.1f}% masculino"), f" ({fmt_int(int(masc))})."
        ], style=_P),
        tbl_gen,
    ], style=_SEC)

    sec4 = html.Div([
        html.H3("4. Remuneração e Impacto Financeiro", style=_H3),
        html.P([
            "Remuneração média: ", html.Strong(rd['media_sal']),
            ". Categoria com maior média: ", html.Strong(maior_rem_cat), "."
        ], style=_P),
        tbl_org, html.Div(style={"height":"10px"}), tbl_cargo,
    ], style=_SEC)

    sec5 = html.Div([
        html.H3("5. Contribuições Previdenciárias", style=_H3),
        html.P([
            "Contribuição total: ", html.Strong(rd['contrib']), ". ",
            "A sustentabilidade depende da relação contribuição/benefícios."
        ], style=_P),
        tbl_rc,
    ], style=_SEC)

    # Seção de Recadastramento no PDF
    sec6 = html.Div([
        html.H3("6. Prova de Vida — Recadastramento 2025", style=_H3),
        html.P([
            "Total de segurados no universo de prova de vida: ", html.Strong(rd.get('total_recad','N/D')),
            ". Taxa de recadastramento: ", html.Strong(rd.get('pct_recad','N/D')),
            ". Pendentes: ", html.Strong(rd.get('recad_pendente','N/D')), "."
        ], style=_P),
        mini_tbl(["Indicador","Valor"], [
            ["Total Segurados", rd.get('total_recad','N/D')],
            ["Recadastrados", rd.get('recad_ok','N/D')],
            ["Pendentes", rd.get('recad_pendente','N/D')],
            ["Taxa", rd.get('pct_recad','N/D')],
        ]),
    ], style=_SEC)

    print_content = html.Div(id="print-report-content", children=[
        # CAPA
        html.Div([
            html.Div(style={"height":"60px"}),
            html.Div([
                html.Img(src='/assets/logo-ipajm.png', style={
                    "height":"80px","filter":"brightness(0) invert(1)","display":"block","margin":"0 auto 28px"}),
                html.H1("Relatório de Análise de Indicadores", style={
                    "fontFamily":"'DM Serif Display',serif","fontSize":"2.4rem","color":"#fff",
                    "textAlign":"center","margin":"0 0 8px"}),
                html.H2("Servidores do Estado do Espírito Santo", style={
                    "fontFamily":"'DM Serif Display',serif","fontSize":"1.35rem",
                    "color":"rgba(255,255,255,0.75)","textAlign":"center","fontWeight":"normal","margin":"0 0 40px"}),
                html.Div([
                    *[html.Div([
                        html.Div(l, style={"fontSize":"0.58rem","color":"rgba(255,255,255,0.50)",
                                           "textTransform":"uppercase","letterSpacing":"0.1em","marginBottom":"6px"}),
                        html.Div(v, style={"fontSize":"1.8rem","fontFamily":"'DM Serif Display',serif",
                                           "color":"#fff","lineHeight":"1","whiteSpace":"nowrap"}),
                    ], style={"textAlign":"center","padding":"18px 28px","flex":"1",
                              "display":"flex","flexDirection":"column","justifyContent":"center","alignItems":"center",
                              "borderRight":"1px solid rgba(255,255,255,0.18)" if i<3 else "none"})
                    for i,(v,l) in enumerate([
                        (rd['total'],"Total Servidores"), (rd['media_sal'],"Remuneração Média"),
                        (f"{rd['media_idade']} anos","Idade Média"), (rd['contrib'],"Contribuição Total")])]
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

        # PÁG 2
        html.Div([rpt_hdr(), sec1, sec2],
                 className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),
        # PÁG 3
        html.Div([rpt_hdr(), sec3, sec4],
                 className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),
        # PÁG 4
        html.Div([rpt_hdr(), sec5, sec6],
                 className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),
        # PÁG 5 — Tabela
        html.Div([
            rpt_hdr(),
            html.H3("Detalhamento dos Principais Cargos", style={**_H3, "marginTop":"10px"}),
            html.Table([
                html.Thead(html.Tr([html.Th(c, style=_TH) for c in ['Cargo','Servidores','Rem. Média','Idade Média']])),
                html.Tbody([
                    html.Tr([
                        html.Td(row.get('Cargo',''), style={**_TD,"textAlign":"left"}),
                        html.Td(row.get('Servidores',''), style=_TD),
                        html.Td(row.get('Rem. Média',''), style=_TD),
                        html.Td(row.get('Idade Média',''), style=_TD),
                    ], style={"background":"#fff" if i%2==0 else "#f8fbf8","borderBottom":"1px solid #d4e6d2"})
                    for i,row in enumerate(rd.get('table',[]))])
            ], style={"width":"100%","borderCollapse":"collapse","border":"1px solid #c8ddc6","overflow":"hidden"}),
        ], className="report-section", style={"padding":"20px 40px","pageBreakBefore":"always"}),

        # Rodapé
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
            "display":"flex","alignItems":"center","justifyContent":"center"},
        children=[
            html.Div([
                html.Div([
                    html.Div([
                        html.Img(src='/assets/logo-ipajm.png', style={"height":"28px","filter":"invert(25%) sepia(60%) saturate(700%) hue-rotate(100deg)"}),
                        html.Span("Exportar Relatório PDF", style={"fontWeight":"700","fontSize":"1rem","color":"#0f2e0d","marginLeft":"10px"}),
                    ], style={"display":"flex","alignItems":"center"}),
                    html.Button("✕", id="btn-close-pdf-modal", style={
                        "background":"none","border":"none","fontSize":"1.1rem",
                        "color":"#6b8e69","cursor":"pointer","padding":"0 4px"})
                ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
                          "marginBottom":"16px","paddingBottom":"12px","borderBottom":"1px solid #c8ddc6"}),
                html.Div([
                    html.Div("📋", style={"fontSize":"2.5rem","textAlign":"center","marginBottom":"12px"}),
                    html.P([
                        "O relatório inclui ", html.Strong("capa institucional"), ", ",
                        html.Strong("indicadores-chave"), ", ",
                        html.Strong("6 análises interpretativas"), ", ",
                        html.Strong("prova de vida"), " e ",
                        html.Strong("tabela de cargos"), "."
                    ], style={"fontSize":"0.85rem","color":"#6b8e69","textAlign":"center",
                              "lineHeight":"1.65","marginBottom":"20px"}),
                    html.Button([html.Span("🖨 "), html.Span("Abrir Diálogo de Impressão")],
                        id="btn-print-pdf", n_clicks=0, style={
                            "width":"100%","padding":"13px","background":"#175414","color":"white",
                            "border":"none","borderRadius":"8px","fontWeight":"700","fontSize":"0.92rem",
                            "cursor":"pointer","fontFamily":"Plus Jakarta Sans,sans-serif"}),
                ]),
            ], style={"background":"#ffffff","borderRadius":"16px","padding":"28px 32px",
                      "width":"440px","boxShadow":"0 12px 48px rgba(0,0,0,0.28)","zIndex":9001,
                      "fontFamily":"Plus Jakarta Sans,sans-serif"})
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
    Output('btn-print-pdf','disabled'),
    Input('btn-print-pdf','n_clicks'),
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
    Output('pdf-modal-container','style'),
    Input('btn-close-pdf-modal','n_clicks'),
    prevent_initial_call=True
)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
