-- ============================================================
-- ABAD · Informe de Ventas — Setup Supabase
-- Ejecutar en: Supabase → SQL Editor → New query → Run
-- ============================================================

-- Tabla principal de ventas
CREATE TABLE IF NOT EXISTS ventas (
    id                   BIGSERIAL PRIMARY KEY,
    mes                  TEXT,
    anio                 SMALLINT,
    fecha                DATE,
    co                   SMALLINT,
    desc_co              TEXT,
    cliente_factura      TEXT,
    razon_social         TEXT,
    sucursal_factura     TEXT,
    lista_precios        TEXT,
    categoria            TEXT,
    clases_clientes      TEXT,
    tipo_docto           TEXT,
    nro_documento        TEXT,
    item_num             TEXT,
    referencia           TEXT,
    desc_item            TEXT,
    desc_tipo_inventario TEXT,
    um_inv               TEXT,
    desc_motivo          TEXT,
    vendedor             TEXT,
    nombre_vendedor      TEXT,
    desc_ciudad          TEXT,
    cantidad             NUMERIC,
    desc_un              TEXT,
    volumen_ltr          NUMERIC,
    precio_unit          NUMERIC,
    valor_descuentos     NUMERIC,
    descuento_1          TEXT,
    descuento_2          TEXT,
    descuento_3          TEXT,
    dscto_promedio_pct   NUMERIC,
    valor_impuestos      NUMERIC,
    vlr_imp_ibua         NUMERIC,
    vlr_imp_icui         NUMERIC,
    vlr_imp_iva          NUMERIC,
    valor_neto           NUMERIC,
    valor_bruto          NUMERIC,
    valor_subtotal       NUMERIC,
    costo_promedio_total NUMERIC,
    margen_promedio      NUMERIC,
    canal_ventas         TEXT,
    rutas_ventas         TEXT,
    sub_grupo            TEXT,
    zonas                TEXT,
    grupos               TEXT,
    familia              TEXT,
    um_litro_suero       NUMERIC,
    tipo_leche           TEXT,
    litros_leche         NUMERIC,
    kilos_suero          NUMERIC,
    rentabilidad         NUMERIC,
    rentabilidad_plata   NUMERIC,
    item_descripcion     TEXT,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de referencia de ítems
CREATE TABLE IF NOT EXISTS items_referencia (
    referencia  TEXT PRIMARY KEY,
    nombre_item TEXT,
    tipo        TEXT,
    peso        NUMERIC,
    volumen     NUMERIC,
    tipo_leche  TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_ventas_mes_anio ON ventas(mes, anio);
CREATE INDEX IF NOT EXISTS idx_ventas_co       ON ventas(co);
CREATE INDEX IF NOT EXISTS idx_ventas_canal    ON ventas(canal_ventas);
CREATE INDEX IF NOT EXISTS idx_ventas_familia  ON ventas(familia);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha    ON ventas(fecha);

-- Habilitar RLS (Row Level Security)
ALTER TABLE ventas           ENABLE ROW LEVEL SECURITY;
ALTER TABLE items_referencia ENABLE ROW LEVEL SECURITY;

-- Políticas de acceso total (uso interno)
DROP POLICY IF EXISTS allow_all_ventas ON ventas;
CREATE POLICY allow_all_ventas
    ON ventas FOR ALL
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS allow_all_items ON items_referencia;
CREATE POLICY allow_all_items
    ON items_referencia FOR ALL
    USING (true) WITH CHECK (true);

-- ============================================================
-- ⏰ TABLA factura_horas — hora de aprobación por factura
--    (segundo archivo "Ventas con hora"). Se cruza con ventas
--    por nro_documento para identificar el descuento HAPPY.
-- ============================================================
CREATE TABLE IF NOT EXISTS factura_horas (
    nro_documento TEXT PRIMARY KEY,
    co            SMALLINT,
    fecha         DATE,
    hora          TEXT,        -- '02:41:41 PM'
    hora_num      NUMERIC,     -- 14.69  (hora decimal, para filtrar)
    dia_semana    SMALLINT,    -- 0=lunes .. 6=domingo
    es_happy      BOOLEAN DEFAULT FALSE,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fh_happy ON factura_horas(es_happy);
CREATE INDEX IF NOT EXISTS idx_fh_doc   ON factura_horas(nro_documento);

ALTER TABLE factura_horas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS allow_all_horas ON factura_horas;
CREATE POLICY allow_all_horas ON factura_horas FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- 🎯 TABLA presupuestos — metas mensuales editables manualmente
--    desde el módulo 💼 Financiero
-- ============================================================
CREATE TABLE IF NOT EXISTS presupuestos (
    mes          TEXT,
    anio         SMALLINT,
    venta_meta   NUMERIC DEFAULT 0,
    util_meta    NUMERIC DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mes, anio)
);
ALTER TABLE presupuestos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS allow_all_presupuestos ON presupuestos;
CREATE POLICY allow_all_presupuestos ON presupuestos FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- 🚀 FUNCIÓN RPC: get_periodos  (CRÍTICO para rendimiento)
-- Devuelve los meses/años únicos en una sola query SQL
-- (sin esto, la app escanea millones de filas)
-- ============================================================
CREATE OR REPLACE FUNCTION get_periodos()
RETURNS TABLE(mes TEXT, anio SMALLINT)
LANGUAGE SQL STABLE AS $$
    SELECT DISTINCT mes, anio
    FROM ventas
    ORDER BY anio, mes;
$$;

-- Permitir que el rol anon/authenticated llame a la función
GRANT EXECUTE ON FUNCTION get_periodos() TO anon, authenticated;

-- Verificar que se crearon correctamente
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('ventas', 'items_referencia');
