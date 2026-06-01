import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Venta Suero · ABAD', page_icon='🧴',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('🧴 Venta de Suero', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = 'familia,desc_item,referencia,canal_ventas,co,desc_co,valor_subtotal,costo_promedio_total,cantidad,kilos_suero,mes,anio'

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad','kilos_suero']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)

df_suero = df_all[df_all['familia'].str.contains(r'suero', case=False, na=False, regex=True)].copy()

if df_suero.empty:
    st.warning('No se encontraron datos de suero. Verifica que la tabla ITEM esté cargada.')
    st.markdown(section_title('Familias disponibles'), unsafe_allow_html=True)
    styled_table(df_all['familia'].value_counts().head(20).reset_index()
                 .rename(columns={'familia':'Familia','count':'Filas'}))
    st.stop()

# ── Filtros INLINE ────────────────────────────────────────────────────────────
canales_disp = sorted(df_suero['canal_ventas'].unique().tolist())
fc1, fc2 = st.columns(2)
with fc1:
    filtro_canal = st.multiselect('🏪 Canal de Venta', canales_disp, default=[], help='Vacío = todos')
with fc2:
    cos_disp = sorted(pd.to_numeric(df_suero['co'], errors='coerce').dropna().astype(int).unique().tolist()) if 'co' in df_suero.columns else []
    filtro_co = st.multiselect('🏢 Centro de Operación', cos_disp, default=[], help='Vacío = todos')

df = df_suero.copy()
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]
if filtro_co:
    df['_co'] = pd.to_numeric(df['co'], errors='coerce').fillna(0).astype(int)
    df = df[df['_co'].isin(filtro_co)]

filter_title({
    'Período': sels,
    'Canal':   filtro_canal,
    'CO':      [f'{c:03d}' for c in filtro_co] if filtro_co else None,
})

if df.empty:
    st.warning('Sin datos para los filtros.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
kilos  = df['kilos_suero'].sum()
uds    = df['cantidad'].sum()

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas Suero'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{kilos:,.1f}','⚖️ Kilos',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(f'{uds:,.0f}','📦 Unidades',val_color='#FFCC80'), unsafe_allow_html=True)
with c5: st.markdown(kpi_html(fmt_currency(costo),'🏭 Costo',val_color='#EF9A9A'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

canal = (df.groupby('canal_ventas')
           .agg(venta=('valor_subtotal','sum'),kilos=('kilos_suero','sum'),
                costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
           .reset_index())
canal['margen_%'] = ((canal['venta']-canal['costo'])/canal['venta']*100).round(2)
canal = canal.sort_values('venta',ascending=False)

col_l, col_r = st.columns(2)
with col_l:
    st.markdown(section_title('Por Canal'), unsafe_allow_html=True)
    cs = canal.sort_values('venta',ascending=True)
    fig = go.Figure(go.Bar(x=cs['venta'],y=cs['canal_ventas'],orientation='h',
        text=cs['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=cs['margen_%'],colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],
                    showscale=True,colorbar=dict(title='Margen %',thickness=10,
                                                 tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,370),use_container_width=True)

with col_r:
    st.markdown(section_title('Top Productos Suero'), unsafe_allow_html=True)
    prod = (df.groupby(['referencia','desc_item'])
               .agg(venta=('valor_subtotal','sum'),kilos=('kilos_suero','sum'),cantidad=('cantidad','sum'))
               .reset_index().sort_values('venta',ascending=False).head(10))
    ps = prod.sort_values('venta',ascending=True)
    fig2 = go.Figure(go.Bar(x=ps['venta'],y=ps['desc_item'],orientation='h',
        text=ps['venta'].apply(fmt_currency),textposition='outside',marker_color='#00838F'))
    st.plotly_chart(dark_chart(fig2,370),use_container_width=True)

st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Suero Maquila vs Canal Normal'), unsafe_allow_html=True)
df['es_maquila'] = df['canal_ventas'].str.contains('MAQUILA', case=False, na=False)
maq = df.groupby('es_maquila').agg(venta=('valor_subtotal','sum'),kilos=('kilos_suero','sum')).reset_index()
maq['tipo'] = maq['es_maquila'].map({True:'Maquila',False:'Canal Normal'})

col_a, col_b = st.columns([1,2])
with col_a:
    fig3 = px.pie(maq,values='venta',names='tipo',hole=0.45,color_discrete_sequence=['#F57F17','#1565C0'])
    fig3.update_traces(textposition='inside',textinfo='percent+label',textfont=dict(color='white'))
    fig3.update_layout(showlegend=True,legend=dict(font=dict(color='white')))
    st.plotly_chart(dark_chart(fig3,300),use_container_width=True)
with col_b:
    maq_d = maq[['tipo','venta','kilos']].copy()
    maq_d['venta'] = maq_d['venta'].apply(lambda x: f'${x:,.0f}')
    maq_d['kilos'] = maq_d['kilos'].apply(lambda x: f'{x:,.1f}')
    st.markdown('<br>', unsafe_allow_html=True)
    styled_table(maq_d.rename(columns={'tipo':'Tipo','venta':'Ventas','kilos':'Kilos'}))

st.markdown('---')
disp = summary_table(canal,money_cols=['venta','costo'],pct_cols=['margen_%'])
disp.insert(2,'Kilos',canal['kilos'].apply(lambda x: f'{x:,.1f}'))
disp = disp.rename(columns={'canal_ventas':'Canal','venta':'Ventas','costo':'Costo',
                             'cantidad':'Cantidad','margen_%':'Margen'})
styled_table(disp)
st.download_button('⬇️ Descargar CSV',prod.to_csv(index=False).encode('utf-8'),
                   f'suero_{label.replace(" ","_")}.csv','text/csv')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
