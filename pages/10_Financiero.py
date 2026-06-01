import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.database import (is_configured, fetch_ventas, fetch_periodos,
                              fetch_presupuestos, upsert_presupuestos)
from utils.charts import summary_table, fmt_currency, fmt_int_co
from utils.ui import (DARK_CSS, dark_chart, kpi_html, section_title, page_header,
                      filter_title, styled_table, minimal_sidebar, period_pills, load_periods,
                      CHART_COLORS, CARD2)

st.set_page_config(page_title='Análisis Financiero · ABAD', page_icon='💼',
                   layout='wide', initial_sidebar_state='auto')
st.markdown(DARK_CSS, unsafe_allow_html=True)
if not is_configured():
    minimal_sidebar()
    st.error('Configura Supabase en 📥 Importar Data.'); st.stop()

minimal_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
page_header('💼 Análisis Financiero',
            'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')

# ── Selector de período ────────────────────────────────────────────────────────
sels, label = period_pills(fetch_periodos)
st.markdown('---')

# ── Carga de datos ────────────────────────────────────────────────────────────
COLS = ('mes,anio,fecha,co,desc_co,canal_ventas,familia,razon_social,desc_item,'
        'valor_subtotal,costo_promedio_total,valor_descuentos,valor_impuestos,'
        'cantidad,nro_documento,desc_motivo')

with st.spinner(f'Cargando {len(sels)} período(s)...'):
    df = load_periods(fetch_ventas, sels, COLS)

if df.empty:
    st.warning('No hay datos para los períodos seleccionados.'); st.stop()

for c in ['valor_subtotal','costo_promedio_total','valor_descuentos','valor_impuestos','cantidad']:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
if 'co' in df.columns:
    df['co'] = pd.to_numeric(df['co'], errors='coerce').fillna(0).astype(int)

filter_title({'Período': sels})
st.markdown('<br>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#   1. KPIs FINANCIEROS
# ══════════════════════════════════════════════════════════════════════════════
venta_neta   = df['valor_subtotal'].sum()
costo        = df['costo_promedio_total'].sum()
descuentos   = df['valor_descuentos'].sum()
impuestos    = df['valor_impuestos'].sum() if 'valor_impuestos' in df.columns else 0
util_bruta   = venta_neta - costo
margen_bruto = (util_bruta / venta_neta * 100) if venta_neta else 0
n_facturas   = df['nro_documento'].nunique() if 'nro_documento' in df.columns else len(df)
ticket_prom  = (venta_neta / n_facturas) if n_facturas else 0

# Devoluciones / anulaciones
dev_mask = df['desc_motivo'].fillna('').str.contains('devol|anula', case=False, regex=True) \
           if 'desc_motivo' in df.columns else pd.Series([False] * len(df))
val_dev  = df.loc[dev_mask, 'valor_subtotal'].sum()
n_dev    = int(dev_mask.sum())
pct_dev  = (abs(val_dev) / venta_neta * 100) if venta_neta else 0

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_html(fmt_currency(venta_neta),  '💰 Venta Neta'), unsafe_allow_html=True)
with c2: st.markdown(kpi_html(fmt_currency(util_bruta),  '📈 Utilidad Bruta', val_color='#4DB6AC'), unsafe_allow_html=True)
with c3: st.markdown(kpi_html(f'{margen_bruto:,.2f}%'.replace(',', '.'), '📊 Margen Bruto', val_color='#4CAF50'), unsafe_allow_html=True)
with c4: st.markdown(kpi_html(fmt_currency(ticket_prom), '🎫 Ticket Promedio', val_color='#FFCC80'), unsafe_allow_html=True)

st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
c5, c6, c7, c8 = st.columns(4)
with c5: st.markdown(kpi_html(fmt_currency(impuestos), '🧾 Impuestos',     val_color='#EF9A9A', bg=CARD2), unsafe_allow_html=True)
with c6: st.markdown(kpi_html(fmt_currency(descuentos), '🎁 Descuentos',    val_color='#CE93D8', bg=CARD2), unsafe_allow_html=True)
with c7: st.markdown(kpi_html(fmt_currency(abs(val_dev)), '↩️ Devoluciones', val_color='#FFAB91', bg=CARD2), unsafe_allow_html=True)
with c8: st.markdown(kpi_html(f'{pct_dev:.2f}% · {n_dev} fact.', '% Devol s/Venta', val_color='#FF8A65', bg=CARD2), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#   2. COMPARATIVO PERÍODO A PERÍODO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('---')
st.markdown(section_title('📅 Comparativo Período a Período'), unsafe_allow_html=True)

if 'mes' in df.columns and 'anio' in df.columns:
    MONTH_ORDER = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO',
                   'JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']
    comp = (df.groupby(['anio', 'mes'])
              .agg(venta      =('valor_subtotal', 'sum'),
                   costo      =('costo_promedio_total', 'sum'),
                   descuentos =('valor_descuentos', 'sum'),
                   impuestos  =('valor_impuestos', 'sum') if 'valor_impuestos' in df.columns else ('valor_subtotal', 'count'),
                   facturas   =('nro_documento', 'nunique') if 'nro_documento' in df.columns else ('valor_subtotal', 'count'),
                   unidades   =('cantidad', 'sum'))
              .reset_index())
    comp['util_bruta']  = comp['venta'] - comp['costo']
    comp['margen_%']    = (comp['util_bruta'] / comp['venta'] * 100).round(2)
    comp['ticket_prom'] = (comp['venta'] / comp['facturas']).round(0)
    comp['_ord']        = comp['mes'].map({m: i for i, m in enumerate(MONTH_ORDER)})
    comp = comp.sort_values(['anio', '_ord'])
    comp['var_venta_%'] = (comp['venta'].pct_change().fillna(0) * 100).round(2)
    comp['var_util_%']  = (comp['util_bruta'].pct_change().fillna(0) * 100).round(2)
    comp['periodo']     = comp['mes'] + ' ' + comp['anio'].astype(str)

    disp = comp[['periodo','venta','util_bruta','margen_%','costo','descuentos','impuestos',
                 'facturas','unidades','ticket_prom','var_venta_%','var_util_%']].copy()
    disp_fmt = summary_table(
        disp,
        money_cols=['venta','util_bruta','costo','descuentos','impuestos','ticket_prom'],
        pct_cols=['margen_%','var_venta_%','var_util_%'],
    )
    disp_fmt = disp_fmt.rename(columns={
        'periodo':'Período', 'venta':'Venta', 'util_bruta':'Utilidad Bruta',
        'margen_%':'Margen %', 'costo':'Costo', 'descuentos':'Descuentos',
        'impuestos':'Impuestos', 'facturas':'Facturas', 'unidades':'Unidades',
        'ticket_prom':'Ticket Prom', 'var_venta_%':'Δ Venta', 'var_util_%':'Δ Utilidad',
    })
    styled_table(disp_fmt)

    # Gráfico evolución
    st.markdown('<br>', unsafe_allow_html=True)
    fig_e = go.Figure()
    fig_e.add_trace(go.Bar(
        x=comp['periodo'], y=comp['venta'], name='Venta',
        marker_color='#1565C0',
        text=comp['venta'].apply(fmt_currency), textposition='outside', textfont=dict(color='white')))
    fig_e.add_trace(go.Scatter(
        x=comp['periodo'], y=comp['util_bruta'], name='Utilidad Bruta',
        mode='lines+markers', line=dict(color='#F57F17', width=2.5),
        marker=dict(size=10), yaxis='y2'))
    fig_e.update_layout(
        yaxis=dict(showticklabels=False),
        yaxis2=dict(overlaying='y', side='right', showticklabels=False),
        barmode='group', legend=dict(font=dict(color='white')))
    st.plotly_chart(dark_chart(fig_e, 380), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#   3. PRESUPUESTO (META) — editable manualmente · cumplimiento real vs meta
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('---')
st.markdown(section_title('🎯 Presupuesto vs Real'), unsafe_allow_html=True)

# Cargar metas existentes
metas = fetch_presupuestos()  # {(mes, anio): {venta_meta, util_meta}}

# Editor en un expander para no estorbar
with st.expander('✏️ Editar presupuesto mensual (metas)', expanded=False):
    st.caption('Define las metas de **venta** y **utilidad bruta** por período. '
               'Se guardan en Supabase y se reutilizan en cada análisis. '
               'Solo verás los períodos disponibles en la base.')

    todos_per = fetch_periodos()
    edit_rows = []
    for p in todos_per:
        m = str(p['mes']).strip().upper()
        a = int(p['anio'])
        meta = metas.get((m, a), {})
        edit_rows.append({
            'Mes':       m,
            'Año':       a,
            'Venta Meta':    float(meta.get('venta_meta', 0)),
            'Utilidad Meta': float(meta.get('util_meta', 0)),
        })
    edit_df = pd.DataFrame(edit_rows)

    edited = st.data_editor(
        edit_df,
        column_config={
            'Mes':           st.column_config.TextColumn(disabled=True),
            'Año':           st.column_config.NumberColumn(disabled=True, format='%d'),
            'Venta Meta':    st.column_config.NumberColumn(
                                min_value=0, step=1000000, format='$%d',
                                help='Meta de venta neta del mes'),
            'Utilidad Meta': st.column_config.NumberColumn(
                                min_value=0, step=1000000, format='$%d',
                                help='Meta de utilidad bruta (Venta − Costo)'),
        },
        hide_index=True, use_container_width=True, key='budget_editor',
    )

    if st.button('💾 Guardar presupuesto', type='primary', key='save_budget'):
        recs = []
        for _, r in edited.iterrows():
            recs.append({
                'mes':        r['Mes'],
                'anio':       int(r['Año']),
                'venta_meta': float(r['Venta Meta'] or 0),
                'util_meta':  float(r['Utilidad Meta'] or 0),
            })
        try:
            upsert_presupuestos(recs)
            st.success(f'✅ Presupuesto guardado para {len(recs)} período(s).')
            st.cache_data.clear()
        except Exception as e:
            st.error(f'Error: {e}')

# Mostrar Real vs Meta de los períodos seleccionados
comp_meta = comp.copy() if 'comp' in dir() else None
if comp_meta is not None and not comp_meta.empty:
    comp_meta['venta_meta'] = comp_meta.apply(
        lambda r: metas.get((str(r['mes']).strip().upper(), int(r['anio'])), {}).get('venta_meta', 0),
        axis=1)
    comp_meta['util_meta'] = comp_meta.apply(
        lambda r: metas.get((str(r['mes']).strip().upper(), int(r['anio'])), {}).get('util_meta', 0),
        axis=1)
    comp_meta['cumpl_venta_%'] = comp_meta.apply(
        lambda r: round(r['venta'] / r['venta_meta'] * 100, 1) if r['venta_meta'] else 0, axis=1)
    comp_meta['cumpl_util_%'] = comp_meta.apply(
        lambda r: round(r['util_bruta'] / r['util_meta'] * 100, 1) if r['util_meta'] else 0, axis=1)
    comp_meta['gap_venta'] = comp_meta['venta'] - comp_meta['venta_meta']
    comp_meta['gap_util']  = comp_meta['util_bruta'] - comp_meta['util_meta']

    sin_meta = (comp_meta[['venta_meta', 'util_meta']].sum().sum() == 0)
    if sin_meta:
        st.info('💡 Aún no has cargado el presupuesto. Abre el editor arriba y define las metas.')
    else:
        # KPIs de cumplimiento agregados
        total_venta_meta = comp_meta['venta_meta'].sum()
        total_util_meta  = comp_meta['util_meta'].sum()
        total_venta_real = comp_meta['venta'].sum()
        total_util_real  = comp_meta['util_bruta'].sum()
        cumpl_v = (total_venta_real / total_venta_meta * 100) if total_venta_meta else 0
        cumpl_u = (total_util_real  / total_util_meta  * 100) if total_util_meta  else 0
        gap_v = total_venta_real - total_venta_meta
        gap_u = total_util_real  - total_util_meta

        # Color por nivel de cumplimiento (semáforo)
        def _color(p):
            if p >= 100: return '#4CAF50'   # verde: logrado
            if p >= 90:  return '#FFC107'   # amarillo: cerca
            return '#EF5350'                # rojo: lejos

        cm1, cm2, cm3, cm4 = st.columns(4)
        with cm1: st.markdown(kpi_html(f'{cumpl_v:.1f}%', '🎯 Cumpl. Venta', val_color=_color(cumpl_v), bg=CARD2), unsafe_allow_html=True)
        with cm2: st.markdown(kpi_html(fmt_currency(gap_v), 'Δ Venta vs Meta', val_color=('#4CAF50' if gap_v >= 0 else '#EF5350'), bg=CARD2), unsafe_allow_html=True)
        with cm3: st.markdown(kpi_html(f'{cumpl_u:.1f}%', '🎯 Cumpl. Utilidad', val_color=_color(cumpl_u), bg=CARD2), unsafe_allow_html=True)
        with cm4: st.markdown(kpi_html(fmt_currency(gap_u), 'Δ Utilidad vs Meta', val_color=('#4CAF50' if gap_u >= 0 else '#EF5350'), bg=CARD2), unsafe_allow_html=True)

        # Tabla detallada
        st.markdown('<br>', unsafe_allow_html=True)
        meta_disp = comp_meta[['periodo','venta_meta','venta','gap_venta','cumpl_venta_%',
                               'util_meta','util_bruta','gap_util','cumpl_util_%']].copy()
        meta_fmt = summary_table(
            meta_disp,
            money_cols=['venta_meta','venta','gap_venta','util_meta','util_bruta','gap_util'],
            pct_cols=['cumpl_venta_%','cumpl_util_%'],
        )
        meta_fmt = meta_fmt.rename(columns={
            'periodo':'Período',
            'venta_meta':'Venta Meta', 'venta':'Venta Real', 'gap_venta':'Δ Venta', 'cumpl_venta_%':'Cumpl. Venta',
            'util_meta':'Util. Meta', 'util_bruta':'Util. Real', 'gap_util':'Δ Util.', 'cumpl_util_%':'Cumpl. Util.',
        })
        styled_table(meta_fmt)

        # Gráfico de cumplimiento por período
        st.markdown('<br>', unsafe_allow_html=True)
        fig_m = go.Figure()
        fig_m.add_trace(go.Bar(
            x=comp_meta['periodo'], y=comp_meta['venta_meta'], name='Meta Venta',
            marker_color='rgba(96,125,139,.45)',
            text=comp_meta['venta_meta'].apply(fmt_currency), textposition='outside',
            textfont=dict(color='#90A4AE')))
        fig_m.add_trace(go.Bar(
            x=comp_meta['periodo'], y=comp_meta['venta'], name='Venta Real',
            marker_color='#1565C0',
            text=comp_meta['venta'].apply(fmt_currency), textposition='outside',
            textfont=dict(color='white')))
        fig_m.add_trace(go.Scatter(
            x=comp_meta['periodo'], y=comp_meta['cumpl_venta_%'], name='Cumplimiento %',
            mode='lines+markers+text', line=dict(color='#F57F17', width=2.5),
            marker=dict(size=10), yaxis='y2',
            text=comp_meta['cumpl_venta_%'].apply(lambda x: f'{x:.0f}%'),
            textposition='top center', textfont=dict(color='#F57F17', size=11)))
        # Línea horizontal en 100%
        fig_m.add_shape(type='line', xref='paper', x0=0, x1=1,
                        y0=100, y1=100, yref='y2',
                        line=dict(color='#FFD54F', dash='dash', width=1.5))
        fig_m.update_layout(
            barmode='group',
            yaxis=dict(showticklabels=False),
            yaxis2=dict(overlaying='y', side='right', range=[0, max(150, comp_meta['cumpl_venta_%'].max() + 15)],
                        title='Cumplimiento %', tickfont=dict(color='#F57F17'),
                        titlefont=dict(color='#F57F17')),
            legend=dict(font=dict(color='white'), x=0.3, y=1.15, orientation='h'),
        )
        st.plotly_chart(dark_chart(fig_m, 420), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#   4. ANÁLISIS ABC / PARETO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('---')
st.markdown(section_title('🎯 Análisis ABC / Pareto (concentración 80/20)'), unsafe_allow_html=True)

DIM_OPTS = {
    'Cliente':         'razon_social',
    'Canal de Venta':  'canal_ventas',
    'Punto de Venta':  'desc_co',
    'Producto':        'desc_item',
    'Familia':         'familia',
}
fc1, fc2 = st.columns([2, 1])
with fc1:
    dim_label = st.selectbox('Analizar concentración por:', list(DIM_OPTS.keys()))
with fc2:
    metric = st.radio('Métrica:', ['Venta', 'Utilidad'], horizontal=True, key='abc_metric')
dim = DIM_OPTS[dim_label]

df['_util'] = df['valor_subtotal'] - df['costo_promedio_total']
val_col = '_util' if metric == 'Utilidad' else 'valor_subtotal'

pareto = (df.groupby(dim).agg(valor=(val_col, 'sum')).reset_index())
pareto = pareto[pareto[dim].fillna('').astype(str).str.strip() != '']
pareto = pareto.sort_values('valor', ascending=False).reset_index(drop=True)
total_p = pareto['valor'].sum()
if total_p != 0:
    pareto['pct']      = (pareto['valor'] / total_p * 100).round(2)
    pareto['pct_acum'] = pareto['pct'].cumsum().round(2)
    pareto['clase']    = pd.cut(pareto['pct_acum'], bins=[-0.01, 80, 95, 100.01],
                                labels=['A', 'B', 'C'])

    n_a = int((pareto['clase'] == 'A').sum())
    n_b = int((pareto['clase'] == 'B').sum())
    n_c = int((pareto['clase'] == 'C').sum())
    total_n = len(pareto)
    pct_a_share = (n_a / total_n * 100) if total_n else 0

    ka, kb, kc, kd = st.columns(4)
    with ka: st.markdown(kpi_html(str(n_a), '🟢 Clase A · 0-80%',  val_color='#4CAF50', bg='#0D2137'), unsafe_allow_html=True)
    with kb: st.markdown(kpi_html(str(n_b), '🟡 Clase B · 80-95%', val_color='#FFC107', bg='#0D2137'), unsafe_allow_html=True)
    with kc: st.markdown(kpi_html(str(n_c), '🔴 Clase C · 95-100%', val_color='#EF5350', bg='#0D2137'), unsafe_allow_html=True)
    with kd: st.markdown(kpi_html(f'{pct_a_share:.1f}%', f'{n_a}/{total_n} = 80% del valor', val_color='#80DEEA', bg='#0D2137'), unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 4])
    with col_l:
        st.markdown(section_title(f'Top 20 — {dim_label}'), unsafe_allow_html=True)
        top20 = pareto.head(20).copy()
        top20_disp = top20.copy()
        top20_disp['valor']    = top20_disp['valor'].apply(fmt_currency)
        top20_disp['pct']      = top20_disp['pct'].astype(str) + '%'
        top20_disp['pct_acum'] = top20_disp['pct_acum'].astype(str) + '%'
        top20_disp = top20_disp.rename(columns={
            dim: dim_label, 'valor': metric, 'pct': '%',
            'pct_acum': '% Acum', 'clase': 'Clase',
        })
        styled_table(top20_disp, max_height=560)

    with col_r:
        st.markdown(section_title(f'Curva de Pareto · Top 30'), unsafe_allow_html=True)
        top30 = pareto.head(30).copy()
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(
            x=top30[dim], y=top30['valor'], name=metric,
            marker_color='#1565C0', yaxis='y'))
        fig_p.add_trace(go.Scatter(
            x=top30[dim], y=top30['pct_acum'], name='% Acumulado',
            mode='lines+markers', line=dict(color='#F57F17', width=2.5),
            marker=dict(size=8), yaxis='y2'))
        # Línea horizontal en 80%
        fig_p.add_shape(type='line', xref='paper', x0=0, x1=1,
                        y0=80, y1=80, yref='y2',
                        line=dict(color='#E1BEE7', dash='dash', width=2))
        fig_p.update_layout(
            yaxis=dict(showticklabels=False),
            yaxis2=dict(overlaying='y', side='right', range=[0, 105],
                        tickfont=dict(color='#F57F17'),
                        title='% Acum', titlefont=dict(color='#F57F17')),
            xaxis=dict(tickangle=40, showticklabels=False),
            legend=dict(font=dict(color='white'), x=0.35, y=1.12, orientation='h'),
        )
        st.plotly_chart(dark_chart(fig_p, 560), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#   4. IMPUESTOS POR CANAL
# ══════════════════════════════════════════════════════════════════════════════
if 'valor_impuestos' in df.columns and df['valor_impuestos'].sum() > 0:
    st.markdown('---')
    st.markdown(section_title('🧾 Análisis de Impuestos por Canal'), unsafe_allow_html=True)

    imp = (df.groupby('canal_ventas')
             .agg(venta     =('valor_subtotal', 'sum'),
                  impuestos =('valor_impuestos', 'sum'))
             .reset_index())
    imp['tasa_efectiva_%'] = (imp['impuestos'] / imp['venta'] * 100).round(2)
    imp = imp.sort_values('impuestos', ascending=False)

    col_l, col_r = st.columns([3, 2])
    with col_l:
        ims = imp.sort_values('impuestos', ascending=True)
        fig_i = go.Figure(go.Bar(
            x=ims['impuestos'], y=ims['canal_ventas'], orientation='h',
            text=ims['impuestos'].apply(fmt_currency), textposition='outside',
            marker=dict(color=ims['tasa_efectiva_%'],
                        colorscale=[[0, '#1565C0'], [0.5, '#7B1FA2'], [1, '#EF5350']],
                        showscale=True,
                        colorbar=dict(title='Tasa %', thickness=10,
                                      tickfont=dict(color='white'),
                                      titlefont=dict(color='white')))))
        st.plotly_chart(dark_chart(fig_i, 420), use_container_width=True)

    with col_r:
        st.markdown(section_title('Detalle'), unsafe_allow_html=True)
        imp_disp = summary_table(imp, money_cols=['venta', 'impuestos'], pct_cols=['tasa_efectiva_%'])
        imp_disp = imp_disp.rename(columns={
            'canal_ventas': 'Canal', 'venta': 'Venta',
            'impuestos': 'Impuestos', 'tasa_efectiva_%': 'Tasa Efectiva',
        })
        styled_table(imp_disp, max_height=420)

# ══════════════════════════════════════════════════════════════════════════════
#   5. DEVOLUCIONES Y ANULACIONES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('---')
st.markdown(section_title('↩️ Devoluciones y Anulaciones'), unsafe_allow_html=True)

if 'desc_motivo' in df.columns and dev_mask.any():
    dev = df.loc[dev_mask].copy()
    dev_g = (dev.groupby('desc_motivo')
                .agg(valor    =('valor_subtotal', 'sum'),
                     facturas =('nro_documento', 'nunique') if 'nro_documento' in dev.columns else ('valor_subtotal', 'count'),
                     unidades =('cantidad', 'sum'))
                .reset_index())
    dev_g['pct_venta_%'] = (dev_g['valor'].abs() / venta_neta * 100).round(2)
    dev_g = dev_g.sort_values('valor', ascending=True)
    dev_disp = summary_table(dev_g, money_cols=['valor'], pct_cols=['pct_venta_%'])
    dev_disp = dev_disp.rename(columns={
        'desc_motivo':'Motivo', 'valor':'Valor', 'facturas':'Facturas',
        'unidades':'Unidades', 'pct_venta_%':'% s/Venta',
    })
    styled_table(dev_disp)

    # Por canal: dónde se dan más devoluciones
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(section_title('Devoluciones por Canal'), unsafe_allow_html=True)
    dev_can = (dev.groupby('canal_ventas')
                  .agg(valor=('valor_subtotal','sum'),
                       facturas=('nro_documento','nunique') if 'nro_documento' in dev.columns else ('valor_subtotal','count'))
                  .reset_index().sort_values('valor', ascending=True))
    fig_dc = go.Figure(go.Bar(
        x=dev_can['valor'].abs(), y=dev_can['canal_ventas'], orientation='h',
        text=dev_can['valor'].abs().apply(fmt_currency), textposition='outside',
        marker_color='#FFAB91'))
    st.plotly_chart(dark_chart(fig_dc, 360), use_container_width=True)
else:
    st.info('No se registran devoluciones ni anulaciones en el período seleccionado.')

# ══════════════════════════════════════════════════════════════════════════════
#   6. TICKET PROMEDIO
# ══════════════════════════════════════════════════════════════════════════════
if 'nro_documento' in df.columns:
    st.markdown('---')
    st.markdown(section_title('🎫 Ticket Promedio'), unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(section_title('Por Canal'), unsafe_allow_html=True)
        tc = (df.groupby('canal_ventas')
                .agg(venta=('valor_subtotal','sum'),
                     facturas=('nro_documento','nunique'))
                .reset_index())
        tc['ticket'] = (tc['venta'] / tc['facturas']).round(0)
        tc = tc.sort_values('ticket', ascending=False)
        tcs = tc.sort_values('ticket', ascending=True)
        fig_tc = go.Figure(go.Bar(
            x=tcs['ticket'], y=tcs['canal_ventas'], orientation='h',
            text=tcs['ticket'].apply(fmt_currency), textposition='outside',
            marker_color='#00838F'))
        st.plotly_chart(dark_chart(fig_tc, 400), use_container_width=True)

    with col_r:
        st.markdown(section_title('Por Punto de Venta'), unsafe_allow_html=True)
        tp = (df.groupby(['co','desc_co'])
                .agg(venta=('valor_subtotal','sum'),
                     facturas=('nro_documento','nunique'))
                .reset_index())
        tp['ticket'] = (tp['venta'] / tp['facturas']).round(0)
        tp = tp.sort_values('ticket', ascending=False)
        tps = tp.sort_values('ticket', ascending=True)
        fig_tp = go.Figure(go.Bar(
            x=tps['ticket'], y=tps['desc_co'], orientation='h',
            text=tps['ticket'].apply(fmt_currency), textposition='outside',
            marker_color='#4DB6AC'))
        st.plotly_chart(dark_chart(fig_tp, 400), use_container_width=True)

st.markdown(f"""<div style="text-align:center;color:#546E7A;font-size:.74rem;margin-top:20px;
padding:10px;border-top:1px solid rgba(21,101,192,.13)">
📊 ABAD · {label} · Documento Confidencial</div>""", unsafe_allow_html=True)
