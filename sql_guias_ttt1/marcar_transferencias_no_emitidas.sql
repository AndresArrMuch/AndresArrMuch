-- =====================================================================================
-- Marcar como "Guia no emitida" las transferencias cuyo numero de guia en realidad es de
-- una guia de VENTA (la valida en SUNAT). Diagnostico del 03/10/2026: 54 casos.
-- NO incluye los 4 casos aparte: FIKA TTT1-000034 (la valida es la transferencia) y los
-- 3 "REVISAR PDF" (FIKA TTT1-000006, FIKA TTT1-000007, FLUMISA TTT1-000004).
--
-- REQUISITO: instalar antes la rama claude/guias-contador-unico (23e7136 o posterior),
-- que es la que entiende esta marca (oculta el numero ajeno y su PDF).
--
-- Que hace: en stock_transfer.notes cambia  [TRF_GUIDE:TTT1-000043]  por
--           [TRF_GUIDE_NO_EMITIDA:TTT1-000043]   (el numero se conserva: es reversible).
-- No toca sales_workflow, ventas, facturas, stock ni NubeCont/SUNAT.
-- Si algo no cuadra se detiene solo; entonces escribir ROLLBACK;
-- =====================================================================================
\set ON_ERROR_STOP on
BEGIN;

CREATE TEMP TABLE trf_a_marcar ON COMMIT DROP AS
SELECT t.id, c.business_name AS empresa, t.transfer_number, t.status,
       substring(t.notes from 'TRF_GUIDE:([A-Z0-9]{4}-[0-9]{6})') AS guia,
       w.quotation_number AS venta_duena_del_numero
FROM stock_transfer t
JOIN company c ON c.id = t.company_id
JOIN sales_workflow w ON w.company_id = t.company_id
                     AND w.guide_number = substring(t.notes from 'TRF_GUIDE:([A-Z0-9]{4}-[0-9]{6})')
WHERE (t.company_id, substring(t.notes from 'TRF_GUIDE:([A-Z0-9]{4}-[0-9]{6})')) NOT IN (
    ('976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'TTT1-000034'),   -- FIKA: la valida es la TRANSFERENCIA
    ('976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'TTT1-000006'),   -- FIKA: REVISAR PDF
    ('976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', 'TTT1-000007'),   -- FIKA: REVISAR PDF
    ('ff8936f6-245c-4ff4-bffa-78b8fc3f8c78', 'TTT1-000004')    -- FLUMISA: REVISAR PDF
);

-- 1) Vista previa: deben ser exactamente 54 transferencias
SELECT empresa, guia, transfer_number, status, venta_duena_del_numero FROM trf_a_marcar ORDER BY empresa, guia;
DO $$ DECLARE n int := (SELECT count(*) FROM trf_a_marcar);
BEGIN IF n <> 54 THEN RAISE EXCEPTION 'Se esperaban 54 transferencias y hay %. No se cambio nada: escribe ROLLBACK;', n; END IF; END $$;

-- 2) Marcar
UPDATE stock_transfer t
SET notes = regexp_replace(t.notes, '\[TRF_GUIDE:([A-Z0-9]{4}-[0-9]{6})\]', '[TRF_GUIDE_NO_EMITIDA:\1]')
FROM trf_a_marcar m
WHERE t.id = m.id;

-- 3) Verificacion: 54 marcadas y ninguna de las 54 sigue con el numero ajeno
SELECT count(*) AS marcadas FROM stock_transfer WHERE notes LIKE '%[TRF_GUIDE_NO_EMITIDA:%';
DO $$ DECLARE n int := (SELECT count(*) FROM stock_transfer t JOIN trf_a_marcar m ON m.id = t.id WHERE t.notes LIKE '%[TRF_GUIDE:%');
BEGIN IF n <> 0 THEN RAISE EXCEPTION 'Quedaron % sin marcar. Escribe ROLLBACK;', n; END IF; END $$;

-- 4) Si todo lo anterior salio bien, confirmar con:
--      COMMIT;
--    (o ROLLBACK; para deshacer)
