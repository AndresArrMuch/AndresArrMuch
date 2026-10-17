-- SOLO LECTURA (17/10/2026), para el contador. Uso: sudo -u postgres psql cea_erp_prod -f /tmp/diag_anuladas_con_asiento.sql
-- Ventas anuladas (status 'cancelled' o sunat_status 'anulada') que todavia tienen su asiento de venta
-- (entry_type 'sale', aprobado o contabilizado) SIN reversa. La anulacion actual (/void y /electronic/void)
-- revierte el stock pero no el asiento. El asiento se reconoce como lo hace el sistema: glosa con el numero
-- del documento ('Venta F030-000120 - ...' o 'Por la provision de la Factura F030-...').
-- Reversa = otro asiento con reversal_of_entry_id = asiento, o el asiento con reversed_on_entry_id.
BEGIN READ ONLY;

\echo '== 1) Detalle'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number, s.document_type, s.emission_date, s.status, s.sunat_status, s.subtotal, s.igv, s.total
  FROM sale s WHERE s.status = 'cancelled' OR s.sunat_status = 'anulada'
), asientos AS (
  SELECT a.*, j.id AS entry_id, j.entry_number, j.entry_date, j.status AS entry_status, j.gloss,
         (SELECT coalesce(sum(l.credit_amount - l.debit_amount), 0) FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
           WHERE l.entry_id = j.id AND c.account_code LIKE '70%') AS ingreso,
         (SELECT coalesce(sum(l.credit_amount - l.debit_amount), 0) FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
           WHERE l.entry_id = j.id AND c.account_code LIKE '40%') AS igv_asiento,
         (SELECT coalesce(sum(l.debit_amount - l.credit_amount), 0) FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
           WHERE l.entry_id = j.id AND c.account_code LIKE '12%') AS cxc
  FROM anuladas a
  JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale' AND j.gloss ILIKE '%' || a.document_number || '%'
       AND j.status IN ('approved', 'posted') AND coalesce(j.is_reversal, false) = false
  WHERE j.reversed_on_entry_id IS NULL
    AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
)
SELECT c.business_name AS empresa, x.document_number, x.document_type, x.emission_date, x.status, coalesce(x.sunat_status, '') AS sunat_status,
       x.entry_number AS asiento, x.entry_date AS fecha_asiento, x.entry_status, left(x.gloss, 60) AS glosa,
       x.ingreso, x.igv_asiento AS igv, x.cxc AS cuenta_por_cobrar
FROM asientos x JOIN company c ON c.id = x.company_id
ORDER BY 1, x.emission_date, x.document_number;

\echo '== 2) Resumen por empresa'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number FROM sale s WHERE s.status = 'cancelled' OR s.sunat_status = 'anulada'
), asientos AS (
  SELECT a.company_id, j.id AS entry_id,
         (SELECT coalesce(sum(l.credit_amount - l.debit_amount), 0) FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
           WHERE l.entry_id = j.id AND c.account_code LIKE '70%') AS ingreso,
         (SELECT coalesce(sum(l.credit_amount - l.debit_amount), 0) FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
           WHERE l.entry_id = j.id AND c.account_code LIKE '40%') AS igv
  FROM anuladas a
  JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale' AND j.gloss ILIKE '%' || a.document_number || '%'
       AND j.status IN ('approved', 'posted') AND coalesce(j.is_reversal, false) = false
  WHERE j.reversed_on_entry_id IS NULL AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
)
SELECT c.business_name AS empresa, count(DISTINCT x.entry_id) AS asientos_sin_reversa, sum(x.ingreso) AS total_ingreso, sum(x.igv) AS total_igv
FROM asientos x JOIN company c ON c.id = x.company_id GROUP BY 1 ORDER BY 1;

\echo '== 3) Ventas anuladas por empresa (para comparar)'
SELECT c.business_name AS empresa, count(*) AS ventas_anuladas FROM sale s JOIN company c ON c.id = s.company_id
WHERE s.status = 'cancelled' OR s.sunat_status = 'anulada' GROUP BY 1 ORDER BY 1;
ROLLBACK;
