import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods,
                      CHART_COLORS, TEAL)

st.set_page_config(page_title='Canal de Ventas · ABAD', page_icon='🏪',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('🏪 Ventas por Canal de Venta', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = 'canal_ventas,co,desc_co,valor_subtotal,costo_promedio_total,cantidad,mes,anio'

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
if 'co' in df_all.columns:
    df_all['co'] = pd.to_numeric(df_all['co'], errors='coerce').fillna(0).astype(int)

# ── Filtros INLINE ────────────────────────────────────────────────────────────
co_desc_map  = df_all.groupby('co')['desc_co'].first().to_dict()
cos_disp     = sorted(df_all['co'].unique().tolist())
canales_disp = sorted(df_all['canal_ventas'].unique().tolist())

fc1, fc2 = st.columns(2)
with fc1:
    filtro_co = st.multiselect('🏢 Centro de Operación (CO)', cos_disp, default=[],
                                format_func=lambda x: f'{x:03d} – {co_desc_map.get(x, str(x))}',
                                help='Vacío = todos')
with fc2:
    filtro_canal = st.multiselect('🏪 Canal de Venta', canales_disp, default=[],
                                   help='Vacío = todos')

df = df_all.copy()
if filtro_co:    df = df[df['co'].isin(filtro_co)]
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]

# Título dinámico con filtros activos
filter_title({
    'Período': sels,
    'CO':     [f'{c:03d} – {co_desc_map.get(c, "")}' for c in filtro_co] if filtro_co else None,
    'Canal':  filtro_canal,
})

if df.empty:
    st.warning('Sin datos para los filtros seleccionados.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
uds    = df['cantidad'].sum()
n_can  = df['canal_ventas'].nunique()

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas Totales'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{uds:,.0f}','📦 Unidades',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(str(n_can),'🏪 Canales Activos',val_color='#FFCC80'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Gráficos ──────────────────────────────────────────────────────────────────
canal = (df.groupby('canal_ventas')
           .agg(venta=('valor_subtotal','sum'), costo=('costo_promedio_total','sum'),
                cantidad=('cantidad','sum'), transacciones=('valor_subtotal','count'))
           .reset_index())
canal['margen_%']      = ((canal['venta']-canal['costo'])/canal['venta']*100).round(2)
canal['participacion'] = (canal['venta']/canal['venta'].sum()*100).round(2)
canal = canal.sort_values('venta', ascending=False)

col_l, col_r = st.columns([3,2])
with col_l:
    st.markdown(section_title('Ventas por Canal'), unsafe_allow_html=True)
    cs = canal.sort_values('venta', ascending=True)
    fig = go.Figure(go.Bar(x=cs['venta'],y=cs['canal_ventas'],orientation='h',
        text=cs['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=cs['margen_%'],
                    colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],showscale=True,
                    colorbar=dict(title='Margen %',thickness=10,tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,400),use_container_width=True)

with col_r:
    st.markdown(section_title('Participación'), unsafe_allow_html=True)
    fig2 = px.pie(canal,values='venta',names='canal_ventas',hole=0.5,color_discrete_sequence=CHART_COLORS)
    fig2.update_traces(textposition='inside',textinfo='percent',textfont=dict(color='white'))
    fig2.update_layout(showlegend=True,legend=dict(orientation='v',font=dict(size=9,color='white')))
    st.plotly_chart(dark_chart(fig2,400),use_container_width=True)

# ── Tendencia mensual si hay varios períodos ──────────────────────────────────
if len(sels)>1 and 'periodo' in df.columns:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Tendencia Mensual por Canal'), unsafe_allow_html=True)
    trend = (df.groupby(['periodo','canal_ventas'])
               .agg(venta=('valor_subtotal','sum')).reset_index())
    fig_t = px.bar(trend,x='periodo',y='venta',color='canal_ventas',
                   text='venta',color_discrete_sequence=CHART_COLORS,barmode='stack')
    fig_t.update_traces(texttemplate='',textfont=dict(color='white'))
    fig_t.update_layout(legend=dict(font=dict(color='white')))
    st.plotly_chart(dark_chart(fig_t,380),use_container_width=True)

st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Detalle Canal × Centro de Operación'), unsafe_allow_html=True)
cross = (df.groupby(['canal_ventas','co','desc_co'])
           .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
           .reset_index())
cross['margen_%']      = ((cross['venta']-cross['costo'])/cross['venta']*100).round(2)
cross['participacion'] = (cross['venta']/cross['venta'].sum()*100).round(2)
disp = summary_table(cross,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
disp = disp.rename(columns={'canal_ventas':'Canal','co':'CO','desc_co':'Centro Op.',
                             'venta':'Ventas','costo':'Costo','cantidad':'Cantidad',
                             'margen_%':'Margen','participacion':'Part %'})
styled_table(disp, max_height=420)

st.markdown('---')
exp = summary_table(canal,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
exp = exp.rename(columns={'canal_ventas':'Canal','venta':'Ventas','costo':'Costo','cantidad':'Cantidad',
                           'transacciones':'Trans.','margen_%':'Margen','participacion':'Part %'})
styled_table(exp)
st.download_button('⬇️ Descargar CSV',canal.to_csv(index=False).encode('utf-8'),
                   f'canal_ventas_{label.replace(" ","_")}.csv','text/csv')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
