"""
Acceso a Postgres directo mediante psycopg (Neon / Postgres local / cualquier Postgres).
Antes usaba la API REST de Supabase; ahora se conecta por SQL directo.

Configuración (en .env local o en Secrets de Streamlit Cloud):
    DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
o, alternativamente, variables sueltas:
    DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

Las funciones públicas conservan la misma firma que antes, así que el resto
de la app (app.py, pages/*, ui.py) no cambia.
"""
import os
import math
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Compatibilidad: constantes que algún módulo podría importar (ya no se usan).
PAGE_SIZE      = 5000
PARALLEL_PAGES = 16


# ── Conexión ──────────────────────────────────────────────────────────────────

def _conninfo() -> str:
    """Cadena de conexión: prioriza DATABASE_URL (Neon), luego variables sueltas."""
    url = os.getenv('DATABASE_URL', '').strip()
    if url:
        return url
    host = os.getenv('DB_HOST', '').strip()
    if not host:
        return ''
    name = os.getenv('DB_NAME', 'postgres').strip()
    user = os.getenv('DB_USER', 'postgres').strip()
    pwd  = os.getenv('DB_PASSWORD', '').strip()
    port = os.getenv('DB_PORT', '5432').strip()
    return f"host={host} dbname={name} user={user} password={pwd} port={port} sslmode=require"


def _connect():
    """Abre una conexión psycopg. Import perezoso para no exigir psycopg al importar."""
    import psycopg  # noqa: import perezoso
    ci = _conninfo()
    if not ci:
        raise RuntimeError(
            'No hay conexión configurada. Define DATABASE_URL (Neon) en el .env '
            'local o en los Secrets de Streamlit Cloud.'
        )
    return psycopg.connect(ci, connect_timeout=20)


def _query_df(sql: str, params=None) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve un DataFrame."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description is None:
                return pd.DataFrame()
            cols = [d[0] for d in cur.description]
            data = cur.fetchall()
    return pd.DataFrame(data, columns=cols)


def _clean_rows(df: pd.DataFrame):
    """
    Prepara un DataFrame para INSERT: fecha→date, co/anio→int, NaN/NaT→None.
    Devuelve (columnas, lista_de_tuplas).
    """
    out = df.copy()
    if 'fecha' in out.columns:
        out['fecha'] = pd.to_datetime(out['fecha'], errors='coerce')
        out['fecha'] = out['fecha'].apply(lambda x: x.date() if pd.notnull(x) else None)
    for col in ('co', 'anio', 'dia_semana'):
        if col in out.columns:
            s = pd.to_numeric(out[col], errors='coerce')
            out[col] = s.apply(lambda x: int(x) if pd.notnull(x) else None)
    # NaN/NaT → None
    out = out.astype(object).where(pd.notnull(out), None)
    cols = list(out.columns)
    rows = [tuple(r) for r in out.to_numpy()]
    return cols, rows


# ── Credenciales ──────────────────────────────────────────────────────────────

def is_configured() -> bool:
    load_dotenv()
    return bool(_conninfo())


def save_credentials(database_url: str, _unused=None):
    """Guarda DATABASE_URL en el .env local. (_unused: compatibilidad de firma)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith(('DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_KEY')):
                    lines.append(line)
    lines.append(f'DATABASE_URL={database_url.strip()}\n')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    load_dotenv(override=True)


# ── Lectura ───────────────────────────────────────────────────────────────────

def fetch_ventas(mes: str = None, anio: int = None, columns: str = '*') -> pd.DataFrame:
    """Descarga ventas filtradas por mes/anio. `columns` es una lista separada por comas."""
    sql = f"SELECT {columns} FROM ventas"
    where, params = [], []
    if mes:
        where.append('mes = %s'); params.append(mes)
    if anio:
        where.append('anio = %s'); params.append(int(anio))
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    return _query_df(sql, params)


_MES_ORDER = {m: i for i, m in enumerate(
    ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
     'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'])}


def _sort_periodos(rows: list) -> list:
    def _key(r):
        return (int(r.get('anio', 0)),
                _MES_ORDER.get(str(r.get('mes', '')).upper(), 99))
    return sorted(rows, key=_key)


def fetch_periodos() -> list:
    """Períodos únicos (mes, anio) ordenados cronológicamente."""
    try:
        df = _query_df('SELECT DISTINCT mes, anio FROM ventas')
    except Exception:
        return []
    if df.empty:
        return []
    recs = [{'mes': r['mes'], 'anio': r['anio']} for r in df.to_dict('records')]
    return _sort_periodos(recs)


def fetch_items() -> pd.DataFrame:
    try:
        return _query_df('SELECT * FROM items_referencia')
    except Exception:
        return pd.DataFrame()


def fetch_happy_docs() -> set:
    """Conjunto de nro_documento marcados como HAPPY (es_happy = true)."""
    try:
        df = _query_df('SELECT nro_documento FROM factura_horas WHERE es_happy = true')
    except Exception:
        return set()
    if df.empty:
        return set()
    return set(df['nro_documento'].astype(str).str.strip())


def horas_disponibles() -> int:
    """Cuántas filas hay en factura_horas (0 si no existe la tabla)."""
    try:
        df = _query_df('SELECT count(*) AS n FROM factura_horas')
        return int(df['n'].iloc[0]) if not df.empty else 0
    except Exception:
        return 0


def fetch_presupuestos() -> dict:
    """{(mes, anio): {'venta_meta':..., 'util_meta':...}}."""
    try:
        df = _query_df('SELECT mes, anio, venta_meta, util_meta FROM presupuestos')
    except Exception:
        return {}
    out = {}
    for r in df.to_dict('records'):
        mes = str(r['mes']).strip().upper()
        try:
            anio = int(r['anio'])
        except (ValueError, TypeError):
            continue
        out[(mes, anio)] = {
            'venta_meta': float(r['venta_meta'] or 0),
            'util_meta':  float(r['util_meta']  or 0),
        }
    return out


# ── Escritura ─────────────────────────────────────────────────────────────────

def upsert_presupuestos(records: list) -> None:
    clean = []
    for r in records:
        mes = str(r.get('mes', '')).strip().upper()
        try:
            anio = int(r.get('anio'))
        except (ValueError, TypeError):
            continue
        if not mes:
            continue
        clean.append((mes, anio, float(r.get('venta_meta') or 0), float(r.get('util_meta') or 0)))
    if not clean:
        return
    sql = ("INSERT INTO presupuestos (mes, anio, venta_meta, util_meta) "
           "VALUES (%s, %s, %s, %s) "
           "ON CONFLICT (mes, anio) DO UPDATE SET "
           "venta_meta = EXCLUDED.venta_meta, util_meta = EXCLUDED.util_meta")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, clean)
        conn.commit()


def insert_ventas(df: pd.DataFrame, mes: str, anio: int, progress_cb=None):
    """Borra el mes/anio y reinserta (reemplazo limpio del período)."""
    cols, rows = _clean_rows(df)
    collist = ', '.join(cols)
    ph      = ', '.join(['%s'] * len(cols))
    sql     = f"INSERT INTO ventas ({collist}) VALUES ({ph})"
    total   = len(rows)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM ventas WHERE mes = %s AND anio = %s', (mes, int(anio)))
            batch = 1000
            for i in range(0, total, batch):
                cur.executemany(sql, rows[i:i + batch])
                if progress_cb:
                    progress_cb(min((i + batch) / total, 1.0) if total else 1.0)
        conn.commit()


def upsert_items(items_df: pd.DataFrame):
    df = items_df.copy()
    df['referencia'] = df['referencia'].astype(str).str.strip()
    df = df[~df['referencia'].isin(['', 'nan', 'None', 'NaN', 'none'])]
    df = df.drop_duplicates(subset='referencia', keep='last')
    cols, rows = _clean_rows(df)
    collist = ', '.join(cols)
    ph      = ', '.join(['%s'] * len(cols))
    sets    = ', '.join(f'{c} = EXCLUDED.{c}' for c in cols if c != 'referencia')
    sql     = (f"INSERT INTO items_referencia ({collist}) VALUES ({ph}) "
               f"ON CONFLICT (referencia) DO UPDATE SET {sets}")
    with _connect() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), 1000):
                cur.executemany(sql, rows[i:i + 1000])
        conn.commit()


def upsert_horas(horas_df: pd.DataFrame, progress_cb=None) -> dict:
    """
    Reemplazo por mes: borra los meses presentes en el archivo y reinserta.
    Devuelve {filas_subidas, meses_borrados, happy}.
    """
    df = horas_df.copy()
    df['nro_documento'] = df['nro_documento'].astype(str).str.strip()
    df = df[~df['nro_documento'].isin(['', 'nan', 'None', 'NaN', 'none'])]
    df = df.drop_duplicates(subset='nro_documento', keep='last')

    fechas = pd.to_datetime(df['fecha'], errors='coerce').dropna()
    months = sorted({(d.year, d.month) for d in fechas}) if not fechas.empty else []

    cols, rows = _clean_rows(df)
    collist = ', '.join(cols)
    ph      = ', '.join(['%s'] * len(cols))
    sets    = ', '.join(f'{c} = EXCLUDED.{c}' for c in cols if c != 'nro_documento')
    sql     = (f"INSERT INTO factura_horas ({collist}) VALUES ({ph}) "
               f"ON CONFLICT (nro_documento) DO UPDATE SET {sets}")

    meses_borrados = []
    total = len(rows)
    with _connect() as conn:
        with conn.cursor() as cur:
            for (yr, mo) in months:
                ny, nm = (yr + 1, 1) if mo == 12 else (yr, mo + 1)
                cur.execute(
                    'DELETE FROM factura_horas WHERE fecha >= %s AND fecha < %s',
                    (f'{yr:04d}-{mo:02d}-01', f'{ny:04d}-{nm:02d}-01'))
                meses_borrados.append(f'{mo:02d}/{yr}')
            batch = 1000
            for i in range(0, total, batch):
                cur.executemany(sql, rows[i:i + batch])
                if progress_cb:
                    progress_cb(min((i + batch) / total, 1.0) if total else 1.0)
        conn.commit()

    happy = int(df['es_happy'].sum()) if 'es_happy' in df.columns else 0
    return {'filas_subidas': total, 'meses_borrados': meses_borrados, 'happy': happy}


# ── Diagnóstico de conexión ───────────────────────────────────────────────────

def test_connection() -> tuple:
    """Devuelve (ok: bool, mensaje: str). Útil para la página de configuración."""
    try:
        df = _query_df('SELECT version()')
        ver = str(df.iloc[0, 0])[:60] if not df.empty else 'OK'
        return True, f'Conexión exitosa · {ver}'
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'
