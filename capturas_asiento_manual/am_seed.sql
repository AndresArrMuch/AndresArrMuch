-- Asiento manual: escenario de prueba (sobre jd_seed n=60). FIKA y FLUMISA.
\set fika '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
\set flu 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
-- Periodos enero..octubre 2026 (los que falten); FIKA: julio y agosto CERRADOS (como en produccion)
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, sales_status, purchases_status, created_at, updated_at, is_active)
SELECT md5(c.cid || d::text)::uuid::text, c.cid, extract(year from d), extract(month from d), d, (d + interval '1 month - 1 day')::date, 'open', 'open', 'open', now(), now(), true
FROM (VALUES (:'fika'), (:'flu')) c(cid), generate_series('2026-01-01'::date, '2026-10-01'::date, interval '1 month') d
WHERE NOT EXISTS (SELECT 1 FROM fiscal_period f WHERE f.company_id = c.cid AND f.period_year = extract(year from d) AND f.period_month = extract(month from d));
UPDATE fiscal_period SET status = 'closed' WHERE company_id = :'fika' AND period_year = 2026 AND period_month IN (7, 8);
-- Cuentas bancarias BCP (soles y dolares) en las dos empresas
INSERT INTO bank_account (id, company_id, bank_name, account_type, account_number, currency, account_holder, is_active, opening_balance, opening_date, created_at, updated_at) VALUES
 ('bk-fika-bcp-mn', :'fika', 'BCP', 'checking', '191-1111111-0-11', 'PEN', 'FIKA SAC', true, 0, '2026-01-01', now(), now()),
 ('bk-fika-bcp-me', :'fika', 'BCP', 'checking', '191-1111111-1-22', 'USD', 'FIKA SAC', true, 0, '2026-01-01', now(), now()),
 ('bk-flu-bcp-mn', :'flu', 'BCP', 'checking', '191 2099725 0', 'PEN', 'FLUMISA EIRL', true, 0, '2026-01-01', now(), now());
-- Tipo de cambio (venta): 14 y 15/10 si; 13/10 NO
INSERT INTO exchange_rate (id, company_id, rate_date, currency, buy_rate, sell_rate, source, created_at, updated_at, is_active)
SELECT md5(c.cid || r.d)::uuid::text, c.cid, r.d::date, 'USD', r.b, r.s, 'SUNAT', now(), now(), true
FROM (VALUES (:'fika'), (:'flu')) c(cid), (VALUES ('2026-07-01', 3.560, 3.570), ('2026-10-14', 3.752, 3.759), ('2026-10-15', 3.754, 3.761)) r(d, b, s);
-- Extractos del 14/10 (casos reales)
INSERT INTO conciliacion_excel_import (id, company_id, bank_account_id, filename, rows_json, periodo, created_at, updated_at, is_active) VALUES
 ('imp-fika-oct', :'fika', 'bk-fika-bcp-mn', 'BCP_MN_FIKA_octubre.xlsx', '[
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01117932","amount":-3000.00,"type":"out","hora":"12:50:35","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01104038","amount":-975.00,"type":"out","hora":"12:20:12","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01108170","amount":-100.00,"type":"out","hora":"12:29:43","movimiento":"TRANSF"}]', '2026-10', now(), now(), true),
 ('imp-flu-oct', :'flu', 'bk-flu-bcp-mn', 'BCP_MN_FLUMISA_octubre.xlsx', '[
   {"date":"2026-10-14","description":"DE FIKA SAC","operation_number":"02117932","amount":3000.00,"type":"in","hora":"12:50:35","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"DE FIKA SAC","operation_number":"02104038","amount":975.00,"type":"in","hora":"12:20:12","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"DE FIKA SAC","operation_number":"02108170","amount":100.00,"type":"in","hora":"12:29:43","movimiento":"TRANSF"}]', '2026-10', now(), now(), true);
-- Un usuario sin permiso de asiento manual (rol Ventas) ya existe: ventas@t.pe
SELECT company_id, period_month, status FROM fiscal_period WHERE period_year = 2026 AND company_id = :'fika' ORDER BY 2;
