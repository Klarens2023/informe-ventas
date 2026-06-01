import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency, fmt_int_co
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Puntos de Venta · ABAD', page_icon='🏬',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

PV_COS   = [2,3,4,5,6]
PV_NAMES = {2:'TPV Principal',3:'TPV CC Mayales',4:'TPV Natividad',5:'TPV Éxito Flores',6:'TPV Parque La Prov.'}

# ── Header ────────────────────────────────────────────────────────────────────
page_header('🏬 Puntos de Venta', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('co,desc_co,familia,desc_item,canal_ventas,fecha,'
        'valor_subtotal,costo_promedio_total,cantidad,nombre_vendedor,mes,anio')

with st.spinner('Cargando...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','cantidad']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
if 'co' in df_all.columns:
    df_all['co'] = pd.to_numeric(df_all['co'], errors='coerce').fillna(0).astype(int)

df_pv = df_all[df_all['co'].isin(PV_COS)].copy()

# ── Filtros INLINE ────────────────────────────────────────────────────────────
co_desc_map     = df_pv.groupby('co')['desc_co'].first().to_dict()
cos_disponibles = sorted([c for c in df_pv['co'].unique() if c in PV_COS])
familias_disp   = sorted([f for f in df_pv['familia'].dropna().unique() if str(f).strip()])

fc1, fc2 = st.columns(2)
with fc1:
    filtro_pv = st.multiselect('🏬 Punto de Venta (CO)', options=cos_disponibles, default=[],
        format_func=lambda x: f'{x:03d} – {co_desc_map.get(x, PV_NAMES.get(x, str(x)))}',
        help='Vacío = todos')
with fc2:
    filtro_fam = st.multiselect('🏷️ Familia', familias_disp, default=[], help='Vacío = todas')

df = df_pv.copy()
if filtro_pv:  df = df[df['co'].isin(filtro_pv)]
if filtro_fam: df = df[df['familia'].isin(filtro_fam)]

filter_title({
    'Período': sels,
    'PV':      [f'{c:03d} – {co_desc_map.get(c, PV_NAMES.get(c, ""))}' for c in filtro_pv] if filtro_pv else None,
    'Familia': filtro_fam,
})

if df.empty:
    st.warning('Sin datos para los puntos de venta seleccionados.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta  = df['valor_subtotal'].sum()
costo  = df['costo_promedio_total'].sum()
margen = (venta-costo)/venta*100 if venta else 0
uds    = df['cantidad'].sum()

c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta),'💰 Ventas PV'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{margen:.2f}%','📈 Margen %',val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{uds:,.0f}','📦 Unidades',val_color='#80DEEA'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(f'{len(df):,}','🔢 Transacciones',val_color='#FFCC80'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Cards por CO ──────────────────────────────────────────────────────────────
st.markdown(section_title('Rendimiento por Punto de Venta'), unsafe_allow_html=True)
co_df = (df.groupby(['co','desc_co'])
           .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),
                cantidad=('cantidad','sum'),transacciones=('valor_subtotal','count'))
           .reset_index())
co_df['margen_%']      = ((co_df['venta']-co_df['costo'])/co_df['venta']*100).round(2)
co_df['participacion'] = (co_df['venta']/co_df['venta'].sum()*100).round(2)
co_df = co_df.sort_values('venta', ascending=False)

n_cols = min(len(co_df), 5)
cols = st.columns(n_cols)
for i, (_, row) in enumerate(co_df.iterrows()):
    with cols[i % n_cols]:
        st.markdown(f"""
<div style="background:#0D2137;border-radius:12px;padding:16px 14px;
            border:1px solid rgba(21,101,192,.25);margin:3px;text-align:center">
  <div style="font-size:.75rem;color:#90CAF9;font-weight:600">CO {int(row['co']):02d}</div>
  <div style="font-size:.82rem;color:#e2e8f0;margin:4px 0">{row['desc_co']}</div>
  <div style="font-size:1.3rem;font-weight:800;color:#F57F17">{fmt_currency(row['venta'])}</div>
  <div style="font-size:.78rem;color:#4DB6AC;margin-top:3px">Margen: {row['margen_%']:.1f}%</div>
  <div style="font-size:.75rem;color:#607D8B">Part: {row['participacion']:.1f}%</div>
</div>""", unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

col_l, col_r = st.columns([3,2])
with col_l:
    st.markdown(section_title('Ventas por Punto de Venta'), unsafe_allow_html=True)
    cs = co_df.sort_values('venta', ascending=True)
    fig = go.Figure(go.Bar(x=cs['venta'],y=cs['desc_co'],orientation='h',
        text=cs['venta'].apply(fmt_currency),textposition='outside',
        marker=dict(color=cs['margen_%'],colorscale=[[0,'#1565C0'],[0.5,'#00838F'],[1,'#4DB6AC']],
                    showscale=True,colorbar=dict(title='Margen %',thickness=10,
                                                 tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(fig,350),use_container_width=True)

with col_r:
    st.markdown(section_title('Composición por Familia'), unsafe_allow_html=True)
    fam = (df.groupby('familia').agg(venta=('valor_subtotal','sum')).reset_index())
    fam = fam[fam['familia'].str.strip()!=''].sort_values('venta', ascending=False).head(10)
    if not fam.empty:
        fig2 = px.pie(fam,values='venta',names='familia',hole=0.45,color_discrete_sequence=CHART_COLORS)
        fig2.update_traces(textposition='inside',textinfo='percent+label',textfont=dict(color='white',size=10))
        fig2.update_layout(showlegend=False)
        st.plotly_chart(dark_chart(fig2,350),use_container_width=True)
    else:
        st.info('Sin datos de familia.')

st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Top 15 Productos en Puntos de Venta'), unsafe_allow_html=True)
prod = (df.groupby(['desc_item','familia'])
          .agg(venta=('valor_subtotal','sum'),costo=('costo_promedio_total','sum'),cantidad=('cantidad','sum'))
          .reset_index())
prod['margen_%'] = ((prod['venta']-prod['costo'])/prod['venta']*100).round(2)
prod = prod.sort_values('venta', ascending=False).head(15)
fig3 = px.bar(prod.sort_values('venta'),x='venta',y='desc_item',orientation='h',
              color='familia',text='venta',color_discrete_sequence=CHART_COLORS)
fig3.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont=dict(color='white'))
fig3.update_layout(showlegend=True,legend=dict(font=dict(color='white')))
st.plotly_chart(dark_chart(fig3,460),use_container_width=True)

st.markdown('---')
disp = summary_table(co_df,money_cols=['venta','costo'],pct_cols=['margen_%','participacion'])
disp = disp.rename(columns={'co':'CO','desc_co':'Punto de Venta','venta':'Ventas','costo':'Costo',
                             'cantidad':'Cantidad','transacciones':'Trans.',
                             'margen_%':'Margen','participacion':'Part %'})
styled_table(disp)

# ── DETALLE DIARIO POR PUNTO DE VENTA (pivote fecha × PV) ─────────────────────
st.markdown('---')
st.markdown(section_title('📅 Detalle Diario por Punto de Venta'), unsafe_allow_html=True)

if 'fecha' in df.columns:
    dfd = df.copy()
    dfd['fecha'] = pd.to_datetime(dfd['fecha'], errors='coerce')
    dfd = dfd.dropna(subset=['fecha'])

    if dfd.empty:
        st.info('No hay fechas válidas para construir el detalle diario.')
    else:
        fmin = dfd['fecha'].min().date()
        fmax = dfd['fecha'].max().date()

        ctrl1, ctrl2 = st.columns([2, 3])
        with ctrl1:
            metrica = st.radio('Métrica a mostrar', ['Venta', 'Cantidad', 'Transacciones'],
                               horizontal=True, key='metrica_diaria')
        with ctrl2:
            rango = st.date_input('📆 Rango de fechas', value=(fmin, fmax),
                                  min_value=fmin, max_value=fmax, key='rango_diario',
                                  format='DD/MM/YYYY')

        # Aplicar filtro de fechas
        if isinstance(rango, (list, tuple)) and len(rango) == 2:
            d0, d1 = rango
            dfd = dfd[(dfd['fecha'].dt.date >= d0) & (dfd['fecha'].dt.date <= d1)]

        if dfd.empty:
            st.info('Sin datos en el rango de fechas seleccionado.')
        else:
            val_col = 'valor_subtotal' if metrica != 'Cantidad' else 'cantidad'
            aggf    = 'count' if metrica == 'Transacciones' else 'sum'

            dfd['dia'] = dfd['fecha'].dt.strftime('%d/%m')
            orden_dias = dfd.sort_values('fecha')['dia'].drop_duplicates().tolist()

            piv = pd.pivot_table(dfd, index='desc_co', columns='dia',
                                 values=val_col, aggfunc=aggf, fill_value=0)
            piv = piv.reindex(columns=orden_dias, fill_value=0)
            piv['TOTAL'] = piv.sum(axis=1)
            piv = piv.sort_values('TOTAL', ascending=False)
            piv.loc['TOTAL GENERAL'] = piv.sum(axis=0)

            fmt = fmt_currency if metrica == 'Venta' else fmt_int_co
            piv_disp = piv.copy()
            for col in piv_disp.columns:
                piv_disp[col] = piv_disp[col].apply(fmt)
            piv_disp = piv_disp.reset_index().rename(columns={'desc_co': 'Punto de Venta'})
            # Muchas columnas de días → permitimos scroll horizontal y vertical
            styled_table(piv_disp, max_height=480, x_scroll=True,
                         total_rows=['TOTAL GENERAL'])

            st.download_button('⬇️ Descargar detalle diario',
                               piv.to_csv().encode('utf-8'),
                               f'pv_diario_{label.replace(" ","_")}.csv', 'text/csv', key='dl_pv_diario')

            # Evolución diaria (línea por punto de venta)
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown(section_title(f'Evolución Diaria · {metrica}'), unsafe_allow_html=True)
            ev = (dfd.groupby(['dia', 'fecha', 'desc_co'])
                     .agg(val=(val_col, aggf)).reset_index().sort_values('fecha'))
            figd = px.line(ev, x='dia', y='val', color='desc_co', markers=True,
                           color_discrete_sequence=CHART_COLORS,
                           labels={'dia': 'Día', 'val': metrica, 'desc_co': 'Punto de Venta'})
            figd.update_traces(line=dict(width=2), marker=dict(size=6))
            figd.update_layout(legend=dict(font=dict(color='white')))
            st.plotly_chart(dark_chart(figd, 420, hide_money_axis='y' if metrica == 'Venta' else None),
                            use_container_width=True)
else:
    st.info('La columna de fecha no está disponible para el detalle diario.')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
