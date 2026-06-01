"""
Acceso a Supabase mediante urllib (librería estándar de Python).
Optimizado para volumen alto:
  · fetch_periodos → RPC SQL (instantáneo) con fallback a scan
  · fetch_ventas   → paginación PARALELA usando Content-Range para saber el total
"""
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_TIMEOUT       = 30
_TIMEOUT_LONG  = 120
PAGE_SIZE      = 5000   # filas por request — Supabase permite hasta 1000 por defecto pero acepta más con Range
PARALLEL_PAGES = 16     # peticiones simultáneas para descargar páginas


# ── Helpers internos ──────────────────────────────────────────────────────────

def _base(table: str) -> str:
    url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    return f'{url}/rest/v1/{table}'


def _hdr(extra: dict = None) -> dict:
    key = os.getenv('SUPABASE_KEY', '').strip()
    h = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    if extra:
        h.update(extra)
    return h


def _get(table: str, params: dict, range_hdr: str = None) -> list:
    """GET simple — devuelve solo data."""
    query    = urllib.parse.urlencode(params)
    full_url = f'{_base(table)}?{query}'
    extra    = {}
    if range_hdr:
        extra.update({'Range': range_hdr, 'Range-Unit': 'items', 'Prefer': 'count=none'})
    req = urllib.request.Request(full_url, headers=_hdr(extra))
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                "Tablas no encontradas en Supabase. "
                "Ve a 📥 Importar Data → '🗄️ Crear tablas' y ejecuta el SQL."
            ) from e
        raise


def _get_with_count(table: str, params: dict, range_hdr: str):
    """GET con Prefer: count=exact — devuelve (rows, total_count)."""
    query    = urllib.parse.urlencode(params)
    full_url = f'{_base(table)}?{query}'
    headers  = _hdr({'Range': range_hdr, 'Range-Unit': 'items', 'Prefer': 'count=exact'})
    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            # Content-Range: "0-999/12345"
            cr = resp.headers.get('Content-Range', '')
            total = None
            if '/' in cr:
                tail = cr.split('/')[-1]
                if tail != '*':
                    try:
                        total = int(tail)
                    except ValueError:
                        total = None
            return data, total
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                "Tablas no encontradas en Supabase. "
                "Ve a 📥 Importar Data → '🗄️ Crear tablas' y ejecuta el SQL."
            ) from e
        raise


def _rpc(function_name: str, params: dict = None) -> list:
    """Llama a una Postgres function vía PostgREST /rpc/."""
    url  = _base(f'rpc/{function_name}')
    body = json.dumps(params or {}).encode('utf-8')
    req  = urllib.request.Request(url, data=body, headers=_hdr(), method='POST')
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _post(table: str, records: list, prefer: str = 'return=minimal') -> None:
    body = json.dumps(records, default=str).encode('utf-8')
    headers = _hdr({'Prefer': prefer})
    req = urllib.request.Request(
        _base(table), data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=_TIMEOUT_LONG):
        pass


def _delete(table: str, params: dict) -> None:
    query    = urllib.parse.urlencode(params)
    full_url = f'{_base(table)}?{query}'
    req = urllib.request.Request(full_url, headers=_hdr(), method='DELETE')
    with urllib.request.urlopen(req, timeout=_TIMEOUT):
        pass


# ── Credenciales ──────────────────────────────────────────────────────────────

def is_configured() -> bool:
    load_dotenv()
    return bool(os.getenv('SUPABASE_URL', '').strip()
                and os.getenv('SUPABASE_KEY', '').strip())


def save_credentials(url: str, key: str):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith(('SUPABASE_URL', 'SUPABASE_KEY')):
                    lines.append(line)
    lines += [f'SUPABASE_URL={url.strip()}\n', f'SUPABASE_KEY={key.strip()}\n']
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    load_dotenv(override=True)


# ── Lectura optimizada ────────────────────────────────────────────────────────

def fetch_ventas(mes: str = None, anio: int = None,
                 columns: str = '*') -> pd.DataFrame:
    """
    Descarga ventas con paginación PARALELA.

    Estrategia:
      1. Pide la primera página + total (Content-Range con Prefer: count=exact)
      2. Si hay más, calcula los offsets restantes y descarga en paralelo
      3. Concatena y devuelve DataFrame
    """
    params = {'select': columns}
    if mes:
        params['mes'] = f'eq.{mes}'
    if anio:
        params['anio'] = f'eq.{int(anio)}'

    # 1. Primera página + total
    first_page, total = _get_with_count(
        'ventas', params, range_hdr=f'0-{PAGE_SIZE - 1}')

    if not first_page:
        return pd.DataFrame()

    actual_size = len(first_page)

    # Si Supabase no devolvió total (header faltante), caemos a paginación secuencial
    if total is None:
        rows = list(first_page)
        offset = actual_size
        while True:
            page = _get('ventas', params,
                        range_hdr=f'{offset}-{offset + actual_size - 1}')
            if not page:
                break
            rows.extend(page)
            if len(page) < actual_size:
                break
            offset += actual_size
        return pd.DataFrame(rows)

    # Si ya recibimos todo
    if actual_size >= total:
        return pd.DataFrame(first_page)

    # 2. Descarga PARALELA del resto
    offsets = list(range(actual_size, total, actual_size))

    def _fetch_chunk(off: int) -> list:
        end = min(off + actual_size - 1, total - 1)
        try:
            return _get('ventas', params, range_hdr=f'{off}-{end}')
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=PARALLEL_PAGES) as ex:
        chunks = list(ex.map(_fetch_chunk, offsets))

    all_rows = list(first_page)
    for chunk in chunks:
        all_rows.extend(chunk)

    return pd.DataFrame(all_rows)


_MES_ORDER = {m: i for i, m in enumerate(
    ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
     'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'])}


def _sort_periodos(rows: list) -> list:
    """Ordena por (anio, mes-numérico) — el SQL ORDER BY mes ordena alfabético."""
    def _key(r):
        return (int(r.get('anio', 0)),
                _MES_ORDER.get(str(r.get('mes', '')).upper(), 99))
    return sorted(rows, key=_key)


def fetch_periodos() -> list:
    """
    Obtiene períodos únicos. Intenta primero la RPC (instantánea);
    si no existe, hace fallback a scan paginado.
    """
    # 1. Intento rápido: RPC SQL
    try:
        rows = _rpc('get_periodos')
        if rows:
            return _sort_periodos(rows)
    except Exception:
        pass  # fallback abajo

    # 2. Fallback: scan paginado. CRÍTICO: Supabase puede capar el tamaño
    #    de página (default 1000) aunque pidamos más. Si pedimos 5000 y nos
    #    devuelve 1000, NO podemos asumir que se acabaron los datos.
    #    Usamos el tamaño real devuelto en la primera página.
    seen, result = set(), []
    first = _get('ventas', {'select': 'mes,anio', 'order': 'anio.asc,mes.asc'},
                 range_hdr=f'0-{PAGE_SIZE - 1}')
    if not first:
        return []

    actual_size = len(first)
    for r in first:
        k = (r.get('mes', ''), r.get('anio', 0))
        if k not in seen:
            seen.add(k)
            result.append({'mes': r['mes'], 'anio': r['anio']})

    # Si la primera página vino "llena" (== tamaño real devuelto), seguimos
    offset = actual_size
    while True:
        page = _get('ventas', {'select': 'mes,anio', 'order': 'anio.asc,mes.asc'},
                    range_hdr=f'{offset}-{offset + actual_size - 1}')
        if not page:
            break
        for r in page:
            k = (r.get('mes', ''), r.get('anio', 0))
            if k not in seen:
                seen.add(k)
                result.append({'mes': r['mes'], 'anio': r['anio']})
        if len(page) < actual_size:
            break
        offset += actual_size

    if not result:
        return []
    order = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
             'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    df = pd.DataFrame(result)
    df['_ord'] = df['mes'].map({m: i for i, m in enumerate(order)})
    df = df.sort_values(['anio', '_ord'])
    return df[['mes', 'anio']].to_dict('records')


def fetch_items() -> pd.DataFrame:
    rows = _get('items_referencia', {'select': '*'})
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_happy_docs() -> set:
    """Devuelve el conjunto de nro_documento marcados como HAPPY (es_happy=true)."""
    docs, offset, size = set(), 0, 1000
    while True:
        try:
            page = _get('factura_horas',
                        {'select': 'nro_documento', 'es_happy': 'eq.true'},
                        range_hdr=f'{offset}-{offset + size - 1}')
        except Exception:
            return docs
        if not page:
            break
        for r in page:
            d = str(r.get('nro_documento', '')).strip()
            if d:
                docs.add(d)
        if len(page) < size:
            break
        offset += size
    return docs


def fetch_presupuestos() -> dict:
    """Devuelve {(mes, anio): {'venta_meta':..., 'util_meta':...}}."""
    try:
        rows = _get('presupuestos', {'select': 'mes,anio,venta_meta,util_meta'})
    except Exception:
        return {}
    out = {}
    for r in rows or []:
        mes = str(r.get('mes', '')).strip().upper()
        try:
            anio = int(r.get('anio'))
        except (ValueError, TypeError):
            continue
        out[(mes, anio)] = {
            'venta_meta': float(r.get('venta_meta') or 0),
            'util_meta':  float(r.get('util_meta')  or 0),
        }
    return out


def upsert_presupuestos(records: list) -> None:
    """records = [{'mes':'MAYO','anio':2026,'venta_meta':...,'util_meta':...}, ...]"""
    if not records:
        return
    clean = []
    for r in records:
        mes = str(r.get('mes', '')).strip().upper()
        try:
            anio = int(r.get('anio'))
        except (ValueError, TypeError):
            continue
        if not mes:
            continue
        clean.append({
            'mes': mes, 'anio': anio,
            'venta_meta': float(r.get('venta_meta') or 0),
            'util_meta':  float(r.get('util_meta')  or 0),
        })
    if not clean:
        return
    url = _base('presupuestos') + '?on_conflict=mes,anio'
    body = json.dumps(clean).encode('utf-8')
    req = urllib.request.Request(
        url, data=body,
        headers=_hdr({'Prefer': 'resolution=merge-duplicates,return=minimal'}),
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_LONG):
            pass
    except urllib.error.HTTPError as e:
        body_err = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Error Supabase {e.code}: {body_err}') from e


def horas_disponibles() -> int:
    """Cuántas filas hay en factura_horas (0 si no existe la tabla)."""
    try:
        _, total = _get_with_count('factura_horas', {'select': 'nro_documento'},
                                   range_hdr='0-0')
        return total or 0
    except Exception:
        return 0


# ── Escritura ─────────────────────────────────────────────────────────────────

def _prepare(df: pd.DataFrame) -> list:
    out = df.copy()
    if 'fecha' in out.columns:
        out['fecha'] = pd.to_datetime(out['fecha'], errors='coerce')
        out['fecha'] = out['fecha'].apply(
            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
    for col in ('co', 'anio'):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce').fillna(0).astype(int)
    out = out.where(pd.notnull(out), None)
    return out.to_dict('records')


def insert_ventas(df: pd.DataFrame, mes: str, anio: int,
                  progress_cb=None):
    _delete('ventas', {'mes': f'eq.{mes}', 'anio': f'eq.{anio}'})
    records = _prepare(df)
    batch, total = 500, len(records)
    for i in range(0, total, batch):
        _post('ventas', records[i:i + batch])
        if progress_cb:
            progress_cb(min((i + batch) / total, 1.0))


def upsert_items(items_df: pd.DataFrame):
    df = items_df.copy()
    df['referencia'] = df['referencia'].astype(str).str.strip()
    df = df[~df['referencia'].isin(['', 'nan', 'None', 'NaN', 'none'])]
    df = df.drop_duplicates(subset='referencia', keep='last')
    df = df.where(pd.notnull(df), None)
    records = df.to_dict('records')

    url = _base('items_referencia') + '?on_conflict=referencia'
    for i in range(0, len(records), 500):
        chunk = records[i:i + 500]
        body  = json.dumps(chunk, default=str).encode('utf-8')
        req   = urllib.request.Request(
            url, data=body,
            headers=_hdr({'Prefer': 'resolution=merge-duplicates,return=minimal'}),
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_LONG):
                pass
        except urllib.error.HTTPError as e:
            body_err = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Error Supabase {e.code}: {body_err}') from e


def _json_clean(v):
    """Convierte valores numpy/NaN/NA a tipos nativos JSON-safe (None, int, float, bool)."""
    import math
    import numpy as np
    if v is None:
        return None
    try:
        if v is pd.NA:
            return None
    except Exception:
        pass
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        f = float(v)
        return None if math.isnan(f) else f
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    return v


def upsert_horas(horas_df: pd.DataFrame, progress_cb=None) -> dict:
    """
    Sube horas a factura_horas con REEMPLAZO por mes (mismo comportamiento que
    insert_ventas): primero borra los meses presentes en el archivo, luego
    inserta. Así una anulación o corte distinto del mismo mes reemplaza limpio.
    Devuelve un dict con estadísticas: meses_borrados, filas_subidas, happy.
    """
    df = horas_df.copy()
    df['nro_documento'] = df['nro_documento'].astype(str).str.strip()
    df = df[~df['nro_documento'].isin(['', 'nan', 'None', 'NaN', 'none'])]
    df = df.drop_duplicates(subset='nro_documento', keep='last')

    # 1. Detectar meses presentes y borrarlos antes de insertar
    fechas = pd.to_datetime(df['fecha'], errors='coerce').dropna()
    meses_borrados = []
    if not fechas.empty:
        meses = sorted({(d.year, d.month) for d in fechas})
        for anio, mes in meses:
            next_anio, next_mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
            ini, fin = f'{anio:04d}-{mes:02d}-01', f'{next_anio:04d}-{next_mes:02d}-01'
            try:
                _delete('factura_horas', {'and': f'(fecha.gte.{ini},fecha.lt.{fin})'})
                meses_borrados.append(f'{mes:02d}/{anio}')
            except Exception:
                pass

    # 2. Limpiar a tipos nativos JSON-safe (evita NaN literal y numpy types)
    records = [{k: _json_clean(v) for k, v in rec.items()}
               for rec in df.to_dict('records')]
    for rec in records:
        if rec.get('co') is not None:
            try:
                rec['co'] = int(rec['co'])
            except (ValueError, TypeError):
                rec['co'] = 0

    # 3. Insertar (sigue siendo upsert por seguridad si quedaran restos)
    url = _base('factura_horas') + '?on_conflict=nro_documento'
    total = len(records)
    for i in range(0, total, 500):
        chunk = records[i:i + 500]
        body  = json.dumps(chunk).encode('utf-8')
        req   = urllib.request.Request(
            url, data=body,
            headers=_hdr({'Prefer': 'resolution=merge-duplicates,return=minimal'}),
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_LONG):
                pass
        except urllib.error.HTTPError as e:
            body_err = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Error Supabase {e.code}: {body_err}') from e
        if progress_cb:
            progress_cb(min((i + 500) / total, 1.0))

    happy_count = int(df['es_happy'].sum()) if 'es_happy' in df.columns else 0
    return {
        'filas_subidas':   total,
        'meses_borrados':  meses_borrados,
        'happy':           happy_count,
    }
