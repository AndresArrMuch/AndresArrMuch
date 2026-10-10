-- Datos de prueba para Alquiler (base copiada de igbase). FIKA PRUEBA SAC.
\set cid '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
UPDATE fiscal_period SET purchases_status = 'open', sales_status = 'open' WHERE company_id = :'cid';
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, sales_status, purchases_status, created_at, updated_at, is_active) VALUES
 ('fp-2026-09', :'cid', 2026, 9, '2026-09-01', '2026-09-30', 'open', 'open', 'closed', now(), now(), true),
 ('fp-2026-11', :'cid', 2026, 11, '2026-11-01', '2026-11-30', 'open', 'open', 'open', now(), now(), true);
INSERT INTO supplier (id, company_id, ruc_or_dni, business_name, address, supplier_type, created_at, updated_at, is_active) VALUES
 ('sup-arr1', :'cid', '10203040', 'JUAN PEREZ ARRENDADOR', 'LIMA', 'local', now(), now(), true),
 ('sup-arr2', :'cid', '50607080', 'MARIA LOPEZ ARRENDADORA', 'LIMA', 'local', now(), now(), true),
 ('sup-sac',  :'cid', '20100000001', 'PROVEEDOR NORMAL SAC', 'LIMA', 'local', now(), now(), true),
 ('sup-rxh',  :'cid', '10456789012', 'CONTADOR INDEPENDIENTE', 'LIMA', 'local', now(), now(), true);
INSERT INTO bank_account (id, company_id, bank_name, account_type, account_number, currency, account_holder, is_active, opening_balance, opening_date, created_at, updated_at) VALUES
 ('bank-pen', :'cid', 'BCP', 'checking', '191-0001', 'PEN', 'FIKA', true, 100000, '2026-01-01', now(), now()),
 ('bank-usd', :'cid', 'BCP', 'checking', '191-0002', 'USD', 'FIKA', true, 50000, '2026-01-01', now(), now());
INSERT INTO exchange_rate (id, company_id, rate_date, currency, buy_rate, sell_rate, source, official, created_at, updated_at, is_active) VALUES
 ('er-1005', :'cid', '2026-10-05', 'USD', 3.74, 3.75, 'SUNAT', true, now(), now(), true),
 ('er-1020', :'cid', '2026-10-20', 'USD', 3.79, 3.80, 'SUNAT', true, now(), now(), true);
