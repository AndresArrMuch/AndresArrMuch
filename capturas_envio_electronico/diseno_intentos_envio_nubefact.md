# Envío electrónico: registro de intentos, estado "pendiente de envío", lista y reintento seguro (diseño, sin programar)

Base: main `2d95f94` con `02d1d29`/`c0bd93a`/`b11f7eb` (no tocan esta parte). Retoma la "función 3" ya aprobada en sus puntos (a)–(d) y la concreta para este caso.

## 0. Qué pasa hoy (leído del código)
- La venta se guarda con `status='emitted'` y `sunat_status` vacío; luego la pantalla llama a `POST /api/sales/<empresa>/<venta>/electronic/send` (`send_sale_to_sunat`).
- En esa ruta, todo error termina en `error_response(...)` **sin escribir nada en la base**:
  - validaciones propias antes de llamar (serie, motivo de NC, documento referido no aceptado, documento del cliente): 400;
  - error de red o de tiempo (`_post_json` devuelve `status_code 0` con el texto de la excepción): 502 `NUBECONT_SEND_ERROR`;
  - rechazo del proveedor (4xx con mensaje): 400/502 con el mensaje;
  - "duplicado" → intenta recuperar; si no puede, 502 `NUBECONT_RECOVERY_FAILED`.
- `electronic/status` (consultar) tampoco guarda nada si NubeFact responde error, por ejemplo "Documento no existe".
- `AuditLog` existe (`app/utils/logger.py`), pero estas rutas no lo usan.
- Resultado: B030-000016 queda `emitted` con `sunat_status` vacío y el motivo solo lo vio quien estaba en pantalla.
- Ya existe (función 1, instalada) un candado por documento: `@single_flight('sale_id')` en send, status y void. Dos envíos simultáneos del mismo documento no son posibles.

## 1. Guardar cada intento: tabla `electronic_send_attempt`
Recomiendo **tabla de intentos** (no un campo en la venta): guarda la historia completa y sirve también para guías y bajas.

| Campo | Contenido |
|---|---|
| `id`, `company_id` | |
| `sale_id` (o `workflow_id` para guías) | documento |
| `document_number` | copia del número en ese momento (el número puede cambiar si se corrige correlativo) |
| `operation` | `send`, `status`, `recover`, `void`, `guide` |
| `outcome` | `en_curso`, `aceptado`, `enviado_sin_cdr`, `error_validacion`, `rechazado_proveedor`, `sin_respuesta`, `no_existe`, `recuperado`, `error_consulta` |
| `http_status` | código HTTP del proveedor (0 = no hubo respuesta) |
| `error_code` | nuestro código (`NUBECONT_SEND_ERROR`, `REFERENCED_DOCUMENT_NOT_ACCEPTED`, …) |
| `provider_code`, `provider_message` | código y mensaje tal como los devolvió NubeFact (texto recortado a 2000) |
| `started_at`, `finished_at`, `duration_ms` | |
| `user_id` | quién lo intentó |

Reglas:
- **Nunca se guarda el token ni el payload completo** (decisión (d)). Solo mensaje, códigos y tiempos. El mensaje se pasa por la misma limpieza de secretos de la rama del token cuando esté instalada.
- **Se escribe con una conexión aparte y su propio commit** (igual que el candado de la función 1). Así, si la venta hace rollback o el proceso cae, el intento queda registrado.
- **Antes de llamar a NubeFact** se inserta la fila con `outcome='en_curso'` y se confirma; al volver se actualiza. Si el proceso muere a mitad (gunicorn reinicia, timeout de 120 s), la fila queda `en_curso`: eso ES el rastro de "se intentó y no sabemos si llegó".
- Además, una línea en `AuditLog` por cada intento fallido ("Envío electrónico fallido B030-000016: <mensaje>"), para que aparezca en la auditoría que ya se revisa.

## 2. Estado "pendiente de envío"
- **No se cambia `status`** (`emitted` lo usan cobranzas, reportes, comisiones, asientos) **ni se escribe en `sunat_status`** (decisión (c); además es varchar(20) y alimenta el PLE).
- El estado de envío se **calcula** con lo que ya existe más el último intento:

| Estado mostrado | Condición |
|---|---|
| Aceptado | `sunat_status = 'aceptada'` (con la regla estricta de la función 3) |
| Anulado | `status='cancelled'` o `sunat_status='anulada'` |
| **Pendiente de envío** | electrónico, `sunat_status` vacío y **sin** intentos, o último intento `error_validacion` |
| **Error de envío** | último intento `rechazado_proveedor` o `no_existe` |
| **Sin respuesta (verificar)** | último intento `sin_respuesta`, o `en_curso` con más de 3 minutos |
| Enviando | `en_curso` con menos de 3 minutos |

- Ventaja: los documentos ya existentes sin `sunat_status` (como B030-000016) aparecen **solos** como "Pendiente de envío", sin migrar ni modificar ninguna venta.
- En la lista de ventas, en la columna SUNAT, se muestra la etiqueta (en lugar de vacío) con el motivo al pasar el mouse.

## 3. Lista "Documentos electrónicos pendientes o con error"
- Visible para Sistema, Gerente y Administrador (lo ya aprobado), con contador en el menú. Pregunta: ¿se suma Tesorería o Ventas?
- Por empresa activa (FIKA o FLUMISA), con filtro de fechas.
- Columnas: documento, fecha de emisión, cliente, total, estado de envío, **motivo** (último `provider_message` o `error_code`), número de intentos, último intento (fecha y usuario), días desde la emisión (SUNAT da plazo limitado para enviar boletas y facturas).
- Al abrir una fila: la historia de intentos.
- Acciones: **"Consultar en NubeFact"** (solo lectura) y **"Reintentar seguro"** (punto 4). Ninguna acción automática.
- Ruta: `GET /api/sales/<empresa>/electronic/pending` (solo lectura).

## 4. Reintento seguro (consultar primero, luego enviar)
`POST /api/sales/<empresa>/<venta>/electronic/retry`, con el mismo candado por documento:
1. **Consulta** en NubeFact (`get_invoice_status`, operación `consultar_comprobante`). Se registra como intento `status`.
2. Según la respuesta:
   - **Existe** en NubeFact → **no se reenvía**. Se recupera ticket, estado y PDF/XML/CDR (la misma lógica que hoy usa el caso "duplicado") → `recuperado`.
   - **"No existe"** (mensaje reconocido explícitamente) → se envía con `send_invoice` → `aceptado` / `rechazado_proveedor` / `sin_respuesta`.
   - **Cualquier otra respuesta o error de red al consultar** → **no se envía**. Queda `error_consulta` con el mensaje y se avisa "No se pudo confirmar en NubeFact; inténtelo más tarde". Nunca se envía a ciegas.
3. Si el último intento fue `error_validacion` (nunca llegó a NubeFact), se puede saltar la consulta, pero igual se hace: es barata y protege.
- **Mensajes reconocidos como "no existe":** se armará la lista con los textos reales que devuelva NubeFact (el de B030-000016: "Documento no existe"). Por eso el punto 1 va primero: guardar los mensajes permite confirmar los textos antes de confiar en ellos. Hasta entonces, solo ese texto exacto (sin distinguir mayúsculas) cuenta como "no existe".
- **La corrección automática de correlativo** (bloque `_extract_last_registered_correlative`, que hoy cambia el número y reenvía) queda detrás del parámetro `nubefact_corregir_correlativo`, apagado (ya aprobado). Con él apagado, ese caso queda como `rechazado_proveedor` con el motivo.
- El botón "Enviar a SUNAT" que ya existe en la venta pasa a usar este mismo camino (consulta antes de enviar) cuando el documento ya tiene algún intento previo.

## 5. Pantalla después de un fallo (venta directa) — ya aprobado en (a)
"QUEDÓ REGISTRADA con el número X pero NO llegó a SUNAT" + motivo + botones "Reintentar envío" (usa el punto 4) y "Nueva venta", con aviso de no repetir la venta.

## 6. Pruebas previstas (solo con NubeFact simulada)
- Error de validación antes de llamar (NC con documento referido no aceptado): intento `error_validacion`, venta sin cambios, aparece como pendiente con el motivo.
- Rechazo del proveedor: `rechazado_proveedor` con el mensaje exacto.
- Caída de red / timeout: `sin_respuesta`; el reintento consulta, la simulada dice "existe" → `recuperado` sin segundo envío (se cuenta que la simulada recibió un solo envío).
- Proceso interrumpido a mitad: fila `en_curso` → a los 3 minutos "Sin respuesta (verificar)".
- "Documento no existe" (caso B030-000016) → reintento envía una sola vez → aceptado.
- Consulta con error de red → no envía.
- Rollback de la venta: el intento sigue grabado (conexión aparte).
- Doble clic en "Reintentar": 409 por el candado; un solo envío.
- Lista: FIKA y FLUMISA por separado, roles permitidos y no permitidos; los documentos viejos sin `sunat_status` aparecen sin migración.
- Ningún token en la tabla, en la respuesta ni en el registro del servicio.

## 7. Qué NO toca
- Ventas ya emitidas: no se cambian `status`, `sunat_status`, número ni importes de nada existente. Solo se crea la tabla nueva (vacía al instalar).
- NubeFact y SUNAT reales: nada en las pruebas. B030-000016 no se reenvía al instalar; queda en la lista para que alguien pulse "Consultar" o "Reintentar seguro" cuando lo decidan.
- PLE, TXT, asientos, cobros, periodos.

## 8. Riesgos
- Si NubeFact responde "no existe" para un documento que sí recibió (inconsistencia del proveedor), el reintento lo enviaría; el propio NubeFact lo rechazaría como duplicado y el código actual lo recupera. Riesgo bajo.
- La tabla crece con cada intento (incluye consultas). Volumen esperado bajo; se puede limpiar a los 12 meses.
