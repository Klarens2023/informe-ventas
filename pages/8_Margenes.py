import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, explain, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Márgenes · ABAD', page_icon='📈',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('📈 Análisis de Márgenes', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = 'familia,canal_ventas,co,desc_co,valor_subtotal,costo_promedio_total,rentabilidad_plata,cantidad,mes,anio'

with st.spinner('Cargando...'):
    df = load_periods(fetch_ventas, sels, COLS)

if df.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','rentabilidad_plata','cantidad']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

# ── Filtro de dimensión INLINE ────────────────────────────────────────────────
GROUP_MAP = {'Familia de Producto':'familia','Canal de Venta':'canal_ventas','Centro de Operación':'desc_co'}
fc1, fc2 = st.columns([1,3])
with fc1:
    agrupar = st.selectbox('📊 Agrupar por', list(GROUP_MAP.keys()))
group_col = GROUP_MAP[agrupar]

filter_title({'Período': sels, 'Agrupado por': agrupar})

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
rent   = df['rentabilidad_plata'].sum()
margen = (venta-costo)/venta*100 if venta else 0

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas Totales'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen Neto %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(fmt_currency(rent),'💵 Rentabilidad $',val_color='#4CAF50'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(fmt_currency(costo),'🏭 Costo Total',val_color='#EF9A9A'), unsafe_allow_html=True)

explain("""
Analiza la rentabilidad según la dimensión elegida arriba (**Familia / Canal / Centro de Operación**).
- **💰 Ventas Totales** — `valor_subtotal`. **🏭 Costo Total** — `costo_promedio_total`.
- **📈 Margen Neto %** — `(Ventas − Costo) ÷ Ventas × 100` (rentabilidad relativa).
- **💵 Rentabilidad $** — `rentabilidad_plata` = `Ventas − Costo` (utilidad bruta en pesos).
""")

st.markdown('<br>', unsafe_allow_html=True)

# ── Agrupación ────────────────────────────────────────────────────────────────
grp = (df.groupby(group_col)
         .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
              rent=('rentabilidad_plata','sum'),cantidad=('cantidad','sum'))
         .reset_index())
grp = grp[grp[group_col].str.strip()!='']
grp['margen_%'] = ((grp['venta']-grp['costo'])/grp['venta']*100).round(2)
grp['part_%']   = (grp['venta']/grp['venta'].sum()*100).round(2)
grp = grp.sort_values('margen_%',ascending=True)
h = max(380,len(grp)*28)

col_l, col_r = st.columns(2)
with col_l:
    st.markdown(section_title(f'Margen % por {agrupar}'), unsafe_allow_html=True)
    rng_min = min(grp['margen_%'].min()-5,0)
    rng_max = max(grp['margen_%'].max()+5,50)
    fig = px.bar(grp,x='margen_%',y=group_col,orientation='h',text='margen_%',
                 color='margen_%',color_continuous_scale='RdYlGn',range_color=[rng_min,rng_max])
    fig.update_traces(texttemplate='%{x:.1f}%',textposition='outside',textfont=dict(color='white'))
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(dark_chart(fig,h),use_container_width=True)

with col_r:
    st.markdown(section_title(f'Rentabilidad $ por {agrupar}'), unsafe_allow_html=True)
    gr = grp.sort_values('rent',ascending=True)
    fig2 = go.Figure(go.Bar(x=gr['rent'],y=gr[group_col],orientation='h',
        text=gr['rent'].apply(fmt_currency),textposition='outside',
        marker=dict(color=gr['rent'],
                    colorscale=[[0,'#B71C1C'],[0.3,'#EF6C00'],[0.6,'#1565C0'],[1,'#4DB6AC']],
                    showscale=False),textfont=dict(color='white')))
    st.plotly_chart(dark_chart(fig2,h),use_container_width=True)

explain("""
- **Margen % por dimensión** (izquierda) — Margen relativo `(Ventas−Costo)÷Ventas`, escala rojo→verde.
- **Rentabilidad $ por dimensión** (derecha) — Utilidad bruta en pesos `Ventas − Costo`.
Un grupo puede tener **margen % alto pero poca rentabilidad $** (vende poco), o al revés.
El **scatter** de abajo cruza ambas: tamaño = venta, eje X = ventas $, eje Y = margen %.
""")

# ── Scatter Venta vs Margen ────────────────────────────────────────────────────
st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title(f'Venta vs Margen por {agrupar}'), unsafe_allow_html=True)
gv = grp.sort_values('venta',ascending=False)
fig3 = px.scatter(gv,x='venta',y='margen_%',size='venta',color=group_col,text=group_col,
                  color_discrete_sequence=CHART_COLORS,size_max=60,
                  labels={'venta':'Ventas $','margen_%':'Margen %'})
fig3.update_traces(textposition='top center',textfont=dict(size=9,color='white'))
fig3.add_hline(y=margen,line_dash='dash',line_color='#F57F17',
               annotation_text=f'Promedio: {margen:.1f}%',annotation_font_color='#F57F17')
st.plotly_chart(dark_chart(fig3,420),use_container_width=True)

# ── Tendencia si hay varios meses ─────────────────────────────────────────────
if len(sels)>1 and 'periodo' in df.columns:
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title(f'Tendencia de Margen % por {agrupar}'), unsafe_allow_html=True)
    trend = (df.groupby([group_col,'periodo'])
               .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'))
               .reset_index())
    trend['margen_%'] = ((trend['venta']-trend['costo'])/trend['venta']*100).round(2)
    trend = trend[trend[group_col].str.strip()!='']
    fig4 = px.line(trend,x='periodo',y='margen_%',color=group_col,
                   markers=True,color_discrete_sequence=CHART_COLORS,
                   labels={'periodo':'Período','margen_%':'Margen %'})
    fig4.update_traces(line=dict(width=2),marker=dict(size=8))
    st.plotly_chart(dark_chart(fig4,420),use_container_width=True)

st.markdown('---')
disp = summary_table(grp.sort_values('venta',ascending=False),
                     money_cols=['venta','costo','rent'],pct_cols=['margen_%','part_%'])
disp = disp.rename(columns={group_col:agrupar,'venta':'Ventas','costo':'Costo',
                              'rent':'Rentabilidad','margen_%':'Margen %','part_%':'Part %'})
styled_table(disp, max_height=460)
st.download_button('⬇️ Descargar CSV',grp.to_csv(index=False).encode('utf-8'),
                   f'margenes_{label.replace(" ","")}.csv','text/csv')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
