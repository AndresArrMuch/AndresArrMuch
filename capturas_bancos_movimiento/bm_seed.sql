-- Bancos > Movimiento entre cuentas: escenario de prueba (sobre am_base). Solo base de prueba.
\set fika '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
-- Interbank MN de FIKA (cuenta propia para la transferencia) y las cuentas internas que Bancos oculta
INSERT INTO bank_account (id, company_id, bank_name, account_type, account_number, currency, account_holder, is_active, opening_balance, opening_date, created_at, updated_at) VALUES
 ('bk-fika-ibk-mn', :'fika', 'Interbank', 'checking', '200-3000111222', 'PEN', 'FIKA SAC', true, 0, '2026-01-01', now(), now()),
 ('bk-fika-comis', :'fika', 'Cuenta Comisiones', 'checking', 'COMISIONES', 'PEN', 'FIKA SAC', true, 0, '2026-01-01', now(), now()),
 ('bk-fika-ret', :'fika', 'Cuenta Retenciones 3%', 'checking', 'RETENCIONES', 'PEN', 'FIKA SAC', true, 0, '2026-01-01', now(), now()),
 ('bk-fika-caja', :'fika', 'Efectivo / Caja', 'cash', 'CAJA', 'PEN', 'FIKA SAC', true, 0, '2026-01-01', now(), now());
-- Extractos: la salida de la transferencia propia en BCP MN y su entrada en Interbank (cada uno con su N. de operacion)
UPDATE conciliacion_excel_import SET rows_json = '[
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01117932","amount":-3000.00,"type":"out","hora":"12:50:35","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01104038","amount":-975.00,"type":"out","hora":"12:20:12","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"TRAN.CTAS.TERC.BM 191 2099725 0","operation_number":"01108170","amount":-100.00,"type":"out","hora":"12:29:43","movimiento":"TRANSF"},
   {"date":"2026-10-14","description":"TRAN.CTAS.PROPIAS A INTERBANK","operation_number":"01200001","amount":-500.00,"type":"out","hora":"15:02:10","movimiento":"TRANSF"}]'
 WHERE id = 'imp-fika-oct';
INSERT INTO conciliacion_excel_import (id, company_id, bank_account_id, filename, rows_json, periodo, created_at, updated_at, is_active) VALUES
 ('imp-fika-ibk-oct', :'fika', 'bk-fika-ibk-mn', 'IBK_MN_FIKA_octubre.xlsx', '[
   {"date":"2026-10-14","description":"TRANSFERENCIA DESDE BCP FIKA","operation_number":"33300001","amount":500.00,"type":"in","hora":"15:02:40","movimiento":"TRANSF"}]', '2026-10', now(), now(), true);
SELECT bank_name, currency FROM bank_account WHERE company_id = :'fika' ORDER BY 1;
