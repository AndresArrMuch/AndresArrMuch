# Función 3 ampliada: "Documentos sin respuesta de SUNAT"

**Estado:** diseño para aprobar. Sin programar.

**Base:** el main que quede tras instalar `claude/rechazar-reanulacion`. Se trabaja en una rama nueva, `claude/sunat-sin-respuesta`.

## 0. Hallazgos del código que cambian el diseño (verificados con NubeFact simulada)

| # | Hallazgo | Evidencia | Consecuencia |
|---|---|---|---|
| H1 | **El token de NubeFact llega al navegador.** `_post_json` devuelve `request` (el payload completo, con `TOKEN`). Las rutas lo reenvían como `provider_response` (si va bien) o como `data` del error (si falla). | Un usuario **Vendedor-FIKA** consultó el estado y la respuesta JSON contenía `"TOKEN": "TOKEN-PRUEBA"`. | Cualquier usuario puede ver el token en el navegador (F12 › Red). Propongo una rama mínima aparte, **antes** que la función 3: quitar `request`, `url` y los base64 de toda respuesta al navegador. Después conviene **rotar el token** en NubeFact. |
| H2 | **El estado se mapea mal.** `_map_sunat_status_from_response` busca `'acept'` en el texto de **toda** la respuesta. Como la clave `aceptada_por_sunat` siempre lo contiene, devuelve `aceptada` aunque valga `false` o diga "RECHAZADA". | `{'aceptada_por_sunat': False, 'sunat_description': 'La Factura ha sido RECHAZADA'}` devuelve `aceptada`. | Un documento rechazado o en proceso puede quedar como "aceptada". La función 3 usa los campos explícitos: `aceptada_por_sunat`, `sunat_responsecode` y `sunat_description`. |
| H3 | **Causa del duplicado F030-000119/000120.** En la venta directa la venta se crea primero y luego se envía. Si el envío falla, la pantalla dice **"No se pudo crear venta: …"** aunque la venta **sí quedó creada**, y el formulario sigue lleno. | `index.html`, flujo `createSale`: venta → precheck → send → `catch` muestra "No se pudo crear venta". | El usuario vuelve a pulsar Guardar y crea una segunda factura. Ninguna función actual lo evita. |
| H4 | **El mensaje del proveedor no se guarda en ningún lado.** Solo viaja al navegador. | El 502 de F030-000119 no se pudo explicar. | Se resuelve con la tabla de registro (a). |
| H5 | **La consulta de estado no es solo lectura:** con cualquier respuesta OK guarda `sunat_status`, con el mapeo de H2. | `get_sale_sunat_status`. | Hay que corregirla junto con H2. |

## 1. Lo que ya estaba pedido

**Después de un error de envío,** dentro del mismo candado de la función 1, el servidor consulta a NubeFact (`get_invoice_status`) **una sola vez**, sin reenviar:

| Respuesta de la consulta | Qué se guarda | Qué ve el usuario |
|---|---|---|
| Existe y `aceptada_por_sunat=true` | `sunat_status` (con el mapeo corregido), `sunat_ticket` y PDF/XML/CDR, igual que un envío correcto | "El documento sí llegó a SUNAT y está aceptado" (recuperado) |
| Existe, pero en proceso o rechazado | El estado real (`en_proceso` o `rechazada`) y el ticket | El estado y el mensaje de SUNAT |
| **No existe** (código 24 / "Documento no existe") | **No se cambia `sunat_status`**: sigue vacío. Queda el registro en la tabla de (a) con resultado `no_existe` | "**No enviado a SUNAT**: <mensaje exacto del proveedor>. Puedes reintentar el envío o anularlo solo en el sistema." |
| La consulta también falla (red, tiempo de espera, 5xx, token) | Nada en la venta; queda el registro | "**Sin confirmar**: no se pudo saber si llegó. No lo vuelvas a crear; usa *Consultar estado* más tarde." |

**Por qué "No enviado" no se guarda en `sunat_status`:** el reporte de ventas del periodo, las comisiones, el PLE y el TXT miran `sunat_status`. Un valor nuevo los cambiaría. La condición se **deriva** del último registro de la tabla de (a), así que no se toca ningún reporte.

**Mensaje de la venta directa (H3).** Si la venta se creó y el envío falló, el mensaje pasa a ser:

> "La venta F030-000119 QUEDÓ REGISTRADA pero NO llegó a SUNAT (<mensaje del proveedor>). No la vuelvas a crear: reintenta desde Ventas › Sin respuesta de SUNAT."

Además, el botón **Guardar** del formulario queda bloqueado para esos mismos datos hasta limpiar el formulario.

**Opcional, con tu OK:** un aviso del servidor al crear una venta igual a otra no enviada de los últimos 10 minutos. Se considera igual si coinciden el cliente, el total y las líneas. Es solo un aviso con confirmación, nunca un bloqueo.

**Botón "Reintentar envío"** (`POST /api/sales/<cid>/<id>/electronic/retry`):
- **Roles:** solo Sistema, Gerente y Administrador, con `MANUAL_JOURNAL_ROLE_PREFIXES`.
- **Candado y estado:** usa el candado de la función 1. Rechaza los documentos anulados (rama 1).
- **Pasos:**
  1. **Consulta primero.** Si el documento ya existe en NubeFact, lo recupera **sin reenviar** (idempotente).
  2. Si no existe, busca **posibles duplicados** con la regla de la función 2: mismo tipo, cliente y total; ±48 h; aceptado; "muy probable" si además coinciden las líneas. Si hay alguno, responde 409 y pide marcar la confirmación.
  3. Envía con la lógica actual de envío y deja registro de todo.
- **Doble clic:** un solo envío. Con el documento ya aceptado: no hace nada y lo dice.

## 2. (a) Registro de cada llamada al proveedor: tabla nueva `electronic_provider_log`

**Columnas:**
- `id`, `company_id`, `sale_id` (o `workflow_id` para guías), `document_number`, `document_type`;
- `action`: `send`, `status`, `void`, `retry`, `get_document`, `send_guide` o `guide_status`;
- `user_id`, `started_at`, `finished_at` (UTC; en pantalla se muestra en hora de Lima), `duration_ms`;
- `outcome`: `ok`, `provider_error`, `timeout`, `network_error`, `not_configured`, `no_answer` o `no_existe`;
- `http_status`, `provider_code` (`codigo`) y `provider_message` (hasta 2000 caracteres);
- `response_excerpt`: la respuesta **limpia**, hasta 4000 caracteres.

**Limpieza obligatoria:** se quitan del registro, y también de la respuesta al navegador (H1):
- las claves `request`, `url`, `TOKEN` y `Authorization`;
- cualquier clave que contenga `token`, `password`, `secret` o `api_key`;
- los campos base64 (`pdf_zip_base64`, `xml_zip_base64`, `cdr_zip_base64`).

Las cabeceras no se guardan nunca. Una prueba automática comprueba que el token no aparece ni en la tabla ni en ninguna respuesta.

**Dónde se escribe:** en `nubecont_service._post_json`, el único punto por el que pasan todas las llamadas.
- Antes de llamar se inserta la fila `started`. Al volver se actualiza con el resultado.
- Si gunicorn mata el proceso a mitad de la llamada, la fila queda `no_answer`. Esto hoy no deja rastro y explica un 502 de nginx.
- La escritura va en una conexión aparte, como el candado de la función 1. Queda guardada aunque la venta haga rollback, y nunca rompe el envío: si el registro falla, solo se avisa en el log del servicio.
- El contexto (venta, acción, usuario) lo pone cada ruta en `flask.g`.

**Tiempo de espera:** `requests.Timeout` se registra como `timeout`, distinto de otro error de red. Es el caso en que NubeFact pudo haber creado el documento, y por eso la consulta posterior es obligatoria.

**Gunicorn:**
- El repositorio no fija `--timeout`. Si el servicio tampoco lo hace (se verifica con `systemctl cat cea-erp`), gunicorn mata la petición a los 30 s.
- El envío con reintento de correlativo hace hasta 2 llamadas de 20 s.
- **Propuesta:** fijar `--timeout 75` en el servicio (cambio de servidor, con tu OK) o bajar `NUBECONT_TIMEOUT`.

## 3. (b) Panel "Documentos sin respuesta de SUNAT"

**Dónde:** en Ventas, como una pestaña nueva junto a la lista de comprobantes, más una tarjeta en el Dashboard. Ventas es donde se emite, y quien envía lo ve en el mismo lugar.

**Contador:** un número rojo junto a "Ventas" en el menú y en la tarjeta del Dashboard.
- Solo lo ven los roles Sistema, Gerente y Administrador; para el resto no existe ni la ruta ni el número.
- Se actualiza al entrar y cada 2 minutos con `GET .../electronic/pending-count`, una consulta liviana con índice.

**Qué lista** (`GET /api/sales/<cid>/electronic/pending`):
- **Filtro:** documentos electrónicos 01, 03, 07 y 08; activos; `status <> 'cancelled'`; `sunat_status` y `pdf_path` vacíos; creados hace más de **10 minutos** (parámetro por empresa).
- **Empresas:** de **todas** las empresas donde el usuario tiene una cuenta con esos roles (FIKA y FLUMISA), con una columna Empresa.
- **Columnas:**
  - número, tipo, cliente, total y moneda, empresa;
  - hora de creación (Lima) y antigüedad;
  - situación: *No enviado*, *Sin confirmar*, *Nunca intentado* (documentos anteriores al registro), *Antiguo* (más de 3 días);
  - último mensaje del proveedor, con fecha y usuario;
  - qué mueve el documento: stock, asiento, guía y cobro;
  - posible duplicado aceptado.
- **Acciones:** *Consultar estado* (corregido, ver H2 y H5) y *Reintentar envío* (sección 1). Más adelante, *Anular solo en el sistema* (función 2).
- **Documentos antiguos** (las boletas de céntimos del 05/10, FC50-000002 de FLUMISA, F001-000003 de prueba):
  - aparecen con la etiqueta *Antiguo*;
  - solo se ofrece *Consultar estado* sin pedir nada;
  - *Reintentar envío* pide confirmar con el aviso "SUNAT puede rechazarlo por fecha de emisión (<fecha>)";
  - **ninguna acción destructiva y nada automático.**
- **Vista previa en producción, ya disponible y solo de lectura:** rama `claude/diag-sin-respuesta-sunat` (commit `29e5853`). Ver el comando en la sección 6.

## 4. (c) Reintento automático que cambia el correlativo: cómo funciona hoy

**Código:** `send_sale_to_sunat`, después de un envío fallido.

**Cuándo ocurre:** se cumplen las tres condiciones.
1. El mensaje del proveedor coincide con `registrado.*?es el\s+(\d+)`, por ejemplo "…el último correlativo registrado es el 118".
2. No es un mensaje de "documento ya existe", que tiene su propio camino.
3. La venta no tiene `sunat_ticket`.

**Qué hace:**
1. Calcula `N = último + 1` con 6 dígitos.
2. Si **en la base** hay otra venta de la misma empresa y serie con ese número, no cambia nada y responde 400 `INVALID_PROVIDER_CORRELATIVE`.
3. Si no la hay:
   - **cambia** `correlative` y `document_number` de la venta a N;
   - **hace commit inmediatamente, antes de reenviar**;
   - reenvía **una vez**. Si el reenvío falla, responde 502, pero la venta **ya quedó con el número N**.

**Qué número deja:** siempre el que NubeFact espera (`último + 1`), sea menor o mayor que el original.

**Riesgos:**
1. **Cambio de número sin avisar.** El vendedor vio F030-000119 y la factura termina con otro número. El asiento que se crea al emitir desde una cotización ("Por la provision de la … F030-000119") **conserva el número viejo**. Ese asiento deja de coincidir, y ni el Libro Diario ni el diagnóstico de anuladas lo encuentran.
2. **Huecos o saltos en el sistema.** Si NubeFact está atrás (último 110 y nosotros 119), la venta pasa a 111. Los números 112 a 118 que existan en la base sin enviar quedan fuera de orden, y cada uno se renumera cuando se envíe. Si NubeFact está adelante (porque se emitió desde su panel), la venta salta hacia arriba y el número original queda libre en el sistema. En SUNAT no hay hueco: allí nunca existió.
3. **Número cambiado sin documento.** El cambio se guarda antes del reenvío. Si el reenvío falla, la venta queda con el número nuevo sin existir en SUNAT, y otro intento puede volver a renumerarla.
4. **Duplicado:** no puede haber dos ventas con el mismo número en la base, porque lo impiden la revisión previa y la restricción única `uq_sale_company_series_corr`. Pero dos envíos a la vez de la **misma serie** pueden chocar: el candado de la función 1 es por documento, no por serie. El segundo terminaría en error 500 por la restricción.

**Propuesta, sin cambiar nada hasta tu OK:**
- **Parámetro por empresa `nubefact_corregir_correlativo`, apagado por defecto.**
  - **Apagado:** no se renumera. Se responde 400 con "NubeFact espera el número N (el documento F030-000119 no se envió). Revisa la serie antes de reintentar" y queda en el registro (a).
  - **Encendido:** se renumera solo si el reenvío es **aceptado**; si falla, se vuelve al número original. Queda el registro "cambió de X a N" en la tabla y en `notes`, y se avisa en pantalla. Si existe un asiento con el número viejo en la glosa, se bloquea y se pide revisión.
- **Antes de decidir:** con la tabla (a) en producción se sabrá cuántas veces ocurre. Hoy no se puede saber, porque el mensaje no se guarda.

## 5. Pruebas planificadas (base de prueba y NubeFact simulada; nunca la real)

La NubeFact simulada se amplía para:
- guardar estado (el documento "existe" después de un envío);
- simular demoras para el tiempo de espera, errores 400, 401 y 500, y el mensaje de "correlativo fuera de rango".

**Casos:**
1. Envío correcto: queda el registro `ok`; el token no aparece en la tabla ni en la respuesta.
2. Error 400 con documento inexistente: *No enviado*, con el mensaje exacto guardado; `sunat_status` vacío; aparece en el panel después de 10 minutos.
3. Tiempo de espera, con NubeFact que **sí** creó el documento: la consulta lo recupera como aceptado y guarda los archivos. Sin duplicado.
4. Tiempo de espera y la consulta también falla: *Sin confirmar*, sin reenvío.
5. Mapeo corregido: rechazada, en proceso y aceptada con observación. Prueba unitaria más API.
6. Reintentar:
   - con el documento ya existente, recupera sin reenviar;
   - con un duplicado, pide confirmación;
   - con doble clic, hace un solo envío;
   - con un rol no autorizado, 403;
   - con un documento anulado, 400.
7. Panel y contador:
   - visibles solo para los 3 roles;
   - muestran ambas empresas;
   - los antiguos aparecen sin acciones destructivas;
   - el corte de 10 minutos funciona.
8. Venta directa con envío fallido: aparece el mensaje "QUEDÓ REGISTRADA" y Guardar queda bloqueado. Main contra rama, con Playwright.
9. Correlativo fuera de rango: con el parámetro apagado (por defecto) no renumera; con el parámetro encendido, solo si se acepta.
10. Lo demás queda igual: reportes, comisiones, PLE y TXT dan lo mismo en main y en la rama para documentos sin cambios.

## 6. Orden de entrega propuesto
1. `claude/rechazar-reanulacion`: **lista** (abajo).
2. **(Nueva, recomendada antes de la función 3)** `claude/sin-token-al-navegador`: H1, quitar el token y los base64 de las respuestas. Rama mínima, con tu OK. Luego, rotar el token.
3. `claude/sunat-sin-respuesta`: la función 3 según este diseño, cuando lo apruebes. Incluye la corrección H2/H5 y el mensaje de H3.
4. La función 2 y, después, el diagnóstico de las notas de crédito.

**Vista previa del panel en producción (solo lectura):**
```
cd ~/cea-erp && git fetch origin && git show origin/claude/diag-sin-respuesta-sunat:backend/scripts/diag_documentos_sin_respuesta_sunat.sql > /tmp/diag_sin_respuesta.sql && sudo -u postgres psql cea_erp_prod -f /tmp/diag_sin_respuesta.sql
```
