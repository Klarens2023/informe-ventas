"""Shared UI helpers: CSS, KPI cards, chart defaults, period pills."""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ── Colores ABAD ──────────────────────────────────────────────────────────────
BG, CARD, CARD2 = '#0A1628', '#0D2137', '#112240'
KPI_VAL = '#F57F17'
KPI_LBL = '#90CAF9'
TEAL,  TEAL2  = '#00838F', '#4DB6AC'
GREEN, RED    = '#2E7D32', '#B71C1C'
ORANGE, TEXT  = '#EF6C00', '#e2e8f0'

CHART_COLORS = [
    '#1565C0','#00838F','#4DB6AC','#1976D2','#F57F17',
    '#2E7D32','#6A1B9A','#B71C1C','#EF6C00','#546E7A',
]

DARK_CSS = """<style>
/* ── Fondo navy ── */
.stApp,[data-testid="stAppViewContainer"]{background:#0A1628!important}
.main .block-container{background:#0A1628;padding-top:1rem;padding-bottom:2rem}

/* ── BARRA SUPERIOR DE STREAMLIT (la blanca) ── */
[data-testid="stHeader"],header[data-testid="stHeader"]{
    background:linear-gradient(90deg,#0A1628 0%,#0D2137 60%,#102a45 100%)!important;
    border-bottom:1px solid rgba(21,101,192,.3)!important;
    height:58px!important;
}
[data-testid="stHeader"] *{color:#e2e8f0!important}
/* Notificaciones tipo "Source file changed" en gris azulado en vez de naranja claro */
[data-testid="stStatusWidget"] *{color:#90CAF9!important;font-size:.78rem!important}

/* ── BANNER KLARENS (sobre la barra de Streamlit) ── */
.klarens-topbar{
    position:fixed;
    top:0; left:0; right:0;
    height:58px;
    background:linear-gradient(90deg,#0A1628 0%,#0D2137 60%,#102a45 100%);
    border-bottom:1px solid rgba(21,101,192,.4);
    display:flex;
    align-items:center;
    padding:0 26px;
    z-index:999990;
    gap:14px;
    pointer-events:none;  /* deja pasar clics al botón nativo de Streamlit */
}
.klarens-topbar .klarens-logo{
    height:38px;
    width:auto;
    object-fit:contain;
}
.klarens-topbar .klarens-placeholder{
    width:38px;height:38px;
    background:linear-gradient(135deg,#F57F17,#FFA726);
    border-radius:9px;
    color:#0A1628;
    font-weight:900;
    font-size:1.45rem;
    display:flex;align-items:center;justify-content:center;
    box-shadow:0 2px 8px rgba(245,127,23,.4);
}
.klarens-topbar .klarens-title{
    color:#fff;
    font-size:1.18rem;
    font-weight:800;
    letter-spacing:.6px;
}
.klarens-topbar .klarens-sub{
    color:#90CAF9;
    font-size:.85rem;
    margin-left:2px;
}

/* ─────────────────────────────────────────────────────────────────────────
   SIDEBAR
   Pantallas normales (>1100px): EXPANDIDO (215px, iconos + texto), siempre visible.
   Pantallas pequeñas (<=1100px): colapsa a 60px (iconos) y expande al hacer hover.
   ───────────────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"],
div[data-testid="stSidebar"],
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0A1628 0%,#0D2137 100%)!important;
    border-right:1px solid rgba(21,101,192,.3)!important;
    width:215px!important;
    min-width:215px!important;
    max-width:215px!important;
    flex-basis:215px!important;
    flex-shrink:0!important;
    transition:width .22s,min-width .22s,max-width .22s,flex-basis .22s!important;
    overflow:hidden!important;
    transform:none!important;
    visibility:visible!important;
    z-index:999;
    position:relative!important;
}
/* Wrappers internos siguen el ancho del padre */
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{
    width:100%!important;
    min-width:100%!important;
    max-width:100%!important;
    padding:0!important;
    overflow:hidden!important;
}

section[data-testid="stSidebar"] *{color:#e2e8f0!important}
section[data-testid="stSidebar"] hr{
    border-color:rgba(21,101,192,.3)!important;
    margin:6px 8px!important;
}

/* En pantalla normal el texto del nav siempre se ve */
.abad-nav .brand .brand-text,
.abad-nav .nav-item .nav-label{opacity:1!important}

/* Ocultar TODOS los controles nativos del sidebar */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[kind="header"],
button[kind="headerNoPadding"],
[data-testid="baseButton-header"],
[data-testid="baseButton-headerNoPadding"],
[data-testid="stSidebarHeader"],
[data-testid="stSidebarNav"],[data-testid="stSidebarNavItems"],[data-testid="stSidebarNavSeparator"]{
    display:none!important;
}

/* Main: el flexbox de Streamlit ya lo coloca al lado del sidebar → sin margin extra */
section.main,.main,[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
    margin-left:0!important;
}

/* ── PANTALLAS PEQUEÑAS: colapsar a iconos + hover para expandir ── */
@media (max-width:1100px){
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"],
    [data-testid="stSidebar"]{
        width:60px!important;min-width:60px!important;max-width:60px!important;flex-basis:60px!important;
    }
    section[data-testid="stSidebar"]:hover,
    div[data-testid="stSidebar"]:hover,
    [data-testid="stSidebar"]:hover{
        width:215px!important;min-width:215px!important;max-width:215px!important;flex-basis:215px!important;
        overflow:visible!important;
    }
    /* texto oculto en reposo, visible en hover */
    .abad-nav .brand .brand-text,
    .abad-nav .nav-item .nav-label{opacity:0!important}
    section[data-testid="stSidebar"]:hover .abad-nav .brand .brand-text,
    section[data-testid="stSidebar"]:hover .abad-nav .nav-item .nav-label{opacity:1!important}
}

/* ── NAVEGACIÓN HTML PURA ───────────────────────────────────────────────── */
.abad-nav{
    display:flex;flex-direction:column;
    padding:8px 0 16px 0;
    width:100%;
    min-height:calc(100vh - 20px);
    overflow:hidden;
}
.abad-nav .brand{
    display:flex;align-items:center;
    padding:8px 0 8px 16px;
    height:48px;overflow:hidden;white-space:nowrap;
    color:#e2e8f0;
}
.abad-nav .brand .logo{
    font-size:1.4rem;line-height:1;
    min-width:24px;max-width:24px;text-align:center;
    flex-shrink:0;
}
.abad-nav .brand .brand-text{
    font-size:.95rem;font-weight:700;
    margin-left:14px;
    opacity:0;transition:opacity .2s ease;
}
section[data-testid="stSidebar"]:hover .abad-nav .brand .brand-text{opacity:1}

.abad-nav .nav-item{
    display:flex!important;align-items:center;
    padding:0 0 0 16px;
    height:40px;
    color:#cfd8e3!important;text-decoration:none!important;
    overflow:hidden;white-space:nowrap;
    transition:background .15s,color .15s;
    box-sizing:border-box;
    border-left:3px solid transparent;
}
.abad-nav .nav-item:hover{
    background:rgba(21,101,192,.28);
    color:#fff!important;
    border-left-color:#F57F17;
}
.abad-nav .nav-item .nav-icon{
    font-size:1.2rem;line-height:1;
    min-width:24px;max-width:24px;
    text-align:center;
    display:inline-block;flex-shrink:0;
}
.abad-nav .nav-item .nav-label{
    font-size:.86rem;color:inherit;
    margin-left:14px;
    opacity:0;transition:opacity .2s ease;
    overflow:hidden;
}
section[data-testid="stSidebar"]:hover .abad-nav .nav-item .nav-label{opacity:1}

/* Sección admin (al final, atenuado y separado) */
.abad-nav-bottom{
    margin-top:auto;
    padding-top:10px;
}
.abad-nav-bottom .admin-divider{
    height:1px;
    background:rgba(21,101,192,.2);
    margin:0 10px 8px 10px;
    border:none;
}
.abad-nav .nav-item.nav-admin{
    opacity:.5;
    height:36px;
}
.abad-nav .nav-item.nav-admin .nav-icon{
    font-size:1rem;
}
.abad-nav .nav-item.nav-admin .nav-label{
    font-size:.78rem;
    color:#90A4AE!important;
}
.abad-nav .nav-item.nav-admin:hover{
    opacity:1;
    background:rgba(245,127,23,.18);
    border-left-color:#F57F17;
}

/* ── Tipografía ── */
h1,h2,h3,h4,h5{color:#fff!important}
p,.stMarkdown,li{color:#e2e8f0!important}
label{color:#90CAF9!important;font-size:.82rem!important}

/* ── Métricas ── */
[data-testid="metric-container"]{
    background:#0D2137;border-radius:12px;
    padding:14px 12px;border:1px solid rgba(21,101,192,.22)
}
[data-testid="stMetricValue"]{color:#F57F17!important;font-weight:800!important}
[data-testid="stMetricLabel"]{color:#90CAF9!important;font-size:.78rem!important}

/* ── Dividers ── */
hr{border-color:rgba(21,101,192,.15)!important}

/* ── DataFrames nativos ── */
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}

/* ── TABLA CUSTOM (.abad-tbl) — diseño agradable, ajusta ancho ── */
.abad-tw{
    border-radius:12px;
    border:1px solid rgba(21,101,192,.22);
    margin:6px 0 14px 0;
    overflow:hidden;
    background:#0B1B2E;
}
.abad-tw.scroll{overflow:auto}
.abad-tbl{
    width:100%;
    border-collapse:collapse;
    font-size:.83rem;
}
.abad-tbl thead th{
    background:linear-gradient(90deg,#102a45,#13294a);
    color:#9FC4EA;
    font-weight:700;
    font-size:.72rem;
    letter-spacing:.5px;
    text-transform:uppercase;
    padding:11px 14px;
    border-bottom:2px solid rgba(21,101,192,.45);
    white-space:nowrap;
    position:sticky;top:0;z-index:2;
}
.abad-tbl thead th.r{text-align:right}
.abad-tbl thead th.l{text-align:left}
.abad-tbl tbody td{
    padding:8px 14px;
    color:#dbe4ee;
    border-bottom:1px solid rgba(21,101,192,.09);
    vertical-align:top;
}
.abad-tbl tbody td.l{text-align:left;white-space:normal;word-break:break-word}
.abad-tbl tbody td.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:600}
.abad-tbl tbody td.b{font-weight:700;color:#fff}
.abad-tbl tbody tr:nth-child(even){background:rgba(13,33,55,.45)}
.abad-tbl tbody tr:hover{background:rgba(21,101,192,.16)}
.abad-tbl tbody tr:last-child td{border-bottom:none}
/* Fila de totales (clase .total) */
.abad-tbl tbody tr.total td{
    background:rgba(245,127,23,.14)!important;
    color:#FFD54F;font-weight:800;
    border-top:2px solid rgba(245,127,23,.5);
}

/* ── BARRA DE SCROLL visible (tema oscuro) ── */
.abad-tw.scroll::-webkit-scrollbar{height:14px;width:14px}
.abad-tw.scroll::-webkit-scrollbar-track{background:#0A1A2C;border-radius:7px}
.abad-tw.scroll::-webkit-scrollbar-thumb{
    background:linear-gradient(135deg,#1565C0,#00838F);
    border-radius:7px;
    border:3px solid #0A1A2C;
    min-height:40px;min-width:40px;
}
.abad-tw.scroll::-webkit-scrollbar-thumb:hover{
    background:linear-gradient(135deg,#1976D2,#4DB6AC);
}
.abad-tw.scroll::-webkit-scrollbar-corner{background:#0A1A2C}
.abad-tw.scroll{scrollbar-width:thin;scrollbar-color:#1565C0 #0A1A2C}

/* ── Tabla ANCHA (scroll horizontal) — ej. detalle diario ── */
.abad-tbl.wide{width:max-content;min-width:100%;table-layout:auto}
.abad-tbl.wide th,.abad-tbl.wide td{white-space:nowrap!important;word-break:normal!important}
.abad-tbl.wide td.r,.abad-tbl.wide th.r{min-width:82px}
/* Primera columna (nombre PV) fija al hacer scroll horizontal */
.abad-tbl.wide th:first-child,.abad-tbl.wide td:first-child{
    position:sticky;left:0;z-index:1;
    min-width:170px;
    background:#0B1B2E;
}
.abad-tbl.wide thead th:first-child{z-index:3;background:#102a45}
.abad-tbl.wide tbody tr:nth-child(even) td:first-child{background:#0E2236}
.abad-tbl.wide tbody tr.total td:first-child{background:#2a1f10!important}

/* ── Inputs / Select ── */
[data-baseweb="select"] > div,[data-baseweb="select"] input{
    background:#0D2137!important;color:#e2e8f0!important;
    border-color:rgba(21,101,192,.4)!important
}
[data-baseweb="tag"]{background:#1565C0!important;color:#fff!important}
[data-baseweb="tag"] span{color:#fff!important}

/* ── DROPDOWN LISTA (el popover blanco) ── */
[data-baseweb="popover"]{background:#0D2137!important}
[data-baseweb="popover"]>div{
    background:#0D2137!important;
    border:1px solid rgba(21,101,192,.4)!important;
    border-radius:8px!important
}
[data-baseweb="menu"]{background:#0D2137!important}
[data-baseweb="option"]{background:#0D2137!important;color:#e2e8f0!important}
[data-baseweb="option"]:hover,[data-baseweb="option"][aria-selected="true"]{background:#112240!important}
ul[role="listbox"]{background:#0D2137!important}
li[role="option"]{color:#e2e8f0!important;background:#0D2137!important}
li[role="option"]:hover,li[role="option"][aria-selected="true"]{background:#112240!important}
[data-baseweb="option"] *,[data-baseweb="menu"] *{color:#e2e8f0!important}

/* ─────────────────────────────────────────────────────────────────────────
   PILLS DE PERÍODO — contraste alto: seleccionado vs no seleccionado
   Selectores agresivos para vencer los estilos default de Streamlit/BaseUI
   ───────────────────────────────────────────────────────────────────────── */
div[data-testid="stPills"],[data-testid="stPills"]{gap:10px!important;flex-wrap:wrap!important;padding:4px 0}
div[data-testid="stPills"] label{
    color:#90CAF9!important;font-size:.82rem!important;
    margin-bottom:8px!important;font-weight:500!important;
}

/* ━━━━━ NO SELECCIONADO ━━━━━ contorno tenue, texto apagado */
div[data-testid="stPills"] button,
[data-testid="stPills"] button,
[data-testid="stPills"] [role="button"]{
    background:transparent!important;
    color:#78909C!important;
    border:1.5px solid rgba(120,144,156,.35)!important;
    border-radius:10px!important;
    padding:9px 22px!important;
    font-size:.85rem!important;
    font-weight:500!important;
    letter-spacing:.4px!important;
    transition:all .2s ease!important;
    box-shadow:none!important;
    text-shadow:none!important;
    cursor:pointer!important;
    min-width:120px!important;
    opacity:.75!important;
}
div[data-testid="stPills"] button:hover,
[data-testid="stPills"] button:hover{
    border-color:#4DB6AC!important;
    color:#4DB6AC!important;
    background:rgba(77,182,172,.06)!important;
    opacity:1!important;
    transform:translateY(-1px);
}

/* ━━━━━ SELECCIONADO ━━━━━ relleno teal brillante, glow, ✓ */
div[data-testid="stPills"] button[aria-pressed="true"],
div[data-testid="stPills"] button[data-selected="true"],
div[data-testid="stPills"] button[kind="pillsActive"],
[data-testid="stPills"] button[aria-pressed="true"],
[data-testid="stPills"] [aria-pressed="true"],
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button.selected,
[data-testid="stPills"] [data-baseweb="button"][aria-pressed="true"]{
    background:linear-gradient(135deg,#00838F 0%,#4DB6AC 100%)!important;
    color:#FFFFFF!important;
    border:1.5px solid #4DB6AC!important;
    border-radius:10px!important;
    font-weight:700!important;
    opacity:1!important;
    box-shadow:0 4px 14px rgba(0,131,143,.5),
               inset 0 1px 0 rgba(255,255,255,.25)!important;
    transform:translateY(-1px);
    text-shadow:0 1px 2px rgba(0,0,0,.2);
}

/* Checkmark sutil antes del texto seleccionado */
div[data-testid="stPills"] button[aria-pressed="true"]::before,
[data-testid="stPills"] [aria-pressed="true"]::before{
    content:"✓ ";
    font-weight:900;
    color:#FFFFFF;
    opacity:.9;
}

div[data-testid="stPills"] button[aria-pressed="true"]:hover,
[data-testid="stPills"] button[aria-pressed="true"]:hover{
    box-shadow:0 6px 18px rgba(0,131,143,.65),
               inset 0 1px 0 rgba(255,255,255,.3)!important;
    transform:translateY(-2px);
}

/* Asegurar texto visible y centrado en ambos estados (anula BaseUI) */
div[data-testid="stPills"] button > div,
div[data-testid="stPills"] button > span,
[data-testid="stPills"] button > div,
[data-testid="stPills"] button > span{
    color:inherit!important;
    font-weight:inherit!important;
    background:transparent!important;
}

/* ── Filter chip (título dinámico de filtros) ── */
.filter-title{
    background:linear-gradient(90deg,#0D2137,#112240);
    border-left:4px solid #F57F17;
    border-radius:8px;
    padding:10px 16px;
    margin:8px 0 14px 0;
    color:#e2e8f0;
    font-size:.92rem;
    display:flex;
    flex-wrap:wrap;
    align-items:center;
    gap:8px;
}
.filter-title .lbl{color:#90CAF9;font-size:.78rem;text-transform:uppercase;letter-spacing:.5px}
.filter-title .chip{
    background:rgba(21,101,192,.25);
    border:1px solid rgba(21,101,192,.5);
    border-radius:14px;
    padding:3px 10px;
    font-size:.8rem;
    color:#e2e8f0;
    font-weight:500;
}
.filter-title .chip.accent{
    background:rgba(245,127,23,.18);
    border-color:rgba(245,127,23,.5);
    color:#FFD54F;
}

/* ── Streamlit buttons (dark theme) ── */
.stButton > button,div[data-testid="stButton"] > button{
    background:#0D2137!important;
    color:#90CAF9!important;
    border:1px solid rgba(21,101,192,.5)!important;
    border-radius:8px!important;
    padding:6px 12px!important;
    font-size:.9rem!important;
    transition:all .15s!important;
}
.stButton > button:hover,div[data-testid="stButton"] > button:hover{
    background:#112240!important;
    border-color:#1565C0!important;
    color:#e2e8f0!important;
    transform:translateY(-1px);
}

/* ── Alerts ── */
.stAlert{border-radius:10px}

/* ── Responsive: en pantallas pequeñas apilar columnas ── */
@media (max-width:900px){
    [data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
}
</style>"""


# ── Layout helpers ────────────────────────────────────────────────────────────

def dark_chart(fig: go.Figure, height: int = 380, hide_money_axis: str = None) -> go.Figure:
    """
    Aplica el tema oscuro + headroom automático para que las etiquetas exteriores
    de las barras (textposition='outside') no se corten cuando el valor es grande.

    hide_money_axis: 'x' o 'y' para ocultar los ticks de ese eje
    (Plotly los muestra en notación SI inglesa G/T, confusa en Colombia).
    """
    fig.update_layout(
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(13,27,42,0.55)',
        font=dict(color=TEXT, family='Arial', size=12),
        margin=dict(l=10, r=110, t=40, b=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT)),
        xaxis=dict(gridcolor='rgba(21,101,192,.14)', zerolinecolor='rgba(21,101,192,.2)'),
        yaxis=dict(gridcolor='rgba(21,101,192,.14)', zerolinecolor='rgba(21,101,192,.2)'),
    )

    # Etiquetas exteriores nunca se recortan
    try:
        fig.update_traces(cliponaxis=False, selector=dict(type='bar'))
    except Exception:
        pass

    # Calcular rangos para barras horizontales/verticales y dejar espacio al label
    try:
        x_vals_h, y_vals_v = [], []
        for tr in fig.data:
            if getattr(tr, 'type', '') != 'bar':
                continue
            ori = getattr(tr, 'orientation', None)
            if ori == 'h' and tr.x is not None:
                x_vals_h += [v for v in tr.x if isinstance(v, (int, float))]
            elif (ori == 'v' or ori is None) and tr.y is not None:
                y_vals_v += [v for v in tr.y if isinstance(v, (int, float))]

        def _range(values, head=0.22, foot=0.05):
            if not values:
                return None
            vmin, vmax = min(values), max(values)
            span = (vmax - vmin) or abs(vmax) or abs(vmin) or 1
            lo = vmin - span * foot if vmin < 0 else 0
            hi = vmax + span * head if vmax > 0 else span * foot
            return [lo, hi]

        rx = _range(x_vals_h)
        if rx:
            fig.update_xaxes(range=rx)
        ry = _range(y_vals_v, head=0.18)
        # Solo aplicar al eje Y si no hay yaxis2 (gráficas de doble eje)
        if ry and 'yaxis2' not in fig.layout:
            fig.update_yaxes(range=ry)
    except Exception:
        pass

    if hide_money_axis == 'y':
        fig.update_yaxes(showticklabels=False)
    elif hide_money_axis == 'x':
        fig.update_xaxes(showticklabels=False)
    return fig


def kpi_html(value: str, label: str, delta: str = '',
             val_color: str = KPI_VAL, bg: str = CARD) -> str:
    dlt = (f'<div style="color:{TEAL2};font-size:.74rem;margin-top:5px">{delta}</div>'
           if delta else '')
    return f"""
<div style="background:{bg};border-radius:12px;padding:18px 14px;text-align:center;
            border:1px solid rgba(21,101,192,.22);margin:3px;min-height:90px">
  <div style="font-size:1.6rem;font-weight:800;color:{val_color};line-height:1.1">{value}</div>
  <div style="font-size:.78rem;color:{KPI_LBL};margin-top:6px;letter-spacing:.3px">{label}</div>
  {dlt}
</div>"""


def section_title(text: str) -> str:
    return (f'<div style="font-size:1rem;font-weight:700;color:#e2e8f0;'
            f'border-left:4px solid {TEAL};padding-left:10px;'
            f'margin:18px 0 10px 0">{text}</div>')


def page_header(title: str, subtitle: str = '', badge: str = '') -> None:
    bdg = (f'<div style="background:#F57F17;color:#0A1628;border-radius:20px;'
           f'padding:7px 20px;font-weight:700;font-size:.88rem">{badge}</div>'
           if badge else '')
    st.markdown(f"""
<div style="background:linear-gradient(90deg,#0A1628,#0D2137,#112240);
            border-radius:14px;padding:18px 26px;margin-bottom:14px;
            border:1px solid rgba(21,101,192,.28);
            display:flex;justify-content:space-between;align-items:center">
  <div>
    <div style="font-size:1.4rem;font-weight:800;color:#fff">{title}</div>
    {f'<div style="font-size:.84rem;color:#90CAF9;margin-top:3px">{subtitle}</div>' if subtitle else ''}
  </div>
  {bdg}
</div>""", unsafe_allow_html=True)


def filter_title(filtros: dict) -> None:
    """
    Muestra un chip con los filtros activos.
    filtros = {'Período': ['ABRIL 2026', 'MAYO 2026'], 'Canal': ['001 - TAT'], ...}
    Las claves con valor vacío o None se muestran como 'Todos'.
    """
    chips = []
    for nombre, valores in filtros.items():
        if not valores:
            txt = 'Todos'
            cls = 'chip'
        elif isinstance(valores, (list, tuple)):
            if len(valores) == 0:
                txt = 'Todos'
                cls = 'chip'
            elif len(valores) <= 3:
                txt = ', '.join(str(v) for v in valores)
                cls = 'chip accent'
            else:
                txt = f'{len(valores)} seleccionados'
                cls = 'chip accent'
        else:
            txt = str(valores)
            cls = 'chip accent'
        chips.append(f'<span class="lbl">{nombre}:</span><span class="{cls}">{txt}</span>')
    html = '<div class="filter-title">📌 ' + '&nbsp;&nbsp;'.join(chips) + '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Tabla estilizada (HTML) ───────────────────────────────────────────────────

import re as _re
# Reconoce números, moneda y formato compacto colombiano: $3,42M  $840,4K  $1,3B  12,34%
_NUM_RE = _re.compile(r'^[\$\-]?\s*[\d.,]+\s*(?:K|M|MM|B)?\s*%?$', _re.IGNORECASE)


def _is_num_col(series) -> bool:
    """True si la columna parece numérica/moneda/porcentaje (para alinear a la derecha)."""
    vals = [str(v).strip() for v in series.tolist() if str(v).strip() not in ('', 'nan', 'None', 'NaN')]
    if not vals:
        return False
    hits = sum(1 for v in vals if _NUM_RE.match(v))
    return hits / len(vals) >= 0.75


def styled_table(df, max_height: int = None, x_scroll: bool = False,
                 total_rows: list = None) -> None:
    """
    Renderiza un DataFrame (ya formateado) como tabla HTML con tema oscuro.
    · Ajusta el ancho al contenedor (columnas de texto hacen wrap → sin scroll horizontal)
    · max_height: activa scroll vertical (px)
    · x_scroll: permite scroll horizontal (para tablas muy anchas, ej. detalle diario)
    · total_rows: lista de valores de la 1ª columna que se resaltan como fila de totales
    """
    import pandas as _pd
    if df is None or len(df) == 0:
        st.info('Sin datos para mostrar.')
        return

    cols = list(df.columns)
    right = {c for c in cols if _is_num_col(df[c])}
    total_rows = set(total_rows or [])

    ths = ''.join(f'<th class="{"r" if c in right else "l"}">{c}</th>' for c in cols)

    body = []
    for _, row in df.iterrows():
        is_total = str(row[cols[0]]) in total_rows
        tds = []
        for i, c in enumerate(cols):
            cls = 'r' if c in right else 'l'
            if i == 0 and not is_total:
                cls += ' b'
            val = row[c]
            val = '' if _pd.isna(val) else str(val)
            tds.append(f'<td class="{cls}">{val}</td>')
        tr_cls = ' class="total"' if is_total else ''
        body.append(f'<tr{tr_cls}>' + ''.join(tds) + '</tr>')

    wrap_cls = 'abad-tw'
    tbl_cls  = 'abad-tbl'
    style = ''
    if max_height or x_scroll:
        wrap_cls += ' scroll'
        if max_height:
            style += f'max-height:{max_height}px;'
        if not x_scroll:
            style += 'overflow-x:hidden;'
    if x_scroll:
        # tabla ancha: columnas con ancho real → aparece scroll horizontal
        tbl_cls += ' wide'

    html = (f'<div class="{wrap_cls}" style="{style}">'
            f'<table class="{tbl_cls}"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')
    st.markdown(html, unsafe_allow_html=True)


# ── Sidebar con navegación HTML custom (sin st.page_link) ────────────────────

_NAV_ITEMS = [
    ('📊', 'Reporte',       '/'),
    ('🏪', 'Canal Ventas',  '/Canal_Ventas'),
    ('👤', 'Vendedor',      '/Vendedor'),
    ('📦', 'Producto',      '/Producto'),
    ('🏬', 'Punto Venta',   '/Punto_Venta'),
    ('🥛', 'Leche',         '/Leche'),
    ('🧴', 'Suero',         '/Suero'),
    ('📈', 'Márgenes',      '/Margenes'),
    ('🎁', 'Descuentos',    '/Descuentos'),
    ('💼', 'Financiero',    '/Financiero'),
]

# Accesos administrativos — discretos, al final del sidebar
_ADMIN_ITEMS = [
    ('⚙️', 'Importar Data', '/Importar_Data'),
]


_LOGO_CACHE = {}


def _klarens_logo_html() -> str:
    """Busca un logo en assets/klarens.{png,svg,jpg}; si no existe, placeholder."""
    import os, base64
    if 'html' in _LOGO_CACHE:
        return _LOGO_CACHE['html']
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets   = os.path.join(base_dir, 'assets')
    mimes    = {'png': 'image/png', 'svg': 'image/svg+xml',
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}
    for ext, mime in mimes.items():
        p = os.path.join(assets, f'klarens.{ext}')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            _LOGO_CACHE['html'] = f'<img class="klarens-logo" src="data:{mime};base64,{b64}" alt="Klarens">'
            return _LOGO_CACHE['html']
    _LOGO_CACHE['html'] = '<div class="klarens-placeholder">K</div>'
    return _LOGO_CACHE['html']


def top_banner() -> None:
    """Banner superior con el logo de Klarens (cubre la barra blanca de Streamlit)."""
    st.markdown(
        f'<div class="klarens-topbar">{_klarens_logo_html()}'
        f'<span class="klarens-title">Klarens</span>'
        f'<span class="klarens-sub">· Reportes ABAD</span></div>',
        unsafe_allow_html=True,
    )


def minimal_sidebar() -> None:
    """Navegación HTML pura — control total sobre tamaños e iconos."""
    top_banner()  # banner superior con logo en cada página
    items_html = ''.join(
        f'<a class="nav-item" href="{href}" target="_self">'
        f'<span class="nav-icon">{icon}</span>'
        f'<span class="nav-label">{label}</span>'
        f'</a>'
        for icon, label, href in _NAV_ITEMS
    )
    admin_html = ''.join(
        f'<a class="nav-item nav-admin" href="{href}" target="_self" title="{label}">'
        f'<span class="nav-icon">{icon}</span>'
        f'<span class="nav-label">{label}</span>'
        f'</a>'
        for icon, label, href in _ADMIN_ITEMS
    )
    nav_html = f"""
<div class="abad-nav">
  <div class="brand">
    <span class="logo">📊</span>
    <span class="brand-text">ABAD</span>
  </div>
  <hr>
  {items_html}
  <div class="abad-nav-bottom">
    <div class="admin-divider"></div>
    {admin_html}
  </div>
</div>
"""
    with st.sidebar:
        st.markdown(nav_html, unsafe_allow_html=True)


# ── Period pills (inline, dentro del módulo) ──────────────────────────────────

MONTH_ORDER = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO',
               'JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']


def period_pills(fetch_periodos_fn) -> tuple:
    """
    Renderiza botones de período dentro del módulo.
    Usa session_state como caché (se limpia al recargar la página del navegador).
    Todos los períodos seleccionados por defecto.
    """
    # Caché en session_state → se renueva con F5, no retiene valores obsoletos
    if 'abad_periodos' not in st.session_state:
        try:
            periodos = fetch_periodos_fn()
            st.session_state['abad_periodos'] = periodos
        except Exception as e:
            st.error(f'Error cargando períodos: {e}')
            st.stop()

    periodos = st.session_state.get('abad_periodos', [])

    if not periodos:
        st.session_state.pop('abad_periodos', None)
        st.warning('Sin datos. Ve a **📥 Importar Data** para cargar el primer mes.')
        st.stop()

    opciones = [f"{p['mes']} {p['anio']}" for p in periodos]

    # Pills + botón recargar pequeño a la derecha
    col_pills, col_reload = st.columns([20, 1])
    with col_pills:
        selected = st.pills(
            f'📅 Período  ·  {len(periodos)} disponible(s)',
            options=opciones,
            selection_mode='multi',
            default=opciones,
            help='Selecciona uno o varios meses. Los nuevos meses aparecen automáticamente.',
        )
    with col_reload:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button('🔄', key='_reload_periodos', help='Recargar períodos desde Supabase'):
            st.session_state.pop('abad_periodos', None)
            st.rerun()

    if not selected:
        st.info('👆 Selecciona al menos un período para ver los datos.')
        st.stop()

    label = selected[0] if len(selected) == 1 else f'{len(selected)} períodos'
    return list(selected), label


# ── Carga multi-período con caché y descarga en paralelo ──────────────────────

# Superconjunto de columnas usadas por TODAS las páginas. Al pedir siempre las
# mismas, el caché se reusa al cambiar de página → la 1ra página descarga,
# las siguientes son instantáneas.
SHARED_COLS = (
    'mes,anio,fecha,co,desc_co,canal_ventas,familia,vendedor,nombre_vendedor,'
    'razon_social,desc_item,referencia,nro_documento,desc_motivo,'
    'valor_subtotal,costo_promedio_total,cantidad,valor_descuentos,valor_impuestos,'
    'dscto_promedio_pct,rentabilidad_plata,'
    'tipo_leche,litros_leche,kilos_suero'
)


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_period_cached(mes: str, anio: int, columns: str) -> pd.DataFrame:
    """Caché por (mes, anio, columnas) — TTL 10 min."""
    from utils.database import fetch_ventas
    return fetch_ventas(mes, anio, columns=columns)


def clear_data_cache() -> None:
    """Limpia caché de ventas y períodos. Llamar después de importar datos nuevos."""
    _fetch_period_cached.clear()
    st.session_state.pop('abad_periodos', None)


def load_periods(fetch_ventas_fn, sels: list, columns: str = None) -> pd.DataFrame:
    """
    Descarga períodos en paralelo con caché COMPARTIDO entre páginas.
    Siempre pedimos SHARED_COLS (ignoramos `columns` para que el caché se reuse).
    1ra página: descarga; cambios de filtro o navegación a otra página: instantáneo.
    """
    from concurrent.futures import ThreadPoolExecutor

    def _one(s: str) -> pd.DataFrame:
        m, a = s.split()
        try:
            d = _fetch_period_cached(m, int(a), SHARED_COLS)
            if not d.empty:
                d = d.copy()
                d['periodo'] = s
            return d
        except Exception:
            return pd.DataFrame()

    workers = min(len(sels), 8) or 1
    with ThreadPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_one, sels))

    dfs = [d for d in parts if not d.empty]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
