-- Casos fabricados para validar el diagnostico del cruce (solo base de prueba)
\set fika '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
\set flu 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
INSERT INTO bank_transaction (id, account_id, company_id, transaction_date, transaction_type, amount, reference_number, description, is_reconciled, created_at, updated_at, is_active) VALUES
 ('dx-1', 'bk-fika-bcp-mn', :'fika', '2026-10-14', 'withdrawal', 2999.00, '01117932', 'monto distinto', false, now(), now(), true),
 ('dx-2', 'bk-fika-bcp-mn', :'fika', '2026-10-14', 'deposit', 975.00, '01104038', 'sentido contrario', false, now(), now(), true),
 ('dx-3', 'bk-fika-ibk-mn', :'fika', '2026-10-14', 'withdrawal', 100.00, '01108170', 'otra cuenta', false, now(), now(), true),
 ('dx-4', 'bk-fika-bcp-mn', :'fika', '2026-10-14', 'withdrawal', 500.00, '01200001', 'correcto', false, now(), now(), true),
 ('dx-5', 'bk-fika-ibk-mn', :'fika', '2026-10-15', 'deposit', 500.00, '33300001', 'otra fecha: no cruza', false, now(), now(), true);
-- FLUMISA: un PAGO (no cobro) con el N. de un abono; una marca del boton Pagar correcta
INSERT INTO payment_record (id, company_id, payment_date, payment_type, bank_account_id, reference_number, total_amount, status, created_at, updated_at, is_active) VALUES
 ('dx-p1', :'flu', '2026-10-16', 'pago', 'bk-flu-bcp-mn', '02117932', 3000.00, 'applied', now(), now(), true);
INSERT INTO conciliacion_pago_registrado (id, company_id, bank_account_id, fecha, operation_number, monto, descripcion, created_at, updated_at, is_active) VALUES
 ('dx-m1', :'flu', 'bk-flu-bcp-mn', '2026-10-14', '02104038', -975.00, 'marca correcta', now(), now(), true);
