# Reporte de ventas PLE: notas de crédito, anulados y documento modificado (análisis, sin cambios)

Base: main `2d95f94`. Diagnóstico de solo lectura en la rama `claude/ple-ventas-nc-anulados` (commit `ffd0b7b`).

## A) Cómo se arma hoy

### A.1 Excel "Exportar Detallado PLE" (`exportSalesPle`, en el navegador)
- **`salesThisMonth`** = `state.cache.sales` filtrado por:
  - **mes de EMISIÓN** (`emission_date` empieza con AAAA-MM);
  - `is_electronic !== false`.
- `state.cache.sales` viene de `GET /api/sales/<empresa>`. Esa ruta filtra solo por empresa y la pantalla quita los `is_active = false`. **No filtra estado ni respuesta de SUNAT.**
- **Entran:** facturas, boletas, NC y ND; aceptadas, **anuladas** (`cancelled`/`anulada`) y **nunca enviadas** (sin `sunat_status`).
- **Importes:** `subtotal`, `igv` y `total` **tal como están guardados**. Las NC se guardan en positivo, así que **suman**.
- **Columnas fijas:**
  - AJ (campo 35, estado) = 1;
  - AK = 0, AL = 0;
  - AM = 101;
  - **AD a AG** (campos 29 a 32, documento modificado) **vacías**.
- **Moneda:** los importes van en la moneda del documento. El tipo de cambio se toma de la tabla del día (`sell_rate`). **Si no hay tipo de cambio de ese día, pone 1 sin avisar.**
- **Datos que se cargan y no se usan:** llama a `generateSalesPeriodicReport()`, pero no usa su resultado.
- **No coincide con el reporte de la pantalla:** el reporte periódico de la pantalla excluye los anulados y los electrónicos sin PDF ni estado SUNAT.

### A.2 `exportSalesPeriodicSunat` → `POST /api/sales/<empresa>/reports/periodic/export-sunat` → `_build_sales_sunat_lines`
- **Filtro:** empresa, **periodo contable** (`fiscal_period_id`, no el mes de emisión) e `is_active`. **Sin filtro de estado.**
- **Mismo problema de signos:** subtotal, IGV y total en positivo, también para las NC.
- **Mismo problema de anulados:** van con su importe completo y el **estado fijo `'1'`**.
- **Documento modificado:** los campos 29 a 32 van vacíos.
- **Tipo de cambio:** usa `doc.exchange_rate`, distinto del Excel, que usa la tabla del día.
- **Archivo:** se llama `LE<RUC><AAAAMM>00140100<…>.txt` y queda guardado en el servidor (`uploads/sunat/sales/…`).

### A.3 `exportPleTxt` (Tributario) → `POST /api/tax/<empresa>/ple/export` → `_build_sales_ple_lines`
- **Filtro:** empresa y periodo contable. **Ni siquiera filtra `is_active`.**
- **No tiene la estructura del PLE 14.1.** Son 12 campos propios: periodo, número de orden, fecha, tipo, serie, número, documento del cliente, nombre, base, IGV, total y el **texto** de `sunat_status` ("aceptada", "anulada", vacío) en lugar de un código de estado.
- **Mismos problemas:** NC en positivo, anulados con su importe completo y sin documento modificado.
- **Riesgo:** si este es el TXT que se sube a SUNAT, el problema es mayor que los signos, porque el formato no es válido. Hay que confirmar con el contador qué archivo se declara de verdad (ver preguntas).

### A.4 Fecha de emisión frente a periodo contable
- El Excel usa el mes de emisión y los dos TXT usan el periodo contable.
- Si hay documentos con periodo distinto del mes de emisión, el Excel y el TXT no cuadran entre sí. La sección 3 del diagnóstico los lista.

## B) Propuesta (sin programar)
1. **Notas de crédito (07):**
   - campos de base, IGV y total en **negativo** (−subtotal, −igv, −total);
   - la ND (08) se mantiene en positivo;
   - también en las NC a boletas (BC40 y BC50).
2. **Anulados** (`status = 'cancelled'` o `sunat_status = 'anulada'`):
   - **se mantienen** en el libro, con todos los importes en **0.00**;
   - campo 35 (columna AJ) con el **código de anulado** (ver la nota de fuente abajo).
3. **Documento modificado** (AD a AG, campos 29 a 32), solo para NC y ND:
   - fecha de emisión del documento modificado (se busca la venta referida por número dentro de la empresa);
   - tipo: `referenced_document_type`, o el tipo de la venta referida si está vacío;
   - serie y número: se separan de `referenced_document_number`;
   - si la venta referida no existe en el sistema, se deja la fecha vacía y se marca en una columna de observación.
4. **Sin estado SUNAT** (por ejemplo B030-000016): según la respuesta del contador, o se excluye y se lista aparte como "no enviado a SUNAT", o se incluye marcado. No se reenvía ni se toca.
5. **Columna de observación** en el Excel para revisión ("NC en negativo", "Anulado", "Sin estado SUNAT", "TC no encontrado: 1").
6. **TXT:** la misma lógica podría aplicarse a `_build_sales_sunat_lines`, **solo con la aprobación del contador**. `exportPleTxt` (Tributario) necesita una decisión aparte (ver A.3). Por ahora no se cambia nada del TXT.

### Código de estado para el anulado: fuente y nivel de certeza
- **Qué recuerdo:** en la estructura del **Registro de Ventas e Ingresos (libro 14.1)** del **Anexo N.° 2 de la Resolución de Superintendencia N.° 286-2009/SUNAT** y sus modificatorias, el campo "Estado que identifica la oportunidad de la anotación o indicación si ésta corresponde a un ajuste" admite:
  - **1:** anotación del periodo;
  - **2:** comprobante **anulado**;
  - **8:** corresponde a un periodo anterior;
  - **9:** ajuste de un periodo anterior.
- **Lo que no pude hacer:** confirmarlo contra el documento publicado, porque desde este entorno no tengo acceso a la web de SUNAT. **El contador debe validarlo contra la versión vigente del Anexo.**
- **Además:** la estructura del Excel (CAR SUNAT, campos 1 a 40 con la operación 101 en el campo 38) se parece a la del **Registro de Ventas e Ingresos Electrónico del SIRE** (Resolución de Superintendencia N.° 112-2021/SUNAT y modificatorias). Si la empresa declara por SIRE, el código y la tabla de estados a usar son los del anexo del SIRE, que también hay que confirmar.

## C) Pruebas (con la implementación, después del OK)
- **Caso de prueba:** una factura normal, una NC, una factura anulada, una boleta sin estado SUNAT y una ND.
- **Comparación:** total del Excel antes y después, contra el esperado.
- **Vista previa ya disponible** (diagnóstico sobre la base de prueba, FIKA octubre): total de hoy 5,207.00; propuesto 4,145.00; diferencia 1,062.00 (NC 236 × 2 más anulado 590).
- **FLUMISA septiembre, con tus cifras:**
  - el total de hoy está inflado en **12,195 × 2 = 24,390** por las NC (lo que encontró Víctor) **más 9,905** por los anulados: **34,295** en total;
  - los 14.00 de B030-000016 dependen de la decisión del punto B.4.

## D) Notas de crédito sin asiento (`accounting_status = 'pending'`)
- **Flujo:** `create_credit_note` crea la NC con `accounting_status='pending'` y sin asiento. La pantalla (botón NC) crea la NC y la envía a NubeFact, pero **nunca llama a `/post`**. La venta directa, en cambio, llama a `/post` después del OK de SUNAT.
- **No hay forma de contabilizarla desde la pantalla:** el controlador `[data-action="post-sale"]` existe en `index.html`, pero **ninguna plantilla dibuja ese botón**.
- **Contabilizarla a mano tampoco serviría hoy:** `post_sale` registra la NC con el **mismo signo que una venta** (Debe 12, Haber 70 y 40). Duplicaría el ingreso en vez de revertirlo.
- **Desde cuándo:** desde el inicio del historial de git (15/08/2026, commit `7c0340c`, que ya trae este código). No hay registro anterior en el repositorio. La sección 4 del diagnóstico da en producción el conteo por mes y estado.
- **Conclusión:** es un **fallo del flujo**, no una decisión de diseño. El modelo prevé `pending → posted → reversed` y las ventas sí se contabilizan, pero para las NC no existe ni el paso ni el asiento correcto. **No se corrige nada aquí.**

Comando del diagnóstico (solo lectura):
```
cd ~/cea-erp && git fetch origin && git show origin/claude/ple-ventas-nc-anulados:backend/scripts/diag_ple_ventas_nc_anulados.sql > /tmp/diag_ple.sql && sudo -u postgres psql cea_erp_prod -v empresa='FLUMISA' -v anio=2026 -v mes=9 -f /tmp/diag_ple.sql
```
