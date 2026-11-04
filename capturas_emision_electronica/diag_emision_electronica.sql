-- Diagnostico de emision electronica (FIKA y FLUMISA). SOLO LECTURA: no modifica nada.
-- Uso: sudo -u postgres psql cea_erp_prod -f /tmp/diag_emision.sql
-- Opcional: -v desde=2026-01-01 (por defecto 2026-01-01). Horas en Lima (UTC-5).
\if :{?desde}
\else
\set desde 2026-01-01
\endif
BEGIN READ ONLY;

\echo '== a) Ventas electronicas activas, no anuladas y SIN respuesta de SUNAT, por empresa y mes'
SELECT co.business_name AS empresa, to_char(s.emission_date, 'YYYY-MM') AS mes,
       count(*) AS documentos,
       count(*) FILTER (WHERE s.total > 0) AS con_total_mayor_0,
       round(sum(s.total) FILTER (WHERE s.total > 0), 2) AS suma_total,
       count(*) FILTER (WHERE s.document_type = '01') AS facturas,
       count(*) FILTER (WHERE s.document_type = '03') AS boletas,
       count(*) FILTER (WHERE s.document_type = '07') AS nc,
       count(*) FILTER (WHERE s.document_type = '08') AS nd
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.is_electronic IS NOT FALSE AND s.is_active IS NOT FALSE
  AND coalesce(s.status, '') <> 'cancelled' AND coalesce(trim(s.sunat_status), '') = ''
  AND s.emission_date >= :'desde'
GROUP BY ROLLUP ((co.business_name), (to_char(s.emission_date, 'YYYY-MM')))
ORDER BY empresa NULLS LAST, mes NULLS LAST;

\echo '== a2) Detalle de esos documentos (con hora de registro en Lima, vendedor y si tienen asiento)'
SELECT co.business_name AS empresa, s.document_number AS documento, s.document_type AS tipo, s.emission_date AS emision,
       to_char(s.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI:SS') AS registrado_lima,
       s.total, s.currency AS mon, s.status, s.accounting_status AS contable,
       coalesce(v.codigo, '') AS vendedor, s.sunat_ticket IS NOT NULL AS tiene_ticket,
       current_date - s.emission_date AS dias, s.id AS sale_id
FROM sale s JOIN company co ON co.id = s.company_id LEFT JOIN vendedor v ON v.id = s.vendedor_id
WHERE s.is_electronic IS NOT FALSE AND s.is_active IS NOT FALSE
  AND coalesce(s.status, '') <> 'cancelled' AND coalesce(trim(s.sunat_status), '') = ''
  AND s.emission_date >= :'desde'
ORDER BY co.business_name, s.emission_date, s.document_number;

\echo '== a3) Posibles ventas repetidas: mismo cliente y total, mismo dia, una SIN respuesta y otra registrada despues (hasta 2 h)'
SELECT co.business_name AS empresa, a.document_number AS sin_respuesta, b.document_number AS registrada_despues,
       b.sunat_status AS estado_de_la_segunda, a.total,
       to_char(a.created_at - interval '5 hours', 'HH24:MI:SS') AS hora_1, to_char(b.created_at - interval '5 hours', 'HH24:MI:SS') AS hora_2
FROM sale a JOIN sale b ON b.company_id = a.company_id AND b.customer_id = a.customer_id AND b.total = a.total
     AND b.emission_date = a.emission_date AND b.id <> a.id
     AND b.created_at > a.created_at AND b.created_at <= a.created_at + interval '2 hours'
JOIN company co ON co.id = a.company_id
WHERE a.is_electronic IS NOT FALSE AND coalesce(a.status, '') <> 'cancelled' AND coalesce(trim(a.sunat_status), '') = ''
  AND a.emission_date >= :'desde'
ORDER BY co.business_name, a.created_at;

\echo '== b) Aceptadas sin XML o sin CDR guardado (y sin ticket)'
SELECT co.business_name AS empresa, to_char(s.emission_date, 'YYYY-MM') AS mes, count(*) AS aceptadas,
       count(*) FILTER (WHERE coalesce(s.xml_path, '') = '') AS sin_xml,
       count(*) FILTER (WHERE coalesce(s.cdr_path, '') = '') AS sin_cdr,
       count(*) FILTER (WHERE coalesce(s.pdf_path, '') = '') AS sin_pdf,
       count(*) FILTER (WHERE coalesce(s.sunat_ticket, '') = '') AS sin_ticket
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.sunat_status = 'aceptada' AND s.emission_date >= :'desde'
GROUP BY ROLLUP ((co.business_name), (to_char(s.emission_date, 'YYYY-MM')))
HAVING count(*) FILTER (WHERE coalesce(s.xml_path, '') = '' OR coalesce(s.cdr_path, '') = '' OR coalesce(s.sunat_ticket, '') = '') > 0
ORDER BY empresa NULLS LAST, mes NULLS LAST;

\echo '== b2) Detalle de aceptadas SIN ticket (no hay prueba de que hayan llegado a NubeFact)'
SELECT co.business_name AS empresa, s.document_number AS documento, s.emission_date AS emision, s.total,
       coalesce(s.xml_path, '') <> '' AS xml, coalesce(s.cdr_path, '') <> '' AS cdr, coalesce(s.pdf_path, '') <> '' AS pdf
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.sunat_status = 'aceptada' AND coalesce(s.sunat_ticket, '') = '' AND s.emission_date >= :'desde'
ORDER BY co.business_name, s.emission_date;

\echo '== b3) Valores de sunat_status en uso (en_proceso / enviado / otros pueden venir del mapeo por subcadenas)'
SELECT co.business_name AS empresa, coalesce(nullif(trim(s.sunat_status), ''), '(vacio)') AS sunat_status, s.status, count(*) AS documentos
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.is_electronic IS NOT FALSE AND s.emission_date >= :'desde'
GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC;

\echo '== c) Notas de credito y debito sin respuesta de SUNAT (y su asiento)'
SELECT co.business_name AS empresa, s.document_number AS documento, CASE s.document_type WHEN '07' THEN 'NC' ELSE 'ND' END AS tipo,
       s.emission_date AS emision, to_char(s.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI') AS registrado_lima,
       s.total, s.referenced_document_number AS modifica,
       coalesce(r.sunat_status, CASE WHEN r.id IS NULL THEN '(no existe)' ELSE '(vacio)' END) AS estado_del_modificado,
       s.status, s.accounting_status AS contable, s.id AS sale_id
FROM sale s JOIN company co ON co.id = s.company_id
LEFT JOIN sale r ON r.company_id = s.company_id AND r.document_number = s.referenced_document_number
WHERE s.document_type IN ('07', '08') AND s.is_active IS NOT FALSE
  AND coalesce(s.status, '') <> 'cancelled' AND coalesce(trim(s.sunat_status), '') NOT IN ('aceptada', 'aceptada_con_obs', 'anulada')
ORDER BY co.business_name, s.total DESC;

\echo '== d) Huecos de numeracion por serie (correlativos que faltan entre el primero y el ultimo registrados)'
WITH n AS (
  SELECT s.company_id, s.series, s.correlative::bigint AS num
  FROM sale s
  WHERE s.is_electronic IS NOT FALSE AND s.correlative ~ '^[0-9]+$'
), g AS (
  SELECT company_id, series, num, lead(num) OVER (PARTITION BY company_id, series ORDER BY num) AS siguiente FROM n
)
SELECT co.business_name AS empresa, g.series AS serie, g.num + 1 AS falta_desde, g.siguiente - 1 AS falta_hasta,
       g.siguiente - g.num - 1 AS cantidad
FROM g JOIN company co ON co.id = g.company_id
WHERE g.siguiente IS NOT NULL AND g.siguiente - g.num > 1
ORDER BY co.business_name, g.series, g.num;

\echo '== d2) Correlativos repetidos dentro de una serie (no deberia haber ninguno)'
SELECT co.business_name AS empresa, s.series, s.correlative, count(*) AS veces
FROM sale s JOIN company co ON co.id = s.company_id
GROUP BY 1, 2, 3 HAVING count(*) > 1 ORDER BY 1, 2, 3;

\echo '== e) Los dos casos reportados (sale_id y hora para buscar en el registro de nginx)'
SELECT co.business_name AS empresa, s.document_number, s.id AS sale_id, s.emission_date,
       to_char(s.created_at - interval '5 hours', 'YYYY-MM-DD HH24:MI:SS') AS registrado_lima,
       to_char(s.created_at, 'YYYY-MM-DD HH24:MI:SS') AS registrado_utc,
       to_char(s.updated_at - interval '5 hours', 'YYYY-MM-DD HH24:MI:SS') AS ultima_modificacion_lima,
       s.status, coalesce(s.sunat_status, '') AS sunat_status, coalesce(s.sunat_ticket, '') <> '' AS ticket, s.total
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.document_number IN ('F020-000214', 'B030-000016')
ORDER BY 1, 2;

ROLLBACK;
