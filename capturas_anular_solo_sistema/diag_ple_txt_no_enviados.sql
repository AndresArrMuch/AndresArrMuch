-- SOLO LECTURA (17/10/2026). Uso: sudo -u postgres psql cea_erp_prod -f /tmp/diag_ple_txt_no_enviados.sql
-- Responde si el PLE (Tributario > PLE) y el TXT SUNAT 14.1 (Ventas > Reportes > Exportar SUNAT) incluyen
-- documentos no enviados o anulados, con las MISMAS condiciones del codigo:
--   TXT SUNAT 14.1 (sale_routes._build_sales_sunat_lines): empresa + fiscal_period_id + is_active. Estado fijo '1'.
--   PLE Tributario (tax_routes._build_sales_ple_lines): empresa + fiscal_period_id (ni siquiera is_active).
--   Reporte de ventas en pantalla: is_active, electronico, status <> cancelled y (pdf_path o sunat_status).
BEGIN READ ONLY;

\echo '== 1) F030-000119 y F030-000120'
SELECT c.business_name AS empresa, s.document_number, s.emission_date, s.status, coalesce(s.sunat_status, '(vacio)') AS sunat_status,
       s.pdf_path IS NOT NULL AS tiene_pdf, s.accounting_status, s.is_active,
       fp.period_year || '-' || lpad(fp.period_month::text, 2, '0') AS periodo_del_documento,
       s.is_active AS entra_txt_sunat_14_1, true AS entra_ple_tributario,
       (s.is_active AND s.is_electronic IS DISTINCT FROM false AND s.status <> 'cancelled' AND (s.pdf_path IS NOT NULL OR s.sunat_status IS NOT NULL)) AS entra_reporte_pantalla,
       (SELECT count(*) FROM journal_entry j WHERE j.company_id = s.company_id AND j.gloss LIKE '%' || s.document_number || '%') AS asientos_con_el_numero,
       (SELECT string_agg(w.name || ' ' || m.movement_type || ' ' || m.quantity::text, ', ') FROM inventory_movement m JOIN inventory_warehouse w ON w.id = m.warehouse_id
         WHERE m.reference_id = s.id AND m.reference_type IN ('sale', 'sale_void')) AS movimientos_stock
FROM sale s JOIN company c ON c.id = s.company_id LEFT JOIN fiscal_period fp ON fp.id = s.fiscal_period_id
WHERE s.document_number IN ('F030-000119', 'F030-000120')
ORDER BY 1, 2;

\echo '== 2) Octubre 2026: electronicos que entran al TXT/PLE sin estar aceptados por SUNAT, o anulados'
SELECT c.business_name AS empresa, s.document_number, s.emission_date, s.status, coalesce(s.sunat_status, '(vacio: no enviado)') AS sunat_status,
       s.pdf_path IS NOT NULL AS tiene_pdf, s.total
FROM sale s JOIN company c ON c.id = s.company_id JOIN fiscal_period fp ON fp.id = s.fiscal_period_id
WHERE fp.period_year = 2026 AND fp.period_month = 10 AND s.is_electronic IS DISTINCT FROM false
  AND (s.status = 'cancelled' OR s.sunat_status IS NULL OR s.sunat_status NOT IN ('aceptada', 'aceptada_con_observacion'))
ORDER BY 1, 2;

\echo '== 3) Resumen octubre 2026 por empresa'
SELECT c.business_name AS empresa, count(*) AS en_ple, sum(s.is_active::int) AS en_txt_14_1,
       sum((s.sunat_status IS NULL)::int) AS no_enviados, sum((s.status = 'cancelled')::int) AS anulados,
       sum((s.sunat_status NOT IN ('aceptada', 'aceptada_con_observacion'))::int) AS otros_estados_sunat
FROM sale s JOIN company c ON c.id = s.company_id JOIN fiscal_period fp ON fp.id = s.fiscal_period_id
WHERE fp.period_year = 2026 AND fp.period_month = 10
GROUP BY 1 ORDER BY 1;
ROLLBACK;
