import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods, TEAL)

st.set_page_config(page_title='Vendedor · ABAD', page_icon='👤',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('👤 Ventas por Vendedor', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('vendedor,nombre_vendedor,co,desc_co,canal_ventas,razon_social,desc_item,'
        'valor_subtotal,costo_promedio_total,cantidad,valor_descuentos,mes,anio')

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad','valor_descuentos']:
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
    filtro_canal = st.multiselect('🏪 Canal de Venta', canales_disp, default=[], help='Vacío = todos')

df = df_all.copy()
if filtro_co:    df = df[df['co'].isin(filtro_co)]
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]

filter_title({
    'Período': sels,
    'CO':     [f'{c:03d} – {co_desc_map.get(c, "")}' for c in filtro_co] if filtro_co else None,
    'Canal':  filtro_canal,
})

if df.empty:
    st.warning('Sin datos para los filtros.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
descto = df['valor_descuentos'].sum()
n_vend = df['vendedor'].nunique()

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas Totales'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{len(df):,}','🔢 Transacciones',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(fmt_currency(descto),'🎁 Descuentos',val_color='#CE93D8'), unsafe_allow_html=True)
with c5: st.markdown(kpi_html(str(n_vend),'👤 Vendedores',val_color='#FFCC80'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Agrupación ────────────────────────────────────────────────────────────────
vend = (df.groupby(['vendedor','nombre_vendedor'])
          .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
               cantidad=('cantidad','sum'),transacciones=('valor_subtotal','count'),
               descuento=('valor_descuentos','sum'))
          .reset_index())
vend['margen_%']      = ((vend['venta']-vend['costo'])/vend['venta']*100).round(2)
vend['participacion'] = (vend['venta']/vend['venta'].sum()*100).round(2)
vend = vend.sort_values('venta', ascending=False)

col_l, col_r = st.columns([2,1])
with col_l:
    st.markdown(section_title('Top 15 Vendedores por Venta'), unsafe_allow_html=True)
    top15 = vend.head(15).sort_values('venta', ascending=True)
    fig = go.Figure(go.Bar(x=top15['venta'],y=top15['nombre_vendedor'],orientation='h',
        text=top15['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=top15['margen_%'],
                    colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],showscale=True,
                    colorbar=dict(title='Margen %',thickness=10,tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,460),use_container_width=True)

with col_r:
    st.markdown(section_title('Top 10 por Margen %'), unsafe_allow_html=True)
    top_m = vend[vend['venta']>0].nlargest(10,'margen_%')[['nombre_vendedor','margen_%','venta']].copy()
    top_m['margen_%'] = top_m['margen_%'].apply(lambda x: f'{x:.2f}%')
    top_m['venta']    = top_m['venta'].apply(lambda x: f'${x:,.0f}')
    styled_table(top_m.rename(columns={'nombre_vendedor':'Vendedor','margen_%':'Margen','venta':'Ventas'}))

    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Mayores Descuentos'), unsafe_allow_html=True)
    top_d = vend.nlargest(8,'descuento')[['nombre_vendedor','descuento','venta']].copy()
    top_d['desc_%'] = (top_d['descuento']/top_d['venta']*100).round(1).apply(lambda x: f'{x}%')
    top_d['descuento'] = top_d['descuento'].apply(lambda x: f'${x:,.0f}')
    styled_table(top_d.rename(columns={'nombre_vendedor':'Vendedor','descuento':'Descuento',
                                        'venta':'Ventas','desc_%':'Desc%'}))

st.markdown('---')
st.markdown(section_title('Tabla Completa de Vendedores'), unsafe_allow_html=True)
disp = summary_table(vend,money_cols=['venta','costo','descuento'],pct_cols=['margen_%','participacion'])
disp = disp.rename(columns={'vendedor':'Cód','nombre_vendedor':'Vendedor','venta':'Ventas','costo':'Costo',
                             'cantidad':'Cantidad','transacciones':'Trans.','descuento':'Descuento',
                             'margen_%':'Margen','participacion':'Part %'})
styled_table(disp, max_height=460)
st.download_button('⬇️ Descargar CSV',vend.to_csv(index=False).encode('utf-8'),
                   f'vendedor_{label.replace(" ","_")}.csv','text/csv')

# ── DETALLE: Clientes e Ítems por Vendedor ────────────────────────────────────
st.markdown('---')
st.markdown(section_title('🔍 Detalle por Vendedor: Clientes e Ítems'), unsafe_allow_html=True)

vend_opts = (df.groupby('nombre_vendedor')['valor_subtotal'].sum()
               .sort_values(ascending=False).index.tolist())
sel_vend = st.selectbox('👤 Selecciona un vendedor para ver su detalle', vend_opts)

dv = df[df['nombre_vendedor'] == sel_vend].copy()

# Métricas del vendedor seleccionado
v_venta = dv['valor_subtotal'].sum()
v_costo = dv['costo_promedio_total'].sum()
v_marg  = (v_venta - v_costo) / v_venta * 100 if v_venta else 0
v_desc  = dv['valor_descuentos'].sum()
v_ncli  = dv['razon_social'].nunique()

m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown(kpi_html(fmt_currency(v_venta), '💰 Venta', bg='#112240'), unsafe_allow_html=True)
with m2: st.markdown(kpi_html(f'{v_marg:.2f}%', '📈 Margen', val_color='#4DB6AC', bg='#112240'), unsafe_allow_html=True)
with m3: st.markdown(kpi_html(fmt_currency(v_desc), '🎁 Descuento', val_color='#CE93D8', bg='#112240'), unsafe_allow_html=True)
with m4: st.markdown(kpi_html(str(v_ncli), '🏢 Clientes', val_color='#FFCC80', bg='#112240'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

dcol1, dcol2 = st.columns(2)

with dcol1:
    st.markdown(section_title('Clientes del Vendedor'), unsafe_allow_html=True)
    cli = (dv.groupby('razon_social')
             .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                  cantidad=('cantidad','sum'),descuento=('valor_descuentos','sum'))
             .reset_index())
    cli['margen_%']      = ((cli['venta']-cli['costo'])/cli['venta']*100).round(2)
    cli['participacion'] = (cli['venta']/cli['venta'].sum()*100).round(2)
    cli = cli.sort_values('venta', ascending=False)
    cli_disp = summary_table(cli, money_cols=['venta','costo','descuento'],
                             pct_cols=['margen_%','participacion'])
    cli_disp = cli_disp.rename(columns={'razon_social':'Cliente','venta':'Ventas','costo':'Costo',
                                        'cantidad':'Cant.','descuento':'Descuento',
                                        'margen_%':'Margen','participacion':'Part %'})
    styled_table(cli_disp, max_height=420)

with dcol2:
    st.markdown(section_title('Ítems Vendidos'), unsafe_allow_html=True)
    itm = (dv.groupby('desc_item')
             .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                  cantidad=('cantidad','sum'),descuento=('valor_descuentos','sum'))
             .reset_index())
    itm['margen_%']      = ((itm['venta']-itm['costo'])/itm['venta']*100).round(2)
    itm['participacion'] = (itm['venta']/itm['venta'].sum()*100).round(2)
    itm = itm.sort_values('venta', ascending=False)
    itm_disp = summary_table(itm, money_cols=['venta','costo','descuento'],
                             pct_cols=['margen_%','participacion'])
    itm_disp = itm_disp.rename(columns={'desc_item':'Ítem','venta':'Ventas','costo':'Costo',
                                        'cantidad':'Cant.','descuento':'Descuento',
                                        'margen_%':'Margen','participacion':'Part %'})
    styled_table(itm_disp, max_height=420)

# Detalle Cliente × Ítem (jerárquico como el pivote de Excel)
st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Detalle Cliente → Ítem'), unsafe_allow_html=True)
ci = (dv.groupby(['razon_social','desc_item'])
        .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
             cantidad=('cantidad','sum'),descuento=('valor_descuentos','sum'))
        .reset_index())
ci['margen_%'] = ((ci['venta']-ci['costo'])/ci['venta']*100).round(2)
ci = ci.sort_values(['razon_social','venta'], ascending=[True, False])
ci_disp = summary_table(ci, money_cols=['venta','costo','descuento'], pct_cols=['margen_%'])
ci_disp = ci_disp.rename(columns={'razon_social':'Cliente','desc_item':'Ítem','venta':'Ventas',
                                  'costo':'Costo','cantidad':'Cant.','descuento':'Descuento','margen_%':'Margen'})
styled_table(ci_disp, max_height=400)
st.download_button('⬇️ Descargar detalle Cliente×Ítem',
                   ci.to_csv(index=False).encode('utf-8'),
                   f'detalle_{sel_vend[:15]}_{label.replace(" ","_")}.csv','text/csv',
                   key='dl_detalle_vend')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
