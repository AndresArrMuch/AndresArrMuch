-- Facturas y boletas ANULADAS que siguen con su asiento de venta vivo (17/10/2026). SOLO LECTURA: no modifica nada.
-- Uso: sudo -u postgres psql cea_erp_prod -f /tmp/diag_anuladas_con_asiento.sql
--
-- Documento anulado: tipo 01 o 03 con status 'cancelled' o sunat_status 'anulada'.
-- Asiento de venta vivo: entry_type 'sale', estado approved o posted, activo, que no es reversa y sin reversa
-- (reversed_on_entry_id vacio y ningun asiento con reversal_of_entry_id apuntandolo), cuya glosa es la que crea el
-- sistema: 'Venta <numero> - <cliente>' (boton Contabilizar / venta directa) o 'Por la provision de la <tipo> <numero>'
-- (emitida desde cotizacion).
-- Solo lineas activas. Importes por cuenta: 12 = Debe - Haber (cuenta por cobrar); 40 y 70 = Haber - Debe (IGV e ingreso); 'otras' = resto.
-- Nota de credito asociada: documento 07 con referenced_document_number = numero de la factura (cualquier estado),
-- y si esa nota tiene un asiento de venta vivo ('Venta <numero NC>...'); el boton Contabilizar registra una NC con el
-- mismo signo que una venta (Debe 12 / Haber 70 y 40): se muestra el importe de su cuenta 12 para revisarlo.
BEGIN READ ONLY;

\echo '== 1) Detalle por documento y asiento'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number, s.document_type, s.emission_date, s.status, s.sunat_status, s.fiscal_period_id,
         s.subtotal, s.igv, s.total
  FROM sale s
  WHERE s.document_type IN ('01', '03') AND (s.status = 'cancelled' OR s.sunat_status = 'anulada')
), vivos AS (
  SELECT a.*, j.id AS entry_id, j.entry_number, j.status AS entry_status, j.entry_date, j.gloss, j.fiscal_period_id AS entry_period_id
  FROM anuladas a
  JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale'
   AND (j.gloss ILIKE 'Venta ' || a.document_number || ' - %' OR j.gloss ILIKE 'Por la provision de la % ' || a.document_number)
   AND j.status IN ('approved', 'posted') AND j.is_active AND coalesce(j.is_reversal, false) = false
   AND j.reversed_on_entry_id IS NULL
   AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
), importes AS (
  SELECT v.entry_id,
         sum(CASE WHEN c.account_code LIKE '12%' THEN l.debit_amount - l.credit_amount ELSE 0 END) AS cta_12,
         sum(CASE WHEN c.account_code LIKE '40%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_40,
         sum(CASE WHEN c.account_code LIKE '70%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_70,
         sum(CASE WHEN c.account_code NOT LIKE '12%' AND c.account_code NOT LIKE '40%' AND c.account_code NOT LIKE '70%'
                  THEN l.debit_amount - l.credit_amount ELSE 0 END) AS otras
  FROM vivos v JOIN journal_entry_line l ON l.entry_id = v.entry_id AND l.is_active JOIN chart_of_account c ON c.id = l.chart_account_id
  GROUP BY v.entry_id
), notas AS (
  SELECT a.id AS sale_id,
         string_agg(n.document_number || ' (' || n.status || coalesce('/' || n.sunat_status, '') || ')', ', ') AS notas_credito,
         string_agg(n.document_number || ': ' || coalesce((
             SELECT string_agg(j.entry_number || ' ' || j.status || ' cta12=' ||
                      (SELECT coalesce(sum(l.debit_amount - l.credit_amount), 0)::text FROM journal_entry_line l JOIN chart_of_account c ON c.id = l.chart_account_id
                        WHERE l.entry_id = j.id AND l.is_active AND c.account_code LIKE '12%'), '; ')
             FROM journal_entry j WHERE j.company_id = n.company_id AND j.entry_type = 'sale' AND j.gloss ILIKE 'Venta ' || n.document_number || ' - %'
               AND j.status IN ('approved', 'posted') AND j.is_active AND coalesce(j.is_reversal, false) = false), 'sin asiento'), ' | ') AS asiento_de_la_nota
  FROM anuladas a JOIN sale n ON n.company_id = a.company_id AND n.document_type = '07' AND n.referenced_document_number = a.document_number
  GROUP BY a.id
)
SELECT co.business_name AS empresa, v.document_number AS documento, v.document_type AS tipo, v.emission_date AS emision,
       v.status, coalesce(v.sunat_status, '') AS sunat_status,
       ps.period_year || '-' || lpad(ps.period_month::text, 2, '0') AS periodo_venta, ps.status AS estado_periodo_venta,
       v.entry_number AS asiento, v.entry_status AS estado_asiento, v.entry_date AS fecha_asiento,
       pe.period_year || '-' || lpad(pe.period_month::text, 2, '0') AS periodo_asiento, pe.status AS estado_periodo_asiento,
       i.cta_12, i.cta_40, i.cta_70, i.otras,
       (SELECT count(*) FROM vivos v2 WHERE v2.id = v.id) AS asientos_vivos_del_documento,
       coalesce(n.notas_credito, '') AS notas_credito, coalesce(n.asiento_de_la_nota, '') AS asiento_de_la_nota
FROM vivos v JOIN importes i ON i.entry_id = v.entry_id JOIN company co ON co.id = v.company_id
LEFT JOIN fiscal_period ps ON ps.id = v.fiscal_period_id LEFT JOIN fiscal_period pe ON pe.id = v.entry_period_id
LEFT JOIN notas n ON n.sale_id = v.id
ORDER BY 1, periodo_asiento, v.emission_date, v.document_number;

\echo '== 2) Resumen por empresa, mes del asiento y estado del periodo'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number FROM sale s
  WHERE s.document_type IN ('01', '03') AND (s.status = 'cancelled' OR s.sunat_status = 'anulada')
), vivos AS (
  SELECT a.id AS sale_id, a.company_id, j.id AS entry_id, j.fiscal_period_id
  FROM anuladas a
  JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale'
   AND (j.gloss ILIKE 'Venta ' || a.document_number || ' - %' OR j.gloss ILIKE 'Por la provision de la % ' || a.document_number)
   AND j.status IN ('approved', 'posted') AND j.is_active AND coalesce(j.is_reversal, false) = false
   AND j.reversed_on_entry_id IS NULL AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
), importes AS (
  SELECT v.*, sum(CASE WHEN c.account_code LIKE '12%' THEN l.debit_amount - l.credit_amount ELSE 0 END) AS cta_12,
         sum(CASE WHEN c.account_code LIKE '40%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_40,
         sum(CASE WHEN c.account_code LIKE '70%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_70
  FROM vivos v JOIN journal_entry_line l ON l.entry_id = v.entry_id AND l.is_active JOIN chart_of_account c ON c.id = l.chart_account_id
  GROUP BY v.sale_id, v.company_id, v.entry_id, v.fiscal_period_id
)
SELECT coalesce(co.business_name, 'TOTAL') AS empresa, p.period_year || '-' || lpad(p.period_month::text, 2, '0') AS mes_asiento, p.status AS estado_periodo,
       count(DISTINCT x.sale_id) AS documentos, count(*) AS asientos, sum(x.cta_70) AS ingreso_70, sum(x.cta_40) AS igv_40, sum(x.cta_12) AS cxc_12
FROM importes x JOIN company co ON co.id = x.company_id LEFT JOIN fiscal_period p ON p.id = x.fiscal_period_id
GROUP BY ROLLUP ((co.business_name), (p.period_year, p.period_month, p.status))
ORDER BY co.business_name NULLS LAST, p.period_year NULLS LAST, p.period_month NULLS LAST;

\echo '== 3) Total por empresa y estado del periodo (abierto / cerrado)'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number FROM sale s
  WHERE s.document_type IN ('01', '03') AND (s.status = 'cancelled' OR s.sunat_status = 'anulada')
), vivos AS (
  SELECT a.id AS sale_id, a.company_id, j.id AS entry_id, j.fiscal_period_id
  FROM anuladas a
  JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale'
   AND (j.gloss ILIKE 'Venta ' || a.document_number || ' - %' OR j.gloss ILIKE 'Por la provision de la % ' || a.document_number)
   AND j.status IN ('approved', 'posted') AND j.is_active AND coalesce(j.is_reversal, false) = false
   AND j.reversed_on_entry_id IS NULL AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
), importes AS (
  SELECT v.*, sum(CASE WHEN c.account_code LIKE '12%' THEN l.debit_amount - l.credit_amount ELSE 0 END) AS cta_12,
         sum(CASE WHEN c.account_code LIKE '40%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_40,
         sum(CASE WHEN c.account_code LIKE '70%' THEN l.credit_amount - l.debit_amount ELSE 0 END) AS cta_70
  FROM vivos v JOIN journal_entry_line l ON l.entry_id = v.entry_id AND l.is_active JOIN chart_of_account c ON c.id = l.chart_account_id
  GROUP BY v.sale_id, v.company_id, v.entry_id, v.fiscal_period_id
)
SELECT coalesce(co.business_name, 'TOTAL') AS empresa, coalesce(p.status, '(todos)') AS estado_periodo,
       count(DISTINCT x.sale_id) AS documentos, sum(x.cta_70) AS ingreso_70, sum(x.cta_40) AS igv_40, sum(x.cta_12) AS cxc_12_con_igv
FROM importes x JOIN company co ON co.id = x.company_id LEFT JOIN fiscal_period p ON p.id = x.fiscal_period_id
GROUP BY GROUPING SETS ((co.business_name, p.status), (co.business_name), (p.status), ())
ORDER BY co.business_name NULLS LAST, p.status NULLS LAST;

\echo '== 4) Documentos con mas de un asiento de venta vivo (posible doble contabilizacion)'
WITH anuladas AS (
  SELECT s.id, s.company_id, s.document_number FROM sale s
  WHERE s.document_type IN ('01', '03') AND (s.status = 'cancelled' OR s.sunat_status = 'anulada')
)
SELECT co.business_name AS empresa, a.document_number, count(*) AS asientos_vivos, string_agg(j.entry_number, ', ') AS asientos
FROM anuladas a JOIN company co ON co.id = a.company_id
JOIN journal_entry j ON j.company_id = a.company_id AND j.entry_type = 'sale'
 AND (j.gloss ILIKE 'Venta ' || a.document_number || ' - %' OR j.gloss ILIKE 'Por la provision de la % ' || a.document_number)
 AND j.status IN ('approved', 'posted') AND j.is_active AND coalesce(j.is_reversal, false) = false
 AND j.reversed_on_entry_id IS NULL AND NOT EXISTS (SELECT 1 FROM journal_entry r WHERE r.reversal_of_entry_id = j.id)
GROUP BY 1, 2 HAVING count(*) > 1 ORDER BY 1, 2;

ROLLBACK;
