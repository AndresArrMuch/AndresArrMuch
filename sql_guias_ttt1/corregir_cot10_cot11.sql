-- =====================================================================================
-- BORRADOR (no aplicar hasta confirmar con el PDF): la guia TTT1-000007 (FIKA) es en realidad
-- de COT-000011 (lo dice la guia aceptada en SUNAT) pero el sistema la tiene en COT-000010.
--   - COT-000011: pasa a tener la guia TTT1-000007 (estado 'delivered', fecha de esa guia).
--   - COT-000010: queda SIN guia (estado 'accepted'), lista para emitirle una guia nueva y valida.
-- Ninguna de las dos tiene factura (si alguna la tuviera, el script se detiene).
-- No toca stock, facturas, transferencias ni NubeCont/SUNAT.
-- Uso: dentro de psql ->  \i /tmp/corregir_cot10_cot11.sql   y luego COMMIT; (o ROLLBACK;)
-- =====================================================================================
\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE antes ON COMMIT DROP AS
SELECT id, quotation_number, status, guide_series, guide_correlative, guide_number, dispatch_date, is_voided_locally, sale_id
FROM sales_workflow
WHERE company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' AND quotation_number IN ('COT-000010', 'COT-000011');
SELECT * FROM antes ORDER BY quotation_number;

-- Verificaciones: el estado debe ser exactamente el reportado; si no, se detiene sin cambiar nada
DO $$ BEGIN
  IF (SELECT count(*) FROM antes) <> 2 THEN RAISE EXCEPTION 'No se encontraron COT-000010 y COT-000011 (una sola vez cada una). ROLLBACK;'; END IF;
  IF NOT EXISTS (SELECT 1 FROM antes WHERE quotation_number='COT-000010' AND guide_number='TTT1-000007' AND status='delivered' AND sale_id IS NULL)
    THEN RAISE EXCEPTION 'COT-000010 no esta como se esperaba (TTT1-000007, delivered, sin factura). ROLLBACK;'; END IF;
  IF NOT EXISTS (SELECT 1 FROM antes WHERE quotation_number='COT-000011' AND guide_number IS NULL AND status='accepted' AND sale_id IS NULL)
    THEN RAISE EXCEPTION 'COT-000011 no esta como se esperaba (sin guia, accepted, sin factura). ROLLBACK;'; END IF;
  IF (SELECT count(*) FROM sales_workflow WHERE company_id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' AND guide_number='TTT1-000007') <> 1
    THEN RAISE EXCEPTION 'TTT1-000007 esta en mas de un registro de venta. ROLLBACK;'; END IF;
END $$;

-- COT-000011 recibe la guia real (con la fecha de despacho que tenia registrada COT-000010)
UPDATE sales_workflow w
SET guide_series = 'TTT1', guide_correlative = '000007', guide_number = 'TTT1-000007',
    status = 'delivered', dispatch_date = a.dispatch_date, is_voided_locally = false, voided_reason = NULL, updated_at = now()
FROM antes a
WHERE w.quotation_number = 'COT-000011' AND w.company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' AND a.quotation_number = 'COT-000010';

-- COT-000010 queda sin guia, como cotizacion aceptada lista para emitirle una guia nueva
UPDATE sales_workflow
SET guide_series = NULL, guide_correlative = NULL, guide_number = NULL, dispatch_date = NULL,
    status = 'accepted', is_voided_locally = false, voided_reason = NULL, updated_at = now()
WHERE quotation_number = 'COT-000010' AND company_id = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';

-- Resultado
SELECT quotation_number, status, guide_number, guide_correlative, dispatch_date, is_voided_locally, sale_id
FROM sales_workflow WHERE company_id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' AND quotation_number IN ('COT-000010','COT-000011') ORDER BY 1;
-- Debe quedar:  COT-000010 accepted, sin guia  |  COT-000011 delivered, TTT1-000007
-- Si esta bien:  COMMIT;     (o ROLLBACK; para deshacer)
