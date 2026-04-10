"""
IPAJM Analytics 360° — Painel Estratégico
Eixos: Nossa Gente | Como nos Mantemos | Garantia de Direitos | Prova de Vida
"""

import os
import re
import unicodedata
from datetime import date

import dash
from dash import Input, Output, State, dcc, html, dash_table
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ──────────────────────────────────────────────────────────────
# Base app
# ──────────────────────────────────────────────────────────────
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
UPDATE_DATE = date.today().strftime("%d/%m/%Y")

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="IPAJM · Analytics 360°",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server


# ──────────────────────────────────────────────────────────────
# Data loading / normalization
# ──────────────────────────────────────────────────────────────
df = pd.read_parquet(os.path.join(BASE_PATH, "data_processed.parquet")).copy()
recad_path = os.path.join(BASE_PATH, "data_recadastramento.parquet")
df_recad = pd.read_parquet(recad_path).copy() if os.path.exists(recad_path) else pd.DataFrame()

for col in [
    "VL_REMUNERACAO",
    "VL_CONTRIBUICAO",
    "VL_BASE_CALCULO",
    "VL_BENEF_PENSAO",
    "IDADE",
    "CO_COMP_MASSA",
    "CO_TIPO_APOSENTADORIA",
]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "VL_APOSENTADORIA" in df.columns:
    df["VL_APOSENTADORIA_NUM"] = pd.to_numeric(df["VL_APOSENTADORIA"], errors="coerce")
else:
    df["VL_APOSENTADORIA_NUM"] = 0.0

for col in ["VL_REMUNERACAO", "VL_CONTRIBUICAO", "VL_BASE_CALCULO", "VL_BENEF_PENSAO", "VL_APOSENTADORIA_NUM"]:
    if col in df.columns:
        df[col] = df[col].fillna(0)


def compute_age_from_birthdate(series, reference_date=None):
    ref = pd.Timestamp(reference_date or date.today()).normalize()
    nascimento = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return (ref - nascimento).dt.days / 365.25


age_sources = []
for birth_col in ["DT_NASC_SERVIDOR", "DT_NASC_APOSENTADO", "DT_NASC_PENSIONISTA"]:
    if birth_col in df.columns:
        age_sources.append(compute_age_from_birthdate(df[birth_col]))

if age_sources:
    df["IDADE_CONSOLIDADA"] = age_sources[0]
    for age_series in age_sources[1:]:
        df["IDADE_CONSOLIDADA"] = df["IDADE_CONSOLIDADA"].fillna(age_series)
else:
    df["IDADE_CONSOLIDADA"] = np.nan

if "IDADE" in df.columns:
    df["IDADE_CONSOLIDADA"] = df["IDADE_CONSOLIDADA"].fillna(df["IDADE"])

df["IDADE"] = df["IDADE_CONSOLIDADA"]
df["IDADE_VALIDA"] = df["IDADE_CONSOLIDADA"].where(df["IDADE_CONSOLIDADA"].between(18, 100))


def normalize_sex_value(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = int(value)
        if numeric == 1:
            return "Masculino"
        if numeric == 2:
            return "Feminino"
        return np.nan
    text = unicodedata.normalize("NFKD", str(value).strip().upper()).encode("ascii", "ignore").decode("ascii")
    text = " ".join(text.split())
    if text in {"1", "1.0", "M", "MASCULINO", "HOMEM"}:
        return "Masculino"
    if text in {"2", "2.0", "F", "FEMININO", "MULHER"}:
        return "Feminino"
    return np.nan


sex_sources = []
for sex_col in ["SEXO_DESC", "CO_SEXO_SERVIDOR", "CO_SEXO_APOSENTADO", "CO_SEXO_PENSIONISTA", "CODIGO_SEXO_PENSIONISTA", "CO_SEXO_INSTITUIDOR"]:
    if sex_col in df.columns:
        sex_sources.append(df[sex_col].apply(normalize_sex_value))

if sex_sources:
    df["SEXO_CONSOLIDADO"] = sex_sources[0]
    for sex_series in sex_sources[1:]:
        df["SEXO_CONSOLIDADO"] = df["SEXO_CONSOLIDADO"].fillna(sex_series)
else:
    df["SEXO_CONSOLIDADO"] = np.nan

df["SEXO_DESC"] = df["SEXO_CONSOLIDADO"].fillna("Não Informado")

for col in ["NO_ORGAO", "NO_CARGO", "NO_CARREIRA", "FAIXA_ETARIA", "CATEGORIA"]:
    if col in df.columns:
        df[col] = df[col].fillna("Não informado").astype(str)

REGIME_MAP = {1: "Civil", 2: "Militar"}
df["REGIME_PREVIDENCIARIO"] = df.get("CO_COMP_MASSA", 0).map(REGIME_MAP).fillna("Não identificado")

TIPO_APOS_MAP = {
    1: "Aposentadoria compulsória",
    2: "Aposentadoria voluntária",
    3: "Aposentadoria especial",
    4: "Incapacidade permanente",
    5: "Magistério / regra especial",
    6: "Decisão judicial / outras hipóteses",
    7: "Tipologia complementar",
    9: "Reserva remunerada (militar)",
    10: "Reforma militar",
}

df["TIPO_DIREITO"] = df.get("CO_TIPO_APOSENTADORIA", 0).map(TIPO_APOS_MAP)
df.loc[df["CATEGORIA"] == "PENSIONISTAS", "TIPO_DIREITO"] = "Pensão por morte"
df["TIPO_DIREITO"] = df["TIPO_DIREITO"].fillna("Sem tipologia informada")

# Valor de referência mais fiel por categoria
conditions = [
    df["CATEGORIA"].eq("ATIVOS"),
    df["CATEGORIA"].eq("INATIVOS"),
    df["CATEGORIA"].eq("PENSIONISTAS"),
]
choices = [
    df["VL_REMUNERACAO"],
    df["VL_APOSENTADORIA_NUM"],
    df["VL_BENEF_PENSAO"],
]
df["VL_VALOR_REFERENCIA"] = np.select(conditions, choices, default=df["VL_REMUNERACAO"]) 
df["VL_VALOR_REFERENCIA"] = pd.to_numeric(df["VL_VALOR_REFERENCIA"], errors="coerce").fillna(0)
df["CONTRIB_PATRONAL_EST"] = np.where(df["CATEGORIA"].eq("ATIVOS"), df["VL_BASE_CALCULO"].fillna(0) * 0.22, 0.0)

df["FAIXA_ETARIA_EXEC"] = pd.cut(
    df["IDADE_VALIDA"],
    bins=[-1, 49, 60, 70, 80, 200],
    labels=["<50", "50-60", "61-70", "71-80", "80+"],
    include_lowest=True,
).astype("object").fillna("Não informado")


def normalize_text(value):
    text = "" if pd.isna(value) else str(value).upper().strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.split())


MILITARY_ORGAO_PATTERN = r"POLICIA MILITAR|BOMBEIRO MILITAR|CORPO BOMBEIROS MILITAR|PMES|CBMES|HPM"
MILITARY_CARGO_PATTERN = r"QPMP|QBMP|QOA ?PM|QOA ?BM|QOC ?PM|QOC ?BM|QOAS ?PM|QOAS ?BM|SOLDADO ?PM|SOLDADO ?BM|ALUNO SOLDADO"

ALL_ORGAOS = sorted([o for o in df["NO_ORGAO"].dropna().unique() if str(o) != "nan"])
ALL_SEXES = sorted([s for s in df["SEXO_DESC"].dropna().unique() if str(s) not in ["nan", "Não Informado"]])
if "Não Informado" in set(df["SEXO_DESC"].dropna().unique()):
    ALL_SEXES.append("Não Informado")

if not df_recad.empty:
    for col in ["IDADE"]:
        if col in df_recad.columns:
            df_recad[col] = pd.to_numeric(df_recad[col], errors="coerce")

    df_recad["IDADE_VALIDA"] = df_recad["IDADE"].where(df_recad["IDADE"].between(18, 110))
    for col in ["STATUS_RECAD", "MODALIDADE_RECAD", "RECAD_CAT_SIMPLES", "RECAD_ORGAO", "RECAD_CARGO", "SEXO_DESC", "FAIXA_ETARIA_RECAD", "MES_ANIV_DESC"]:
        if col in df_recad.columns:
            df_recad[col] = df_recad[col].fillna("Não informado").astype(str)

    df_recad["FAIXA_ETARIA_EXEC"] = pd.cut(
        df_recad["IDADE_VALIDA"],
        bins=[-1, 49, 60, 70, 80, 200],
        labels=["<50", "50-60", "61-70", "71-80", "80+"],
        include_lowest=True,
    ).astype("object").fillna("Não informado")

    df_recad["RECAD_ORGAO_NORM"] = df_recad["RECAD_ORGAO"].apply(normalize_text)
    df_recad["RECAD_CARGO_NORM"] = df_recad["RECAD_CARGO"].apply(normalize_text)

    military_org_mask = df_recad["RECAD_ORGAO_NORM"].str.contains(MILITARY_ORGAO_PATTERN, regex=True, na=False)
    military_cargo_mask = df_recad["RECAD_CARGO_NORM"].str.contains(MILITARY_CARGO_PATTERN, regex=True, na=False)
    military_cargo_mask = military_cargo_mask | df_recad["RECAD_CARGO_NORM"].str.contains(r"(?:^|[^A-Z])(?:PM|BM)(?:[^A-Z]|$)", regex=True, na=False)

    df_recad["RECAD_REGIME_INFERIDO"] = np.where(military_org_mask | military_cargo_mask, "Militar", "Civil")

    modalidade_norm = df_recad["MODALIDADE_RECAD"].apply(normalize_text)
    df_recad["MODALIDADE_GRUPO"] = np.select(
        [
            modalidade_norm.str.contains("GOV BR", regex=False),
            modalidade_norm.str.contains("SISPREV", regex=False),
        ],
        ["Digital / Gov.br", "Presencial / Sisprev"],
        default="Outros / Pendente",
    )


# ──────────────────────────────────────────────────────────────
# Visual helpers
# ──────────────────────────────────────────────────────────────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#6b8e69", size=11),
    colorway=["#175414", "#2a8a24", "#3db836", "#72d96a", "#b5e4b2", "#c8a84b"],
    xaxis=dict(showgrid=False, zeroline=False, showline=False, tickcolor="#9ab898"),
    yaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)", zeroline=False, showline=False, tickcolor="#9ab898"),
    margin=dict(t=10, b=10, l=10, r=10),
    hoverlabel=dict(
        bgcolor="#ffffff",
        bordercolor="#b0ccae",
        font=dict(color="#0f2e0d", family="Plus Jakarta Sans, sans-serif"),
    ),
)
LEGEND_BASE = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#6b8e69"))
GREENS = ["#175414", "#1e6e19", "#2a8a24", "#3db836", "#72d96a", "#b5e4b2", "#e8f5e6"]
DROP_STYLE = {"fontFamily": "Plus Jakarta Sans,sans-serif", "fontSize": "0.88rem", "minWidth": "180px"}

TIP_CONTRIB_SEG = "Valor descontado do servidor para financiar a previdência."
TIP_CONTRIB_PAT = "Estimativa da contrapartida patronal calculada sobre a base dos ativos."
TIP_RECAD = "Prova de vida anual obrigatória para manutenção do benefício."
TIP_DIREITOS = "Leitura agregada do estoque de benefícios e suas tipologias cadastrais."


def safe_float(value):
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def fmt_brl(value):
    value = safe_float(value)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_mil(value):
    value = safe_float(value)
    if value >= 1e9:
        return f"R$ {value / 1e9:.1f}B".replace(".", ",")
    return f"R$ {value / 1e6:.1f}M".replace(".", ",")


def fmt_int(value):
    value = 0 if pd.isna(value) else int(round(float(value)))
    return f"{value:,}".replace(",", ".")


def empty_figure(message="Sem dados para exibir"):
    fig = go.Figure()
    fig.update_layout(**BASE_LAYOUT)
    fig.update_layout(
        annotations=[
            dict(
                text=message,
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#6b8e69"),
            )
        ]
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def kpi_card(value, label, delta=None):
    children = [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value")]
    if delta:
        children.append(html.Div(delta, className="kpi-delta"))
    return html.Div(children, className="kpi-card")


def chart_card(title, gid, tooltip=None):
    header_children = [html.Span(title, className="chart-card-title")]
    if tooltip:
        header_children.append(
            html.Span(
                "ⓘ",
                title=tooltip,
                style={"cursor": "help", "marginLeft": "8px", "color": "#9ab898", "fontSize": "0.85rem"},
            )
        )
    return html.Div(
        [
            html.Div(header_children, className="chart-card-header"),
            dcc.Graph(id=gid, config={"displayModeBar": False, "responsive": True}, style={"height": "320px"}),
        ],
        className="chart-card h-100",
    )


def note_box(text):
    return html.Div(
        text,
        className="info-note",
        style={
            "background": "#f8fbf8",
            "border": "1px solid #d4e6d2",
            "borderLeft": "4px solid #175414",
            "borderRadius": "10px",
            "padding": "12px 14px",
            "color": "#2d4a2b",
            "fontSize": "0.84rem",
            "lineHeight": "1.55",
            "margin": "10px 0 18px",
        },
    )


def data_table_from_df(table_df, left_cols=None):
    left_cols = left_cols or []
    if table_df.empty:
        return html.Div("Nenhum registro encontrado para os filtros atuais.", style={"padding": "18px", "color": "#6b8e69"})

    return dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_as_list_view=True,
        page_size=10,
        style_header={
            "backgroundColor": "#f2faf1",
            "color": "#175414",
            "fontWeight": "700",
            "fontSize": "0.67rem",
            "letterSpacing": "0.1em",
            "textTransform": "uppercase",
            "borderBottom": "2px solid #b0ccae",
            "padding": "12px 16px",
            "textAlign": "center",
        },
        style_cell={
            "backgroundColor": "#ffffff",
            "color": "#2d4a2b",
            "fontFamily": "Plus Jakarta Sans,sans-serif",
            "fontSize": "0.83rem",
            "padding": "11px 16px",
            "border": "none",
            "borderBottom": "1px solid #d4e6d2",
            "textAlign": "center",
        },
        style_cell_conditional=[
            {"if": {"column_id": col}, "textAlign": "left", "paddingLeft": "20px"} for col in left_cols
        ],
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafcfa"},
            {"if": {"state": "active"}, "backgroundColor": "#e8f5e6", "color": "#175414"},
        ],
    )


def filter_main_df(regime="__all__", category="__all__", sex="__all__", orgao="__all__"):
    dff = df.copy()
    if regime and regime != "__all__":
        dff = dff[dff["REGIME_PREVIDENCIARIO"] == regime]
    if category and category != "__all__":
        dff = dff[dff["CATEGORIA"] == category]
    if sex and sex != "__all__":
        dff = dff[dff["SEXO_DESC"] == sex]
    if orgao and orgao != "__all__":
        dff = dff[dff["NO_ORGAO"] == orgao]
    return dff


# ──────────────────────────────────────────────────────────────
# Layout
# ──────────────────────────────────────────────────────────────
app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(html.Img(src="/assets/logo-ipajm.png", alt="IPAJM"), className="header-logo-wrap"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Img(
                                    src="/assets/Brasao_Governo.png",
                                    alt="Governo do ES",
                                    style={"height": "56px", "width": "auto", "filter": "brightness(0) invert(1)", "opacity": "0.88"},
                                ),
                                html.Span(f"Atualizado em {UPDATE_DATE}", className="header-date-pill"),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "14px"},
                        ),
                        html.Button([html.Span("↓ "), html.Span("Exportar Relatório")], id="btn-export-pdf", className="btn-export-pdf", n_clicks=0),
                    ],
                    className="header-right",
                ),
            ],
            className="ipajm-header",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Painel executivo do RPPS capixaba", className="section-label", style={"marginTop": "0", "justifyContent": "center"}),
                        html.H1(
                            "Dashboard Estratégico 360° IPAJM",
                            style={
                                "margin": "8px 0 10px",
                                "fontFamily": "'DM Serif Display', serif",
                                "color": "#0f2e0d",
                                "fontSize": "3rem",
                                "fontWeight": "400",
                                "textAlign": "center",
                                "letterSpacing": "-0.03em",
                                "lineHeight": "1.05",
                                "textShadow": "0 2px 10px rgba(23,84,20,.08)",
                            },
                        ),
                        html.Div(
                            style={
                                "width": "160px",
                                "height": "4px",
                                "margin": "0 auto 6px",
                                "borderRadius": "999px",
                                "background": "linear-gradient(90deg, rgba(23,84,20,0) 0%, #175414 50%, rgba(23,84,20,0) 100%)",
                            }
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Regime previdenciário", className="sel-label"),
                                dcc.Dropdown(
                                    id="global-regime",
                                    options=[
                                        {"label": "Civil + Militar", "value": "__all__"},
                                        {"label": "Somente Civil", "value": "Civil"},
                                        {"label": "Somente Militar", "value": "Militar"},
                                    ],
                                    value="__all__",
                                    clearable=False,
                                    searchable=False,
                                    className="drop-select",
                                    style=DROP_STYLE,
                                ),
                            ],
                            className="filter-group filter-group--regime",
                        ),
                        html.Div(
                            [
                                html.Label("Categoria", className="sel-label"),
                                dcc.Dropdown(
                                    id="filter-category",
                                    options=[{"label": "Todas as categorias", "value": "__all__"}] + [{"label": x, "value": x} for x in sorted(df["CATEGORIA"].unique())],
                                    value="__all__",
                                    clearable=False,
                                    searchable=False,
                                    className="drop-select",
                                    style=DROP_STYLE,
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Label("Sexo", className="sel-label"),
                                dcc.Dropdown(
                                    id="filter-sex",
                                    options=[{"label": "Todos", "value": "__all__"}] + [{"label": x, "value": x} for x in ALL_SEXES],
                                    value="__all__",
                                    clearable=False,
                                    searchable=False,
                                    className="drop-select",
                                    style=DROP_STYLE,
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Label("Órgão", className="sel-label"),
                                dcc.Dropdown(
                                    id="filter-orgao",
                                    options=[{"label": "Todos os órgãos", "value": "__all__"}] + [{"label": x, "value": x} for x in ALL_ORGAOS],
                                    value="__all__",
                                    clearable=False,
                                    searchable=True,
                                    className="drop-select",
                                    style=DROP_STYLE,
                                ),
                            ],
                            className="filter-group filter-group--orgao",
                        ),
                    ],
                    className="filter-bar filter-bar--unified",
                    style={"marginTop": "18px"},
                ),
            ],
            className="page-body",
            style={"paddingBottom": "10px"},
        ),
        html.Div(
            [
                dcc.Tabs(
                    id="main-tabs",
                    value="tab-gente",
                    children=[
                        dcc.Tab(label="👥 Nossa Gente", value="tab-gente", className="nav-tab", selected_className="nav-tab--selected"),
                        dcc.Tab(label="💰 Como nos Mantemos", value="tab-receitas", className="nav-tab", selected_className="nav-tab--selected"),
                        dcc.Tab(label="🛡️ Garantia de Direitos", value="tab-direitos", className="nav-tab", selected_className="nav-tab--selected"),
                        dcc.Tab(label="✅ Prova de Vida", value="tab-recad", className="nav-tab", selected_className="nav-tab--selected"),
                    ],
                    className="nav-tabs-bar",
                )
            ],
            className="tabs-wrapper",
        ),
        html.Div(id="tab-content"),
        html.Footer(
            [
                html.Span("IPAJM · Instituto de Previdência dos Servidores do Estado do Espírito Santo"),
                html.Span(f"Visão consolidada · Build {UPDATE_DATE}"),
            ],
            className="ipajm-footer",
        ),
        dcc.Store(id="store-report-data"),
        html.Div(id="pdf-modal-container"),
    ],
    style={"minHeight": "100vh", "backgroundColor": "#f0f4f0"},
)


# ──────────────────────────────────────────────────────────────
# Tab builders
# ──────────────────────────────────────────────────────────────
def build_tab_gente():
    return html.Div(
        [
            note_box("LGPD: a leitura é sempre agregada, sem expor nome, CPF ou matrícula individual."),
            html.Div("Indicadores-chave", className="section-label"),
            html.Div(id="kpi-row", className="kpi-grid"),
            html.Div("Distribuições", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Composição por categoria", "graph-cat"), md=4, className="mb-4"),
                    dbc.Col(chart_card("Pirâmide etária por sexo", "graph-age", tooltip="Faixas executivas espelhadas de 18-24 até 70+, com homens à esquerda e mulheres à direita."), md=8, className="mb-4"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(chart_card("Valor médio por órgão (Top 10)", "graph-salary"), md=8, className="mb-4"),
                    dbc.Col(chart_card("Distribuição por sexo", "graph-sex"), md=4, className="mb-4"),
                ]
            ),
            html.Div("Análises avançadas", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Top 10 cargos ativos por remuneração", "graph-top-cargos"), md=7, className="mb-4"),
                    dbc.Col(chart_card("Valor médio por categoria", "graph-contrib"), md=5, className="mb-4"),
                ]
            ),
            html.Div("Detalhamento", className="section-label"),
            html.Div(
                [
                    html.Div(html.Span("Principais cargos", className="chart-card-title"), className="chart-card-header"),
                    html.Div(id="table-output"),
                ],
                className="chart-card mb-5",
            ),
        ],
        className="page-body",
    )


def build_tab_receitas():
    return html.Div(
        [
            note_box([
                html.Strong("Custeio por regime, origem e status. "),
                "Esta leitura separa segurado x patronal estimado e evidencia ativos, inativos e pensionistas em cada recorte."
            ]),
            note_box("A base atual traz o corte 07/2025; o comparativo histórico fica pronto para ampliar automaticamente quando novas competências forem incorporadas."),
            html.Div("Indicadores de custeio", className="section-label"),
            html.Div(id="kpi-receitas", className="kpi-grid"),
            html.Div("Contribuições por categoria", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Segurado x patronal por status", "graph-contrib-cat", tooltip=TIP_CONTRIB_SEG), md=6, className="mb-4"),
                    dbc.Col(chart_card("Participação do custeio por status", "graph-contrib-vol", tooltip="Peso de ativos, inativos e pensionistas no total arrecadado."), md=6, className="mb-4"),
                ]
            ),
            html.Div("Análise por órgão", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Top 10 órgãos por contribuição", "graph-contrib-orgao", tooltip=TIP_CONTRIB_PAT), md=7, className="mb-4"),
                    dbc.Col(chart_card("Relação de custeio por regime", "graph-contrib-ratio", tooltip="Percentual de participação de segurado e patronal em cada regime."), md=5, className="mb-4"),
                ]
            ),
            html.Div("Detalhamento", className="section-label"),
            html.Div(
                [
                    html.Div(html.Span("Contribuições por órgão", className="chart-card-title"), className="chart-card-header"),
                    html.Div(id="table-receitas"),
                ],
                className="chart-card mb-5",
            ),
        ],
        className="page-body",
    )


def build_tab_direitos():
    return html.Div(
        [
            note_box([
                html.Strong("Produtividade e concessões de direitos. "),
                "Os atos civis são lidos como aposentadorias e pensões; os militares, como reserva remunerada, reforma e pensão, sempre em visão agregada."
            ]),
            html.Div("Indicadores de benefícios", className="section-label"),
            html.Div(id="kpi-direitos", className="kpi-grid"),
            html.Div("Tipologias e despesa", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Atos civis e militares por tipologia", "graph-direitos-tipos", tooltip=TIP_DIREITOS), md=6, className="mb-4"),
                    dbc.Col(chart_card("Despesa mensal por categoria", "graph-direitos-benef-cat"), md=6, className="mb-4"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(chart_card("Civil x Militar", "graph-direitos-regime"), md=5, className="mb-4"),
                    dbc.Col(chart_card("Top 10 órgãos por despesa previdenciária", "graph-direitos-orgao"), md=7, className="mb-4"),
                ]
            ),
            html.Div("Detalhamento", className="section-label"),
            html.Div(
                [
                    html.Div(html.Span("Órgãos com maior estoque de benefícios", className="chart-card-title"), className="chart-card-header"),
                    html.Div(id="table-direitos"),
                ],
                className="chart-card mb-4",
            ),
            html.Div(
                [
                    html.Div(html.Span("Módulo de investimentos", className="chart-card-title"), className="chart-card-header"),
                    html.P(
                        "A base atual não traz carteira, meta atuarial ou rentabilidade. O espaço foi deixado pronto para integrar esse eixo sem retrabalho visual.",
                        style={"margin": 0, "color": "#2d4a2b", "fontSize": "0.9rem"},
                    ),
                ],
                className="chart-card mb-5",
            ),
        ],
        className="page-body",
    )


def build_tab_recad():
    if df_recad.empty:
        return html.Div(
            [html.Div("Dados de recadastramento não disponíveis.", style={"padding": "60px", "textAlign": "center", "color": "#6b8e69", "fontSize": "1.1rem"})],
            className="page-body",
        )

    return html.Div(
        [
            note_box([
                html.Strong("Regime inferido por órgão e cargo. "),
                "Nesta aba a separação Civil/Militar passa a ser estimada por padrões como PMES/CBMES, Bombeiro Militar e tipologias de cargo PM/BM."
            ]),
            html.Div("Indicadores de recadastramento", className="section-label"),
            html.Div(id="kpi-recad", className="kpi-grid"),
            html.Div("Visão geral", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Status do recadastramento", "graph-recad-status", tooltip=TIP_RECAD), md=4, className="mb-4"),
                    dbc.Col(chart_card("Recadastramento por modalidade", "graph-recad-modal"), md=4, className="mb-4"),
                    dbc.Col(chart_card("Status por regime / categoria", "graph-recad-cat"), md=4, className="mb-4"),
                ]
            ),
            html.Div("Análise temporal e demográfica", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Histórico anual / mês de referência", "graph-recad-mes"), md=6, className="mb-4"),
                    dbc.Col(chart_card("Distribuição por faixa etária", "graph-recad-age"), md=6, className="mb-4"),
                ]
            ),
            html.Div("Análise por órgão e sexo", className="section-label"),
            dbc.Row(
                [
                    dbc.Col(chart_card("Top 10 órgãos com pendências", "graph-recad-orgao"), md=7, className="mb-4"),
                    dbc.Col(chart_card("Recadastramento por sexo", "graph-recad-sexo"), md=5, className="mb-4"),
                ]
            ),
            html.Div("Detalhamento", className="section-label"),
            html.Div(
                [
                    html.Div(html.Span("Situação por órgão", className="chart-card-title"), className="chart-card-header"),
                    html.Div(id="table-recad"),
                ],
                className="chart-card mb-5",
            ),
        ],
        className="page-body",
    )


# ──────────────────────────────────────────────────────────────
# Tab rendering
# ──────────────────────────────────────────────────────────────
@app.callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab):
    if tab == "tab-gente":
        return build_tab_gente()
    if tab == "tab-receitas":
        return build_tab_receitas()
    if tab == "tab-direitos":
        return build_tab_direitos()
    if tab == "tab-recad":
        return build_tab_recad()
    return html.Div("Selecione uma aba.")


# ──────────────────────────────────────────────────────────────
# Report store
# ──────────────────────────────────────────────────────────────
@app.callback(Output("store-report-data", "data"), Input("global-regime", "value"))
def update_report_store(regime):
    dff = filter_main_df(regime=regime)
    benefits = dff[dff["CATEGORIA"].isin(["INATIVOS", "PENSIONISTAS"])]
    idade_base = dff["IDADE_VALIDA"].dropna()

    rec_total = len(df_recad) if not df_recad.empty else 0
    rec_ok = len(df_recad[df_recad["STATUS_RECAD"] == "RECADASTRADO"]) if not df_recad.empty else 0
    rec_pending = rec_total - rec_ok
    rec_pct = (rec_ok / rec_total * 100) if rec_total else 0

    return {
        "regime_label": "Civil + Militar" if regime == "__all__" else regime,
        "total_pessoas": fmt_int(len(dff)),
        "ativos": fmt_int((dff["CATEGORIA"] == "ATIVOS").sum()),
        "inativos": fmt_int((dff["CATEGORIA"] == "INATIVOS").sum()),
        "pensionistas": fmt_int((dff["CATEGORIA"] == "PENSIONISTAS").sum()),
        "media_idade": f"{safe_float(idade_base.mean()):.1f}",
        "idade_base": fmt_int(len(idade_base)),
        "valor_medio": fmt_brl(dff["VL_VALOR_REFERENCIA"].mean()),
        "contrib_total": fmt_mil(dff["VL_CONTRIBUICAO"].sum()),
        "patronal_total": fmt_mil(dff["CONTRIB_PATRONAL_EST"].sum()),
        "benef_total": fmt_mil(benefits["VL_VALOR_REFERENCIA"].sum()),
        "rec_total": fmt_int(rec_total),
        "rec_ok": fmt_int(rec_ok),
        "rec_pending": fmt_int(rec_pending),
        "rec_pct": f"{rec_pct:.1f}%",
        "update_date": UPDATE_DATE,
    }


# ──────────────────────────────────────────────────────────────
# Nossa Gente
# ──────────────────────────────────────────────────────────────
@app.callback(
    [
        Output("kpi-row", "children"),
        Output("graph-cat", "figure"),
        Output("graph-age", "figure"),
        Output("graph-salary", "figure"),
        Output("graph-sex", "figure"),
        Output("graph-top-cargos", "figure"),
        Output("graph-contrib", "figure"),
        Output("table-output", "children"),
    ],
    [
        Input("filter-category", "value"),
        Input("filter-sex", "value"),
        Input("filter-orgao", "value"),
        Input("global-regime", "value"),
    ],
)
def update_gente(category, sex, orgao, regime):
    dff = filter_main_df(regime=regime, category=category, sex=sex, orgao=orgao)
    if dff.empty:
        empty = empty_figure()
        kpis = [
            kpi_card("0", "Total de servidores"),
            kpi_card("R$ 0,00", "Valor médio"),
            kpi_card("0,0 anos", "Idade média"),
            kpi_card("R$ 0,0M", "Contribuição total"),
        ]
        return kpis, empty, empty, empty, empty, empty, empty, data_table_from_df(pd.DataFrame())

    total = len(dff)
    media_valor = dff["VL_VALOR_REFERENCIA"].mean()
    age_valid = dff["IDADE_VALIDA"].dropna()
    media_idade = safe_float(age_valid.mean())
    base_idade = len(age_valid)
    contrib_total = dff["VL_CONTRIBUICAO"].sum()
    regime_label = "Base consolidada" if regime == "__all__" else f"Regime {regime}"

    kpis = [
        kpi_card(fmt_int(total), "Total de servidores", regime_label),
        kpi_card(fmt_brl(media_valor), "Valor médio mensal"),
        kpi_card(f"{media_idade:.1f} anos", "Idade média", f"{fmt_int(base_idade)} com idade informada"),
        kpi_card(fmt_mil(contrib_total), "Contribuição total"),
    ]

    cc = dff["CATEGORIA"].value_counts().reset_index()
    cc.columns = ["CATEGORIA", "count"]
    fig_cat = go.Figure(
        go.Pie(
            labels=cc["CATEGORIA"],
            values=cc["count"],
            hole=0.58,
            textinfo="percent",
            marker=dict(colors=GREENS, line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>%{value:,} registros<extra></extra>",
        )
    )
    fig_cat.update_layout(**BASE_LAYOUT, showlegend=True, legend=dict(**LEGEND_BASE, orientation="v"))

    pyramid_source = dff[dff["IDADE_VALIDA"].notna()].copy()
    pyramid_labels = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70+"]
    if pyramid_source.empty:
        fig_age = empty_figure("Sem idades válidas para montar a pirâmide")
    else:
        pyramid_source["FAIXA_PIRAMIDE"] = pd.cut(
            pyramid_source["IDADE_VALIDA"],
            bins=[18, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 120],
            labels=pyramid_labels,
            right=False,
            include_lowest=True,
        )
        pyramid = (
            pyramid_source.groupby(["FAIXA_PIRAMIDE", "SEXO_DESC"], observed=False)
            .size()
            .unstack(fill_value=0)
            .reindex(pyramid_labels)
            .fillna(0)
        )
        masculino = -(pyramid.get("Masculino", pd.Series(0, index=pyramid.index)) / max(base_idade, 1) * 100)
        feminino = (pyramid.get("Feminino", pd.Series(0, index=pyramid.index)) / max(base_idade, 1) * 100)
        max_range = max(abs(masculino.min()), abs(feminino.max()), 1)
        tick_vals = np.linspace(-max_range, max_range, 5)
        tick_text = [f"{abs(v):.1f}%" for v in tick_vals]

        fig_age = go.Figure()
        fig_age.add_trace(
            go.Bar(
                name="Homem",
                y=pyramid.index,
                x=masculino,
                orientation="h",
                marker_color="#1f9ae0",
                hovertemplate="<b>%{y}</b><br>Homens: %{x:.2f}%<extra></extra>",
            )
        )
        fig_age.add_trace(
            go.Bar(
                name="Mulher",
                y=pyramid.index,
                x=feminino,
                orientation="h",
                marker_color="#ff8c3a",
                hovertemplate="<b>%{y}</b><br>Mulheres: %{x:.2f}%<extra></extra>",
            )
        )
        fig_age.update_layout(**BASE_LAYOUT, barmode="relative", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))
        fig_age.update_xaxes(tickvals=tick_vals, ticktext=tick_text, title="Participação na base com idade informada")
        fig_age.update_yaxes(title="Faixa etária", categoryorder="array", categoryarray=pyramid_labels)

    org = dff.groupby("NO_ORGAO")["VL_VALOR_REFERENCIA"].mean().sort_values(ascending=True).tail(10).reset_index()
    fig_sal = go.Figure(
        go.Bar(
            x=org["VL_VALOR_REFERENCIA"],
            y=org["NO_ORGAO"],
            orientation="h",
            text=org["VL_VALOR_REFERENCIA"].apply(fmt_brl),
            textposition="outside",
            marker=dict(color=org["VL_VALOR_REFERENCIA"], colorscale=[[0, "#b5e4b2"], [1, "#175414"]], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig_sal.update_layout(**BASE_LAYOUT)
    fig_sal.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)"))

    sex_df = dff["SEXO_DESC"].value_counts().reset_index()
    sex_df.columns = ["SEXO_DESC", "count"]
    fig_sex = go.Figure(
        go.Pie(
            labels=sex_df["SEXO_DESC"],
            values=sex_df["count"],
            hole=0.58,
            textinfo="percent",
            marker=dict(colors=GREENS, line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>",
        )
    )
    fig_sex.update_layout(**BASE_LAYOUT, showlegend=True, legend=dict(**LEGEND_BASE, orientation="v"))

    ativos = dff[dff["CATEGORIA"] == "ATIVOS"]
    if ativos.empty:
        fig_tc = empty_figure("Sem ativos para o filtro atual")
    else:
        tc = ativos.groupby("NO_CARGO")["VL_VALOR_REFERENCIA"].mean().sort_values(ascending=True).tail(10).reset_index()
        tc["label"] = tc["NO_CARGO"].apply(lambda x: str(x)[:38] + "…" if len(str(x)) > 38 else str(x))
        fig_tc = go.Figure(
            go.Bar(
                x=tc["VL_VALOR_REFERENCIA"],
                y=tc["label"],
                orientation="h",
                text=tc["VL_VALOR_REFERENCIA"].apply(fmt_brl),
                textposition="outside",
                marker=dict(color="#1e6e19", opacity=0.9, line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
            )
        )
        fig_tc.update_layout(**BASE_LAYOUT)
        fig_tc.update_layout(yaxis=dict(showgrid=False))

    cat_val = dff.groupby("CATEGORIA")["VL_VALOR_REFERENCIA"].mean().reset_index()
    fig_contrib = go.Figure(
        go.Bar(
            x=cat_val["CATEGORIA"],
            y=cat_val["VL_VALOR_REFERENCIA"],
            text=cat_val["VL_VALOR_REFERENCIA"].apply(fmt_brl),
            textposition="outside",
            marker=dict(color=cat_val["VL_VALOR_REFERENCIA"], colorscale=[[0, "#b5e4b2"], [1, "#175414"]], line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_contrib.update_layout(**BASE_LAYOUT)
    fig_contrib.update_traces(width=0.45)

    table_df = (
        dff.groupby("NO_CARGO")
        .agg(Servidores=("VL_VALOR_REFERENCIA", "count"), Valor_Medio=("VL_VALOR_REFERENCIA", "mean"), Idade_Media=("IDADE_VALIDA", "mean"))
        .reset_index()
        .sort_values("Servidores", ascending=False)
        .head(15)
    )
    table_df["Servidores"] = table_df["Servidores"].apply(fmt_int)
    table_df["Valor_Medio"] = table_df["Valor_Medio"].apply(fmt_brl)
    table_df["Idade_Media"] = table_df["Idade_Media"].apply(lambda x: f"{safe_float(x):.1f}")
    table_df.columns = ["Cargo", "Servidores", "Valor Médio", "Idade Média"]

    return kpis, fig_cat, fig_age, fig_sal, fig_sex, fig_tc, fig_contrib, data_table_from_df(table_df, left_cols=["Cargo"])


# ──────────────────────────────────────────────────────────────
# Como nos Mantemos
# ──────────────────────────────────────────────────────────────
@app.callback(
    [
        Output("kpi-receitas", "children"),
        Output("graph-contrib-cat", "figure"),
        Output("graph-contrib-vol", "figure"),
        Output("graph-contrib-orgao", "figure"),
        Output("graph-contrib-ratio", "figure"),
        Output("table-receitas", "children"),
    ],
    [Input("main-tabs", "value"), Input("global-regime", "value")],
)
def update_receitas(tab, regime):
    empty = empty_figure()
    if tab != "tab-receitas":
        return [], empty, empty, empty, empty, html.Div()

    dff = filter_main_df(regime=regime)
    if dff.empty:
        return [], empty, empty, empty, empty, data_table_from_df(pd.DataFrame())

    contrib_total = dff["VL_CONTRIBUICAO"].sum()
    patronal_total = dff["CONTRIB_PATRONAL_EST"].sum()
    base_total = dff["VL_BASE_CALCULO"].sum()
    contrib_benef = dff[dff["CATEGORIA"].isin(["INATIVOS", "PENSIONISTAS"])]["VL_CONTRIBUICAO"].sum()
    aliq_media = (contrib_total / base_total * 100) if base_total else 0
    pct_benef = (contrib_benef / contrib_total * 100) if contrib_total else 0

    kpis = [
        kpi_card(fmt_mil(contrib_total), "Segurado arrecadado", TIP_CONTRIB_SEG),
        kpi_card(fmt_mil(patronal_total), "Patronal estimado", "22% sobre a base dos ativos"),
        kpi_card(f"{pct_benef:.1f}%", "Peso de inativos/pensões", "contribuição sobre proventos"),
        kpi_card(f"{aliq_media:.2f}%", "Alíquota efetiva", "segurado / base"),
    ]

    cat_agg = dff.groupby("CATEGORIA").agg(Segurado=("VL_CONTRIBUICAO", "sum"), Patronal=("CONTRIB_PATRONAL_EST", "sum")).reset_index()
    fig_cc = go.Figure()
    fig_cc.add_trace(
        go.Bar(
            name="Segurado",
            x=cat_agg["CATEGORIA"],
            y=cat_agg["Segurado"],
            marker_color="#175414",
            text=cat_agg["Segurado"].apply(fmt_mil),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Segurado: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_cc.add_trace(
        go.Bar(
            name="Patronal estimado",
            x=cat_agg["CATEGORIA"],
            y=cat_agg["Patronal"],
            marker_color="#b5e4b2",
            text=cat_agg["Patronal"].apply(fmt_mil),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Patronal: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_cc.update_layout(**BASE_LAYOUT, barmode="group", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    status_source = dff.groupby("CATEGORIA")["VL_CONTRIBUICAO"].sum().reset_index()
    fig_cv = go.Figure(
        go.Pie(
            labels=status_source["CATEGORIA"],
            values=status_source["VL_CONTRIBUICAO"],
            hole=0.55,
            textinfo="percent+label",
            marker=dict(colors=GREENS, line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>",
        )
    )
    fig_cv.update_layout(**BASE_LAYOUT, showlegend=False)

    org = dff.groupby("NO_ORGAO")["VL_CONTRIBUICAO"].sum().sort_values(ascending=True).tail(10).reset_index()
    fig_org = go.Figure(
        go.Bar(
            x=org["VL_CONTRIBUICAO"],
            y=org["NO_ORGAO"],
            orientation="h",
            text=org["VL_CONTRIBUICAO"].apply(fmt_mil),
            textposition="outside",
            marker=dict(color=org["VL_CONTRIBUICAO"], colorscale=[[0, "#b5e4b2"], [1, "#175414"]], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig_org.update_layout(**BASE_LAYOUT)
    fig_org.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)"))

    if regime == "__all__":
        ratio = dff.groupby("REGIME_PREVIDENCIARIO").agg(Segurado=("VL_CONTRIBUICAO", "sum"), Patronal=("CONTRIB_PATRONAL_EST", "sum")).reset_index()
        eixo = "REGIME_PREVIDENCIARIO"
    else:
        ratio = dff.groupby("CATEGORIA").agg(Segurado=("VL_CONTRIBUICAO", "sum"), Patronal=("CONTRIB_PATRONAL_EST", "sum")).reset_index()
        eixo = "CATEGORIA"

    ratio["Total"] = ratio["Segurado"] + ratio["Patronal"]
    ratio["Pct_Segurado"] = np.where(ratio["Total"] > 0, ratio["Segurado"] / ratio["Total"] * 100, 0)
    ratio["Pct_Patronal"] = np.where(ratio["Total"] > 0, ratio["Patronal"] / ratio["Total"] * 100, 0)

    fig_ratio = go.Figure()
    fig_ratio.add_trace(
        go.Bar(
            name="Segurado",
            x=ratio[eixo],
            y=ratio["Pct_Segurado"],
            text=ratio["Pct_Segurado"].apply(lambda x: f"{x:.1f}%"),
            textposition="inside",
            marker_color="#175414",
            hovertemplate="<b>%{x}</b><br>Segurado: %{y:.1f}% do custeio<extra></extra>",
        )
    )
    fig_ratio.add_trace(
        go.Bar(
            name="Patronal",
            x=ratio[eixo],
            y=ratio["Pct_Patronal"],
            text=ratio["Pct_Patronal"].apply(lambda x: f"{x:.1f}%"),
            textposition="inside",
            marker_color="#72d96a",
            hovertemplate="<b>%{x}</b><br>Patronal: %{y:.1f}% do custeio<extra></extra>",
        )
    )
    fig_ratio.update_layout(**BASE_LAYOUT, barmode="stack", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))
    fig_ratio.update_yaxes(range=[0, 100], ticksuffix="%")

    table_df = (
        dff.groupby("NO_ORGAO")
        .agg(Servidores=("VL_CONTRIBUICAO", "count"), Segurado=("VL_CONTRIBUICAO", "sum"), Patronal_Est=("CONTRIB_PATRONAL_EST", "sum"), Base_Media=("VL_BASE_CALCULO", "mean"))
        .reset_index()
        .sort_values("Segurado", ascending=False)
        .head(15)
    )
    table_df["Servidores"] = table_df["Servidores"].apply(fmt_int)
    table_df["Segurado"] = table_df["Segurado"].apply(fmt_mil)
    table_df["Patronal_Est"] = table_df["Patronal_Est"].apply(fmt_mil)
    table_df["Base_Media"] = table_df["Base_Media"].apply(fmt_brl)
    table_df.columns = ["Órgão", "Servidores", "Segurado", "Patronal Est.", "Base Média"]

    return kpis, fig_cc, fig_cv, fig_org, fig_ratio, data_table_from_df(table_df, left_cols=["Órgão"])


# ──────────────────────────────────────────────────────────────
# Garantia de Direitos
# ──────────────────────────────────────────────────────────────
@app.callback(
    [
        Output("kpi-direitos", "children"),
        Output("graph-direitos-tipos", "figure"),
        Output("graph-direitos-benef-cat", "figure"),
        Output("graph-direitos-regime", "figure"),
        Output("graph-direitos-orgao", "figure"),
        Output("table-direitos", "children"),
    ],
    [Input("main-tabs", "value"), Input("global-regime", "value")],
)
def update_direitos(tab, regime):
    empty = empty_figure()
    if tab != "tab-direitos":
        return [], empty, empty, empty, empty, html.Div()

    dff = filter_main_df(regime=regime)
    benef = dff[dff["CATEGORIA"].isin(["INATIVOS", "PENSIONISTAS"])]
    if benef.empty:
        return [], empty, empty, empty, empty, data_table_from_df(pd.DataFrame())

    total = len(benef)
    despesa = benef["VL_VALOR_REFERENCIA"].sum()
    ticket = benef["VL_VALOR_REFERENCIA"].mean()
    pct_pens = (benef["CATEGORIA"].eq("PENSIONISTAS").sum() / total * 100) if total else 0

    kpis = [
        kpi_card(fmt_int(total), "Benefícios no estoque", "inativos + pensionistas"),
        kpi_card(fmt_mil(despesa), "Despesa mensal estimada"),
        kpi_card(fmt_brl(ticket), "Ticket médio"),
        kpi_card(f"{pct_pens:.1f}%", "Participação de pensões"),
    ]

    tipos = benef["TIPO_DIREITO"].value_counts().head(10).sort_values(ascending=True).reset_index()
    tipos.columns = ["TIPO_DIREITO", "count"]
    fig_tipos = go.Figure(
        go.Bar(
            x=tipos["count"],
            y=tipos["TIPO_DIREITO"],
            orientation="h",
            text=tipos["count"].apply(fmt_int),
            textposition="outside",
            marker=dict(color="#175414", opacity=0.9, line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>%{x:,} benefícios<extra></extra>",
        )
    )
    fig_tipos.update_layout(**BASE_LAYOUT)
    fig_tipos.update_layout(yaxis=dict(showgrid=False))

    cat = benef.groupby("CATEGORIA")["VL_VALOR_REFERENCIA"].sum().reset_index()
    fig_cat = go.Figure(
        go.Bar(
            x=cat["CATEGORIA"],
            y=cat["VL_VALOR_REFERENCIA"],
            text=cat["VL_VALOR_REFERENCIA"].apply(fmt_mil),
            textposition="outside",
            marker=dict(color=["#2a8a24", "#175414"][: len(cat)], line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_cat.update_layout(**BASE_LAYOUT)

    reg = benef.groupby("REGIME_PREVIDENCIARIO")["VL_VALOR_REFERENCIA"].sum().reset_index()
    fig_reg = go.Figure(
        go.Pie(
            labels=reg["REGIME_PREVIDENCIARIO"],
            values=reg["VL_VALOR_REFERENCIA"],
            hole=0.55,
            textinfo="percent+label",
            marker=dict(colors=["#175414", "#72d96a", "#b5e4b2"], line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>",
        )
    )
    fig_reg.update_layout(**BASE_LAYOUT, showlegend=False)

    org = benef.groupby("NO_ORGAO")["VL_VALOR_REFERENCIA"].sum().sort_values(ascending=True).tail(10).reset_index()
    fig_org = go.Figure(
        go.Bar(
            x=org["VL_VALOR_REFERENCIA"],
            y=org["NO_ORGAO"],
            orientation="h",
            text=org["VL_VALOR_REFERENCIA"].apply(fmt_mil),
            textposition="outside",
            marker=dict(color=org["VL_VALOR_REFERENCIA"], colorscale=[[0, "#b5e4b2"], [1, "#175414"]], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>",
        )
    )
    fig_org.update_layout(**BASE_LAYOUT)
    fig_org.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)"))

    table_df = (
        benef.groupby("NO_ORGAO")
        .agg(Beneficios=("VL_VALOR_REFERENCIA", "count"), Despesa=("VL_VALOR_REFERENCIA", "sum"), Ticket_Medio=("VL_VALOR_REFERENCIA", "mean"))
        .reset_index()
        .sort_values("Despesa", ascending=False)
        .head(15)
    )
    table_df["Beneficios"] = table_df["Beneficios"].apply(fmt_int)
    table_df["Despesa"] = table_df["Despesa"].apply(fmt_mil)
    table_df["Ticket_Medio"] = table_df["Ticket_Medio"].apply(fmt_brl)
    table_df.columns = ["Órgão", "Benefícios", "Despesa", "Ticket Médio"]

    return kpis, fig_tipos, fig_cat, fig_reg, fig_org, data_table_from_df(table_df, left_cols=["Órgão"])


# ──────────────────────────────────────────────────────────────
# Prova de Vida
# ──────────────────────────────────────────────────────────────
@app.callback(
    [
        Output("kpi-recad", "children"),
        Output("graph-recad-status", "figure"),
        Output("graph-recad-modal", "figure"),
        Output("graph-recad-cat", "figure"),
        Output("graph-recad-mes", "figure"),
        Output("graph-recad-age", "figure"),
        Output("graph-recad-orgao", "figure"),
        Output("graph-recad-sexo", "figure"),
        Output("table-recad", "children"),
    ],
    [Input("main-tabs", "value"), Input("global-regime", "value")],
)
def update_recad(tab, regime):
    empty = empty_figure()
    if tab != "tab-recad" or df_recad.empty:
        return [], empty, empty, empty, empty, empty, empty, empty, html.Div()

    rdf = df_recad.copy()
    if regime != "__all__":
        rdf = rdf[rdf["RECAD_REGIME_INFERIDO"] == regime]

    if rdf.empty:
        return [], empty, empty, empty, empty, empty, empty, empty, data_table_from_df(pd.DataFrame())

    total = len(rdf)
    recad_ok = len(rdf[rdf["STATUS_RECAD"] == "RECADASTRADO"])
    pendente = total - recad_ok
    pct = (recad_ok / total * 100) if total else 0

    rec_only = rdf[rdf["STATUS_RECAD"] == "RECADASTRADO"]
    gov_br = len(rec_only[rec_only["MODALIDADE_GRUPO"] == "Digital / Gov.br"])
    pct_digital = (gov_br / recad_ok * 100) if recad_ok else 0
    scope_label = "regime inferido por cargo/órgão" if regime == "__all__" else f"{regime} inferido por cargo/órgão"

    kpis = [
        kpi_card(fmt_int(total), "Total segurados", scope_label),
        kpi_card(f"{pct:.1f}%", "Taxa de recadastramento", f"{fmt_int(recad_ok)} concluídos"),
        kpi_card(fmt_int(pendente), "Pendentes", "prioridade de contato"),
        kpi_card(f"{pct_digital:.1f}%", "Uso do Gov.br", f"{fmt_int(gov_br)} digitais"),
    ]

    st = rdf["STATUS_RECAD"].value_counts().reset_index()
    st.columns = ["STATUS_RECAD", "count"]
    fig_st = go.Figure(
        go.Pie(
            labels=st["STATUS_RECAD"],
            values=st["count"],
            hole=0.6,
            textinfo="percent+label",
            marker=dict(colors=["#175414", "#e74c3c"], line=dict(color="#fff", width=2)),
            hovertemplate="<b>%{label}</b><br>%{value:,}<extra></extra>",
        )
    )
    fig_st.update_layout(**BASE_LAYOUT, showlegend=False)

    modal = rec_only["MODALIDADE_GRUPO"].value_counts().reset_index()
    modal.columns = ["MODALIDADE_GRUPO", "count"]
    fig_modal = go.Figure(
        go.Bar(
            x=modal["MODALIDADE_GRUPO"],
            y=modal["count"],
            text=modal["count"].apply(fmt_int),
            textposition="outside",
            marker=dict(color=["#175414", "#2a8a24", "#72d96a"][: len(modal)], line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
        )
    )
    fig_modal.update_layout(**BASE_LAYOUT)

    if regime == "__all__":
        cat = rdf.groupby(["RECAD_REGIME_INFERIDO", "STATUS_RECAD"]).size().reset_index(name="count")
        eixo_cat = "RECAD_REGIME_INFERIDO"
    else:
        cat = rdf.groupby(["RECAD_CAT_SIMPLES", "STATUS_RECAD"]).size().reset_index(name="count")
        eixo_cat = "RECAD_CAT_SIMPLES"

    fig_cat = go.Figure()
    for idx, status_name in enumerate(["RECADASTRADO", "NÃO RECADASTRADO"]):
        sub = cat[cat["STATUS_RECAD"] == status_name]
        fig_cat.add_trace(
            go.Bar(
                name=status_name.title(),
                x=sub[eixo_cat],
                y=sub["count"],
                text=sub["count"].apply(fmt_int),
                textposition="outside",
                marker_color=["#175414", "#e74c3c"][idx],
                hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
            )
        )
    fig_cat.update_layout(**BASE_LAYOUT, barmode="group", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    anos = []
    if "ANO" in rdf.columns:
        anos = sorted(pd.to_numeric(rdf["ANO"], errors="coerce").dropna().astype(int).unique().tolist())

    fig_mes = go.Figure()
    if len(anos) > 1:
        hist = rdf.groupby(["ANO", "STATUS_RECAD"]).size().reset_index(name="count")
        for idx, status_name in enumerate(["RECADASTRADO", "NÃO RECADASTRADO"]):
            sub = hist[hist["STATUS_RECAD"] == status_name]
            fig_mes.add_trace(
                go.Bar(
                    name=status_name.title(),
                    x=sub["ANO"].astype(str),
                    y=sub["count"],
                    marker_color=["#175414", "#e74c3c"][idx],
                    hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
                )
            )
        fig_mes.update_layout(**BASE_LAYOUT, barmode="group", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))
    else:
        mes_order = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        mes = rdf.groupby(["MES_ANIV_DESC", "STATUS_RECAD"]).size().reset_index(name="count")
        for idx, status_name in enumerate(["RECADASTRADO", "NÃO RECADASTRADO"]):
            sub = mes[mes["STATUS_RECAD"] == status_name].set_index("MES_ANIV_DESC").reindex(mes_order).fillna(0).reset_index()
            fig_mes.add_trace(
                go.Bar(
                    name=status_name.title(),
                    x=sub["MES_ANIV_DESC"],
                    y=sub["count"],
                    marker_color=["#175414", "#e74c3c"][idx],
                    hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
                )
            )
        fig_mes.update_layout(**BASE_LAYOUT, barmode="stack", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    fe_order = ["<50", "50-60", "61-70", "71-80", "80+"]
    fe = rdf["FAIXA_ETARIA_EXEC"].value_counts().reindex(fe_order).fillna(0).reset_index()
    fe.columns = ["FAIXA_ETARIA_EXEC", "count"]
    fig_fe = go.Figure(
        go.Bar(
            x=fe["count"],
            y=fe["FAIXA_ETARIA_EXEC"],
            orientation="h",
            text=fe["count"].apply(fmt_int),
            textposition="outside",
            marker=dict(color=fe["count"], colorscale=[[0, "#b5e4b2"], [1, "#175414"]], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>",
        )
    )
    fig_fe.update_layout(**BASE_LAYOUT)
    fig_fe.update_layout(yaxis=dict(showgrid=False), xaxis=dict(showgrid=True, gridcolor="rgba(180,210,178,.35)"))

    nao = rdf[rdf["STATUS_RECAD"] == "NÃO RECADASTRADO"]
    org = nao["RECAD_ORGAO"].value_counts().head(10).sort_values(ascending=True).reset_index()
    org.columns = ["ORGAO", "count"]
    fig_org = go.Figure(
        go.Bar(
            x=org["count"],
            y=org["ORGAO"],
            orientation="h",
            text=org["count"].apply(fmt_int),
            textposition="outside",
            marker=dict(color="#e74c3c", opacity=0.9, line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>%{x:,} pendentes<extra></extra>",
        )
    )
    fig_org.update_layout(**BASE_LAYOUT)
    fig_org.update_layout(yaxis=dict(showgrid=False))

    sx = rdf.groupby(["SEXO_DESC", "STATUS_RECAD"]).size().reset_index(name="count")
    fig_sx = go.Figure()
    for idx, status_name in enumerate(["RECADASTRADO", "NÃO RECADASTRADO"]):
        sub = sx[sx["STATUS_RECAD"] == status_name]
        fig_sx.add_trace(
            go.Bar(
                name=status_name.title(),
                x=sub["SEXO_DESC"],
                y=sub["count"],
                text=sub["count"].apply(fmt_int),
                textposition="outside",
                marker_color=["#175414", "#e74c3c"][idx],
                hovertemplate="<b>%{x}</b><br>%{y:,}<extra></extra>",
            )
        )
    fig_sx.update_layout(**BASE_LAYOUT, barmode="group", showlegend=True, legend=dict(**LEGEND_BASE, orientation="h", y=1.12))

    if regime == "__all__":
        table_df = rdf.groupby(["RECAD_REGIME_INFERIDO", "RECAD_ORGAO"]).agg(Total=("STATUS_RECAD", "count"), Recadastrados=("STATUS_RECAD", lambda x: (x == "RECADASTRADO").sum())).reset_index()
        table_df.columns = ["Regime", "Órgão", "Total", "Recadastrados"]
    else:
        table_df = rdf.groupby("RECAD_ORGAO").agg(Total=("STATUS_RECAD", "count"), Recadastrados=("STATUS_RECAD", lambda x: (x == "RECADASTRADO").sum())).reset_index()
        table_df.columns = ["Órgão", "Total", "Recadastrados"]

    table_df["Pendentes"] = table_df["Total"] - table_df["Recadastrados"]
    table_df["Taxa"] = np.where(table_df["Total"] > 0, table_df["Recadastrados"] / table_df["Total"] * 100, 0)
    table_df = table_df.sort_values("Total", ascending=False).head(15)
    table_df["Total"] = table_df["Total"].apply(fmt_int)
    table_df["Recadastrados"] = table_df["Recadastrados"].apply(fmt_int)
    table_df["Pendentes"] = table_df["Pendentes"].apply(fmt_int)
    table_df["Taxa"] = table_df["Taxa"].apply(lambda x: f"{x:.1f}%")

    left_cols = ["Órgão"]
    if regime == "__all__":
        left_cols = ["Regime", "Órgão"]

    return kpis, fig_st, fig_modal, fig_cat, fig_mes, fig_fe, fig_org, fig_sx, data_table_from_df(table_df, left_cols=left_cols)


# ──────────────────────────────────────────────────────────────
# PDF modal / print report
# ──────────────────────────────────────────────────────────────
@app.callback(
    Output("pdf-modal-container", "children"),
    Input("btn-export-pdf", "n_clicks"),
    State("store-report-data", "data"),
    State("main-tabs", "value"),
    State("global-regime", "value"),
    prevent_initial_call=True,
)
def open_pdf_modal(n_clicks, rd, active_tab, regime):
    if not n_clicks or not rd:
        return []

    regime = regime or "__all__"
    active_tab = active_tab or "tab-gente"
    regime_label = rd.get("regime_label", "Civil + Militar")
    tab_map = {
        "tab-gente": "Nossa Gente",
        "tab-receitas": "Como nos Mantemos",
        "tab-direitos": "Garantia de Direitos",
        "tab-recad": "Prova de Vida",
    }
    session_label = tab_map.get(active_tab, "Sessão Executiva")

    def metric(label, value):
        return html.Div(
            [
                html.Div(label, style={"fontSize": "0.58rem", "textTransform": "uppercase", "letterSpacing": "0.09em", "color": "rgba(255,255,255,0.55)", "marginBottom": "6px"}),
                html.Div(value, style={"fontSize": "1.55rem", "fontFamily": "'DM Serif Display',serif", "color": "#fff"}),
            ],
            style={"flex": "1", "textAlign": "center", "padding": "16px"},
        )

    def prose_block(title, text):
        return html.Div(
            [
                html.H3(title, style={"fontFamily": "'DM Serif Display',serif", "fontSize": "1.08rem", "color": "#175414", "margin": "0 0 8px"}),
                html.P(text, style={"margin": 0, "color": "#2d4a2b", "fontSize": "0.89rem", "lineHeight": "1.7", "textAlign": "justify"}),
            ],
            style={"background": "#f8fbf8", "border": "1px solid #d4e6d2", "borderLeft": "4px solid #175414", "borderRadius": "10px", "padding": "16px 18px", "marginBottom": "12px"},
        )

    def graph_block(title, fig, note=None):
        plot_fig = go.Figure(fig)
        plot_fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=30))
        children = [
            html.H4(title, style={"margin": "0 0 8px", "color": "#175414", "fontSize": "0.95rem", "fontWeight": "700"}),
            dcc.Graph(figure=plot_fig, config={"displayModeBar": False}, style={"height": "320px"}),
        ]
        if note:
            children.append(html.P(note, style={"margin": "6px 0 0", "fontSize": "0.8rem", "color": "#5d7a5b", "lineHeight": "1.55"}))
        return html.Div(children, style={"background": "#fff", "border": "1px solid #dcead9", "borderRadius": "12px", "padding": "12px", "pageBreakInside": "avoid"})

    def pair(*blocks):
        return html.Div(list(blocks), style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "14px", "marginBottom": "14px"})

    def table_block(title, component):
        return html.Div(
            [
                html.H4(title, style={"margin": "0 0 10px", "color": "#175414", "fontSize": "0.96rem", "fontWeight": "700"}),
                component,
            ],
            style={"background": "#fff", "border": "1px solid #dcead9", "borderRadius": "12px", "padding": "14px", "marginTop": "4px", "pageBreakInside": "avoid"},
        )

    def safe_mode(series, fallback="Não identificado"):
        vals = series.dropna().astype(str).str.strip()
        vals = vals[vals.ne("")]
        if vals.empty:
            return fallback
        return vals.value_counts().idxmax()

    lead = ""
    metrics_row = []
    analysis_cards = []
    visual_blocks = []
    appendix = html.Div()

    if active_tab == "tab-gente":
        dff = filter_main_df(regime=regime)
        valid_age = dff["IDADE_VALIDA"].dropna()
        media_idade = safe_float(valid_age.mean()) if not valid_age.empty else 0
        faixa_base = dff["FAIXA_ETARIA_EXEC"].replace("Não informado", np.nan)
        faixa_top = safe_mode(faixa_base, "Faixa não identificada")
        orgao_top = safe_mode(dff["NO_ORGAO"], "Órgão não identificado")
        sexo_norm = dff["SEXO_DESC"].fillna("").astype(str).str.strip().str.upper()
        pct_mulheres = safe_float(sexo_norm.isin(["FEMININO", "MULHER", "F"]).mean() * 100) if len(dff) else 0
        _, fig_cat, fig_age, fig_sal, fig_sex, fig_tc, fig_contrib, table_component = update_gente("__all__", "__all__", "__all__", regime)

        lead = (
            f"A sessão Nossa Gente consolida o retrato institucional do estoque previdenciário no recorte {regime_label}, "
            "privilegiando leitura demográfica, composição funcional e sinais de renovação da força vinculada ao regime próprio."
        )
        metrics_row = [
            metric("Total de pessoas", rd.get("total_pessoas", "0")),
            metric("Idade média válida", f"{media_idade:.1f} anos"),
            metric("Ativos", rd.get("ativos", "0")),
            metric("Valor médio", rd.get("valor_medio", "R$ 0,00")),
        ]
        analysis_cards = [
            prose_block(
                "Leitura demográfica",
                f"O painel reúne {rd.get('total_pessoas', '0')} vínculos, com predominância operacional de {rd.get('ativos', '0')} ativos, "
                f"além de {rd.get('inativos', '0')} inativos e {rd.get('pensionistas', '0')} pensionistas. A idade média confiável do universo com informação válida ficou em {media_idade:.1f} anos, "
                f"e a faixa mais representativa foi {faixa_top}, sinalizando o centro de gravidade etário da massa analisada.",
            ),
            prose_block(
                "Equilíbrio de perfis",
                f"A distribuição por sexo mostra participação feminina próxima de {pct_mulheres:.1f}% do total filtrado. Quando lida em conjunto com a pirâmide etária, essa fotografia ajuda a identificar grupos mais maduros, "
                "potenciais pressões futuras de aposentação e espaços de reposição geracional por carreira e regime.",
            ),
            prose_block(
                "Estrutura funcional",
                f"O órgão com maior presença relativa no recorte foi {orgao_top}. A comparação entre cargos, remuneração média e massa por categoria permite priorizar análises de lotação, sucessão e concentração remuneratória sem expor dados individualizados.",
            ),
        ]
        visual_blocks = [
            pair(
                graph_block("Pirâmide etária por sexo", fig_age, "Homens são exibidos à esquerda e mulheres à direita, facilitando a leitura executiva da estrutura demográfica."),
                graph_block("Distribuição por sexo", fig_sex, "Complementa a leitura da pirâmide com a participação agregada de homens e mulheres."),
            ),
            pair(
                graph_block("Composição por categoria", fig_cat, "Permite comparar o peso relativo de ativos, inativos e pensionistas."),
                graph_block("Massa por faixa remuneratória", fig_sal, "Evidencia onde se concentra o maior volume de vínculos por nível de renda."),
            ),
            pair(
                graph_block("Top cargos", fig_tc, "Destaca as carreiras com maior volume de vínculos no recorte selecionado."),
                graph_block("Valor médio por categoria", fig_contrib, "Resume a diferença de referência financeira entre os principais grupos previdenciários."),
            ),
        ]
        appendix = table_block("Microanálise dos cargos com maior volume", table_component)

    elif active_tab == "tab-receitas":
        dff = filter_main_df(regime=regime)
        contrib_total = dff["VL_CONTRIBUICAO"].sum()
        patronal_total = dff["CONTRIB_PATRONAL_EST"].sum()
        base_total = dff["VL_BASE_CALCULO"].sum()
        aliq_media = (contrib_total / base_total * 100) if base_total else 0
        contrib_benef = dff[dff["CATEGORIA"].isin(["INATIVOS", "PENSIONISTAS"])]["VL_CONTRIBUICAO"].sum()
        pct_benef = (contrib_benef / contrib_total * 100) if contrib_total else 0
        org_agg = dff.groupby("NO_ORGAO")["VL_CONTRIBUICAO"].sum().sort_values(ascending=False)
        orgao_top = org_agg.index[0] if not org_agg.empty else "Órgão não identificado"
        orgao_top_pct = safe_float(org_agg.iloc[0] / contrib_total * 100) if len(org_agg) and contrib_total else 0
        _, fig_cc, fig_cv, fig_org, fig_ratio, table_component = update_receitas("tab-receitas", regime)

        lead = (
            f"A sessão Como nos Mantemos traduz o custeio do RPPS no recorte {regime_label}, "
            "observando arrecadação do segurado, contrapartida patronal estimada e concentração da base contributiva por órgão e categoria."
        )
        metrics_row = [
            metric("Segurado", rd.get("contrib_total", "R$ 0,0M")),
            metric("Patronal estimado", rd.get("patronal_total", "R$ 0,0M")),
            metric("Alíquota efetiva", f"{aliq_media:.2f}%"),
            metric("Pressão de benefícios", f"{pct_benef:.1f}%"),
        ]
        analysis_cards = [
            prose_block(
                "Capacidade arrecadatória",
                f"A massa filtrada gerou {fmt_mil(contrib_total)} de contribuição do segurado e {fmt_mil(patronal_total)} de contrapartida patronal estimada. Em leitura executiva, isso permite enxergar o quanto do fluxo mensal é sustentado pela folha ativa e qual o espaço de resposta do patrocinador institucional.",
            ),
            prose_block(
                "Sustentação do custeio",
                f"A alíquota efetiva apurada sobre a base de cálculo ficou em {aliq_media:.2f}%. Já a participação de inativos e pensionistas na contribuição incidente sobre proventos atingiu {pct_benef:.1f}%, indicador útil para medir o peso dos benefícios no esforço de financiamento corrente.",
            ),
            prose_block(
                "Concentração institucional",
                f"O órgão de maior arrecadação foi {orgao_top}, concentrando aproximadamente {orgao_top_pct:.1f}% do total contributivo observado. Esse dado sinaliza onde oscilações de folha ou mudanças de quadro funcional tendem a repercutir com mais intensidade no caixa previdenciário.",
            ),
        ]
        visual_blocks = [
            pair(
                graph_block("Segurado x patronal por categoria", fig_cc, "Compara a fonte de custeio entre ativos, inativos e pensionistas."),
                graph_block("Participação da arrecadação por categoria", fig_cv, "Mostra a composição relativa do ingresso contributivo."),
            ),
            pair(
                graph_block("Top órgãos arrecadadores", fig_org, "Ajuda a localizar concentração e dependência institucional da arrecadação."),
                graph_block("Relação percentual do custeio", fig_ratio, "Expõe o equilíbrio entre esforço do segurado e contribuição patronal."),
            ),
        ]
        appendix = table_block("Órgãos com maior peso no custeio", table_component)

    elif active_tab == "tab-direitos":
        dff = filter_main_df(regime=regime)
        benef = dff[dff["CATEGORIA"].isin(["INATIVOS", "PENSIONISTAS"])]
        total_benef = len(benef)
        despesa = benef["VL_VALOR_REFERENCIA"].sum()
        ticket = benef["VL_VALOR_REFERENCIA"].mean() if total_benef else 0
        pct_pens = (benef["CATEGORIA"].eq("PENSIONISTAS").sum() / total_benef * 100) if total_benef else 0
        tipo_top = safe_mode(benef["TIPO_DIREITO"], "Tipologia não identificada")
        reg_agg = benef.groupby("REGIME_PREVIDENCIARIO")["VL_VALOR_REFERENCIA"].sum().sort_values(ascending=False)
        regime_top = reg_agg.index[0] if not reg_agg.empty else regime_label
        _, fig_tipos, fig_cat, fig_reg, fig_org, table_component = update_direitos("tab-direitos", regime)

        lead = (
            f"A sessão Garantia de Direitos apresenta o estoque de benefícios e sua pressão financeira no recorte {regime_label}, "
            "com foco em tipologias, despesa agregada e pontos de atenção para sustentabilidade e governança previdenciária."
        )
        metrics_row = [
            metric("Estoque de benefícios", fmt_int(total_benef)),
            metric("Despesa estimada", rd.get("benef_total", fmt_mil(despesa))),
            metric("Ticket médio", fmt_brl(ticket)),
            metric("Participação de pensões", f"{pct_pens:.1f}%"),
        ]
        analysis_cards = [
            prose_block(
                "Estoque e pressão financeira",
                f"No recorte selecionado, o sistema contabiliza {fmt_int(total_benef)} benefícios, com despesa mensal estimada de {fmt_mil(despesa)} e ticket médio de {fmt_brl(ticket)}. Essa leitura resume o esforço financeiro associado à proteção previdenciária já materializada no estoque de pagamentos.",
            ),
            prose_block(
                "Tipologias predominantes",
                f"A tipologia com maior presença foi {tipo_top}. A abertura por categoria e por regime permite diferenciar aposentadorias civis, pensões e tipologias militares, ajudando a localizar onde o gasto está mais concentrado e quais regras de elegibilidade devem orientar análises futuras.",
            ),
            prose_block(
                "Governança e próximos acoplamentos",
                f"Na leitura atual, o regime com maior despesa agregada foi {regime_top}. O módulo já está preparado para acoplar dados de investimentos, meta atuarial e rentabilidade, permitindo que a garantia de direitos avance da fotografia do passivo para a visão integrada de solvência e cobertura.",
            ),
        ]
        visual_blocks = [
            pair(
                graph_block("Tipologias de direito", fig_tipos, "Evidencia os grupos de benefício mais numerosos no estoque."),
                graph_block("Despesa por categoria", fig_cat, "Compara aposentadorias e pensões pela ótica financeira."),
            ),
            pair(
                graph_block("Participação da despesa por regime", fig_reg, "Mostra a repartição percentual entre civil e militar."),
                graph_block("Órgãos com maior despesa", fig_org, "Indica os principais polos institucionais de pagamento de benefícios."),
            ),
        ]
        appendix = table_block("Órgãos com maior estoque e despesa", table_component)

    else:
        rdf = df_recad.copy()
        if regime != "__all__":
            rdf = rdf[rdf["RECAD_REGIME_INFERIDO"] == regime]

        total = len(rdf)
        rec_ok = len(rdf[rdf["STATUS_RECAD"] == "RECADASTRADO"])
        pendente = total - rec_ok
        pct = (rec_ok / total * 100) if total else 0
        rec_only = rdf[rdf["STATUS_RECAD"] == "RECADASTRADO"]
        gov_br = len(rec_only[rec_only["MODALIDADE_GRUPO"] == "Digital / Gov.br"])
        pct_digital = (gov_br / rec_ok * 100) if rec_ok else 0
        org_pend = rdf[rdf["STATUS_RECAD"] == "NÃO RECADASTRADO"]["RECAD_ORGAO"].value_counts()
        orgao_critico = org_pend.index[0] if not org_pend.empty else "Sem concentração crítica identificada"
        _, fig_st, fig_modal, fig_cat, fig_mes, fig_fe, fig_org, fig_sx, table_component = update_recad("tab-recad", regime)

        lead = (
            f"A sessão Prova de Vida sintetiza a execução do recadastramento no recorte {regime_label}, "
            "incluindo cobertura, pendências, preferência de canal e focos prioritários de atuação operacional."
        )
        metrics_row = [
            metric("Universo monitorado", rd.get("rec_total", fmt_int(total))),
            metric("Taxa de conclusão", rd.get("rec_pct", f"{pct:.1f}%")),
            metric("Pendentes", rd.get("rec_pending", fmt_int(pendente))),
            metric("Adoção Gov.br", f"{pct_digital:.1f}%"),
        ]
        analysis_cards = [
            prose_block(
                "Cobertura da campanha",
                f"O universo acompanhado nesta sessão reúne {fmt_int(total)} segurados, com {fmt_int(rec_ok)} registros concluídos e {fmt_int(pendente)} pendências. A taxa de conclusão de {pct:.1f}% oferece uma visão direta da maturidade operacional da campanha e da distância até a regularização integral da base.",
            ),
            prose_block(
                "Canal de atendimento",
                f"Entre os casos já concluídos, {pct_digital:.1f}% ocorreram por meio digital via Gov.br. Esse indicador ajuda a medir adesão tecnológica, necessidade de suporte assistido e capacidade de deslocar parte do esforço operacional do atendimento presencial para canais mais escaláveis.",
            ),
            prose_block(
                "Foco de cobrança",
                f"No estágio atual, o maior volume de pendências se concentra em {orgao_critico}. A leitura conjunta de status, faixa etária, sexo e órgão ajuda a orientar ações segmentadas de comunicação, reforço de prazo e busca ativa dos públicos mais críticos.",
            ),
        ]
        visual_blocks = [
            pair(
                graph_block("Status do recadastramento", fig_st, "Resume o universo já regularizado versus os casos ainda pendentes."),
                graph_block("Modalidade utilizada", fig_modal, "Mostra o peso do canal digital frente ao atendimento presencial e outros fluxos."),
            ),
            pair(
                graph_block("Status por regime/categoria", fig_cat, "Permite comparar desempenho entre grupos inferidos ou categorias simplificadas."),
                graph_block("Sazonalidade operacional", fig_mes, "Exibe a distribuição por mês de aniversário ou histórico disponível na base."),
            ),
            pair(
                graph_block("Faixas etárias do recadastramento", fig_fe, "Ajuda a calibrar linguagem e esforço operacional por perfil etário."),
                graph_block("Pendências por órgão e sexo", fig_org, "Abertura útil para definir ações de busca ativa e priorização administrativa."),
            ),
            html.Div(graph_block("Recadastramento por sexo e status", fig_sx, "Complementa a leitura de cobertura com o recorte demográfico."), style={"marginBottom": "14px"}),
        ]
        appendix = table_block("Órgãos com maior universo monitorado", table_component)

    print_content = html.Div(
        id="print-report-content",
        children=[
            html.Div(
                [
                    html.Img(src="/assets/logo-ipajm.png", style={"height": "80px", "display": "block", "margin": "0 auto 24px", "filter": "brightness(0) invert(1)"}),
                    html.H1("Relatório Executivo Previdenciário", style={"fontFamily": "'DM Serif Display',serif", "fontSize": "2.15rem", "color": "#fff", "textAlign": "center", "margin": "0 0 8px"}),
                    html.H2(f"Sessão: {session_label}", style={"fontFamily": "'DM Serif Display',serif", "fontSize": "1.28rem", "color": "rgba(255,255,255,0.88)", "textAlign": "center", "fontWeight": "normal", "margin": "0 0 4px"}),
                    html.Div(f"Recorte analítico: {regime_label}", style={"textAlign": "center", "color": "rgba(255,255,255,0.7)", "marginBottom": "22px", "fontSize": "0.95rem"}),
                    html.Div(metrics_row, style={"display": "flex", "gap": "8px", "background": "rgba(255,255,255,0.08)", "border": "1px solid rgba(255,255,255,0.15)", "borderRadius": "12px"}),
                    html.Div(f"Gerado em {rd.get('update_date', UPDATE_DATE)}", style={"textAlign": "center", "marginTop": "24px", "color": "rgba(255,255,255,0.55)"}),
                ],
                className="report-cover",
            ),
            html.Div(
                [
                    prose_block("Síntese executiva da sessão", lead),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("✅ Confiabilidade", style={"fontWeight": "700", "color": "#175414", "marginBottom": "6px"}),
                                    html.P(
                                        "Os indicadores exibidos nesta impressão são agregados e passam por tratamentos de consistência. No módulo demográfico, por exemplo, a idade média utiliza apenas idades válidas; no recadastramento, a segregação Civil/Militar foi inferida a partir de órgão e cargo para maximizar aderência operacional.",
                                        style={"margin": 0, "fontSize": "0.84rem", "lineHeight": "1.6", "color": "#2d4a2b"},
                                    ),
                                ],
                                style={"background": "#f2faf1", "border": "1px solid #d4e6d2", "borderRadius": "10px", "padding": "14px 16px", "marginBottom": "14px"},
                            )
                        ]
                    ),
                    *analysis_cards,
                ],
                className="report-section",
                style={"padding": "20px 40px", "pageBreakBefore": "always"},
            ),
            html.Div(visual_blocks, className="report-section", style={"padding": "0 40px 24px"}),
            html.Div([appendix], className="report-section", style={"padding": "0 40px 30px"}),
            html.Div(
                [
                    prose_block(
                        "LGPD e governança",
                        "O relatório permanece estritamente agregado, sem exibição de nome, CPF, matrícula ou qualquer identificador sensível. Sua finalidade é apoiar decisão executiva, priorização administrativa e acompanhamento institucional do RPPS com segurança informacional.",
                    )
                ],
                className="report-section",
                style={"padding": "0 40px 30px"},
            ),
        ],
    )

    return html.Div(
        [
            html.Div(
                id="pdf-overlay",
                style={
                    "position": "fixed",
                    "top": 0,
                    "left": 0,
                    "width": "100vw",
                    "height": "100vh",
                    "backgroundColor": "rgba(0,0,0,0.62)",
                    "zIndex": 9000,
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
                children=[
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Img(src="/assets/logo-ipajm.png", style={"height": "28px", "filter": "invert(25%) sepia(60%) saturate(700%) hue-rotate(100deg)"}),
                                            html.Span("Exportar Relatório PDF", style={"fontWeight": "700", "fontSize": "1rem", "color": "#0f2e0d", "marginLeft": "10px"}),
                                        ],
                                        style={"display": "flex", "alignItems": "center"},
                                    ),
                                    html.Button("✕", id="btn-close-pdf-modal", style={"background": "none", "border": "none", "fontSize": "1.1rem", "color": "#6b8e69", "cursor": "pointer"}),
                                ],
                                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px", "paddingBottom": "12px", "borderBottom": "1px solid #c8ddc6"},
                            ),
                            html.Div(
                                [
                                    html.Div("📋", style={"fontSize": "2.5rem", "textAlign": "center", "marginBottom": "10px"}),
                                    html.P(
                                        f"O relatório será gerado com base na sessão {session_label} e no recorte {regime_label}, incluindo gráficos, síntese analítica e microanálise das subseções.",
                                        style={"fontSize": "0.88rem", "color": "#6b8e69", "textAlign": "center", "lineHeight": "1.65", "marginBottom": "18px"},
                                    ),
                                    html.Button(
                                        [html.Span("🖨 "), html.Span("Abrir diálogo de impressão")],
                                        id="btn-print-pdf",
                                        n_clicks=0,
                                        style={"width": "100%", "padding": "13px", "background": "#175414", "color": "white", "border": "none", "borderRadius": "8px", "fontWeight": "700", "fontSize": "0.92rem", "cursor": "pointer"},
                                    ),
                                ]
                            ),
                        ],
                        style={"background": "#ffffff", "borderRadius": "16px", "padding": "28px 32px", "width": "460px", "boxShadow": "0 12px 48px rgba(0,0,0,0.28)", "zIndex": 9001, "fontFamily": "Plus Jakarta Sans,sans-serif"},
                    )
                ],
            ),
            print_content,
        ]
    )


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
    Output("btn-print-pdf", "disabled"),
    Input("btn-print-pdf", "n_clicks"),
    prevent_initial_call=True,
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
    Output("pdf-modal-container", "style"),
    Input("btn-close-pdf-modal", "n_clicks"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
