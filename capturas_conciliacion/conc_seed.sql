-- Conciliacion (sobre igbase + alq_seed.sql): FIKA con BCP PEN y BCP USD; FLUMISA con su cuenta.
\set cid '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, sales_status, purchases_status, created_at, updated_at, is_active)
VALUES ('fp-2026-08', :'cid', 2026, 8, '2026-08-01', '2026-08-31', 'open', 'open', 'open', now(), now(), true);
INSERT INTO bank_account (id, company_id, bank_name, account_type, account_number, currency, account_holder, is_active, opening_balance, opening_date, created_at, updated_at) VALUES
 ('bank-flu', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 'BCP', 'checking', '191-9999', 'PEN', 'FLUMISA', true, 0, '2026-01-01', now(), now());
-- Agosto: 5 depositos del sistema en BCP PEN (como los 303 de produccion), sin Excel
INSERT INTO bank_transaction (id, account_id, company_id, transaction_date, transaction_type, amount, reference_number, description, is_reconciled, created_at, updated_at, is_active)
SELECT 'tx-ago-' || g, 'bank-pen', :'cid', ('2026-08-0' || g)::date, 'deposit', 1000 * g, 'AG' || g, 'Cancelacion de Factura F001-00' || g, false, now(), now(), true
FROM generate_series(1, 5) g;
-- Octubre: movimientos del sistema en BCP PEN (2 coinciden con el Excel, 1 no esta en el Excel)
INSERT INTO bank_transaction (id, account_id, company_id, transaction_date, transaction_type, amount, reference_number, description, is_reconciled, created_at, updated_at, is_active) VALUES
 ('tx-oct-1', 'bank-pen', :'cid', '2026-10-03', 'deposit', 1180, 'OP-100', 'Cobro F001-000001', false, now(), now(), true),
 ('tx-oct-2', 'bank-pen', :'cid', '2026-10-04', 'withdrawal', 500, 'OP-200', 'Pago proveedor', false, now(), now(), true),
 ('tx-oct-3', 'bank-pen', :'cid', '2026-10-06', 'deposit', 77, 'OP-999', 'Deposito solo en sistema', false, now(), now(), true),
 ('tx-oct-usd', 'bank-usd', :'cid', '2026-10-05', 'deposit', 300, 'USD-1', 'Cobro en dolares', false, now(), now(), true);
-- Excel de BCP PEN octubre: Registrado (OP-100, OP-200), Error (OP-300), Duplicado (OP-300 repetido), ITF (Pagar) y anticipo
INSERT INTO conciliacion_excel_import (id, company_id, bank_account_id, filename, rows_json, uploaded_by, periodo, created_at, updated_at, is_active)
SELECT 'imp-pen-oct', :'cid', 'bank-pen', 'BCP_MN_octubre.xlsx',
 '[{"date":"2026-10-03","description":"ABONO CLIENTE","operation_number":"OP-100","amount":1180,"type":"in","movimiento":"ABONO","hora":"09:10"},
   {"date":"2026-10-04","description":"TRAN.CTAS.TERC.BM","operation_number":"OP-200","amount":-500,"type":"out","movimiento":"CARGO","hora":"10:00"},
   {"date":"2026-10-05","description":"DEPOSITO EFECTIVO","operation_number":"OP-300","amount":250,"type":"in","movimiento":"ABONO","hora":"11:00"},
   {"date":"2026-10-05","description":"DEPOSITO EFECTIVO","operation_number":"OP-300","amount":250,"type":"in","movimiento":"ABONO","hora":"11:00"},
   {"date":"2026-10-07","description":"IMPUESTO ITF","operation_number":"OP-400","amount":-0.05,"type":"out","movimiento":"CARGO","hora":"12:00"},
   {"date":"2026-10-08","description":"TRAN.CTAS.TERC.BM PROVEEDOR","operation_number":"OP-500","amount":-1200,"type":"out","movimiento":"CARGO","hora":"13:00"}]',
 (SELECT id FROM "user" WHERE email = 'admin@t.pe' LIMIT 1), '2026-10', now() - interval '2 hours', now() - interval '2 hours', true;
-- Excel de BCP USD octubre
INSERT INTO conciliacion_excel_import (id, company_id, bank_account_id, filename, rows_json, uploaded_by, periodo, created_at, updated_at, is_active)
SELECT 'imp-usd-oct', :'cid', 'bank-usd', 'BCP_ME_octubre.xlsx',
 '[{"date":"2026-10-05","description":"ABONO EXTERIOR","operation_number":"USD-1","amount":300,"type":"in","movimiento":"ABONO","hora":"09:00"},
   {"date":"2026-10-09","description":"COMISION","operation_number":"USD-2","amount":-15,"type":"out","movimiento":"CARGO","hora":"09:30"}]',
 (SELECT id FROM "user" WHERE email = 'admin@t.pe' LIMIT 1), '2026-10', now() - interval '1 hour', now() - interval '1 hour', true;
-- admin@t.pe tambien tiene usuario en FLUMISA (para probar el cambio de empresa)
INSERT INTO "user" SELECT (jsonb_populate_record(null::"user", to_jsonb(u) || jsonb_build_object('id', 'u-admin-flu', 'username', 'adminflu', 'company_id', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'))).*
FROM "user" u WHERE u.email = 'admin@t.pe' AND u.company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
