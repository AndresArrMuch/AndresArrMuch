# Anuladas con asiento de venta vivo: diagnóstico, origen del 621 y diseño (sin implementar)

## 1. Diagnóstico (solo lectura)
- Rama `claude/diag-anuladas-con-asiento`, script `backend/scripts/diag_anuladas_con_asiento.sql`.
- Es `BEGIN READ ONLY` … `ROLLBACK`, sin escrituras.
- Secciones:
  1. Detalle por documento y asiento.
  2. Resumen por empresa, mes y estado del periodo.
  3. Total abierto/cerrado (incluye el total de periodos cerrados).
  4. Documentos con más de un asiento vivo.
- **Prueba** en la base de prueba (`diag_anuladas_con_asiento_prueba.txt`):
  - una factura con asiento en un periodo cerrado (provisión desde cotización);
  - una factura con dos asientos vivos y una NC con asiento;
  - una factura con su asiento ya revertido, que queda excluida.
- La glosa se compara de forma exacta: `Venta <número> - ` o `Por la provision de la <tipo> <número>`. La cifra puede diferir unos céntimos de la consulta manual que usó `'Venta <número>...'`.

## 2. De dónde salen hoy el PDT 621 y los registros (lectura del código)
| Salida | Función (`tax_routes.py` y otras) | Fuente | Filtro |
|---|---|---|---|
| PDT 621 (IGV de ventas) | `generate_tax_declaration` → `_sum_sales_breakdown_for_period` | **Documentos** `sale` | empresa, periodo, `is_active` |
| Registro de ventas (Tributario) | `generate_tax_register` → `_sum_sales_for_period` | **Documentos** `sale` | empresa, periodo, `is_active` |
| PLE 14.1 | `_build_sales_ple_lines` | **Documentos** | empresa, periodo |
| TXT 14.1 | `_build_sales_sunat_lines` | **Documentos** | empresa, periodo, `is_active`; estado fijo '1' |
| Reporte de ventas en pantalla | — | Documentos | excluye `cancelled` y los electrónicos sin `pdf_path`/`sunat_status` |

- **Los asientos no intervienen en el 621 ni en los registros.** Revertir asientos no cambia ningún monto tributario ya calculado.
- **Las anuladas sí entran en el cálculo del IGV hoy:**
  - el 621 y el registro no filtran `status='cancelled'` ni `sunat_status`;
  - también entran los documentos no enviados.
- **Hallazgo previo que se mantiene:** las NC (07) se guardan con importes positivos y en el 621 se **suman** en lugar de restarse.
- `TaxRegister` y `TaxDeclaration` guardan los totales calculados al generar. Lo ya generado no cambia solo.
- **El riesgo contable** del hallazgo está en la contabilidad (balance, 12/40/70, Libro Diario/Mayor), no en el 621.
- **El riesgo tributario** es distinto e independiente: anuladas y NC mal sumadas dentro del 621. Hace falta una propuesta aparte; no se toca aquí.

## 3a. Corrección controlada de los asientos existentes
**Principio:** nunca editar ni borrar el asiento original. Por cada asiento vivo se crea **un asiento de reversa**, siguiendo el mismo patrón que ya usa la anulación de asiento manual (`manual_journal_routes.void_manual_journal`):
- débito y crédito invertidos, línea por línea, incluido el importe en moneda extranjera;
- `is_reversal=true` y `reversal_of_entry_id` = el original;
- el original queda con `reversed_on_entry_id` = la reversa;
- correlativo del periodo de la reversa, con un bloqueo `FOR UPDATE` del periodo;
- glosa `Reversa por anulacion de <número> - asiento <n.°>`.

**Opciones según el estado del periodo del asiento original:**

| Caso | Opción recomendada | Alternativas |
|---|---|---|
| Periodo **abierto** (FLUMISA: todos; FIKA: excepto julio y agosto) | **R1:** reversa con fecha = fecha del asiento original, en su mismo periodo. El mes queda como si la venta no hubiera existido, igual que la baja en SUNAT. | **R2:** reversa con fecha de hoy, en el periodo actual. Es más simple, pero deja el ingreso inflado en el mes original. |
| Periodo **cerrado** (FIKA julio y agosto) | **R2:** reversa en el **primer periodo abierto** (o el actual), con glosa que indique el periodo de origen ("anulada en jul-2026"). No se reabre ni se crea ningún periodo. | **R3:** que el contador registre el ajuste a mano con Asiento manual. **R4:** reabrir el periodo; no recomendado y fuera del alcance. |
| Factura anulada **con NC asociada** (columna `notas_credito`) | **No se revierte en automático:** queda en la lista de revisión manual. Si la NC también tiene asiento (hoy `post_sale` registra la NC con el mismo signo que una venta), revertir ambas o solo una depende de lo que el contador decida. | — |
| **Más de un asiento vivo** (sección 4) | Se revierten **todos**, porque la venta no existe. Primero los revisa el contador, ya que puede tratarse de una doble contabilización anterior. | — |

**Mecanismo propuesto:** un script o una ruta de administración con dos modos.
1. **Vista previa** (por defecto): devuelve exactamente lo que listaría el diagnóstico y lo que crearía (periodo, fecha y líneas de cada reversa). No escribe nada.
2. **Aplicar:** recibe la empresa, la opción (R1 o R2) y la **lista explícita de `sale_id` aprobada por el contador**. Funciona así:
   - una transacción por documento;
   - si un documento falla (periodo cerrado, asiento ya revertido), se omite y se informa, sin detener el resto;
   - el rol requerido es el mismo `MANUAL_JOURNAL_ROLE_PREFIXES`;
   - deja un registro en una tabla nueva `sale_void_reversal` con la venta, el asiento original, la reversa, la opción, el usuario, la fecha y el origen (`correccion` u `anulacion`).

**Orden sugerido:**
1. FLUMISA, con todos sus periodos abiertos y R1.
2. FIKA en periodos abiertos, con R1.
3. FIKA julio y agosto, con R2 o R3, según lo que decida el contador.
4. Volver a ejecutar el diagnóstico: debe dar 0 filas, salvo los casos con NC que queden en revisión manual.

## 3b. Corrección hacia adelante en `electronic/void` (y en `/void`)
**Comportamiento con el parámetro por empresa `anulacion_revierte_asiento` = `true`** (se guarda en `system_parameter`; **apagado por defecto**: si falta o es `false`, todo queda idéntico a hoy):

1. **Validación previa, antes de llamar a NubeFact.** La baja en SUNAT no se puede deshacer, así que todo se valida antes:
   - se ubican los asientos vivos del documento, con la misma regla del diagnóstico;
   - si hay alguno, el periodo de la fecha de hoy (Lima) debe existir y estar abierto. Si no, se **bloquea** con el mensaje "El periodo <mes> está cerrado; periodos abiertos: …" y **no se llama a NubeFact**;
   - si el documento tiene una NC asociada y no anulada, se bloquea (igual que en la función 2).
2. **Se llama a NubeFact** (sin cambios).
3. **Si la respuesta es correcta,** en **una sola transacción** se hacen: estado, stock (como hoy) y reversa de cada asiento vivo, con fecha de hoy en el periodo de hoy. Al original no se le cambia nada, salvo `reversed_on_entry_id`.
   - Si la venta era de un periodo ya cerrado, la reversa va igual en el periodo abierto de hoy.
   - Si **no hay asiento**, no se crea ninguno (como el caso F030-000119).
4. **Si la transacción falla después del OK de SUNAT** (es raro): se guarda el estado `anulada` y se registra una "reversa pendiente" en `sale_void_reversal`, con el aviso "Anulada en SUNAT; el asiento quedó pendiente de reversa". Un botón **"Revertir asiento pendiente"** lo completa, y es idempotente (ver 3c).
5. **Alcance:**
   - primera activación solo para 01 y 03;
   - las NC y ND (07/08) en una segunda etapa, porque su asiento hoy tiene el signo de una venta (hallazgo aparte);
   - la reversa de un asiento invierte exactamente lo que tenía, sea cual sea su signo.

## 3c. Evitar re-anular y la reversa duplicada
- **Hoy `/electronic/void` no rechaza un documento ya anulado** (solo `/void` lo hace). Una segunda llamada exitosa volvería a sumar el stock. Propuesta:
  - rechazar con `ALREADY_CANCELLED` si `status='cancelled'` o `sunat_status='anulada'`;
  - aplicarlo **siempre**: no depende del parámetro, porque es una protección.
- **Concurrencia:** la función 1 (`single_flight`, candado por documento) ya evita dos anulaciones a la vez. Se agrega `SELECT … FOR UPDATE` sobre la venta y sobre el asiento original.
- **Reversa única:** solo se revierte un asiento con `reversed_on_entry_id` vacío y sin ningún asiento que tenga `reversal_of_entry_id` = el original. Opcional, como garantía en la base de datos: un índice único parcial en `journal_entry(reversal_of_entry_id) WHERE is_active AND reversal_of_entry_id IS NOT NULL`. Requiere comprobar antes que no haya duplicados.
- **Stock:** no se crean entradas `sale_void` si ya existen para esa venta.
- **Corrección 3a y 3b juntas:** comparten la misma función y el mismo registro, así que una no duplica a la otra.

## Riesgos
1. **El enlace es la glosa:** el asiento se vincula a la venta solo por la glosa. Si alguien editó la glosa a mano, el asiento no se detecta y queda vivo. Mitigación: comparar el diagnóstico con el total de la cuenta 12 por cliente y, a futuro, un `sale_id` en el asiento (cambio de esquema, aparte).
2. **Asientos en periodo cerrado:** una reversa en otro mes cambia los saldos del mes actual, no los del mes original. El contador debe saberlo para sus estados de julio y agosto.
3. **NC con asiento del mismo signo:** revertir la factura sin revisar la NC puede dejar la cuenta 12 con un saldo raro. Por eso estos casos van a revisión manual.
4. **Cobros:** si una anulada tiene cobros aplicados, la reversa deja un saldo acreedor en la cuenta 12 del cliente. Hay que listarlos antes.
5. **Volumen:**
   - 71 documentos y S/ 276,135.57 con IGV;
   - aplicar por empresa y con lista aprobada, nunca todo de una vez;
   - para volver atrás basta anular la reversa con su propia reversa, sin borrar nada.
6. **Lo que no cambia:**
   - el 621, los registros, el PLE y el TXT, que salen de documentos;
   - la diferencia tributaria se trata aparte.

## Activación segura
1. Ejecutar el diagnóstico en producción y que el contador apruebe la lista y la opción por caso.
2. Instalar el código con `anulacion_revierte_asiento` apagado. Comportamiento idéntico, más el bloqueo de re-anulación.
3. Corrección 3a en vista previa, luego aplicarla por empresa, y volver a ejecutar el diagnóstico.
4. Encender el parámetro primero en FLUMISA (todos sus periodos están abiertos), probar una anulación real controlada y después encenderlo en FIKA.
5. Volver atrás: apagar el parámetro. No se borra ningún dato.
