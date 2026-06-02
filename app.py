import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import fmt_currency, fmt_int_co, summary_table, axis_money_co
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, explain, minimal_sidebar, period_pills, load_periods,
                      CHART_COLORS, TEAL, KPI_VAL, CARD, CARD2)

st.set_page_config(
    page_title='Informe Gerencial · ABAD', page_icon='📊',
    layout='wide', initial_sidebar_state='auto',
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

if not is_configured():
    minimal_sidebar()
    st.error('⚠️ Sin conexión a Supabase. Ve a **📥 Importar Data** para configurar.')
    st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('📊 Reporte Gerencial de Ventas',
            'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período (PILLS inline) ───────────────────────────────────────
sels, label = period_pills(fetch_periodos)

# Título dinámico con filtros activos
filter_title({'Período': sels})

st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('canal_ventas,co,desc_co,familia,nombre_vendedor,vendedor,'
        'valor_subtotal,costo_promedio_total,rentabilidad_plata,'
        'cantidad,mes,anio,fecha,valor_descuentos')

with st.spinner(f'Cargando {len(sels)} período(s)...'):
    df = load_periods(fetch_ventas, sels, COLS)

if df.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','rentabilidad_plata','cantidad','valor_descuentos']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
if 'co' in df.columns:
    df['co'] = pd.to_numeric(df['co'], errors='coerce').fillna(0).astype(int)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
rent   = df['rentabilidad_plata'].sum()
margen = (venta - costo) / venta * 100 if venta else 0
descto = df['valor_descuentos'].sum()
uds    = df['cantidad'].sum()
n_co   = df['co'].nunique()
n_mes  = df['mes'].nunique() if 'mes' in df.columns else len(sels)

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta), '💰 Ventas Totales'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:,.2f}%'.replace(',', '.'), '📈 Margen Promedio', val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(fmt_currency(rent), '💵 Rentabilidad', val_color='#4CAF50'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(fmt_int_co(len(df)), '🔢 Transacciones'), unsafe_allow_html=True)

st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
c5,c6,c7,c8 = st.columns(4)
with c5: st.markdown(kpi_html(fmt_currency(costo), '🏭 Costo Total', val_color='#EF9A9A', bg=CARD2), unsafe_allow_html=True)
with c6: st.markdown(kpi_html(fmt_currency(descto), '🎁 Descuentos', val_color='#CE93D8', bg=CARD2), unsafe_allow_html=True)
with c7: st.markdown(kpi_html(fmt_int_co(uds), '📦 Unidades', val_color='#80DEEA', bg=CARD2), unsafe_allow_html=True)
with c8: st.markdown(kpi_html(f'{n_co} CO · {n_mes} mes{"es" if n_mes>1 else ""}', '🏢 Alcance', val_color='#FFCC80', bg=CARD2), unsafe_allow_html=True)

explain("""
**Indicadores principales del período seleccionado:**
- **💰 Ventas Totales** — Suma de `valor_subtotal` (venta neta, antes de impuestos).
- **📈 Margen Promedio** — `(Ventas − Costo) ÷ Ventas × 100`. Qué % de la venta queda como utilidad bruta.
- **💵 Rentabilidad** — Suma de `rentabilidad_plata` = `Ventas − Costo` en pesos (utilidad bruta total).
- **🔢 Transacciones** — Número de filas (líneas de factura) del período.
- **🏭 Costo Total** — Suma de `costo_promedio_total` (costo de la mercancía vendida).
- **🎁 Descuentos** — Suma de `valor_descuentos` aplicados.
- **📦 Unidades** — Suma de `cantidad` vendida.
- **🏢 Alcance** — Nº de Centros de Operación (CO) y meses incluidos en la vista.
""")

st.markdown('<br>', unsafe_allow_html=True)

# ── Canal de Ventas ───────────────────────────────────────────────────────────
canal = (df.groupby('canal_ventas')
           .agg(venta=('valor_subtotal','sum'), costo=('costo_promedio_total','sum'), cantidad=('cantidad','sum'))
           .reset_index())
canal['margen_%'] = ((canal['venta']-canal['costo'])/canal['venta']*100).round(2)
canal['part_%']   = (canal['venta']/canal['venta'].sum()*100).round(2)
canal = canal.sort_values('venta', ascending=False)

col_l, col_r = st.columns([3,2])
with col_l:
    st.markdown(section_title('Ventas por Canal de Venta'), unsafe_allow_html=True)
    cs = canal.sort_values('venta', ascending=True)
    fig = go.Figure(go.Bar(x=cs['venta'],y=cs['canal_ventas'],orientation='h',
        text=cs['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=cs['margen_%'],
                    colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],showscale=True,
                    colorbar=dict(title='Margen %',thickness=10,tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,400),use_container_width=True)

with col_r:
    st.markdown(section_title('Participación por Canal'), unsafe_allow_html=True)
    fig2 = px.pie(canal,values='venta',names='canal_ventas',hole=0.5,color_discrete_sequence=CHART_COLORS)
    fig2.update_traces(textposition='inside',textinfo='percent',textfont=dict(color='white'))
    fig2.update_layout(showlegend=True,legend=dict(orientation='v',font=dict(size=9,color='white')))
    st.plotly_chart(dark_chart(fig2,400),use_container_width=True)

explain("""
- **Ventas por Canal** (izquierda) — Barras horizontales con la venta total de cada canal. **El color indica el margen %** del canal (azul = bajo, verde = alto), calculado como `(Ventas − Costo) ÷ Ventas`.
- **Participación por Canal** (derecha) — Dona con el **% que cada canal aporta** a la venta total: `Venta del canal ÷ Venta total × 100`.
""")

st.markdown('<br>', unsafe_allow_html=True)

# ── Evolución mensual (si hay varios meses) ───────────────────────────────────
if len(sels) > 1 and 'mes' in df.columns:
    st.markdown(section_title('Evolución Mensual de Ventas'), unsafe_allow_html=True)
    MONTH_ORDER = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO',
                   'JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']
    evol = (df.groupby(['mes','anio'])
              .agg(venta=('valor_subtotal','sum'),rent=('rentabilidad_plata','sum'))
              .reset_index())
    evol['periodo']  = evol['mes'] + ' ' + evol['anio'].astype(str)
    evol['mes_ord']  = evol['mes'].map({m: i for i,m in enumerate(MONTH_ORDER)})
    evol = evol.sort_values(['anio','mes_ord'])
    fig_e = go.Figure()
    fig_e.add_trace(go.Bar(x=evol['periodo'],y=evol['venta'],name='Ventas',
        marker_color='#1565C0',text=evol['venta'].apply(fmt_currency),textposition='outside',textfont=dict(color='white')))
    fig_e.add_trace(go.Scatter(x=evol['periodo'],y=evol['rent'],name='Rentabilidad $',
        mode='lines+markers',line=dict(color='#F57F17',width=2),marker=dict(size=8),yaxis='y2'))
    fig_e.update_layout(
        yaxis2=dict(overlaying='y',side='right',showgrid=False,
                    tickfont=dict(color='#F57F17'),title='Rentabilidad $',titlefont=dict(color='#F57F17')),
        barmode='group',legend=dict(font=dict(color='white')))
    st.plotly_chart(dark_chart(fig_e,380),use_container_width=True)
    explain("""
**Evolución Mensual** (aparece al seleccionar varios meses):
- **Barras azules** — Venta total de cada mes (`valor_subtotal`).
- **Línea naranja** — Rentabilidad en pesos del mes (`Ventas − Costo`), en eje derecho.
Permite ver la tendencia y comparar si la utilidad crece al mismo ritmo que la venta.
""")
    st.markdown('<br>', unsafe_allow_html=True)

# ── Vendedores + Familia ──────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(section_title('Top 15 Vendedores'), unsafe_allow_html=True)
    vend = (df.groupby('nombre_vendedor').agg(venta=('valor_subtotal','sum'))
              .reset_index().sort_values('venta',ascending=False).head(15))
    vs = vend.sort_values('venta',ascending=True)
    fig3 = go.Figure(go.Bar(x=vs['venta'],y=vs['nombre_vendedor'],orientation='h',
        text=vs['venta'].apply(fmt_currency),textposition='outside',marker_color=TEAL))
    st.plotly_chart(dark_chart(fig3,420),use_container_width=True)

with col_b:
    st.markdown(section_title('Ventas por Familia de Producto'), unsafe_allow_html=True)
    fam = (df.groupby('familia')
             .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'))
             .reset_index())
    fam = fam[fam['familia'].str.strip()!=''].sort_values('venta',ascending=False).head(12)
    if not fam.empty:
        fam['margen_%'] = ((fam['venta']-fam['costo'])/fam['venta']*100).round(1)
        fs = fam.sort_values('venta',ascending=True)
        fig4 = go.Figure(go.Bar(x=fs['venta'],y=fs['familia'],orientation='h',
            text=fs['venta'].apply(fmt_currency),textposition='outside',
            marker=dict(color=fs['margen_%'],colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#F57F17']],showscale=False)))
        st.plotly_chart(dark_chart(fig4,420),use_container_width=True)
    else:
        st.info('Sin datos de familia. Carga la tabla ITEM en 📥 Importar Data.')

explain("""
- **Top 15 Vendedores** (izquierda) — Los 15 vendedores con mayor venta total (`valor_subtotal` sumado por `nombre_vendedor`).
- **Ventas por Familia** (derecha) — Venta por familia de producto. **El color indica el margen %** de cada familia. La familia viene del cruce con la tabla ITEM por `referencia`.
""")

st.markdown('---')
st.markdown(section_title('Resumen por Centro de Operación'), unsafe_allow_html=True)
co_df = (df.groupby(['co','desc_co'])
           .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                cantidad=('cantidad','sum'),transacciones=('valor_subtotal','count'))
           .reset_index())
co_df['margen_%']      = ((co_df['venta']-co_df['costo'])/co_df['venta']*100).round(2)
co_df['participacion'] = (co_df['venta']/co_df['venta'].sum()*100).round(2)
co_df = co_df.sort_values('venta',ascending=False)
disp = summary_table(co_df,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
disp = disp.rename(columns={'co':'CO','desc_co':'Centro de Operación','venta':'Ventas','costo':'Costo',
                             'cantidad':'Cantidad','transacciones':'Trans.','margen_%':'Margen','participacion':'Part %'})
styled_table(disp)
explain("""
**Resumen por Centro de Operación (CO)** — cada fila es un punto/centro:
- **Ventas** — `valor_subtotal` sumado por CO.
- **Costo** — `costo_promedio_total` sumado por CO.
- **Cantidad** — unidades vendidas.
- **Trans.** — número de líneas de factura.
- **Margen** — `(Ventas − Costo) ÷ Ventas × 100`.
- **Part %** — participación del CO en la venta total: `Venta CO ÷ Venta total × 100`.
""")

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
