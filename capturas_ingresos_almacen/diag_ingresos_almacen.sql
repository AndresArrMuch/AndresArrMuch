-- Productos creados e ingresos MANUALES de stock de los ultimos 30 dias (19/10/2026). SOLO LECTURA: no modifica nada.
-- Uso: sudo -u postgres psql cea_erp_prod -f /tmp/diag_ingresos_almacen.sql
--
-- Ingreso manual = movimiento sin reference_type (la pantalla Inventario > Registrar movimiento no envia referencia).
-- Los demas movimientos tienen referencia: sale, sale_void, credit_note, transfer, purchase, free_transfer, etc.
-- IMPORTANTE: hoy la pantalla de movimientos y la de crear producto NO guardan el usuario (created_by vacio);
-- se muestra el usuario solo si existe. La carga masiva (bulk_load_job) si guarda el usuario.
-- Horas en Lima (UTC-5).
BEGIN READ ONLY;

\echo '== 1) Resumen de ingresos manuales por empresa, almacen y dia'
SELECT co.business_name AS empresa, w.name AS almacen, (m.created_at - interval '5 hours')::date AS dia_lima,
       count(*) AS movimientos, count(DISTINCT m.item_id) AS productos, sum(m.quantity) AS unidades,
       round(sum(m.total_cost), 2) AS valor_costo,
       count(*) FILTER (WHERE m.unit_cost <= 0.01) AS con_costo_0_o_0_01,
       count(*) FILTER (WHERE coalesce(trim(m.notes), '') = '') AS sin_comentario,
       coalesce(string_agg(DISTINCT u.email, ', '), '(sin usuario registrado)') AS usuarios
FROM inventory_movement m
JOIN company co ON co.id = m.company_id
JOIN inventory_warehouse w ON w.id = m.warehouse_id
LEFT JOIN "user" u ON u.id = m.created_by
WHERE m.reference_type IS NULL AND m.movement_type IN ('in', 'adjustment')
  AND m.created_at >= (now() at time zone 'utc') - interval '30 days'
GROUP BY ROLLUP ((co.business_name), (w.name), ((m.created_at - interval '5 hours')::date))
ORDER BY co.business_name NULLS LAST, w.name NULLS LAST, dia_lima NULLS LAST;

\echo '== 2) Detalle de ingresos manuales (ultimos 30 dias)'
SELECT co.business_name AS empresa, to_char(m.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI') AS registrado_lima,
       m.movement_date AS fecha_mov, w.name AS almacen, m.movement_type AS tipo, i.item_code AS codigo,
       left(i.description, 45) AS producto, coalesce(i.secondary_description, '') AS detalle, m.quantity AS cantidad,
       m.unit_cost AS costo_unit, m.total_cost AS costo_total, coalesce(m.notes, '') AS comentario,
       coalesce(u.email, '(sin usuario)') AS usuario,
       (m.unit_cost <= 0.01) AS costo_relleno,
       (coalesce(trim(m.notes), '') = '' OR m.notes ~* '(correcci|para factur|ajuste|regulariz|prueba)') AS comentario_sin_documento
FROM inventory_movement m
JOIN company co ON co.id = m.company_id
JOIN inventory_warehouse w ON w.id = m.warehouse_id
JOIN inventory_item i ON i.id = m.item_id
LEFT JOIN "user" u ON u.id = m.created_by
WHERE m.reference_type IS NULL AND m.movement_type IN ('in', 'adjustment')
  AND m.created_at >= (now() at time zone 'utc') - interval '30 days'
ORDER BY co.business_name, m.created_at;

\echo '== 3) Productos creados en los ultimos 30 dias (con su primer ingreso y stock actual)'
WITH last_bal AS (
  SELECT DISTINCT ON (m.item_id, m.warehouse_id) m.item_id, m.warehouse_id, m.balance_quantity
  FROM inventory_movement m
  ORDER BY m.item_id, m.warehouse_id, m.movement_date DESC, m.created_at DESC
)
SELECT co.business_name AS empresa, to_char(i.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI') AS creado_lima,
       i.item_code AS codigo, left(i.description, 45) AS producto, coalesce(i.secondary_description, '') AS detalle,
       i.unit_of_measure AS unidad, i.current_cost AS costo, i.sale_price AS precio, i.requires_digemid AS digemid,
       coalesce(u.email, '(sin usuario)') AS creado_por,
       (SELECT to_char(min(m.created_at) - interval '5 hours', 'YYYY-MM-DD HH24:MI') FROM inventory_movement m WHERE m.item_id = i.id) AS primer_movimiento_lima,
       (SELECT coalesce(min(m.reference_type), 'manual') FROM inventory_movement m WHERE m.item_id = i.id
          AND m.created_at = (SELECT min(m2.created_at) FROM inventory_movement m2 WHERE m2.item_id = i.id)) AS tipo_primer_movimiento,
       coalesce((SELECT sum(b.balance_quantity) FROM last_bal b WHERE b.item_id = i.id), 0) AS stock_total
FROM inventory_item i
JOIN company co ON co.id = i.company_id
LEFT JOIN "user" u ON u.id = i.created_by
WHERE i.created_at >= (now() at time zone 'utc') - interval '30 days'
ORDER BY co.business_name, i.created_at;

\echo '== 4) Productos creados por dia (cuantos codigos crea almacen cada dia)'
SELECT co.business_name AS empresa, (i.created_at - interval '5 hours')::date AS dia_lima, count(*) AS productos_creados,
       count(DISTINCT i.description) AS descripciones_distintas
FROM inventory_item i JOIN company co ON co.id = i.company_id
WHERE i.created_at >= (now() at time zone 'utc') - interval '30 days'
GROUP BY ROLLUP ((co.business_name), ((i.created_at - interval '5 hours')::date))
ORDER BY co.business_name NULLS LAST, dia_lima NULLS LAST;

\echo '== 5) Misma descripcion con varios codigos y stock en mas de uno (riesgo de vender el codigo equivocado)'
WITH last_bal AS (
  SELECT DISTINCT ON (m.item_id, m.warehouse_id) m.item_id, m.balance_quantity
  FROM inventory_movement m ORDER BY m.item_id, m.warehouse_id, m.movement_date DESC, m.created_at DESC
), stock AS (
  SELECT item_id, sum(balance_quantity) AS qty FROM last_bal GROUP BY item_id
)
SELECT co.business_name AS empresa, left(i.description, 50) AS producto, count(*) AS codigos,
       count(*) FILTER (WHERE coalesce(s.qty, 0) > 0) AS codigos_con_stock,
       string_agg(i.item_code || '(' || coalesce(s.qty, 0)::text || ')', ', ' ORDER BY i.item_code) AS codigos_y_stock
FROM inventory_item i JOIN company co ON co.id = i.company_id LEFT JOIN stock s ON s.item_id = i.id
WHERE i.is_active
GROUP BY co.business_name, i.description
HAVING count(*) > 1 AND count(*) FILTER (WHERE coalesce(s.qty, 0) > 0) > 1
ORDER BY codigos DESC, producto
LIMIT 60;

\echo '== 6) Cargas masivas de los ultimos 30 dias (si guardan usuario)'
SELECT co.business_name AS empresa, to_char(j.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI') AS cuando_lima, j.job_type AS tipo,
       j.file_name AS archivo, j.total_rows AS filas, j.successful_rows AS ok, j.failed_rows AS fallidas, coalesce(u.email, '-') AS usuario
FROM bulk_load_job j JOIN company co ON co.id = j.company_id LEFT JOIN "user" u ON u.id = j.user_id
WHERE j.created_at >= (now() at time zone 'utc') - interval '30 days'
ORDER BY j.created_at;

ROLLBACK;
