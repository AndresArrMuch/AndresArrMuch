# Función 2 — "Anular solo en el sistema" (diseño, pendiente de aprobación)

Base: main b7440fc (y la función 1 si ya está instalada; si no, la rama 2 la incluye).

## Cuándo aparece la opción
- En la fila de la factura, junto a "Anular", solo para los roles autorizados.
- Al intentar "Anular" (baja) cuando NubeFact responde "Documento no existe" (código 24). El mensaje actual se reemplaza por: *"Este documento nunca llegó a SUNAT. Puedes reintentar el envío o anularlo solo en el sistema."*

## Condiciones obligatorias (las revisa el servidor; nunca solo la pantalla)
1. **Documento electrónico** (`is_electronic`) de tipo 01 o 03, con `status` distinto de `cancelled`.
2. **Sin rastro SUNAT:** `sunat_status`, `sunat_ticket` y `pdf_path` vacíos.
3. **Consulta nueva a NubeFact en ese momento:** `get_invoice_status` (lo mismo que hace "Estado SUNAT") debe responder "Documento no existe" o código 24.
   - Si responde que existe, o con otro error o un tiempo vencido, **no se permite**. Se muestra el mensaje del proveedor.
   - La consulta se hace al confirmar, no se reutiliza una anterior.
   - Usa el candado de la función 1: una sola operación por documento.
4. **Rol:** Sistema, Gerente o Administrador. Se usa `can_register_manual` de `manual_journal_routes`, es decir la misma constante `MANUAL_JOURNAL_ROLE_PREFIXES` ('sistema', 'administrador', 'gerente'), con comparación "empieza con" tras normalizar.
5. **Motivo obligatorio y confirmación fuerte:** escribir el número del documento (por ejemplo "F030-000119") para confirmar.

## Bloqueos (con mensaje claro)
| Bloqueo | Cómo se detecta |
|---|---|
| Tiene guía | Hay un `sales_workflow` con `sale_id` = la venta y un número de guía |
| Viene de una cotización o guía vinculada | Hay cualquier `sales_workflow` con `sale_id` = la venta (no se desvincula sin criterio) |
| Tiene cobros | `amount_paid` > 0 o alguna línea de cobro (`payment_line`) aplicada a la venta |
| Tiene nota de crédito o débito | Un documento 07 u 08 con `referenced_document_number` = el número y no anulado |
| Periodo cerrado | El periodo de la venta **o** el del día de la anulación (hora Lima) está cerrado o no existe. Se muestra la lista de periodos abiertos; no se abre ni se crea ningún periodo |

## Qué revierte (solo lo que existe)
- **(a) Stock:**
  - Por cada salida `reference_type='sale'` de esa venta, se crea una entrada igual, con el mismo producto, almacén, cantidad y costo, `reference_type='sale_system_void'` y `reference_id` = la venta.
  - El saldo se calcula como en `sale_void`, con fecha de hoy (Lima) y el periodo del día.
  - Si la venta no tiene salidas, no se crea nada.
- **(b) Asiento:**
  - Se busca el asiento de venta del documento: `entry_type='sale'`, glosa con el número, aprobado o contabilizado, que no sea reversa y sin reversa previa.
  - **Solo si existe** se crea la reversa (debe y haber invertidos, `is_reversal`, `reversal_of_entry_id`; el original queda con `reversed_on_entry_id`), con numeración correlativa del periodo del día.
  - **Si no existe ninguno, no se crea ninguno.** Es el caso de F030-000119.
- **(c) Estado:**
  - `status='cancelled'`. `sunat_status` queda vacío: SUNAT nunca lo recibió.
  - Leyenda en pantalla: **"Anulada — No enviado a SUNAT"**, con el motivo, el usuario y la fecha.
  - Nada se borra y el número queda consumido.

**Registro nuevo:** tabla `sale_system_void`. No toca tablas existentes. Guarda:
- venta, motivo, usuario y fecha;
- la respuesta de NubeFact de esa consulta;
- los ids de los movimientos de stock creados y del asiento de reversa (o "sin asiento");
- el duplicado advertido, si hubo uno.

**Efectos que ya resuelve el `status='cancelled'`:**
- sale de Cobranza y cuentas por cobrar, y del reporte de ventas en pantalla;
- de las comisiones sale con la rama separada `claude/comisiones-sin-anuladas`. Esta función no las toca.

**Lo que no se toca:** el PLE y el TXT. Según el diagnóstico, siguen incluyendo el documento hasta que el contador decida.

## Aviso de posible duplicado (advertencia, nunca bloqueo)
- **Busca otro documento con:**
  - la misma empresa, el mismo tipo y el mismo cliente;
  - total con una diferencia menor a 0.01;
  - creado dentro de ±48 horas;
  - aceptado por SUNAT (`aceptada` o `aceptada_con_observacion`).
- **"Duplicado muy probable"** si además tiene las mismas líneas: mismos productos (`inventory_item_id`, o la descripción si no hay producto) con las mismas cantidades.
- **Texto:** por ejemplo, *"F030-000120, mismo cliente, mismo monto y mismas líneas, 19 segundos después, aceptada"*.
- **Confirmación:** si hay candidatos, la anulación (y el reintento de la función 3) exige marcar una casilla de confirmación. El servidor rechaza sin esa marca y guarda lo que se advirtió.

## Rutas y pantalla
- **`GET /api/sales/<cid>/<id>/system-void/check`:**
  - devuelve si se puede o no, los bloqueos, los posibles duplicados y los periodos abiertos;
  - **no** consulta a NubeFact; eso se hace solo al confirmar.
- **`POST /api/sales/<cid>/<id>/system-void`** con `{reason, confirm_number, confirm_duplicate}`:
  - revalida todo;
  - hace la consulta nueva a NubeFact;
  - registra todo en una sola transacción.
- **Modal** con el resumen de lo que se va a revertir:
  - "2 entradas de stock: 20 NITRILO… y 24 GUANTE… en TDA FIKA CAPON";
  - "Asiento: no existe, no se crea reversa";
  - el aviso de duplicado;
  - el motivo, el número a escribir y el botón protegido por la función 1.

## Pruebas (base de prueba, NubeFact simulado)
1. **Caso real:**
   - F030-000119 sin enviar y sin asiento, más F030-000120 aceptada con las mismas líneas: se ve el aviso "duplicado muy probable, 19 segundos después";
   - al anular aparecen las 2 entradas (20 y 24) en TDA FIKA CAPON y el stock vuelve al valor correcto;
   - no se crea ningún asiento;
   - la 000119 sale de los reportes y de cuentas por cobrar;
   - F030-000120 y su asiento quedan idénticos.
2. Factura sin enviar **con** asiento (emitida desde cotización o con "Contabilizar"): se crea la reversa y los saldos quedan en cero.
3. Factura que **sí existe** en NubeFact: no se permite.
4. Con guía, con cobros, con nota de crédito, con periodo cerrado (julio/agosto) y con usuario sin permiso: bloqueados con su mensaje.
5. Doble clic: una sola anulación. Repetir sobre una ya anulada: rechazado.
6. Lo demás queda igual: ventas, Cobranza, Libro Diario y kardex de otros documentos.
