-- Clientes como en produccion: todos bajo FLUMISA; FIKA solo tiene a FLUMISA EIRL
UPDATE customer SET company_id = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
INSERT INTO customer SELECT (jsonb_populate_record(null::customer, to_jsonb(c) || jsonb_build_object(
  'id', 'cli-' || g, 'company_id', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78',
  'ruc_or_dni', (20100000000 + g * 37)::text, 'business_name', 'EMPRESA CLIENTE ' || lpad(g::text, 4, '0') || ' SAC'))).*
FROM customer c, generate_series(1, 6510) g WHERE c.id = (SELECT min(id) FROM customer);
INSERT INTO customer SELECT (jsonb_populate_record(null::customer, to_jsonb(c) || jsonb_build_object(
  'id', x.id, 'company_id', x.cid, 'ruc_or_dni', x.ruc, 'business_name', x.nom))).*
FROM customer c, (VALUES
  ('cli-sandoval', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', '10451705178', 'SANDOVAL SANTISTEBAN JOSE DEL CARMEN'),
  ('cli-sandoval2', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', '10404040401', 'SANDOVAL RUIZ MARIA'),
  ('cli-clinica', 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', '20451234567', 'CLINICA SAN PABLO SAC'),
  ('cli-flu-eirl-fika', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', '20557450565', 'FLUMISA EIRL')) x(id, cid, ruc, nom)
WHERE c.id = (SELECT min(id) FROM customer WHERE id NOT LIKE 'cli-%');
