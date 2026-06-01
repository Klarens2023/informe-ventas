"""Helpers de formato y charts. Formato Colombiano:
   . = separador de miles, , = decimal
   M  = millón     (10^6)
   MM = mil millones (10^9)
   B  = billón     (10^12)
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

BLUE_SCALE  = px.colors.sequential.Blues_r
BRAND_COLOR = '#1d4ed8'
GOLD_COLOR  = '#f59e0b'


# ── FORMATO MONEDA COLOMBIANO ─────────────────────────────────────────────────

def _co_number(val: float, decimals: int = 0) -> str:
    """Formato Colombiano: 1.234.567,89 (. miles, , decimal)."""
    if pd.isna(val):
        return '0'
    s = f'{val:,.{decimals}f}'          # 1,234,567.89  (formato US)
    # Swap separators: , → tmp → . → , → tmp → .
    return s.replace(',', '·').replace('.', ',').replace('·', '.')


def fmt_currency(val: float) -> str:
    """
    Formato moneda compacto Colombiano con $.
    Ej.:  $1,5M   = 1.500.000
          $14,2MM = 14.200.000.000
          $1,3B   = 1.300.000.000.000
    """
    if pd.isna(val) or val == 0:
        return '$0'
    sign = '-' if val < 0 else ''
    a = abs(val)

    if a >= 1_000_000_000_000:
        return f'{sign}${_co_number(a / 1_000_000_000_000, 2)}B'
    if a >= 1_000_000_000:
        return f'{sign}${_co_number(a / 1_000_000_000, 2)}MM'
    if a >= 1_000_000:
        return f'{sign}${_co_number(a / 1_000_000, 2)}M'
    if a >= 1_000:
        return f'{sign}${_co_number(a / 1_000, 1)}K'
    return f'{sign}${_co_number(a, 0)}'


def fmt_money_full(val: float) -> str:
    """Moneda completa: $1.234.567,89 — usado en tablas/totales."""
    if pd.isna(val):
        return '$0'
    sign = '-' if val < 0 else ''
    return f'{sign}${_co_number(abs(val), 0)}'


def fmt_int_co(val: float) -> str:
    """Entero con separadores Colombianos: 1.234.567"""
    if pd.isna(val):
        return '0'
    return _co_number(val, 0)


def fmt_pct(val: float, decimals: int = 2) -> str:
    if pd.isna(val):
        return '0%'
    return f'{_co_number(val, decimals)}%'


# ── HELPERS DE FORMATO PARA EJES PLOTLY ──────────────────────────────────────

def axis_money_co(fig: go.Figure, axis: str = 'y', hide_labels: bool = True) -> go.Figure:
    """
    Aplica al eje (x o y) un formato monetario Colombiano.

    Plotly muestra ticks en notación SI inglesa (G = 10⁹, T = 10¹²), que en
    Colombia es confuso. Por defecto ocultamos los ticks (las barras ya
    muestran los valores formateados en español con fmt_currency).
    """
    if hide_labels:
        upd = dict(showticklabels=False, showgrid=True,
                   gridcolor='rgba(21,101,192,.14)', zerolinecolor='rgba(21,101,192,.2)')
    else:
        upd = dict(tickprefix='$', separatethousands=True, tickformat=',.0f')
    if axis == 'y':
        fig.update_yaxes(**upd)
    else:
        fig.update_xaxes(**upd)
    return fig


def fix_money_axes(fig: go.Figure) -> go.Figure:
    """Atajo: oculta ticks de ambos ejes para gráficas con etiquetas en barras."""
    axis_money_co(fig, 'y', hide_labels=True)
    return fig


# ── CHART HELPERS ─────────────────────────────────────────────────────────────

def bar_horizontal(df: pd.DataFrame, x: str, y: str, color_col: str = None,
                   title: str = '', height: int = 400) -> go.Figure:
    df = df.sort_values(x, ascending=True)
    fig = px.bar(
        df, x=x, y=y, orientation='h', text=x,
        color=color_col or x,
        color_continuous_scale=BLUE_SCALE,
        title=title,
    )
    fig.update_traces(text=df[x].apply(fmt_currency), textposition='outside')
    fig.update_layout(height=height, coloraxis_showscale=False,
                      margin=dict(l=10, r=10, t=40, b=10))
    axis_money_co(fig, 'x')
    return fig


def bar_vertical(df: pd.DataFrame, x: str, y: str, color_col: str = None,
                 title: str = '', height: int = 350) -> go.Figure:
    fig = px.bar(
        df, x=x, y=y, text=y,
        color=color_col or y,
        color_continuous_scale=BLUE_SCALE,
        title=title,
    )
    fig.update_traces(text=df[y].apply(fmt_currency), textposition='outside')
    fig.update_xaxes(tickangle=40)
    fig.update_layout(height=height, coloraxis_showscale=False,
                      margin=dict(l=10, r=10, t=40, b=80))
    axis_money_co(fig, 'y')
    return fig


def donut(df: pd.DataFrame, values: str, names: str, title: str = '') -> go.Figure:
    fig = px.pie(df, values=values, names=names, hole=0.45,
                 color_discrete_sequence=px.colors.qualitative.Safe,
                 title=title)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def line_trend(df: pd.DataFrame, x: str, y: str, group: str = None,
               title: str = '', height: int = 350) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=group, markers=True,
                  title=title, color_discrete_sequence=px.colors.qualitative.Safe)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10))
    axis_money_co(fig, 'y')
    return fig


# ── KPI ────────────────────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, delta: str = '', color: str = BRAND_COLOR) -> str:
    delta_html = f'<div style="font-size:0.8rem;color:#6b7280">{delta}</div>' if delta else ''
    return f"""
    <div style="background:{color};padding:16px 20px;border-radius:12px;
                color:white;text-align:center;margin:4px">
        <div style="font-size:1.6rem;font-weight:700;color:#fbbf24">{value}</div>
        <div style="font-size:0.85rem;opacity:0.9">{label}</div>
        {delta_html}
    </div>"""


# ── TABLAS ────────────────────────────────────────────────────────────────────

def summary_table(df: pd.DataFrame, money_cols: list = None,
                  pct_cols: list = None) -> pd.DataFrame:
    """
    Convierte columnas a strings con formato.
    money_cols → formato moneda completo ($1.234.567)
    pct_cols   → formato porcentaje (12,34%)
    """
    out = df.copy()
    for col in (money_cols or []):
        if col in out.columns:
            out[col] = out[col].apply(fmt_money_full)
    for col in (pct_cols or []):
        if col in out.columns:
            out[col] = out[col].apply(lambda v: fmt_pct(v, 2))
    return out
