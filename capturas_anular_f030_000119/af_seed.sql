\set ON_ERROR_STOP 1
-- Replica del caso F030-000119 / F030-000120 (datos de prueba)
UPDATE company SET nubecont_api_url='http://127.0.0.1:8931/api', nubecont_api_token='TOKEN-PRUEBA' WHERE id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
CREATE TEMP TABLE tc AS SELECT * FROM customer WHERE id='80bb9db3-6e9f-426f-8ba6-a94f64e83655';
INSERT INTO customer SELECT (jsonb_populate_record(tc, jsonb_build_object('id','af-cust','ruc_or_dni','20516083647','business_name','PONEDORAS S.A.C.'))).* FROM tc;
CREATE TEMP TABLE ti AS SELECT * FROM inventory_item WHERE id='2a9e4da0-d0eb-4d65-9823-4554349027b2';
INSERT INTO inventory_item SELECT (jsonb_populate_record(ti, jsonb_build_object('id','af-i1','item_code','SSG2603FMANG75TM','description','NITRILO VERDE X100 GUANTES DE 7.5','current_cost',10))).* FROM ti;
INSERT INTO inventory_item SELECT (jsonb_populate_record(ti, jsonb_build_object('id','af-i2','item_code','YXRP0291C25NYTL','description','GUANTE INDUSTRIAL FIKA CAL 25 BICOLOR','current_cost',5))).* FROM ti;
CREATE TEMP TABLE ts AS SELECT * FROM sale WHERE id='F1';
INSERT INTO sale SELECT (jsonb_populate_record(ts, jsonb_build_object('id','b20e1049-9875-4dce-aacc-a37cf275d4ce','document_number','F030-000119','series','F030','correlative','000119',
  'customer_id','af-cust','document_type','01','status','emitted','sunat_status',null,'sunat_ticket',null,'pdf_path',null,'total',540.00,'subtotal',457.63,'igv',82.37,
  'amount_paid',0,'accounting_status','pending','emission_date','2026-10-16','created_at','2026-10-16 21:31:23','referenced_document_number',null,'notes',null,
  'fiscal_period_id','ed4a35e4-8128-4b35-839b-f4d5ff62d837'))).* FROM ts;
INSERT INTO sale SELECT (jsonb_populate_record(ts, jsonb_build_object('id','af-s120','document_number','F030-000120','series','F030','correlative','000120',
  'customer_id','af-cust','document_type','01','status','emitted','sunat_status','aceptada','pdf_path','http://x/F030-000120.pdf','total',540.00,'subtotal',457.63,'igv',82.37,
  'amount_paid',0,'accounting_status','posted','emission_date','2026-10-16','created_at','2026-10-16 21:31:42','referenced_document_number',null,
  'fiscal_period_id','ed4a35e4-8128-4b35-839b-f4d5ff62d837'))).* FROM ts;
CREATE TEMP TABLE tl AS SELECT * FROM sale_line LIMIT 1;
INSERT INTO sale_line SELECT (jsonb_populate_record(tl, jsonb_build_object('id',left(md5(s||i),36),'sale_id',s,'company_id','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','inventory_item_id','af-i'||i,
  'quantity',q,'unit_price',p,'total',q*p))).* FROM tl, (VALUES (1,20,15.00),(2,24,10.00)) v(i,q,p), unnest(array['b20e1049-9875-4dce-aacc-a37cf275d4ce','af-s120']) s;
-- Kardex TDA FIKA CAPON: saldo inicial, salida de la 000119 y salida de la 000120
CREATE TEMP TABLE tm AS SELECT * FROM inventory_movement LIMIT 1;
INSERT INTO inventory_movement SELECT (jsonb_populate_record(tm, jsonb_build_object('id',v.mid,'company_id','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','item_id',it,
  'warehouse_id','ec674a11-2d4d-40e3-93b5-4ebf1c2085f6','fiscal_period_id','ed4a35e4-8128-4b35-839b-f4d5ff62d837','movement_date',d,'movement_type',mt,
  'reference_type',rt,'reference_id',rid,'quantity',q,'unit_cost',c,'total_cost',q*c,'balance_quantity',bq,'balance_cost',bq*c,'created_at',ca,'notes',null,'journal_entry_id',null))).*
FROM tm, (VALUES
 ('af-m1','af-i1','2026-10-01','in','purchase','af-compra',100,10,100,'2026-10-01 10:00'),
 ('af-m2','af-i2','2026-10-01','in','purchase','af-compra',80,5,80,'2026-10-01 10:00'),
 ('af-m3','af-i1','2026-10-16','out','sale','b20e1049-9875-4dce-aacc-a37cf275d4ce',20,10,80,'2026-10-16 21:31:23'),
 ('af-m4','af-i2','2026-10-16','out','sale','b20e1049-9875-4dce-aacc-a37cf275d4ce',24,5,56,'2026-10-16 21:31:23'),
 ('af-m5','af-i1','2026-10-16','out','sale','af-s120',20,10,60,'2026-10-16 21:31:42'),
 ('af-m6','af-i2','2026-10-16','out','sale','af-s120',24,5,32,'2026-10-16 21:31:42')) v(mid,it,d,mt,rt,rid,q,c,bq,ca);
-- Asiento de la F030-000120 (no debe tocarse)
CREATE TEMP TABLE je AS SELECT * FROM journal_entry LIMIT 1;
INSERT INTO journal_entry SELECT (jsonb_populate_record(je, jsonb_build_object('id','af-j120','company_id','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','entry_number','000120','entry_type','sale',
  'gloss','Venta F030-000120 - PONEDORAS S.A.C.','status','approved','is_active',true,'is_reversal',false,'reversal_of_entry_id',null,'reversed_on_entry_id',null,
  'fiscal_period_id','ed4a35e4-8128-4b35-839b-f4d5ff62d837','entry_date','2026-10-16'))).* FROM je;
CREATE TEMP TABLE jl AS SELECT * FROM journal_entry_line LIMIT 1;
INSERT INTO journal_entry_line SELECT (jsonb_populate_record(jl, jsonb_build_object('id','af-jl'||n,'entry_id','af-j120','company_id','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433',
  'chart_account_id',(SELECT id FROM chart_of_account WHERE company_id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' AND account_code LIKE a||'%' ORDER BY account_code LIMIT 1),
  'debit_amount',d,'credit_amount',c,'is_active',true))).* FROM jl, (VALUES (1,'12',540.00,0),(2,'40',0,82.37),(3,'70',0,457.63)) v(n,a,d,c);
