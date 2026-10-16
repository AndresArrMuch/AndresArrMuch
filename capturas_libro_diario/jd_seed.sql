-- Libro Diario: asientos de prueba (psql -v n=5000). FIKA n asientos, FLUMISA n/10. 3 lineas cada uno.
\set fika '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
\set flu 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
-- Periodos 2025-11 .. 2026-10 para las dos empresas
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, sales_status, purchases_status, created_at, updated_at, is_active)
SELECT md5(c.cid || d::text)::uuid::text, c.cid, extract(year from d), extract(month from d), d, (d + interval '1 month - 1 day')::date, 'open', 'open', 'open', now(), now(), true
FROM (VALUES (:'fika'), (:'flu')) c(cid), generate_series('2025-11-01'::date, '2026-10-01'::date, interval '1 month') d
WHERE NOT EXISTS (SELECT 1 FROM fiscal_period f WHERE f.company_id = c.cid AND f.period_year = extract(year from d) AND f.period_month = extract(month from d));
-- FLUMISA: copia del plan de cuentas de FIKA (si no tiene)
INSERT INTO chart_of_account SELECT (jsonb_populate_record(null::chart_of_account, to_jsonb(a) || jsonb_build_object(
  'id', md5('flu' || a.id)::uuid::text, 'company_id', :'flu',
  'parent_account_id', CASE WHEN a.parent_account_id IS NULL THEN NULL ELSE md5('flu' || a.parent_account_id)::uuid::text END))).*
FROM chart_of_account a WHERE a.company_id = :'fika' AND NOT EXISTS (SELECT 1 FROM chart_of_account x WHERE x.company_id = :'flu');

CREATE TEMP TABLE acc AS
SELECT c.cid,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code = '121201') a_cxc,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code = '104101') a_banco,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code LIKE '7%' AND accepts_movement ORDER BY account_code LIMIT 1) a_venta,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code LIKE '4011%' AND accepts_movement ORDER BY account_code LIMIT 1) a_igv,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code = '421201') a_cxp,
  (SELECT id FROM chart_of_account WHERE company_id = c.cid AND account_code = '691111') a_costo
FROM (VALUES (:'fika'), (:'flu')) c(cid);

CREATE TEMP TABLE gen AS
SELECT c.cid, g, ('2025-11-01'::date + ((g * 347) % 350)) AS dt, ((g * 7919) % 5000) + 10.55 AS monto
FROM (VALUES (:'fika', :n), (:'flu', :n / 10)) c(cid, total), generate_series(1, c.total) g;

INSERT INTO journal_entry (id, company_id, fiscal_period_id, entry_number, entry_date, gloss, entry_type, currency, exchange_rate, status, is_reversal, created_at, updated_at, is_active)
SELECT md5(gen.cid || 'je' || g)::uuid::text, gen.cid, fp.id, lpad(g::text, 6, '0'), dt,
  CASE g % 8
    WHEN 0 THEN 'Venta F001-' || lpad(g::text, 6, '0') || ' - CLIENTE PRUEBA SAC'
    WHEN 1 THEN 'Compra F002-' || lpad(g::text, 5, '0') || ' - proveedor DISTRIBUIDORA SAC'
    WHEN 2 THEN 'Cobro RC-' || g || ' de factura'
    WHEN 3 THEN 'Pago a proveedor OP-' || g
    WHEN 4 THEN 'Ajuste de inventario AJ-' || g
    WHEN 5 THEN 'Planilla del mes'
    WHEN 6 THEN 'Conciliacion bancaria - comision'
    ELSE 'Asiento de reclasificacion ' || g END,
  CASE g % 8 WHEN 0 THEN 'sale' WHEN 1 THEN 'purchase' WHEN 2 THEN 'operation' WHEN 3 THEN 'operation' WHEN 4 THEN 'adjustment' ELSE 'operation' END,
  CASE WHEN g % 10 = 9 THEN 'USD' ELSE 'PEN' END, CASE WHEN g % 10 = 9 THEN 3.75 ELSE 1 END,
  CASE WHEN g % 97 = 0 THEN 'draft' ELSE 'approved' END, false,
  now() - (g || ' seconds')::interval, now() - (g || ' seconds')::interval, true
FROM gen JOIN fiscal_period fp ON fp.company_id = gen.cid AND fp.period_year = extract(year from dt) AND fp.period_month = extract(month from dt);

INSERT INTO journal_entry_line (id, entry_id, company_id, chart_account_id, debit_amount, credit_amount, debit_amount_me, credit_amount_me, currency_me, reference_document, description, created_at, updated_at, is_active)
SELECT md5(gen.cid || 'jl' || g || '-' || k)::uuid::text, md5(gen.cid || 'je' || g)::uuid::text, gen.cid,
  CASE k WHEN 1 THEN (CASE WHEN g % 2 = 0 THEN acc.a_cxc ELSE acc.a_banco END) WHEN 2 THEN (CASE WHEN g % 3 = 0 THEN acc.a_costo ELSE acc.a_venta END) ELSE (CASE WHEN g % 2 = 0 THEN acc.a_igv ELSE acc.a_cxp END) END,
  CASE k WHEN 1 THEN monto ELSE 0 END,
  CASE k WHEN 2 THEN round(monto * 0.82, 2) WHEN 3 THEN monto - round(monto * 0.82, 2) ELSE 0 END,
  CASE WHEN g % 10 = 9 AND k = 1 THEN round(monto / 3.75, 2) ELSE 0 END,
  CASE WHEN g % 10 = 9 AND k = 2 THEN round(monto * 0.82 / 3.75, 2) WHEN g % 10 = 9 AND k = 3 THEN round((monto - round(monto * 0.82, 2)) / 3.75, 2) ELSE 0 END,
  CASE WHEN g % 10 = 9 THEN 'USD' END,
  CASE WHEN g % 4 = 2 THEN 'OP-' || g END,
  CASE WHEN k = 3 AND g % 5 = 0 THEN 'Detalle de linea ' || g END,
  now(), now(), true
FROM gen JOIN acc ON acc.cid = gen.cid, generate_series(1, 3) k;
SELECT company_id, count(*) FROM journal_entry GROUP BY 1;
