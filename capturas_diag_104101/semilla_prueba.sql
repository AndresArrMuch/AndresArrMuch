\set c '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
insert into conciliacion_excel_import (id, company_id, bank_account_id, filename, rows_json, periodo, created_at, updated_at, is_active)
values (gen_random_uuid()::text, :'c', 'bk-fika-bcp-mn', 'bcp_sep.xlsx', '[{"date":"2026-09-03","operation_number":"111","amount":1000,"description":"DEP A"},{"date":"2026-09-05","operation_number":"222","amount":500,"description":"DEP B"},{"date":"2026-09-09","operation_number":"999","amount":300,"description":"DEP SIN ASIENTO"},{"date":"2026-10-01","operation_number":"666","amount":90,"description":"DEP OCT"},{"date":"2026-09-10","operation_number":"777","amount":-40,"description":"PAGO"}]', '2026-09', now(), now(), true),
       (gen_random_uuid()::text, :'c', 'bk-fika-ibk-mn', 'ibk_sep.xlsx', '[{"date":"2026-09-07","operation_number":"333","amount":700,"description":"DEP IBK"}]', '2026-09', now(), now(), true);
select id as per from fiscal_period where company_id=:'c' and period_year=2026 and period_month=9 \gset
select id as cta from chart_of_account where company_id=:'c' and account_code='104101' \gset
select id as cxc from chart_of_account where company_id=:'c' and account_code like '1212%' and accepts_movement limit 1 \gset
create temp table s(n int, f date, op text, m numeric, g text, rev bool);
insert into s values (1,'2026-09-03','111',1000,'Cobro A',false),(2,'2026-09-05','222',600,'Cobro B',false),(3,'2026-09-07','333',700,'Cobro en IBK',false),
 (4,'2026-09-08','444',200,'Cobro D',false),(5,'2026-09-08','444',200,'Cobro D otra vez',false),(6,'2026-09-12','555',50,'Anulacion de pago',true),
 (7,'2026-09-13','',80,'Deposito sin numero',false),(8,'2026-09-30','666',90,'Cobro con fecha de septiembre',false),(9,'2026-09-20','888',120,'Cobro sin extracto',false);
insert into journal_entry (id, company_id, fiscal_period_id, entry_number, entry_date, gloss, entry_type, currency, exchange_rate, status, is_reversal, created_at, updated_at, is_active)
select 'dg-'||n, :'c', :'per', 'DG'||n, f, g, 'operation', 'PEN', 1, 'approved', rev, now(), now(), true from s;
insert into journal_entry_line (id, entry_id, company_id, chart_account_id, debit_amount, credit_amount, reference_document, created_at, updated_at, is_active)
select gen_random_uuid()::text, 'dg-'||n, :'c', :'cta', m, 0, op, now(), now(), true from s
union all select gen_random_uuid()::text, 'dg-'||n, :'c', :'cxc', 0, m, op, now(), now(), true from s;
