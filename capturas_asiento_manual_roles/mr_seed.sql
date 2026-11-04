-- Roles de prueba (nombres de produccion) y un usuario por rol. SOLO base de prueba. Clave: p
\set fika '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
\set flu 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
CREATE TEMP TABLE r(name text);
INSERT INTO r VALUES ('Administrador-FIKA'),('Administrador-FLUMISA'),('AlmacenGuias-FIKA'),('AlmacenGuias-FLUMISA'),('Almacenero-FLUMISA'),
 ('Gerente-FIKA'),('Gerente-FLUMISA'),('Sistema-FIKA'),('Sistema-FLUMISA'),('TiendaCapon-FIKA'),('TiendaCapon-FLUMISA'),
 ('TiendaMalvinas-FIKA'),('TiendaMalvinas-FLUMISA'),('Vendedor-FIKA'),('Vendedor-FLUMISA'),('Tesoreria'),('Encargado-FIKA'),('Encargado-FLUMISA'),
 ('Sistemas'),('Gerente'),('Administrador');
INSERT INTO role (id, name, description, company_id, created_at, updated_at, is_active)
SELECT md5('rol' || r.name)::uuid::text, r.name, 'prueba', :'fika', now(), now(), true FROM r WHERE NOT EXISTS (SELECT 1 FROM role x WHERE x.name = r.name);
-- Un usuario por rol, en la empresa del sufijo (sin sufijo: FIKA)
INSERT INTO "user" (id, email, username, password_hash, first_name, last_name, role_id, company_id, is_locked, failed_login_attempts, two_factor_enabled, created_at, updated_at, is_active)
SELECT md5('usr' || r.name)::uuid::text, lower(replace(r.name, '-', '.')) || '@t.pe', lower(replace(r.name, '-', '.')), a.password_hash, 'Prueba', r.name,
       (SELECT id FROM role WHERE name = r.name), CASE WHEN r.name LIKE '%-FLUMISA' THEN :'flu' ELSE :'fika' END, false, 0, false, now(), now(), true
FROM r, (SELECT password_hash FROM "user" WHERE email = 'admin@t.pe' LIMIT 1) a;
SELECT r.name, u.email, CASE u.company_id WHEN :'fika' THEN 'FIKA' ELSE 'FLUMISA' END FROM "user" u JOIN role r ON r.id = u.role_id WHERE u.email LIKE '%.%@t.pe' OR u.last_name = r.name ORDER BY 1;
