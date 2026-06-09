-- ============================================================
-- ABAD · Informe de Ventas — Esquema de base de datos
-- Postgres estándar: funciona en Neon, Postgres local o cualquier proveedor.
-- Ejecutar en: Neon → SQL Editor → Run   (o en psql)
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

-- Hora de aprobación por factura (segundo archivo "Ventas con hora").
-- Se cruza con ventas por nro_documento para identificar el descuento HAPPY.
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

-- Metas mensuales editables desde el módulo 💼 Financiero
CREATE TABLE IF NOT EXISTS presupuestos (
    mes          TEXT,
    anio         SMALLINT,
    venta_meta   NUMERIC DEFAULT 0,
    util_meta    NUMERIC DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mes, anio)
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_ventas_mes_anio ON ventas(mes, anio);
CREATE INDEX IF NOT EXISTS idx_ventas_co       ON ventas(co);
CREATE INDEX IF NOT EXISTS idx_ventas_canal    ON ventas(canal_ventas);
CREATE INDEX IF NOT EXISTS idx_ventas_familia  ON ventas(familia);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha    ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_fh_happy        ON factura_horas(es_happy);
CREATE INDEX IF NOT EXISTS idx_fh_doc          ON factura_horas(nro_documento);

-- Verificar que se crearon correctamente
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('ventas', 'items_referencia', 'factura_horas', 'presupuestos');
