
-- Datos de prueba para el kardex de tiendas (clon de igbase). FIKA + FLUMISA.
INSERT INTO role (id, name, company_id, created_at, updated_at, is_active) VALUES
 ('r-vend-fika', 'Vendedor-FIKA', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', now(), now(), true),
 ('r-vend-flu', 'Vendedor-FLUMISA', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', now(), now(), true);
INSERT INTO inventory_warehouse SELECT (jsonb_populate_record(null::inventory_warehouse, to_jsonb(w) || jsonb_build_object('id', x.id, 'company_id', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 'code', x.code, 'name', x.name))).*
FROM inventory_warehouse w, (VALUES ('wh-almflu','ALMFLU','ALM FLUMISA'), ('wh-fcapon','TDAFLUCAPON','TDA FLUMISA CAPON'), ('wh-fmalv','TDAFLUMALVINAS','TDA FLUMISA MALVINAS')) x(id, code, name)
WHERE w.code = 'ALMFIKA';
INSERT INTO fiscal_period (id, company_id, period_year, period_month, start_date, end_date, status, sales_status, purchases_status, created_at, updated_at, is_active)
VALUES ('fp-flu-10', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 2026, 10, '2026-10-01', '2026-10-31', 'open', 'open', 'open', now(), now(), true);
INSERT INTO inventory_item SELECT (jsonb_populate_record(null::inventory_item, to_jsonb(i) || jsonb_build_object('id', md5('flu' || i.id)::uuid::text, 'company_id', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'))).*
FROM inventory_item i WHERE i.company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' ORDER BY i.item_code LIMIT 2;
INSERT INTO inventory_movement SELECT (jsonb_populate_record(null::inventory_movement, to_jsonb(m) || jsonb_build_object(
  'id', md5(x.wh || m.id)::uuid::text, 'company_id', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 'warehouse_id', x.wh, 'fiscal_period_id', 'fp-flu-10',
  'item_id', (SELECT id FROM inventory_item WHERE company_id = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78' ORDER BY item_code LIMIT 1), 'notes', 'carga prueba ' || x.wh))).*
FROM (SELECT * FROM inventory_movement WHERE warehouse_id = (SELECT id FROM inventory_warehouse WHERE code='ALMFIKA') ORDER BY created_at LIMIT 1) m,
     (VALUES ('wh-almflu'), ('wh-fcapon'), ('wh-fmalv')) x(wh);
INSERT INTO "user" SELECT (jsonb_populate_record(null::"user", to_jsonb(u) || jsonb_build_object(
  'id', x.id, 'email', x.email, 'username', x.username, 'company_id', x.cid, 'role_id', x.rid,
  'warehouse_id', (SELECT id FROM inventory_warehouse WHERE code = x.whcode), 'password_hash', 'pbkdf2:sha256:600000$rt8oGnM2OSgezhz1$5c72cfc20b3fbd05c50cb888cbce8d9a5c96113336d1a15cf97fd28d6f9566b5'))).*
FROM "user" u, (VALUES
  ('u-nilton', 'ventas2@fikaperu.com', 'ventas2', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'r-vend-fika', 'TDAFIKAMALVINAS'),
  ('u-saul', 'ventas.tda.filomena@gmail.com', 'filomena', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'r-vend-fika', 'TDAFIKACAPON'),
  ('u-fran-fika', 'ventas1@fikaperu.com', 'ventas1', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'r-vend-fika', 'TDAFIKAMALVINAS'),
  ('u-fran-flu', 'ventas1@fikaperu.com', 'ventas1flu', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 'r-vend-flu', 'TDAFLUMALVINAS'),
  ('u-admin-flu', 'admin@t.pe', 'adminflu', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', (SELECT id FROM role WHERE name = 'Administrador'), NULL),
  ('u-alm-flu', 'central@t.pe', 'centralflu', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', (SELECT id FROM role WHERE name = 'AlmacenGeneral'), 'ALMFLU')
) x(id, email, username, cid, rid, whcode)
WHERE u.email = 'admin@t.pe' AND u.company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
UPDATE "user" SET password_hash = 'pbkdf2:sha256:600000$rt8oGnM2OSgezhz1$5c72cfc20b3fbd05c50cb888cbce8d9a5c96113336d1a15cf97fd28d6f9566b5' WHERE email IN ('admin@t.pe', 'central@t.pe', 'ventas@t.pe', 'capon@t.pe', 'malvinas@t.pe');
update inventory_movement set reference_type='transfer', reference_id=NULL where company_id='ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
