-- SOLO PRUEBA: ventas de octubre 2026 de FIKA con un caso de cada tipo
\set cid '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
\set cli '80bb9db3-6e9f-426f-8ba6-a94f64e83655'
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, created_at, updated_at, is_active)
VALUES ('fp-sep', :'cid', 2026, 9, '2026-09-01', '2026-09-30', 'open', now(), now(), true);
INSERT INTO vendedor (id, company_id, codigo, first_name, last_name, commission_percentage, is_active, created_at, updated_at)
VALUES ('v1', :'cid', 'AC0001', 'ANA', 'VENTAS', 1, true, now(), now());
CREATE TEMP TABLE _d (id text, tipo text, num text, emision date, fp text, cur text, tc numeric, total numeric, sub numeric, lt numeric, ls numeric, status text, sunat text, pdf text, vend text, ref text);
INSERT INTO _d VALUES
 ('F1',  '01', 'F001-000001', '2026-10-01', 'oct', 'PEN', 1,    1180, 1000,   1180, 1000,   'emitted',   'aceptada', 'x.pdf', 'v1', NULL),
 ('B1',  '03', 'B001-000001', '2026-10-02', 'oct', 'PEN', 1,    118,  100,    118,  100,    'emitted',   'aceptada', 'x.pdf', 'v1', NULL),
 ('NC1', '07', 'FC01-000001', '2026-10-03', 'oct', 'PEN', 1,    236,  200,    236,  200,    'emitted',   'aceptada', 'x.pdf', 'v1', 'F001-000001'),
 ('ND1', '08', 'FD01-000001', '2026-10-04', 'oct', 'PEN', 1,    59,   50,     59,   50,     'emitted',   'aceptada', 'x.pdf', NULL, 'F001-000001'),
 ('FA',  '01', 'F001-000002', '2026-10-05', 'oct', 'PEN', 1,    590,  500,    590,  500,    'cancelled', 'anulada',  'x.pdf', 'v1', NULL),
 ('FN',  '01', 'F001-000003', '2026-10-06', 'oct', 'PEN', 1,    354,  300,    354,  300,    'emitted',   NULL,       NULL,    'v1', NULL),
 ('FU',  '01', 'F001-000004', '2026-10-07', 'oct', 'USD', 3.75, 100,  84.75,  100,  84.75,  'emitted',   'aceptada', 'x.pdf', 'v1', NULL),
 ('FX',  '01', 'F001-000005', '2026-10-02', 'sep', 'PEN', 1,    472,  400,    472,  400,    'emitted',   'aceptada', 'x.pdf', 'v1', NULL),
 ('FL',  '01', 'F001-000006', '2026-10-08', 'oct', 'PEN', 1,    1018, 862.71, 1000, 847.46, 'emitted',   'aceptada', 'x.pdf', 'v1', NULL);
INSERT INTO sale (id, company_id, customer_id, fiscal_period_id, document_type, series, correlative, document_number, emission_date, due_date, registration_date,
                  is_electronic, sunat_status, pdf_path, currency, exchange_rate, subtotal, igv, total, status, vendedor_id, referenced_document_number, created_at, updated_at, is_active)
SELECT id, :'cid', :'cli', CASE fp WHEN 'sep' THEN 'fp-sep' ELSE (SELECT id FROM fiscal_period WHERE company_id = :'cid' AND period_year = 2026 AND period_month = 10) END,
       tipo, split_part(num, '-', 1), split_part(num, '-', 2), num, emision, emision, emision, true, sunat, pdf, cur, tc, sub, total - sub, total, status, vend, ref, now(), now(), true
FROM _d;
INSERT INTO sale_line (id, sale_id, company_id, description, quantity, unit, unit_price, subtotal, igv, total, created_at, updated_at, is_active)
SELECT id || '-l', id, :'cid', 'ITEM', 1, 'NIU', lt, ls, lt - ls, lt, now(), now(), true FROM _d;
INSERT INTO sales_workflow (id, company_id, customer_id, quotation_number, quotation_date, status, total, subtotal, vendedor_id, is_voided_locally, created_at, updated_at, is_active)
VALUES ('c1', :'cid', :'cli', 'COT-V1', '2026-10-01', 'invoiced', 1180, 1000, 'v1', false, now(), now(), true),
       ('c2', :'cid', :'cli', 'COT-V2', '2026-10-09', 'rejected', 500, 423.73, 'v1', false, now(), now(), true);
