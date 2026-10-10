-- Usa en la base de prueba los mismos ids de almacen que produccion (la pantalla los tiene fijos)
CREATE TEMP TABLE _map(code text, new_id text);
INSERT INTO _map VALUES ('ALMFIKA','20e9a97f-c3c9-4302-b488-c27f74bdcc1f'), ('TDAFIKACAPON','ec674a11-2d4d-40e3-93b5-4ebf1c2085f6'),
 ('TDAFIKAMALVINAS','93a6b31a-df95-4d61-91da-f2be9c3cf105'), ('ALMFLU','b866396b-152c-44a9-9e72-5f2a995fe4b1'),
 ('TDAFLUCAPON','b466063a-48af-424d-9745-739dada78e1a'), ('TDAFLUMALVINAS','dd2c0d0a-0aed-4249-9cda-af8333d5b9f9');
DO $$
DECLARE r record; fk record; old_id text;
BEGIN
  FOR r IN SELECT m.code, m.new_id, w.id AS old_id FROM _map m JOIN inventory_warehouse w ON w.code = m.code LOOP
    INSERT INTO inventory_warehouse SELECT (jsonb_populate_record(null::inventory_warehouse, to_jsonb(w) || jsonb_build_object('id', r.new_id, 'code', w.code || '_tmp'))).* FROM inventory_warehouse w WHERE w.id = r.old_id;
    FOR fk IN SELECT cl.relname AS tbl, att.attname AS col FROM pg_constraint c JOIN pg_class cl ON cl.oid = c.conrelid
              JOIN pg_attribute att ON att.attrelid = c.conrelid AND att.attnum = ANY(c.conkey)
              WHERE c.contype = 'f' AND c.confrelid = 'inventory_warehouse'::regclass LOOP
      EXECUTE format('UPDATE %I SET %I = %L WHERE %I = %L', fk.tbl, fk.col, r.new_id, fk.col, r.old_id);
    END LOOP;
    UPDATE "user" SET warehouse_id = r.new_id WHERE warehouse_id = r.old_id;
    DELETE FROM inventory_warehouse WHERE id = r.old_id;
    UPDATE inventory_warehouse SET code = r.code WHERE id = r.new_id;
  END LOOP;
END $$;
