import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, explain, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Producto · ABAD', page_icon='📦',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Sin conexión. Ve a 📥 Importar Data para configurar.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('📦 Ventas por Producto', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('familia,desc_item,referencia,canal_ventas,co,razon_social,'
        'valor_subtotal,costo_promedio_total,cantidad,mes,anio')

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)

# ── Filtros INLINE ────────────────────────────────────────────────────────────
familias_disp = sorted([f for f in df_all['familia'].dropna().unique() if str(f).strip()])
canales_disp  = sorted(df_all['canal_ventas'].unique().tolist())

fc1, fc2, fc3 = st.columns(3)
with fc1:
    filtro_fam   = st.multiselect('🏷️ Familia', familias_disp, default=[], help='Vacío = todas')
with fc2:
    filtro_canal = st.multiselect('🏪 Canal', canales_disp, default=[], help='Vacío = todos')
with fc3:
    top_n = st.slider('Top N productos', 5, 50, 20)

df = df_all.copy()
if filtro_fam:   df = df[df['familia'].isin(filtro_fam)]
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]

filter_title({
    'Período': sels,
    'Familia': filtro_fam,
    'Canal':   filtro_canal,
    'Top':     f'{top_n} productos',
})

if df.empty:
    st.warning('Sin datos para los filtros.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
uds    = df['cantidad'].sum()

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{uds:,.0f}','📦 Unidades',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(str(df['referencia'].nunique()),'🔖 Referencias',val_color='#FFCC80'), unsafe_allow_html=True)

explain("""
- **💰 Ventas** — `valor_subtotal` sumado de los productos filtrados.
- **📈 Margen %** — `(Ventas − Costo) ÷ Ventas × 100`.
- **📦 Unidades** — `cantidad` total vendida.
- **🔖 Referencias** — Número de productos (referencias) distintos vendidos.
""")

st.markdown('<br>', unsafe_allow_html=True)

# ── Por familia ───────────────────────────────────────────────────────────────
fam = (df.groupby('familia')
         .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
         .reset_index())
fam = fam[fam['familia'].str.strip()!='']
fam['margen_%']      = ((fam['venta']-fam['costo'])/fam['venta']*100).round(2)
fam['participacion'] = (fam['venta']/fam['venta'].sum()*100).round(2)
fam = fam.sort_values('venta', ascending=False)

col_l, col_r = st.columns([3,2])
with col_l:
    st.markdown(section_title('Ventas por Familia'), unsafe_allow_html=True)
    fs = fam.sort_values('venta', ascending=True)
    fig = go.Figure(go.Bar(x=fs['venta'],y=fs['familia'],orientation='h',
        text=fs['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=fs['margen_%'],colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],
                    showscale=True,colorbar=dict(title='Margen %',thickness=10,
                                                 tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,400),use_container_width=True)

with col_r:
    st.markdown(section_title('Margen % por Familia'), unsafe_allow_html=True)
    fm = fam.sort_values('margen_%', ascending=True)
    fig2 = px.bar(fm,x='margen_%',y='familia',orientation='h',text='margen_%',
                  color='margen_%',color_continuous_scale='RdYlGn',range_color=[0,80])
    fig2.update_traces(texttemplate='%{x:.1f}%',textposition='outside',textfont=dict(color='white'))
    fig2.update_layout(coloraxis_showscale=False)
    st.plotly_chart(dark_chart(fig2,400),use_container_width=True)

explain("""
- **Ventas por Familia** (izquierda) — Venta de cada familia de producto; **color = margen %**.
- **Margen % por Familia** (derecha) — Margen `(Ventas−Costo)÷Ventas` ordenado, escala
rojo→verde. Identifica familias muy vendidas pero de bajo margen, o viceversa.
La familia se obtiene del cruce con la tabla ITEM por `referencia`.
""")

st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title(f'Top {top_n} Productos'), unsafe_allow_html=True)
prod = (df.groupby(['referencia','desc_item','familia'])
          .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
          .reset_index())
prod['margen_%']      = ((prod['venta']-prod['costo'])/prod['venta']*100).round(2)
prod['participacion'] = (prod['venta']/prod['venta'].sum()*100).round(2)
prod = prod.sort_values('venta', ascending=False).head(top_n)

fig3 = px.bar(prod.sort_values('venta'),x='venta',y='desc_item',orientation='h',
              color='familia',text='venta',color_discrete_sequence=CHART_COLORS)
fig3.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont=dict(color='white'))
fig3.update_layout(showlegend=True,legend=dict(font=dict(color='white')))
st.plotly_chart(dark_chart(fig3,max(420,top_n*22)),use_container_width=True)
explain("""
**Top N Productos** — Los productos de mayor venta (ajusta N con el control de arriba).
Cada barra es un producto y **el color indica su familia**. La tabla siguiente trae el
detalle con Margen `(Ventas−Costo)÷Ventas` y Part % sobre la venta total.
""")

st.markdown('---')
disp = summary_table(prod,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
disp = disp.rename(columns={'referencia':'Ref','desc_item':'Descripción','familia':'Familia',
                             'venta':'Ventas','costo':'Costo','cantidad':'Cantidad',
                             'margen_%':'Margen','participacion':'Part %'})
styled_table(disp, max_height=460)
st.download_button('⬇️ Descargar CSV',prod.to_csv(index=False).encode('utf-8'),
                   f'productos_{label.replace(" ","_")}.csv','text/csv')

explain("""
Al elegir una **familia** se muestra qué **clientes** la compraron (`razon_social`),
qué **productos** de esa familia se vendieron, y el cruce **Cliente → Producto**.
Sirve para saber a quién venderle más de cada línea.
""")

# ── DETALLE: Clientes que compraron de una Familia ────────────────────────────
st.markdown('---')
st.markdown(section_title('🔍 Detalle por Familia: Clientes y Productos'), unsafe_allow_html=True)

fam_opts = sorted([f for f in df['familia'].dropna().unique() if str(f).strip()])
if fam_opts:
    sel_fam = st.selectbox('🏷️ Selecciona una familia para ver qué clientes la compraron', fam_opts)
    dfam = df[df['familia'] == sel_fam].copy()

    f_venta = dfam['valor_subtotal'].sum()
    f_costo = dfam['costo_promedio_total'].sum()
    f_marg  = (f_venta - f_costo) / f_venta * 100 if f_venta else 0
    f_uds   = dfam['cantidad'].sum()
    f_ncli  = dfam['razon_social'].nunique()

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(kpi_html(fmt_currency(f_venta), '💰 Venta Familia', bg='#112240'), unsafe_allow_html=True)
    with m2: st.markdown(kpi_html(f'{f_marg:.2f}%', '📈 Margen', val_color='#4DB6AC', bg='#112240'), unsafe_allow_html=True)
    with m3: st.markdown(kpi_html(f'{f_uds:,.0f}', '📦 Unidades', val_color='#80DEEA', bg='#112240'), unsafe_allow_html=True)
    with m4: st.markdown(kpi_html(str(f_ncli), '🏢 Clientes', val_color='#FFCC80', bg='#112240'), unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # Tablas a todo el ancho (apiladas) — los nombres son largos
    st.markdown(section_title('Clientes que compraron esta familia'), unsafe_allow_html=True)
    cli = (dfam.groupby('razon_social')
             .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                  cantidad=('cantidad','sum'))
             .reset_index())
    cli['margen_%']      = ((cli['venta']-cli['costo'])/cli['venta']*100).round(2)
    cli['participacion'] = (cli['venta']/cli['venta'].sum()*100).round(2)
    cli = cli.sort_values('venta', ascending=False)
    cli_disp = summary_table(cli, money_cols=['venta','costo'], pct_cols=['margen_%','participacion'])
    cli_disp = cli_disp.rename(columns={'razon_social':'Cliente','venta':'Ventas','costo':'Costo',
                                        'cantidad':'Cant.','margen_%':'Margen','participacion':'Part %'})
    styled_table(cli_disp, max_height=420)

    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Productos de esta familia'), unsafe_allow_html=True)
    prods = (dfam.groupby('desc_item')
               .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                    cantidad=('cantidad','sum'))
               .reset_index())
    prods['margen_%'] = ((prods['venta']-prods['costo'])/prods['venta']*100).round(2)
    prods = prods.sort_values('venta', ascending=False)
    prods_disp = summary_table(prods, money_cols=['venta','costo'], pct_cols=['margen_%'])
    prods_disp = prods_disp.rename(columns={'desc_item':'Producto','venta':'Ventas','costo':'Costo',
                                            'cantidad':'Cant.','margen_%':'Margen'})
    styled_table(prods_disp, max_height=420)

    # Detalle Cliente × Producto
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Detalle Cliente → Producto'), unsafe_allow_html=True)
    cp = (dfam.groupby(['razon_social','desc_item'])
            .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                 cantidad=('cantidad','sum'))
            .reset_index())
    cp['margen_%'] = ((cp['venta']-cp['costo'])/cp['venta']*100).round(2)
    cp = cp.sort_values(['razon_social','venta'], ascending=[True, False])
    cp_disp = summary_table(cp, money_cols=['venta','costo'], pct_cols=['margen_%'])
    cp_disp = cp_disp.rename(columns={'razon_social':'Cliente','desc_item':'Producto','venta':'Ventas',
                                      'costo':'Costo','cantidad':'Cant.','margen_%':'Margen'})
    styled_table(cp_disp, max_height=400)
    st.download_button('⬇️ Descargar detalle Cliente×Producto',
                       cp.to_csv(index=False).encode('utf-8'),
                       f'familia_{sel_fam[:15]}_{label.replace(" ","_")}.csv','text/csv',
                       key='dl_detalle_fam')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
