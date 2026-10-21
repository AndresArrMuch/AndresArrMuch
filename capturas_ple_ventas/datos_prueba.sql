-- Base de prueba ple_test = copia de af_base (base de pruebas, no produccion) mas 3 ventas:
-- boleta sin estado SUNAT, NC a boleta y NC con documento modificado inexistente.
create temp table t as select * from sale where document_number='B001-000001' and company_id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
update t set id=gen_random_uuid()::text, series='B030', correlative='000016', document_number='B030-000016', emission_date='2026-10-17', sunat_status=null, subtotal=11.86, igv=2.14, total=14.00;
insert into sale select * from t;
update t set id=gen_random_uuid()::text, document_type='07', series='BC40', correlative='000001', document_number='BC40-000001', emission_date='2026-10-18', sunat_status='aceptada', subtotal=50.00, igv=9.00, total=59.00, referenced_document_type='03', referenced_document_number='B001-000001';
insert into sale select * from t;
update t set id=gen_random_uuid()::text, series='FC50', correlative='000001', document_number='FC50-000001', emission_date='2026-10-19', subtotal=10.00, igv=1.80, total=11.80, referenced_document_type='01', referenced_document_number='F999-000001';
insert into sale select * from t;
