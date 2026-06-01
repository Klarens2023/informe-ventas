import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Venta Leche · ABAD', page_icon='🥛',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('🥛 Venta de Leche', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = 'familia,tipo_leche,canal_ventas,co,desc_co,valor_subtotal,costo_promedio_total,cantidad,litros_leche,mes,anio'

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad','litros_leche']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)

# Filtrar leche: por familia, si no por tipo_leche
df_leche = df_all[df_all['familia'].str.contains(r'leche|uht|lácteo|latte', case=False, na=False, regex=True)].copy()
if df_leche.empty:
    df_leche = df_all[df_all['tipo_leche'].notna() &
                      (~df_all['tipo_leche'].isin(['','nan','N.R','N/R','NR']))].copy()

if df_leche.empty:
    st.warning('No se encontraron datos de leche. Verifica que la tabla ITEM esté cargada.')
    st.markdown(section_title('Familias disponibles en el período'), unsafe_allow_html=True)
    styled_table(df_all['familia'].value_counts().head(20).reset_index()
                 .rename(columns={'familia':'Familia','count':'Filas'}))
    st.stop()

# ── Filtros INLINE ────────────────────────────────────────────────────────────
tipos_leche  = sorted([t for t in df_leche['tipo_leche'].unique()
                       if t and str(t).strip() not in ('','nan','N.R','N/R','NR')])
canales_disp = sorted(df_leche['canal_ventas'].unique().tolist())

fc1, fc2 = st.columns(2)
with fc1:
    filtro_tipo  = st.multiselect('🥛 Tipo de Leche', tipos_leche, default=[], help='Vacío = todos')
with fc2:
    filtro_canal = st.multiselect('🏪 Canal de Venta', canales_disp, default=[], help='Vacío = todos')

df = df_leche.copy()
if filtro_tipo:  df = df[df['tipo_leche'].isin(filtro_tipo)]
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]

filter_title({
    'Período':     sels,
    'Tipo Leche': filtro_tipo,
    'Canal':       filtro_canal,
})

if df.empty:
    st.warning('Sin datos para los filtros.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
litros = df['litros_leche'].sum()
uds    = df['cantidad'].sum()

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas Leche'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{litros:,.1f}','💧 Litros',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(f'{uds:,.0f}','📦 Unidades',val_color='#FFCC80'), unsafe_allow_html=True)
with c5: st.markdown(kpi_html(fmt_currency(costo),'🏭 Costo',val_color='#EF9A9A'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Por tipo de leche ─────────────────────────────────────────────────────────
tipo_df = (df.groupby('tipo_leche')
             .agg(venta=('valor_subtotal','sum'),litros=('litros_leche','sum'),cantidad=('cantidad','sum'))
             .reset_index())
tipo_df = tipo_df[~tipo_df['tipo_leche'].isin(['','nan','N.R','N/R'])].sort_values('venta',ascending=False)

col_l, col_r = st.columns(2)
with col_l:
    st.markdown(section_title('Ventas por Tipo de Leche'), unsafe_allow_html=True)
    if not tipo_df.empty:
        fig = px.bar(tipo_df,x='tipo_leche',y='venta',color='tipo_leche',text='venta',
                     color_discrete_sequence=CHART_COLORS)
        fig.update_traces(texttemplate='$%{y:,.0f}',textposition='outside',textfont=dict(color='white'))
        fig.update_layout(showlegend=False,xaxis_tickangle=30)
        st.plotly_chart(dark_chart(fig,370),use_container_width=True)
    else:
        st.info('Sin clasificación por tipo de leche. Carga la tabla ITEM.')

with col_r:
    st.markdown(section_title('Litros por Tipo'), unsafe_allow_html=True)
    tipo_ltr = tipo_df[tipo_df['litros']>0]
    if not tipo_ltr.empty:
        fig2 = px.pie(tipo_ltr,values='litros',names='tipo_leche',hole=0.45,
                      color_discrete_sequence=CHART_COLORS)
        fig2.update_traces(textposition='inside',textinfo='percent+label',textfont=dict(color='white'))
        fig2.update_layout(showlegend=False)
        st.plotly_chart(dark_chart(fig2,370),use_container_width=True)
    else:
        st.info('Sin datos de litros — carga la tabla ITEM con el peso por referencia.')

st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Ventas de Leche por Canal'), unsafe_allow_html=True)
canal = (df.groupby('canal_ventas')
           .agg(venta=('valor_subtotal','sum'),litros=('litros_leche','sum'),
                costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
           .reset_index())
canal['margen_%']      = ((canal['venta']-canal['costo'])/canal['venta']*100).round(2)
canal['participacion'] = (canal['venta']/canal['venta'].sum()*100).round(2)
canal = canal.sort_values('venta',ascending=False)

cs = canal.sort_values('venta',ascending=True)
fig3 = go.Figure(go.Bar(x=cs['venta'],y=cs['canal_ventas'],orientation='h',
    text=cs['venta'].apply(fmt_currency),textposition='outside',
    marker=dict(color=cs['margen_%'],colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],
                showscale=True,colorbar=dict(title='Margen %',thickness=10,
                                             tickfont=dict(color='white'),titlefont=dict(color='white')))))
st.plotly_chart(dark_chart(fig3,370),use_container_width=True)

st.markdown('---')
disp = summary_table(canal,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
disp.insert(2,'Litros',canal['litros'].apply(lambda x: f'{x:,.1f}'))
disp = disp.rename(columns={'canal_ventas':'Canal','venta':'Ventas','costo':'Costo',
                             'cantidad':'Cantidad','margen_%':'Margen','participacion':'Part %'})
styled_table(disp)
st.download_button('⬇️ Descargar CSV',canal.to_csv(index=False).encode('utf-8'),
                   f'leche_{label.replace(" ","_")}.csv','text/csv')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
