-- =====================================================================================
-- Marcar como "Guia no emitida" las transferencias cuyo numero de guia en realidad es de
-- una guia de VENTA (la valida en SUNAT). Diagnostico del 03/10/2026, revisado con los PDF:
--   54 casos + FLUMISA TTT1-000004 (TRF-00003) + FIKA TTT1-000006 (TRF-00005)
--   + FIKA TTT1-000007 (TRF-00006)  =  57 transferencias.
-- Unico excluido: FIKA TTT1-000034 (alli la valida es la TRANSFERENCIA TRF-00033).
-- Sirve aunque ya se haya aplicado la version de 54: solo marca las que falten.
--
-- REQUISITO: tener instalada la rama claude/guias-contador-unico (23e7136 o posterior).
-- Cambia [TRF_GUIDE:TTT1-000043] por [TRF_GUIDE_NO_EMITIDA:TTT1-000043] (reversible).
-- No toca sales_workflow, ventas, facturas, stock ni NubeCont/SUNAT.
-- Uso: dentro de psql ->  \i /tmp/marcar_no_emitidas.sql   y luego COMMIT; (o ROLLBACK;)
-- =====================================================================================
\set ON_ERROR_STOP on
BEGIN;

CREATE TEMP TABLE trf_chocan ON COMMIT DROP AS
SELECT t.id, c.business_name AS empresa, t.transfer_number, t.status,
       substring(t.notes from 'TRF_GUIDE(?:_NO_EMITIDA)?:([A-Z0-9]{4}-[0-9]{6})') AS guia,
       (t.notes LIKE '%[TRF_GUIDE_NO_EMITIDA:%') AS ya_marcada,
       w.quotation_number AS venta_duena_del_numero
FROM stock_transfer t
JOIN company c ON c.id = t.company_id
JOIN sales_workflow w ON w.company_id = t.company_id
                     AND w.guide_number = substring(t.notes from 'TRF_GUIDE(?:_NO_EMITIDA)?:([A-Z0-9]{4}-[0-9]{6})')
WHERE (t.company_id, substring(t.notes from 'TRF_GUIDE(?:_NO_EMITIDA)?:([A-Z0-9]{4}-[0-9]{6})'))
      <> ('976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'TTT1-000034');   -- FIKA: la valida es la TRANSFERENCIA

-- 1) Vista previa: deben ser exactamente 57 (ya_marcada = t si se aplico antes la version de 54)
SELECT empresa, guia, transfer_number, status, ya_marcada, venta_duena_del_numero FROM trf_chocan ORDER BY empresa, guia;
DO $$ DECLARE n int := (SELECT count(*) FROM trf_chocan);
BEGIN IF n <> 57 THEN RAISE EXCEPTION 'Se esperaban 57 transferencias y hay %. No se cambio nada: escribe ROLLBACK;', n; END IF; END $$;

-- 2) Marcar las que falten
UPDATE stock_transfer t
SET notes = regexp_replace(t.notes, '\[TRF_GUIDE:([A-Z0-9]{4}-[0-9]{6})\]', '[TRF_GUIDE_NO_EMITIDA:\1]')
FROM trf_chocan m
WHERE t.id = m.id AND NOT m.ya_marcada;

-- 3) Verificacion: las 57 marcadas
SELECT count(*) AS marcadas_de_las_57 FROM stock_transfer t JOIN trf_chocan m ON m.id = t.id WHERE t.notes LIKE '%[TRF_GUIDE_NO_EMITIDA:%';
DO $$ DECLARE n int := (SELECT count(*) FROM stock_transfer t JOIN trf_chocan m ON m.id = t.id WHERE t.notes LIKE '%[TRF_GUIDE:%');
BEGIN IF n <> 0 THEN RAISE EXCEPTION 'Quedaron % sin marcar. Escribe ROLLBACK;', n; END IF; END $$;

-- 4) Si todo salio bien:  COMMIT;     (o ROLLBACK; para deshacer)
