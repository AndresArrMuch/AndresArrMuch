-- Deshace la marca (por si hiciera falta): vuelve [TRF_GUIDE_NO_EMITIDA:X] a [TRF_GUIDE:X]
\set ON_ERROR_STOP on
BEGIN;
UPDATE stock_transfer
SET notes = regexp_replace(notes, '\[TRF_GUIDE_NO_EMITIDA:([A-Z0-9]{4}-[0-9]{6})\]', '[TRF_GUIDE:\1]')
WHERE notes LIKE '%[TRF_GUIDE_NO_EMITIDA:%';
-- revisar el numero de filas y luego: COMMIT;
