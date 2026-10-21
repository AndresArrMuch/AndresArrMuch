-- Reporte de ventas PLE (Excel "Exportar Detallado PLE"): notas de credito, anulados y sin estado SUNAT. SOLO LECTURA.
-- Uso: sudo -u postgres psql cea_erp_prod -v empresa='FLUMISA' -v anio=2026 -v mes=9 -f /tmp/diag_ple_ventas_nc_anulados.sql
-- Reproduce los documentos que entran hoy al Excel (empresa, mes de EMISION, activos, electronicos; todos los estados)
-- y compara el total de hoy (NC en positivo, anulados con importe completo) con el propuesto (NC en negativo,
-- anulados en 0). Tambien: documentos cuyo periodo contable difiere del mes de emision (el TXT usa el periodo),
-- y notas de credito sin asiento por mes.
BEGIN READ ONLY;

\echo '== 1) Documentos del Excel PLE de hoy, con el importe de hoy y el propuesto'
WITH d AS (
  SELECT co.business_name AS empresa, s.document_number, s.document_type AS tipo, s.emission_date, s.status,
         coalesce(s.sunat_status, '(vacio)') AS sunat_status, s.currency, s.subtotal, s.igv, s.total,
         coalesce(s.referenced_document_type, '') AS ref_tipo, coalesce(s.referenced_document_number, '') AS ref_num,
         CASE WHEN s.status = 'cancelled' OR s.sunat_status = 'anulada' THEN 0
              WHEN s.document_type = '07' THEN -1 ELSE 1 END AS factor
  FROM sale s JOIN company co ON co.id = s.company_id
  WHERE co.business_name ILIKE '%' || :'empresa' || '%' AND s.is_active AND coalesce(s.is_electronic, true)
    AND extract(year FROM s.emission_date) = :anio AND extract(month FROM s.emission_date) = :mes
)
SELECT empresa, document_number, tipo, emission_date, status, sunat_status, currency, ref_tipo, ref_num,
       total AS total_hoy, round(total * factor, 2) AS total_propuesto,
       CASE WHEN factor = 0 THEN 'ANULADO: importe 0 y estado de anulado'
            WHEN factor = -1 THEN 'NOTA DE CREDITO: en negativo'
            WHEN sunat_status = '(vacio)' THEN 'SIN ESTADO SUNAT: revisar' ELSE '' END AS observacion
FROM d ORDER BY emission_date, document_number;

\echo '== 2) Totales del Excel: hoy vs propuesto (base, IGV, total), por moneda'
WITH d AS (
  SELECT s.currency, s.subtotal, s.igv, s.total, s.document_type, s.status, s.sunat_status,
         CASE WHEN s.status = 'cancelled' OR s.sunat_status = 'anulada' THEN 0
              WHEN s.document_type = '07' THEN -1 ELSE 1 END AS factor
  FROM sale s JOIN company co ON co.id = s.company_id
  WHERE co.business_name ILIKE '%' || :'empresa' || '%' AND s.is_active AND coalesce(s.is_electronic, true)
    AND extract(year FROM s.emission_date) = :anio AND extract(month FROM s.emission_date) = :mes
)
SELECT currency AS moneda, count(*) AS documentos,
       sum(subtotal) AS base_hoy, sum(igv) AS igv_hoy, sum(total) AS total_hoy,
       round(sum(subtotal * factor), 2) AS base_propuesta, round(sum(igv * factor), 2) AS igv_propuesto, round(sum(total * factor), 2) AS total_propuesto,
       round(sum(total) - sum(total * factor), 2) AS diferencia,
       count(*) FILTER (WHERE document_type = '07' AND factor = -1) AS notas_credito,
       count(*) FILTER (WHERE factor = 0) AS anulados,
       count(*) FILTER (WHERE coalesce(sunat_status, '') = '' AND factor <> 0) AS sin_estado_sunat
FROM d GROUP BY ROLLUP (currency) ORDER BY currency NULLS LAST;

\echo '== 3) Mes de emision distinto del periodo contable (el Excel usa la emision; los TXT usan el periodo)'
SELECT s.document_number, s.document_type AS tipo, s.emission_date, p.period_year || '-' || lpad(p.period_month::text, 2, '0') AS periodo_contable, s.total
FROM sale s JOIN company co ON co.id = s.company_id JOIN fiscal_period p ON p.id = s.fiscal_period_id
WHERE co.business_name ILIKE '%' || :'empresa' || '%' AND s.is_active
  AND ((extract(year FROM s.emission_date) = :anio AND extract(month FROM s.emission_date) = :mes)
       OR (p.period_year = :anio AND p.period_month = :mes))
  AND (extract(year FROM s.emission_date) <> p.period_year OR extract(month FROM s.emission_date) <> p.period_month)
ORDER BY s.emission_date;

\echo '== 4) Notas de credito por mes y estado contable (desde cuando quedan sin asiento)'
SELECT co.business_name AS empresa, to_char(s.emission_date, 'YYYY-MM') AS mes, s.accounting_status,
       count(*) AS notas, sum(s.total) AS total,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM journal_entry j WHERE j.company_id = s.company_id AND j.is_active
                                       AND j.gloss ILIKE '%' || s.document_number || '%')) AS con_asiento_por_glosa,
       min(s.emission_date) AS primera, max(s.emission_date) AS ultima
FROM sale s JOIN company co ON co.id = s.company_id
WHERE s.document_type = '07' AND s.is_active
GROUP BY co.business_name, to_char(s.emission_date, 'YYYY-MM'), s.accounting_status
ORDER BY co.business_name, mes, s.accounting_status;

ROLLBACK;
