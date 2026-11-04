\set ON_ERROR_STOP 1
UPDATE company SET nubecont_api_url='http://127.0.0.1:8933/api/prueba', nubecont_api_token='TKN-PRUEBA-GUIAS' WHERE id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
CREATE TEMP TABLE ti AS SELECT * FROM inventory_item WHERE id='2a9e4da0-d0eb-4d65-9823-4554349027b2';
INSERT INTO inventory_item SELECT (jsonb_populate_record(ti, jsonb_build_object('id',v.id,'item_code',v.code,'description',v.descr,'unit_of_measure',v.um,'requires_digemid',v.dg,
  'barcode',v.bc,'sale_price',v.sp,'current_cost',v.cc,'secondary_description',v.sd))).* FROM ti, (VALUES
  ('gd-niu','BSTL260708NG65TL','GUANTE NITRILO BSTL 26 L VERDE','NIU',false,'1211',0,0.01,'L, VERDE'),
  ('gd-bx','GDBX00000001','PRODUCTO PRUEBA EN CAJA','BX',false,'2001',10,5,''),
  ('gd-dgniu','GDDIGNIU0001','MASCARILLA DIGEMID PRUEBA NIU','NIU',true,'3001',5,1,''),
  ('gd-dgbx','GDDIGBX00001','JERINGA DIGEMID PRUEBA CAJA','BX',true,'4001',50,20,'')) v(id,code,descr,um,dg,bc,sp,cc,sd);
CREATE TEMP TABLE tm AS SELECT * FROM inventory_movement LIMIT 1;
INSERT INTO inventory_movement SELECT (jsonb_populate_record(tm, jsonb_build_object('id','gd-m-'||v.it,'company_id','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','item_id',v.it,
  'warehouse_id','ec674a11-2d4d-40e3-93b5-4ebf1c2085f6','fiscal_period_id','ed4a35e4-8128-4b35-839b-f4d5ff62d837','movement_date','2026-10-01','movement_type','in',
  'reference_type','purchase','reference_id','gd-compra','quantity',100000,'unit_cost',1,'total_cost',100000,'balance_quantity',100000,'balance_cost',100000,'notes',null,'journal_entry_id',null))).*
FROM tm, (VALUES ('gd-niu'),('gd-bx'),('gd-dgniu'),('gd-dgbx')) v(it);
CREATE TEMP TABLE tw AS SELECT * FROM sales_workflow WHERE id='66e16c23-de73-4f99-9650-17967490bd87';
INSERT INTO sales_workflow SELECT (jsonb_populate_record(tw, jsonb_build_object('id',v.id,'quotation_number',v.q,'status','accepted','guide_number',null,'guide_series',null,
  'guide_correlative',null,'sale_id',null,'parent_workflow_id',null,'notes','','is_voided_locally',false))).* FROM tw, (VALUES
  ('gd-w1','COT-GD1-BXsNIU'),('gd-w2','COT-GD2-NIUsNIU'),('gd-w3','COT-GD3-BXsBX'),('gd-w4','COT-GD4-DG-BXsNIU'),('gd-w5','COT-GD5-DG-BXsBX')) v(id,q);
INSERT INTO sales_workflow_line (id,workflow_id,company_id,inventory_item_id,warehouse_id,description,quantity,unit,unit_price,subtotal,total,igv,discount_percentage,discount_amount,igv_percentage,isc,icbper_amount,operation_type,created_at,updated_at,is_active)
SELECT 'gd-l-'||v.w, v.w, '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', v.it, 'ec674a11-2d4d-40e3-93b5-4ebf1c2085f6', i.description, v.q, v.u, 17, 17*v.q, 17*v.q*1.18, 17*v.q*0.18, 0, 0, 18, 0, 0, 'gravada', now(), now(), true
FROM (VALUES ('gd-w1','gd-niu','BX',3800),('gd-w2','gd-niu','NIU',3800),('gd-w3','gd-bx','BX',3800),('gd-w4','gd-dgniu','BX',10),('gd-w5','gd-dgbx','BX',10)) v(w,it,u,q)
JOIN inventory_item i ON i.id=v.it;
