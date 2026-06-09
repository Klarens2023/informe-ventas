import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from utils.ui import DARK_CSS, minimal_sidebar, page_header

st.set_page_config(page_title='Importar Data · ABAD', page_icon='📥', layout='wide')
st.markdown(DARK_CSS, unsafe_allow_html=True)
minimal_sidebar()

page_header('📥 Importar y Procesar Data',
            'Empresa ABAD &nbsp;|&nbsp; Documento Confidencial')


def _cred_ok():
    load_dotenv()
    from utils.database import is_configured
    return is_configured()


# ── 1. Configuración de la base de datos (Neon / Postgres) ─────────────────────
with st.expander('⚙️ Configuración de la base de datos', expanded=not _cred_ok()):
    st.markdown(
        'Crea una base gratis en [neon.tech](https://neon.tech) → New Project. '
        'Copia la **Connection string** (Pooled connection) y pégala aquí. '
        'También funciona con cualquier Postgres (local o de otro proveedor).'
    )
    db_url = st.text_input(
        'Connection string (DATABASE_URL)',
        placeholder='postgresql://user:password@ep-xxxx-pooler.region.aws.neon.tech/dbname?sslmode=require',
        value=os.getenv('DATABASE_URL', ''),
        type='password',
    )
    cbtn1, cbtn2 = st.columns([1, 1])
    with cbtn1:
        if st.button('💾 Guardar conexión'):
            if db_url.strip():
                from utils.database import save_credentials
                save_credentials(db_url)
                load_dotenv(override=True)
                st.success('✅ Conexión guardada. Recarga la página.')
                st.rerun()
            else:
                st.error('Ingresa la connection string.')
    with cbtn2:
        if st.button('🔌 Probar conexión'):
            from utils.database import test_connection
            ok, msg = test_connection()
            (st.success if ok else st.error)(msg)


# ── 2. Crear tablas (solo primera vez) ─────────────────────────────────────────
with st.expander('🗄️ Crear tablas (solo primera vez)'):
    st.markdown('Copia el siguiente SQL y ejecútalo en el **SQL Editor de Neon** '
                '(o en `psql` si usas Postgres local):')
    sql = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setup_supabase.sql'), encoding='utf-8').read()
    st.code(sql, language='sql')

st.divider()

# ── 3. Cargar tabla ITEM ───────────────────────────────────────────────────────
st.subheader('1. Actualizar tabla de Items (Referencia)')
st.caption('Sube el Excel del informe para extraer la hoja ITEM. Solo necesitas hacerlo si cambiaron los ítems.')

item_file = st.file_uploader('Excel con hoja ITEM', type=['xlsx', 'xls'], key='item_file')
if item_file and st.button('🔄 Actualizar Items en BD'):
    if not _cred_ok():
        st.error('Primero configura las credenciales de Supabase.')
    else:
        try:
            from utils.processor import read_items_from_excel
            from utils.database import upsert_items
            items_df = read_items_from_excel(item_file)
            upsert_items(items_df)
            st.cache_data.clear()
            st.success(f'✅ {len(items_df)} ítems actualizados en la base de datos.')
        except Exception as e:
            st.error(f'Error: {e}')

st.divider()

# ── 3b. Archivo de horas (descuento HAPPY) ────────────────────────────────────
st.subheader('🕒 Archivo de horas (descuento HAPPY)')
st.caption('Sube el archivo "Ventas con hora" (cabecera de factura con la hora de '
           'aprobación). Se cruza con las ventas por Nro documento para identificar '
           'el HAPPY: miércoles 2:00–3:00 pm en los puntos de venta CO 002-006.')

horas_file = st.file_uploader('Excel "Ventas con hora"', type=['xlsx', 'xls'], key='horas_file')
if horas_file and st.button('🕒 Cargar horas a la BD'):
    if not _cred_ok():
        st.error('Primero configura las credenciales de Supabase.')
    else:
        try:
            from utils.processor import read_horas_from_excel
            from utils.database import upsert_horas
            with st.spinner('Leyendo archivo de horas...'):
                horas_df = read_horas_from_excel(horas_file)
            prog = st.progress(0.0, text='Subiendo a Supabase...')
            stats = upsert_horas(
                horas_df,
                progress_cb=lambda v: prog.progress(v, text=f'Subiendo... {v*100:.0f}%'),
            )
            prog.progress(1.0, text='✅ Completado')
            st.cache_data.clear()
            meses_txt = ', '.join(stats['meses_borrados']) or 'ninguno'
            st.success(
                f'✅ {stats["filas_subidas"]:,} facturas cargadas · '
                f'{stats["happy"]:,} marcadas como HAPPY (miércoles 2-3pm, CO 002-006).\n\n'
                f'🗑️ Meses reemplazados (limpios antes de insertar): **{meses_txt}**'
            )
        except Exception as e:
            st.error(f'Error cargando horas: {e}')

st.divider()

# ── 4. Importar datos del mes ──────────────────────────────────────────────────
st.subheader('2. Importar datos del mes')

col1, col2 = st.columns([2, 1])
with col1:
    data_file = st.file_uploader(
        'Archivo de ventas (TXT separado por tabulación o Excel)',
        type=['txt', 'csv', 'xlsx', 'xls'],
        key='data_file',
    )
with col2:
    st.info(
        '**El archivo reemplazará** todos los datos del mes detectado.\n\n'
        'Reglas que se aplican automáticamente:\n'
        '1. Eliminar subtotal = 0\n'
        '2-4. Reclasificar por ítem (Cuesta, Frescampo, Latti)\n'
        '5. CO 02-06 → Puntos de Venta\n'
        '6. CO 01 + Puntos → Otros Canales'
    )

if data_file:
    from utils.processor import read_file, process
    from utils.database import fetch_items, insert_ventas

    with st.spinner('Leyendo archivo...'):
        try:
            raw_df = read_file(data_file, data_file.name)
            st.success(f'Archivo leído: **{len(raw_df):,} filas**, {len(raw_df.columns)} columnas.')
        except Exception as e:
            st.error(f'Error leyendo archivo: {e}')
            st.stop()

    with st.spinner('Cargando tabla de ítems...'):
        try:
            items_df = fetch_items()
            if items_df.empty:
                st.warning('⚠️ Tabla ITEM vacía. Sube el Excel con la hoja ITEM (paso 1) antes de importar.')
        except Exception as e:
            st.warning(f'No se pudo cargar tabla ITEM: {e}. Se calcularán sin lookup.')
            items_df = pd.DataFrame(columns=['referencia','tipo','peso','tipo_leche'])

    with st.spinner('Aplicando reglas de transformación...'):
        try:
            processed_df, stats = process(raw_df, items_df)
        except Exception as e:
            st.error(f'Error procesando: {e}')
            st.stop()

    # Detectar mes/año
    mes_det  = processed_df['mes'].mode()[0] if not processed_df.empty else '?'
    anio_det = int(processed_df['anio'].mode()[0]) if not processed_df.empty else 0

    st.markdown(f'### Período detectado: **{mes_det} {anio_det}**')

    # Resumen de reglas
    st.subheader('Resumen de transformaciones')
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('Eliminadas (subtotal=0)', stats.get('eliminadas_subtotal_cero', 0))
    c2.metric('Reclasif. Cuesta', stats.get('reclasificadas_cuesta', 0))
    c3.metric('Reclasif. Frescampo', stats.get('reclasificadas_frescampo', 0))
    c4.metric('Reclasif. Latti', stats.get('reclasificadas_latti', 0))
    c5.metric('→ Puntos de Venta', stats.get('reclasificadas_a_puntos', 0))
    c6.metric('→ Otros Canales', stats.get('reclasificadas_a_otros', 0))

    st.metric('**Filas finales**', f"{stats.get('filas_finales', 0):,}")

    # Preview
    with st.expander('👁 Vista previa (primeras 100 filas)'):
        preview_cols = ['fecha', 'co', 'desc_co', 'desc_item', 'canal_ventas',
                        'valor_subtotal', 'margen_promedio', 'nombre_vendedor']
        show_cols = [c for c in preview_cols if c in processed_df.columns]
        st.dataframe(processed_df[show_cols].head(100), use_container_width=True)

    # Canal distribution after rules
    with st.expander('📊 Distribución de Canal de Ventas post-transformación'):
        dist = processed_df['canal_ventas'].value_counts().reset_index()
        dist.columns = ['Canal', 'Filas']
        st.dataframe(dist, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader('3. Guardar en base de datos')
    st.warning(
        f'⚠️ Esto **eliminará y reemplazará** todos los datos de **{mes_det} {anio_det}** '
        f'en la base de datos y cargará las {stats.get("filas_finales", 0):,} filas procesadas.'
    )

    if st.button(f'🚀 Importar {mes_det} {anio_det} a Supabase', type='primary'):
        if not _cred_ok():
            st.error('Configura las credenciales de Supabase primero.')
        else:
            progress = st.progress(0.0, text='Importando...')
            try:
                insert_ventas(
                    processed_df, mes_det, anio_det,
                    progress_cb=lambda v: progress.progress(v, text=f'Importando... {v*100:.0f}%'),
                )
                progress.progress(1.0, text='✅ Completado')
                st.success(f'✅ {stats.get("filas_finales", 0):,} filas importadas para {mes_det} {anio_det}.')
                st.cache_data.clear()
                st.session_state.pop('abad_periodos', None)
                st.balloons()
            except Exception as e:
                st.error(f'Error importando: {e}')
