import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import is_configured, fetch_ventas, fetch_periodos
from utils.charts import summary_table, fmt_currency, fmt_pct, fmt_int_co
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods, CHART_COLORS)

st.set_page_config(page_title='Descuentos · ABAD', page_icon='🎁',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('🎁 Análisis de Descuentos', 'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('desc_item,referencia,razon_social,co,desc_co,canal_ventas,fecha,nro_documento,'
        'vendedor,nombre_vendedor,familia,valor_subtotal,valor_descuentos,'
        'dscto_promedio_pct,cantidad,mes,anio')

with st.spinner(f'Cargando {len(sels)} período(s)...'):
    df_all = load_periods(fetch_ventas, sels, COLS)

if df_all.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','valor_descuentos','dscto_promedio_pct','cantidad']:
    if c in df_all.columns:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
if 'co' in df_all.columns:
    df_all['co'] = pd.to_numeric(df_all['co'], errors='coerce').fillna(0).astype(int)

# ── Filtros INLINE ────────────────────────────────────────────────────────────
co_desc_map  = df_all.groupby('co')['desc_co'].first().to_dict()
cos_disp     = sorted(df_all['co'].unique().tolist())
canales_disp = sorted(df_all['canal_ventas'].dropna().unique().tolist())

fc1, fc2, fc3 = st.columns(3)
with fc1:
    filtro_co = st.multiselect('🏢 Centro de Operación', cos_disp, default=[],
                                format_func=lambda x: f'{x:03d} – {co_desc_map.get(x, str(x))}',
                                help='Vacío = todos')
with fc2:
    filtro_canal = st.multiselect('🏪 Canal de Venta', canales_disp, default=[], help='Vacío = todos')
with fc3:
    solo_con_dscto = st.checkbox('Solo con descuento > 0', value=True)

df = df_all.copy()
if filtro_co:    df = df[df['co'].isin(filtro_co)]
if filtro_canal: df = df[df['canal_ventas'].isin(filtro_canal)]
if solo_con_dscto:
    df = df[df['valor_descuentos'] > 0]

filter_title({
    'Período': sels,
    'CO':     [f'{c:03d} – {co_desc_map.get(c, "")}' for c in filtro_co] if filtro_co else None,
    'Canal':  filtro_canal,
})

if df.empty:
    st.warning('Sin datos para los filtros.'); st.stop()

st.markdown('<br>', unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
venta     = df['valor_subtotal'].sum()
descuento = df['valor_descuentos'].sum()
dscto_pct = (descuento / venta * 100) if venta else 0
n_trans   = len(df)
n_items   = df['desc_item'].nunique()
n_cli     = df['razon_social'].nunique()

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(kpi_html(fmt_currency(descuento),'🎁 Descuento Total'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(f'{dscto_pct:.2f}%','📉 % Dscto s/Venta',val_color='#CE93D8'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(fmt_currency(venta),'💰 Venta Asociada',val_color='#4DB6AC'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(fmt_int_co(n_trans),'🔢 Transacciones',val_color='#80DEEA'), unsafe_allow_html=True)
with c5: st.markdown(kpi_html(str(n_cli),'🏢 Clientes',val_color='#FFCC80'), unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Descuento por Canal y por CO ──────────────────────────────────────────────
col_l, col_r = st.columns(2)
with col_l:
    st.markdown(section_title('Descuento por Canal'), unsafe_allow_html=True)
    dc = (df.groupby('canal_ventas')
            .agg(descuento=('valor_descuentos','sum'),venta=('valor_subtotal','sum'))
            .reset_index())
    dc['dscto_%'] = (dc['descuento']/dc['venta']*100).round(2)
    dc = dc.sort_values('descuento', ascending=False)
    ds = dc.sort_values('descuento', ascending=True)
    figc = go.Figure(go.Bar(x=ds['descuento'],y=ds['canal_ventas'],orientation='h',
        text=ds['descuento'].apply(fmt_currency),textposition='outside',
        marker=dict(color=ds['dscto_%'],colorscale=[[0,'#1565C0'],[0.5,'#6A1B9A'],[1,'#CE93D8']],
                    showscale=True,colorbar=dict(title='% Dscto',thickness=10,
                                                 tickfont=dict(color='white'),titlefont=dict(color='white')))))
    st.plotly_chart(dark_chart(figc,400,hide_money_axis='x'),use_container_width=True)

with col_r:
    st.markdown(section_title('Descuento por Centro de Operación'), unsafe_allow_html=True)
    dco = (df.groupby(['co','desc_co'])
             .agg(descuento=('valor_descuentos','sum'),venta=('valor_subtotal','sum'))
             .reset_index())
    dco['dscto_%'] = (dco['descuento']/dco['venta']*100).round(2)
    dco = dco.sort_values('descuento', ascending=False)
    dcs = dco.sort_values('descuento', ascending=True)
    figco = go.Figure(go.Bar(x=dcs['descuento'],y=dcs['desc_co'],orientation='h',
        text=dcs['descuento'].apply(fmt_currency),textposition='outside',marker_color='#6A1B9A'))
    st.plotly_chart(dark_chart(figco,400,hide_money_axis='x'),use_container_width=True)

# ── Tabla: Ítem × Cliente × % Descuento (como el pivote de Excel) ─────────────
st.markdown('<br>', unsafe_allow_html=True)
st.markdown(section_title('Descuento por Ítem y Cliente'), unsafe_allow_html=True)

ic = (df.groupby(['desc_item','razon_social'])
        .agg(venta=('valor_subtotal','sum'),
             descuento=('valor_descuentos','sum'),
             dscto_pct_prom=('dscto_promedio_pct','mean'),
             cantidad=('cantidad','sum'))
        .reset_index())
ic['dscto_%_real'] = (ic['descuento']/ic['venta']*100).round(2)
ic['dscto_pct_prom'] = ic['dscto_pct_prom'].round(2)
ic = ic.sort_values(['desc_item','descuento'], ascending=[True, False])

ic_disp = summary_table(ic, money_cols=['venta','descuento'],
                        pct_cols=['dscto_pct_prom','dscto_%_real'])
ic_disp = ic_disp.rename(columns={'desc_item':'Ítem','razon_social':'Cliente',
                                  'venta':'Ventas','descuento':'Descuento $',
                                  'dscto_pct_prom':'% Dscto Prom','dscto_%_real':'% Dscto Real',
                                  'cantidad':'Cant.'})
styled_table(ic_disp, max_height=460)
st.download_button('⬇️ Descargar Ítem×Cliente',
                   ic.to_csv(index=False).encode('utf-8'),
                   f'descuentos_item_cliente_{label.replace(" ","_")}.csv','text/csv',
                   key='dl_ic')

# ── Top clientes con mayor descuento ──────────────────────────────────────────
st.markdown('<br>', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(section_title('Top 15 Clientes con Mayor Descuento'), unsafe_allow_html=True)
    tc = (df.groupby('razon_social')
            .agg(descuento=('valor_descuentos','sum'),venta=('valor_subtotal','sum'))
            .reset_index())
    tc['dscto_%'] = (tc['descuento']/tc['venta']*100).round(2)
    tc = tc.sort_values('descuento', ascending=False).head(15)
    tcs = tc.sort_values('descuento', ascending=True)
    figtc = go.Figure(go.Bar(x=tcs['descuento'],y=tcs['razon_social'],orientation='h',
        text=tcs['descuento'].apply(fmt_currency),textposition='outside',marker_color='#CE93D8'))
    st.plotly_chart(dark_chart(figtc,460,hide_money_axis='x'),use_container_width=True)

with col_b:
    st.markdown(section_title('Top 15 Ítems con Mayor Descuento'), unsafe_allow_html=True)
    ti = (df.groupby('desc_item')
            .agg(descuento=('valor_descuentos','sum'),venta=('valor_subtotal','sum'))
            .reset_index())
    ti['dscto_%'] = (ti['descuento']/ti['venta']*100).round(2)
    ti = ti.sort_values('descuento', ascending=False).head(15)
    tis = ti.sort_values('descuento', ascending=True)
    figti = go.Figure(go.Bar(x=tis['descuento'],y=tis['desc_item'],orientation='h',
        text=tis['descuento'].apply(fmt_currency),textposition='outside',marker_color='#9575CD'))
    st.plotly_chart(dark_chart(figti,460,hide_money_axis='x'),use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#   DESCUENTO HAPPY — definición oficial:
#   Miércoles + CO 002-006 + Hora aprobacion 2:00-3:00 pm + descuento ≥ 20%
#   (las del 20% son HAPPY puro; las > 20% son HAPPY + un descuento extra
#    aplicado por error. En ambos casos solo se cuenta el 20% como Happy.)
# ══════════════════════════════════════════════════════════════════════════════
HAPPY_CO    = [2, 3, 4, 5, 6]
HAPPY_RATE  = 0.20        # 20% es lo que aporta HAPPY
HAPPY_MIN   = 19.5        # umbral de filtro (% mínimo para considerar HAPPY)

st.markdown('---')
st.markdown("""
<div style="background:linear-gradient(90deg,#6A1B9A,#8E24AA,#AB47BC);
            border-radius:12px;padding:14px 22px;margin:10px 0;
            border:1px solid rgba(206,147,216,.4)">
  <div style="font-size:1.3rem;font-weight:800;color:#fff">😊 Descuento HAPPY</div>
  <div style="font-size:.84rem;color:#E1BEE7;margin-top:3px">
    Facturas de los <b>miércoles</b> en <b>CO 002-006</b>,
    aprobadas entre <b>2:00 y 3:00 pm</b> y con <b>descuento ≥ 20%</b>.
    El monto se calcula como <b>20% del valor bruto</b>; el resto (cuando hay)
    proviene de un descuento adicional aplicado por error.
  </div>
</div>""", unsafe_allow_html=True)

from utils.database import fetch_happy_docs, horas_disponibles

if horas_disponibles() == 0:
    st.info('ℹ️ Sube el archivo "Ventas con hora" en **📥 Importar Data** '
            'para activar el análisis HAPPY (necesita la hora real de aprobación).')
    st.stop()

# Empezar desde las ventas, aplicar los 4 filtros
dh = df_all.copy()
dh['fecha_dt']  = pd.to_datetime(dh['fecha'], errors='coerce')
dh = dh.dropna(subset=['fecha_dt'])

# 1. Miércoles
dh = dh[dh['fecha_dt'].dt.dayofweek == 2]
# 2. CO 002-006
dh = dh[dh['co'].isin(HAPPY_CO)]
# 3. Hora 2-3pm (cruce con factura_horas via nro_documento)
happy_docs = fetch_happy_docs()
if 'nro_documento' in dh.columns and happy_docs:
    dh['_doc'] = dh['nro_documento'].astype(str).str.strip()
    dh = dh[dh['_doc'].isin(happy_docs)]
else:
    dh = dh.iloc[0:0]
# 4. Descuento ≥ 20% (incluye 20% puro y 27.2% = 20% + extra por error)
if 'dscto_promedio_pct' in dh.columns:
    dh['dscto_promedio_pct'] = pd.to_numeric(dh['dscto_promedio_pct'], errors='coerce').fillna(0)
    dh = dh[dh['dscto_promedio_pct'] >= HAPPY_MIN]

# Calcular el descuento HAPPY: solo el 20% del valor bruto (no incluye los extras)
# valor_bruto = valor_subtotal + valor_descuentos (no viene en SHARED_COLS, lo derivamos)
if not dh.empty:
    _vs = pd.to_numeric(dh['valor_subtotal'], errors='coerce').fillna(0)
    _vd = pd.to_numeric(dh['valor_descuentos'], errors='coerce').fillna(0)
    dh['valor_bruto']      = _vs + _vd
    dh['descuento_happy']  = dh['valor_bruto'] * HAPPY_RATE
    # Marca para reportar dobles descuentos
    dh['tiene_extra']      = dh['dscto_promedio_pct'] > 21.0

if dh.empty:
    st.warning(
        'No se encontraron facturas HAPPY con los 4 filtros activos '
        '(miércoles + CO 002-006 + 2-3pm + descuento ≥ 20%) en el período seleccionado.'
    )
else:
    h_venta     = dh['valor_subtotal'].sum()
    h_desc      = dh['descuento_happy'].sum()                # solo el 20%
    h_desc_real = dh['valor_descuentos'].sum()                # incluye dobles
    h_extra     = h_desc_real - h_desc                        # parte aplicada por error
    h_pct       = (h_desc / h_venta * 100) if h_venta else 0
    h_fact      = dh['nro_documento'].nunique() if 'nro_documento' in dh.columns else len(dh)
    h_uds       = dh['cantidad'].sum()
    n_doble     = int(dh['tiene_extra'].sum())                # facturas con doble descuento

    h1, h2, h3, h4, h5 = st.columns(5)
    with h1: st.markdown(kpi_html(fmt_currency(h_desc), '😊 Descuento Happy (20%)', val_color='#CE93D8', bg='#2A1438'), unsafe_allow_html=True)
    with h2: st.markdown(kpi_html(fmt_currency(h_venta), '💰 Venta Happy', val_color='#4DB6AC', bg='#2A1438'), unsafe_allow_html=True)
    with h3: st.markdown(kpi_html(fmt_int_co(h_fact), '🧾 Facturas', val_color='#80DEEA', bg='#2A1438'), unsafe_allow_html=True)
    with h4: st.markdown(kpi_html(fmt_int_co(h_uds), '📦 Unidades', val_color='#FFCC80', bg='#2A1438'), unsafe_allow_html=True)
    with h5: st.markdown(kpi_html(fmt_currency(h_extra), f'⚠️ Dscto extra ({n_doble} fact.)', val_color='#EF9A9A', bg='#2A1438'), unsafe_allow_html=True)

    # ── Pivote: filas = PV, columnas = fechas (miércoles), valores = Cantidad + Venta ──
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Happy: Punto de Venta × Miércoles'), unsafe_allow_html=True)

    dh['dia'] = dh['fecha_dt'].dt.strftime('%d/%m/%Y')
    orden_dias = dh.sort_values('fecha_dt')['dia'].drop_duplicates().tolist()

    piv_v = pd.pivot_table(dh, index='desc_co', columns='dia',
                           values='valor_subtotal', aggfunc='sum', fill_value=0)
    piv_c = pd.pivot_table(dh, index='desc_co', columns='dia',
                           values='cantidad', aggfunc='sum', fill_value=0)
    piv_v = piv_v.reindex(columns=orden_dias, fill_value=0)
    piv_c = piv_c.reindex(columns=orden_dias, fill_value=0)
    piv_v['TOTAL'] = piv_v.sum(axis=1)
    piv_c['TOTAL'] = piv_c.sum(axis=1)

    # Construir tabla mostrando Cantidad y Venta por fecha (como el Excel)
    cols_finales = []
    rows_data = {pv: {} for pv in piv_v.index}
    for dia in orden_dias + ['TOTAL']:
        cols_finales += [f'{dia} · Cant', f'{dia} · Venta']
        for pv in piv_v.index:
            rows_data[pv][f'{dia} · Cant']  = fmt_int_co(piv_c.at[pv, dia])
            rows_data[pv][f'{dia} · Venta'] = fmt_currency(piv_v.at[pv, dia])

    # Fila total general
    total_row = {}
    for dia in orden_dias + ['TOTAL']:
        total_row[f'{dia} · Cant']  = fmt_int_co(piv_c[dia].sum())
        total_row[f'{dia} · Venta'] = fmt_currency(piv_v[dia].sum())

    pv_orden = piv_v.sum(axis=1).sort_values(ascending=False).index.tolist()
    table_rows = []
    for pv in pv_orden:
        row = {'Punto de Venta': pv, **rows_data[pv]}
        table_rows.append(row)
    table_rows.append({'Punto de Venta': 'TOTAL GENERAL', **total_row})

    pivot_df = pd.DataFrame(table_rows, columns=['Punto de Venta'] + cols_finales)
    styled_table(pivot_df, max_height=420, x_scroll=True, total_rows=['TOTAL GENERAL'])

    # ── Detalle Ítem × Cliente ──
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Detalle Happy: Ítem y Cliente'), unsafe_allow_html=True)
    hd = (dh.groupby(['desc_item', 'razon_social'])
            .agg(venta=('valor_subtotal', 'sum'),
                 descuento=('descuento_happy', 'sum'),     # solo 20%
                 cantidad=('cantidad', 'sum'),
                 facturas=('nro_documento', 'nunique'))
            .reset_index())
    hd = hd.sort_values('venta', ascending=False)
    hd_disp = summary_table(hd, money_cols=['venta', 'descuento'])
    hd_disp = hd_disp.rename(columns={'desc_item': 'Ítem', 'razon_social': 'Cliente',
                                      'venta': 'Venta', 'descuento': 'Dscto Happy (20%)',
                                      'cantidad': 'Cant.', 'facturas': 'Facturas'})
    styled_table(hd_disp, max_height=440)
    st.download_button('⬇️ Descargar detalle Happy',
                       hd.to_csv(index=False).encode('utf-8'),
                       f'happy_{label.replace(" ", "_")}.csv', 'text/csv', key='dl_happy')

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
