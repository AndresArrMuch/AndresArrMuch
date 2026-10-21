# Revisión integral de la emisión electrónica (solo lectura, sin programar)

- **Base:** main del servidor `710e86b`.
- **Rama de diagnóstico:** `claude/diag-emision-electronica`. Trae dos scripts de solo lectura: `backend/scripts/diag_emision_electronica.sql` y `backend/scripts/diag_emision_registro_servidor.sh`.
- **Qué no se tocó:** producción, NubeFact, SUNAT ni documentos.
- **Líneas de código:** las referencias son a `710e86b`. `index.html` es `backend/index.html`; `sale_routes` es `backend/app/routes/sale_routes.py`.

---

## Resumen
1. **El error de envío no se guarda en ninguna parte.** Cualquier fallo después de guardar la venta (de validación, de red, del proveedor o de la pestaña) deja el documento en `emitted` con `sunat_status` vacío. El motivo solo existe en la pantalla de quien emitía.
2. **No hay forma de reintentar desde la pantalla.** Los manejadores de "Enviar a SUNAT", "Consultar estado" y "Contabilizar" existen, pero ninguna plantilla dibuja sus botones. Por eso F020-000214 solo se pudo enviar con un script.
3. **Para una venta de tienda, el envío de la pantalla y el del script son la misma petición:** el mismo cuerpo y la misma ruta, y los dos salen del servidor hacia NubeFact. La diferencia no está en el contenido. El primer intento **no llegó a registrarse en NubeFact** por algo transitorio (tiempo, red, reinicio, sesión o pestaña) o **ni siquiera se llamó**. Con lo guardado hoy no se puede saber cuál fue. El registro de nginx (script 2) puede decirlo.
4. **La clave de firma de sesiones de 19 bytes es exactamente el valor por defecto escrito en el código:** `config.py:13`, `'cea-jwt-secret-2024'`. Quien tenga el repositorio puede fabricar una sesión válida de cualquier usuario. Esto pasa a **prioridad 1**.

---

## A1. Puntos donde un documento puede quedar guardado sin respuesta de NubeFact

### Facturas y boletas desde "Venta" (`createQuickSale`, index.html 15806–15937)
| # | Momento | Qué pasa | Línea |
|---|---|---|---|
| 1 | Se guarda la venta | `POST /api/sales/<empresa>` hace commit (`_create_sale_inner`, sale_routes 3342). Desde aquí el documento existe con número. | index.html 15876 |
| 2 | **División DIGEMID** | `create_sale` crea dos documentos, cada uno con su propio commit (sale_routes 3083–3092). Si el segundo falla, devuelve error `PARTIAL_SALE_SPLIT_FAILURE`. **El primero queda guardado** y la pantalla dice "No se pudo crear venta". Nunca se envía. | sale_routes 3094–3102 |
| 3 | Validación previa | Si falla la red o la sesión, o si `ok: false`, sale "Venta registrada, pero no enviada". No se guarda nada. | index.html 15910–15916 |
| 4 | Envío | `saleSendSunat`. Si devuelve error (400, 409, 502 o 504), se ve el mensaje y el documento queda sin respuesta. | index.html 15917 |
| 5 | **Mensaje engañoso** | Cualquier error en 3 o 4 cae en el mismo `catch`, que dice **"No se pudo crear venta: …"** aunque la venta SÍ se creó. Quien vende puede repetirla (con otro correlativo) y dejar la primera colgada. | index.html 15930–15933 |
| 6 | Pestaña cerrada, recarga o pérdida de wifi entre 1 y 4 | No queda ningún rastro. | — |
| 7 | **Sesión vencida** (24 h) entre 1 y 4 | `api()` cierra la sesión ante un 401 o 422 y lanza "Tu sesión expiró". El documento ya está guardado. | index.html 1644–1650 |
| 8 | Varios documentos (división) | El bucle se corta en el primer error; los que siguen quedan sin enviar. | index.html 15903–15920 |

### Emitir desde el flujo comercial (`wf-emit`, index.html 24105–24152)
Tiene los puntos 3, 4, 6 y 7. Además, **no llama a `/post` (Contabilizar)** después del envío. Hay que confirmar si la ruta de emisión del flujo contabiliza por su cuenta.

### Notas de crédito (`_finalizarNotaCredito`, index.html 23494–23516)
- Crea la NC (commit) y la envía **sin validación previa**.
- Si falla, muestra "generada, pero no se pudo enviar" y nada más.
- Causa frecuente: el servidor exige que el documento referido esté `aceptada` en nuestra base (sale_routes 3684–3693). Si el referido quedó vacío o mal marcado, la NC se rechaza **antes** de llegar a NubeFact.
- La NC nunca llama a `/post`. Eso explica las 8 NC sin asiento.

### Notas de débito
Mismo patrón que las NC (creación y envío separados).

### Lado del servidor (`send_sale_to_sunat`, sale_routes 3552–3869)
| # | Caso | Qué guarda | Línea |
|---|---|---|---|
| 9 | Validaciones propias (serie, motivo de NC, referido) | Nada; responde 400 | 3609–3693 |
| 10 | Error de red o tiempo hacia NubeFact (`status_code 0`) | Nada; responde 502 con el texto de la excepción | nubecont_service 225–233, sale_routes 3826–3832 |
| 11 | NubeFact rechaza (4xx) | Nada; responde 400 o 502 con su mensaje | 3700–3832 |
| 12 | "Ya existe" y la recuperación falla | Nada; responde 502 `NUBECONT_RECOVERY_FAILED` | 3730–3797 |
| 13 | **Corrección automática de correlativo** | Cambia el número y **hace commit antes** de reenviar. Si el reenvío falla, el documento queda con otro número y sin respuesta. | 3799–3832 |
| 14 | NubeFact acepta, pero la descarga de PDF/XML/CDR tarda (hasta 3 × 30 s, **antes** del commit) | Si el proceso se corta aquí, **NubeFact tiene el documento y nuestra base no**. Es el síntoma contrario: aceptada allá, vacía aquí. | 3845–3867, electronic_storage 42–160 |
| 15 | Estado mal interpretado | Ver A4 y B3: `aceptada_por_sunat: false` se guarda como `aceptada`. | 167–179 |

### Consultar estado (`get_sale_sunat_status`, sale_routes 3900–3922)
Si NubeFact responde un error (por ejemplo "Documento no existe", código 24), devuelve 502 y no guarda nada. Si responde 200 con un error dentro del cuerpo, el mapeo por subcadenas puede escribir `enviado` o incluso `aceptada`.

### Baja (`low_sale_in_nubecont`, 3927–3960)
- **Riesgo distinto:** marca `cancelled` y `anulada` apenas NubeFact acepta el **pedido** de baja (HTTP 2xx), sin confirmar el ticket de SUNAT. Si SUNAT rechaza después la baja, el sistema la da por anulada. No es este caso, pero entra en la lista de "sin respuesta real".
- La re-baja ya está bloqueada desde `5b48984`.

### Guías (issue-guide, send-guide)
- Se numeran y guardan antes de enviar. Si falla el envío, la pantalla dice "Guía emitida. Falló el envío…" (index.html 24064–24070).
- Hay recuperación por `guide_created_anyway`, pero tampoco se guarda el motivo del fallo.

### Reinicio del servicio
- `systemctl restart`, por ejemplo al instalar: gunicorn espera `graceful_timeout` (30 s por defecto) y corta lo que siga en curso.
- **El 21/10 hubo instalaciones con reinicio.** Los commits instalados ese día van de las 15:53 a las 18:17 UTC (10:53 a 13:17 hora de Lima). El último, `710e86b`, es de las 18:17 UTC. La hora exacta de cada reinicio la da el script 2.
- Si F020-000214 se emitió cerca de uno de esos reinicios, esa es la causa más probable. La sección e) del SQL da la hora exacta de registro; el script 2 da los reinicios.

---

## A2. La pantalla frente a la ruta directa
- **Cuerpo que manda la pantalla:**
  - `createQuickSale` sin guía y `wf-emit` mandan **`null`**. `api()` manda `Content-Type: application/json` sin cuerpo y el servidor lo lee como `{}`. **Es idéntico al script.**
  - `createQuickSale` con guía manda `{source_workflow_id, guide_data}`. Eso agrega a NubeFact la referencia de la guía y los puntos de partida y llegada escritos en el modal. Es la única diferencia posible de contenido. Una venta de mostrador de tienda normalmente no lleva guía.
  - Las NC mandan `{credit_note_reason_code, credit_note_reason_text}`.
- **Campos obligatorios:** los mismos en los dos casos (sale_routes 3561–3693). La validación previa revisa lo mismo que el envío, salvo lo que solo sabe NubeFact (serie habilitada, cliente o RUC, catálogos).
- **Red:** los dos salen del servidor hacia NubeFact. El navegador nunca habla con NubeFact.
- **Conclusión para F020-000214:** si se emitió desde la tienda sin guía, el contenido no pudo ser la causa. NubeFact dice "no existe", así que el primer intento:
  - **(a)** no se llegó a llamar: puntos 3, 5, 6 o 7;
  - **(b)** se llamó y NubeFact lo rechazó por algo transitorio;
  - **(c)** se llamó y la llamada se cortó (tiempo de espera, red o reinicio).

  El registro de nginx de esa venta distingue los tres casos: si aparece `POST …/electronic/send` y con qué código.

---

## A3. Tiempos de espera
| Capa | Valor | Fuente |
|---|---|---|
| requests hacia NubeFact | 20 s para conectar y 20 s para leer (`NUBECONT_TIMEOUT`, 20 si no está definido) | nubecont_service 34–37, 226 |
| Descarga de PDF/XML/CDR | 30 s cada una, **dentro** de la petición de envío y antes del commit | electronic_storage 42 |
| gunicorn | `-w 2 --threads 8`, timeout 120 (según tu dato; no está en el repositorio) | script 2, sección 1 |
| nginx | `proxy_read_timeout 120` (confirmado por ti el 22/10) | script 2, sección 1 |

¿Puede cortarse una emisión lenta sin dejar error? **Sí, de dos maneras:**
1. **nginx corta a los 120 s** (el envío más lento posible dura unos 130 s) mientras el envío y la descarga siguen. Con 120 s es poco frecuente, pero posible si NubeFact y las descargas van lentas a la vez. El navegador recibe un 504 en HTML, `api()` no puede leerlo (`payload = {}`) y muestra "Error en solicitud". Pero el servidor **sigue y hace commit**: el documento queda aceptado aunque la pantalla dijo error, y la persona puede repetir la venta. La sección a3) del SQL busca estos pares.
2. **Reinicio del servicio** a mitad de la llamada. Si muere antes de que NubeFact reciba el documento, queda "no existe" (como F020-000214). Si muere después, queda aceptada allá y vacía aquí.

**Sobre el timeout de 120 s de gunicorn:** con hilos (`gthread`), el aviso de vida lo da el hilo principal, así que una petición larga **no** dispara "WORKER TIMEOUT". El riesgo real está en nginx y en los reinicios.

En el peor caso, el envío dura 20 + 20 (NubeFact) + 3 × 30 (descargas) = **130 s**, más que nginx (60) y que gunicorn (120).

---

## A4. Desfase entre creación y envío
- **Sí hay desfase:** la venta se confirma (commit) en una petición y se envía en otra (2 a 4 viajes del navegador al servidor).
- **No existe ningún reintento que consulte antes de reenviar.** Solo hay una recuperación **después** de que NubeFact diga "ya existe" (sale_routes 3730).
- La corrección automática de correlativo (3799–3832) reenvía con otro número sin consultar.

---

## A5. Scripts de solo lectura (los ejecutas tú)

**1) SQL**, `backend/scripts/diag_emision_electronica.sql`:
- **a)** Electrónicas no anuladas y sin respuesta, por empresa y mes, separando las de total > 0.
  - **a2)** El detalle, con la hora de registro en Lima, el vendedor y el `sale_id`.
  - **a3)** **Posibles ventas repetidas:** el mismo cliente y total, el mismo día, una sin respuesta y otra registrada hasta 2 horas después.
- **b)** Aceptadas sin XML, sin CDR, sin PDF o sin ticket, por mes.
  - **b2)** Las aceptadas sin ticket: no hay prueba de que hayan llegado a NubeFact.
  - **b3)** Qué valores de `sunat_status` hay en uso.
- **c)** NC y ND sin respuesta, con el estado del documento al que modifican y su situación contable.
- **d)** Huecos de numeración por serie.
  - **d2)** Correlativos repetidos.
- **e)** F020-000214 y B030-000016: `sale_id` y hora exacta de registro (Lima y UTC).

```
cd ~/cea-erp && git fetch origin && git show origin/claude/diag-emision-electronica:backend/scripts/diag_emision_electronica.sql > /tmp/diag_emision.sql && sudo -u postgres psql cea_erp_prod -f /tmp/diag_emision.sql
```
Para una fecha de inicio distinta, agrega `-v desde=2026-08-01`. El script abre una transacción de solo lectura y termina con `ROLLBACK`. Lo probé en la base de prueba.

**2) Registros del servidor**, `backend/scripts/diag_emision_registro_servidor.sh`:
- **Tiempos de espera:** los de gunicorn, `NUBECONT_TIMEOUT` y nginx. Oculta cualquier valor llamado TOKEN, SECRET, KEY o PASSWORD.
- **Peticiones de la venta:** las de cada `sale_id` en el registro de nginx (precheck, send, status, post) con su código HTTP.
- **Cortes:** las respuestas 499, 502 y 504 a la creación y al envío, y lo que registró `error.log`.
- **Reinicios y workers** del 17/09 y del 21/10.
- **Días de historial:** cuántos guarda nginx. Si el 17/09 ya se borró, B030-000016 no se podrá reconstruir.

```
cd ~/cea-erp && git show origin/claude/diag-emision-electronica:backend/scripts/diag_emision_registro_servidor.sh > /tmp/diag_registro.sh && bash /tmp/diag_registro.sh <sale_id_de_F020-000214> <sale_id_de_B030-000016>
```
Antes de compartir la salida, revísala: solo imprime líneas filtradas, pero es tu servidor.

---

## Causas probables, ordenadas
Para **F020-000214**, a confirmar con el script 2:
1. **Reinicio del servicio durante la emisión**, el 21/10, día de varias instalaciones. Encaja con "no existe" y sin rastro.
2. **El envío no se llamó o se cortó en el navegador:** pestaña o red, sesión vencida o validación previa caída por la red. La persona vio un error con el texto engañoso "No se pudo crear venta". Encaja con no haber rastro en el servidor.
3. **Rechazo o caída transitoria de NubeFact:** el mismo cuerpo funcionó después desde el servidor. Hubo 502 con mensaje del proveedor, pero no se guardó.
4. **División DIGEMID con fallo en la segunda parte:** solo si esa venta tenía productos DIGEMID mezclados.

Para **B030-000016**: las mismas, más el límite de cuántos días guarda los registros nginx.

Para **las 4 NC sin respuesta**: es muy probable el rechazo local `REFERENCED_DOCUMENT_NOT_ACCEPTED`, porque el documento referido no estaba `aceptada` en nuestra base. La sección c) lo muestra.

---

## B. Propuesta por prioridad (sin programar)

### Prioridad 1 — B5: clave de firma de sesiones (riesgo de seguridad, hoy)
- **Hoy:** `JWT_SECRET_KEY` no está definida en el servidor, así que se usa `'cea-jwt-secret-2024'` de `config.py:13`. Pasa lo mismo con `SECRET_KEY`, `'cea-erp-secret-key-2024'` en la línea 10. **Ese valor está en el repositorio.**
- **Corrección sin cerrar sesiones a mitad de jornada:**
  1. **Código:** aceptar una clave actual y una anterior, con `JWT_DECODE_KEY` o un callback de flask-jwt-extended que pruebe las dos. Los tokens nuevos se firman con la nueva y los viejos se siguen aceptando hasta que venzan (24 h). En producción, si falta `JWT_SECRET_KEY` o mide menos de 32 bytes, el servicio no arranca, en lugar de caer al valor por defecto.
  2. **Servidor:** poner `JWT_SECRET_KEY` (64 bytes aleatorios) y `JWT_SECRET_KEY_ANTERIOR='cea-jwt-secret-2024'` en un override de systemd, no en el repositorio. Reiniciar **fuera de horario**.
  3. **Al día siguiente (más de 24 h):** quitar la clave anterior. Ya no queda ninguna sesión firmada con ella, así que nadie se desconecta.
  4. Lo mismo para `SECRET_KEY`.
- **Riesgo:** bajo. Si se olvida el paso 3, la clave vieja sigue siendo válida; se puede programar que deje de aceptarse sola después de una fecha.

### Prioridad 2 — B4: el token y la respuesta del proveedor fuera de logs, errores y salidas
- **Instalar `claude/sin-token-al-navegador` (`f16fcbd`).** Limpia las respuestas de la API y el registro del servicio (22 de 119 respuestas llevaban el token).
- **Quitar `request` del resultado de `_post_json`** (nubecont_service 205–253). Ninguna parte de la aplicación lo lee; hoy solo sirve para que el payload con `TOKEN` (líneas 368, 530, 550, 585, 613, 738, 860 y 882) viaje en `error_response(..., result)`.
- **Recortar las respuestas de error:** devolver solo `{codigo, mensaje}` del proveedor, nunca el `result` completo.
- **Scripts:** una función `redactar()` común (la de la rama del token) que **todos** los scripts de `backend/scripts` usen antes de imprimir, y una regla de revisión: ningún `print(result)`. Así se habría evitado que el token de FLUMISA apareciera en una salida.
- **Rotar los tokens de FIKA y FLUMISA** después de instalar la rama (procedimiento en `capturas_token_nubefact/procedimiento_rotar_token_nubefact.md`).

### Prioridad 3 — B3: corregir `_map_sunat_status_from_response` (sale_routes 167)
Hoy busca `'102'` y `'acept'` en **todo** el texto de la respuesta. Cualquier importe o ticket con "102", o la clave `aceptada_por_sunat`, lo marca `aceptada`.

Nueva regla, en este orden:

| Respuesta | `sunat_status` |
|---|---|
| `aceptada_por_sunat === true` y sin errores | `aceptada` |
| `sunat_responsecode` 0 con `aceptada_por_sunat` true | `aceptada` |
| `aceptada_por_sunat === true` con observaciones (`sunat_note` / código > 4000) | `aceptada_obs`, que entra en 20 caracteres (hoy `aceptada_con_observacion` no cabe) |
| código de rechazo (2000–3999) o `sunat_description` de rechazo explícito | `rechazada` |
| `anulado === true` | `anulada` |
| `aceptada_por_sunat === false` sin rechazo (pendiente en SUNAT) | **no se cambia**; se registra como "pendiente SUNAT" en la tabla de intentos |
| "no existe", errores, respuesta vacía o ambigua | **no se cambia** |

- **Ajustes al resto del sistema:** el PLE y los filtros que usan `aceptada` también deben leer `aceptada_obs`.
- **Documentos ya marcados:** se revisan con `claude/diag-estado-aceptada` (`32c804b`, de solo lectura) antes de cambiar nada.
- **Riesgo:** medio. Depende de los nombres exactos de los campos de NubeFact. Por eso la tabla de intentos (B1) debe guardar primero las respuestas reales, sin el token, para confirmarlos.

### Prioridad 4 — B1: intentos de envío (diseño aprobado, ajustado)
Se mantiene lo aprobado: la tabla `electronic_send_attempt`, el estado calculado sin campo nuevo en la venta, la lista para Sistema, Gerente y Administrador, y el reintento manual que consulta antes de enviar.

Ajustes por lo encontrado:
1. **Registrar también lo que hoy no llega al servidor.** Desde la pantalla, si el envío falla en el navegador (red, pestaña o 504 sin cuerpo), `POST /electronic/attempt-failed` guarda el motivo visto ("Error en solicitud", "Tu sesión expiró", HTTP 504). Si esa llamada también falla, el documento igual aparece como "Pendiente de envío", porque el estado se calcula.
2. **Fila `en_curso` antes de llamar a NubeFact,** con una conexión aparte. Si el proceso muere (reinicio), queda "Sin respuesta (verificar)".
3. **Descargas fuera del camino crítico:** hacer commit del ticket y del estado **antes** de descargar PDF/XML/CDR. Las descargas pasan a un segundo paso que se puede reintentar. Así el envío baja de 130 s a unos 40 s como máximo, bien por debajo de los 120 s de nginx.
4. **Corrección de correlativo:** queda detrás de `nubefact_corregir_correlativo`, apagado, y consulta antes de reenviar.
5. **Baja:** registrar el intento y no marcar `anulada` hasta confirmar el ticket. Diseño aparte: ¿lo incluyo?
6. **Mensaje correcto en la pantalla:** "La venta QUEDÓ REGISTRADA como X pero NO se envió: <motivo>", con "Reintentar envío" (ya aprobado). Nunca más "No se pudo crear venta" cuando la venta sí se creó.
7. **División DIGEMID:** si la segunda parte falla, la respuesta incluye la primera ya creada, y la pantalla la envía o la muestra como pendiente.

### Prioridad 5 — B2: botones en la fila de Facturación
- **"Enviar a SUNAT":** solo si `sunat_status` está vacío, el documento no está anulado y es electrónico. Usa el reintento seguro: primero consulta y solo envía si NubeFact dice "no existe". Reutiliza el manejador que ya existe (index.html 23645), que hoy no tiene botón.
- **"Consultar estado":** si `sunat_status` está vacío o es distinto de aceptada. Es solo lectura en NubeFact; con B3 nunca escribe un estado ambiguo. Reutiliza 23883.
- **Permisos:** Sistema, Gerente y Administrador. Pregunta: ¿también Ventas o Tesorería, o la tienda para sus propios documentos?
- **Candado:** `@single_flight` en el servidor (ya existe) y `_elecUnaVez` con el botón en "Procesando…" en la pantalla (ya existe).
- **"Contabilizar":** fuera de este alcance. Las NC necesitan su propio asiento (pendiente de definición contable).

---

## Riesgos de la propuesta
- **B3:** es el cambio más delicado. Si se equivoca, los documentos dejan de marcarse como aceptados (quedan pendientes, que es más seguro que lo contrario). Hay que probarlo con respuestas reales guardadas.
- **B5:** si se reinicia sin las dos claves cargadas, se cierran todas las sesiones. Por eso va fuera de horario y con la clave anterior aceptada 24 h.
- **B1 punto 3:** al separar las descargas, un documento puede quedar aceptado sin PDF unos segundos. La pantalla ya consulta el PDF aparte.
- **Ninguna propuesta reenvía nada al instalar.** F020-000214 ya está aceptada. B030-000016 y las 4 NC quedan en la lista para que alguien decida.

---

## Preguntas para ti
1. **F020-000214:** ¿la persona de la tienda recuerda qué mensaje vio? ¿Se emitió desde "Venta" o desde una cotización (flujo comercial)? ¿Llevaba guía o productos DIGEMID?
2. **Horario:** ¿a qué hora se emitió, y a qué horas reiniciaste el servicio el 21/10? La sección e) y el script 2 lo responden si nginx todavía tiene el registro.
3. **B5:** ¿puedo programar el cambio de clave con la clave anterior aceptada 24 h? ¿En qué horario reiniciarías?
4. **B2:** además de Sistema, Gerente y Administrador, ¿quién más puede pulsar "Enviar a SUNAT" y "Consultar estado"?
5. **Baja (B1.5):** ¿incluyo en esta tanda no marcar `anulada` hasta que SUNAT confirme?
6. **Orden:** propongo B5 → instalar la rama del token y rotar (B4) → B3 junto con B1 (una sola rama, porque comparten la tabla) → B2. ¿De acuerdo?
7. ~~¿El timeout de nginx está en 60 s?~~ Respondida: está en 120 s. No hace falta cambiarlo; B1.3 basta.


---

# Adenda (22/10/2026): resultados del diagnóstico en producción

## Lo que mostró el script (según tu resumen)
- **27 documentos sin respuesta.** La mayoría no son reales:
  - 11 pruebas de FIKA, con totales de 0.00 a 1.06;
  - 8 de una carga masiva de FLUMISA del 24/09, en series E001 y EB01.
- **Reales:**
  - **facturas repetidas en FIKA:** F010-000007, F010-000008 y F010-000009, de 4,250.00 cada una;
  - **5 notas de crédito.** Una de ellas, FC10-000001, modifica una factura **anulada**.
- **nginx** está en `proxy_read_timeout 120`. Ya corregí A3. El caso de 130 s sigue siendo posible pero raro, y B1.3 lo elimina.

## Lectura de los hallazgos
- **F010-000007/8/9:** es el patrón de A1, punto 5. La pantalla dijo "No se pudo crear venta" (aunque la venta se creó) y la persona volvió a emitir. Cada vez quedó otra factura con correlativo nuevo y sin enviar.
- **FC10-000001:** una NC sobre una factura anulada **no se puede enviar nunca**. El servidor exige que el documento referido esté `aceptada` (sale_routes 3684–3693), y una factura anulada en SUNAT no admite NC. Hoy nada impide **crearla**: `create_credit_note` no revisa si el referido está anulado.
- **Series E001 y EB01:** en SUNAT, las series que empiezan con **E** son las de comprobantes emitidos en el **portal de SUNAT (SEE-SOL)**, no por un proveedor como NubeFact. Si esa carga masiva registró documentos emitidos en SOL, **no deben enviarse a NubeFact**: se duplicarían en SUNAT. Hay que confirmarlo (pregunta 9).

## Cambios en B1 (intentos de envío)

### B1.8 — El reintento no deja ventas repetidas sin respuesta
1. **Al crear una venta (servidor):**
   - **Qué revisa:** si ya existe, en la misma empresa, una venta electrónica con el mismo cliente, el mismo tipo de documento, el mismo total y la misma fecha de emisión, creada en las últimas 24 h, **sin respuesta de SUNAT** y no anulada.
   - **Si existe:** responde 409 `POSIBLE_VENTA_REPETIDA` con el número de esa venta y **no crea** la nueva.
   - **Pantalla:** "Ya existe F010-000007 por 4,250.00 para este cliente, registrada a las 10:42 y SIN enviar a SUNAT". Ofrece dos botones:
     - **"Enviar F010-000007"** (recomendado): usa el reintento seguro y no crea nada nuevo;
     - **"Crear otra venta igual"**: pide marcar la casilla "Confirmo que es una venta distinta", reenvía con `confirmar_repetida: true` y queda anotado en la tabla de intentos y en la auditoría.
   - Este es el aviso con casilla y sin bloqueo duro que ya aprobaste en (a), pero ahora **lo valida el servidor**, no solo la pantalla.
2. **Al reintentar un documento:** si existe un "gemelo" (mismos datos que arriba) que ya está **aceptado**, el reintento no envía. Responde 409 `GEMELO_ACEPTADO`: "F010-000009, igual a este, ya está aceptada en SUNAT. Si esta venta es distinta, un Gerente o Administrador debe confirmarlo". Así el reintento nunca convierte una venta repetida en dos facturas aceptadas.
3. **En la lista de pendientes:**
   - los documentos con gemelo se agrupan: "F010-000007, -000008 y -000009: posibles repetidas";
   - el botón "Enviar" se habilita en **uno solo** del grupo;
   - los otros quedan para **descartar** (B1.10).

### B1.9 — NC sobre un documento anulado
- **Al crear la NC:** `create_credit_note` rechaza con 400 `REFERENCED_DOCUMENT_CANCELLED` si el documento referido tiene `status='cancelled'` o `sunat_status='anulada'`. Es el mismo criterio de `_already_voided_error` (`5b48984`).
- **En la lista:** las NC existentes en esa situación (FC10-000001) aparecen como **"No enviable: modifica un documento anulado"**, sin el botón "Enviar", solo con "Descartar".

### B1.10 — Descartar documentos que no se van a enviar
- **Para qué:** las 11 pruebas, los repetidos y FC10-000001 deben salir de la lista sin enviarse.
- **Cómo:** acción **"Descartar (no se envía a SUNAT)"**, solo para Sistema, Gerente y Administrador, con un motivo obligatorio. Pone `status='cancelled'` en el sistema y deja `sunat_status` vacío, porque nunca llegó a SUNAT. Revierte el stock como una anulación local y queda en la tabla de intentos (`outcome='descartado'`) y en la auditoría.
- **Límites:**
  - solo sobre documentos **sin ticket** que NubeFact confirme como "no existe" (se consulta antes);
  - nunca sobre documentos aceptados;
  - **no hace baja en SUNAT**, porque no hay nada que dar de baja.
- **Pregunta para el contador:** ¿basta con descartarlos en el sistema, o SUNAT/NubeFact exigen el correlativo enviado y luego dado de baja (pregunta 10)?

### B1.11 — Series emitidas fuera de NubeFact (E001, EB01)
- **Regla:** una serie que empiece con **E** se considera emitida fuera de NubeFact.
  - No aparece en la lista de pendientes; va en un apartado "Emitidos en SUNAT (SOL)".
  - El servidor rechaza su envío a NubeFact: 400 `SERIE_EMITIDA_FUERA_DE_NUBEFACT`.
  - El botón "Enviar" no se dibuja.
- **Pendiente:** confirmar con el contador. Si se confirma, conviene marcar esos 8 documentos con `is_electronic=false` o un indicador "emitido en SOL", para que tampoco cuenten como "sin respuesta". Eso modifica datos, así que va aparte y con tu OK.

## Cambio en el Excel "Exportar Detallado PLE"

### B6 — NC sin respuesta de SUNAT: no restan, o restan marcadas
- **Hoy (`02d1d29`):** toda NC no anulada sale en negativo, haya respondido SUNAT o no. Una NC que nunca llegó a SUNAT (como FC10-000001) **resta sin aviso**.
- **Propuesta:**
  - **NC con `sunat_status` vacío o distinto de aceptada:**
    - importes en **0** (con el formato, se ven "-"), así que **no restan**;
    - **AJ** queda en 1;
    - **BF** dice "NC sin respuesta de SUNAT: no resta hasta que SUNAT la acepte".
  - **NC sobre un documento anulado:** igual, en 0, con la observación "NC sobre documento anulado (no enviable)".
  - **NC aceptada:** sin cambio, en negativo.
- **Solo el Excel,** como pediste. Los TXT no cambian.
- **Pregunta (11):** ¿las **facturas y boletas** sin respuesta deben quedar igual? Hoy suman su importe completo, marcadas "Sin estado SUNAT", y B030-000016 se incluye marcada por tu decisión. Si las NC sin respuesta no restan pero las facturas sin respuesta sí suman, el libro queda asimétrico. Opciones:
  - **(a)** solo las NC en 0, como pediste;
  - **(b)** todo documento sin respuesta en 0 y marcado;
  - **(c)** todo documento sin respuesta con su importe y marcado, como hoy, sin restar las NC.
  - Recomiendo **(b)**, para que el total del Excel refleje solo lo que SUNAT tiene. La decisión es del contador.
- **Prueba prevista:** en la base de prueba, una NC aceptada (resta), una NC sin respuesta (0 y marcada) y una NC sobre un documento anulado (0 y marcada), comparando el total contra `710e86b`.

## Orden propuesto (actualizado)
1. **B5:** clave de sesiones.
2. **Instalar la rama del token y rotar los tokens (B4).**
3. **B6:** Excel del PLE. Es chico, se puede hacer en paralelo y no depende del resto.
4. **B3 + B1 en una sola rama,** con 8 a 11 incluidos.
5. **B2:** botones en Facturación.

## Preguntas nuevas
8. **F010-000007/8/9:** ¿cuál de las tres es la venta real (o eran tres ventas distintas)? La lista dejará enviar solo una.
9. **E001 y EB01 (FLUMISA, 24/09):** ¿son comprobantes emitidos en el portal de SUNAT (SOL) y cargados al sistema solo para registro? Si es así, no deben enviarse a NubeFact.
10. **Para el contador:** los documentos que nunca llegaron a SUNAT (pruebas y repetidos), ¿se descartan solo en el sistema o hay que enviarlos y darlos de baja para no dejar huecos en la correlatividad?
11. **Para el contador:** en el Excel del PLE, ¿opción (a), (b) o (c) para los documentos sin respuesta?

---

# Rediseño pedido (22/10/2026): registrar solo lo que llegó a NubeFact

Pedido: que no haya problemas con NubeFact, que todo quede correcto con los PDF guardados, y que **no se registre una venta si no llegó a NubeFact**.

## Idea
Hoy el sistema hace "guardar → enviar". Se cambia a **"preparar → enviar → guardar"**, en **una sola llamada al servidor**: `POST /api/sales/<empresa>/emit`. La pantalla ya no guarda la venta por un lado y la envía por otro.

1. **Validar** lo mismo que hoy: cliente, serie, líneas, stock, periodo, NC y referido. Si algo falla, no se guarda nada.
2. **Tomar el número** con un candado por empresa y serie. Dos ventas de la misma serie no pueden tomar el mismo número ni cruzarse.
3. **Armar la venta, sin guardarla todavía:** la venta, sus líneas y el stock quedan dentro de una transacción abierta.
4. **Anotar el intento** en la tabla de intentos (conexión aparte): número, empresa, total y cliente, `en_curso`.
5. **Enviar a NubeFact.** Según la respuesta:

| Respuesta de NubeFact | Qué queda en el sistema |
|---|---|
| Lo recibió (ticket o enlace) | **Se guarda** la venta con su ticket, el stock y el asiento contable. Se descargan PDF, XML y CDR. |
| Lo rechazó con un motivo claro | **No se guarda nada.** El número queda libre y la pantalla muestra el motivo de NubeFact para corregir y volver a emitir. |
| No se pudo llamar (sin red, NubeFact caído, token) | **No se guarda nada.** El número queda libre. Mensaje: "NubeFact no responde; no se registró la venta, inténtelo de nuevo". |
| Se cortó sin respuesta (tiempo agotado) | Se **consulta** a NubeFact en el acto. Si dice "no existe", no se guarda nada. Si existe, se guarda como recibido. |
| Se cortó y la consulta tampoco responde | **Único caso que se guarda sin confirmar**, porque NubeFact pudo haberlo recibido y no puede quedar un comprobante en SUNAT que el sistema no tiene. Queda "Por verificar" en la lista, con el motivo, y el botón "Consultar" lo resuelve. Debería ser muy raro. |

6. **PDF, XML y CDR:** se descargan apenas se guarda la venta, en la misma operación. Si NubeFact todavía no los tiene listos (pasa con boletas, que SUNAT acepta después por resumen diario), la venta queda guardada como **recibida por NubeFact** y la lista "Aceptadas sin PDF/CDR" los vuelve a pedir. Nunca queda una venta sin poder bajar su PDF.

## Lo que esto resuelve
- **F020-000214 y B030-000016:** no habrían quedado registradas sin enviar. La tienda habría visto el motivo y vuelto a emitir con el mismo número.
- **F010-000007/8/9:** no habrían existido. Como la primera no se guardó, emitir de nuevo usa el mismo número, en lugar de crear otra factura colgada.
- **No más "No se pudo crear venta" cuando sí se creó:** si la pantalla dice que no, es que no hay nada guardado.
- **Las NC** siguen el mismo camino: solo existen si NubeFact las recibió. Una NC sobre una factura anulada se rechaza antes.

## Riesgos y cómo se cubren
- **El proceso muere (reinicio) justo después de que NubeFact lo recibió:** la transacción se deshace, así que NubeFact tiene el documento y el sistema no.
  - **Cobertura:** la fila `en_curso` de la tabla de intentos queda grabada porque usa una conexión aparte. Al arrancar el servicio, y en la lista, esos intentos se consultan en NubeFact. Si existe, se muestra "Recibido en NubeFact pero no registrado" con los datos del intento para volver a emitirlo con ese mismo número.
  - **Además:** si NubeFact responde "ya existe" para un número, el sistema **no** copia ese comprobante dentro de otra venta distinta (hoy lo hace, sale_routes 3730). Solo lo recupera si coinciden cliente y total; si no, avisa.
- **Mientras se espera a NubeFact (hasta unos 40 s), otra venta de la misma serie espera su turno.** Cada tienda tiene su serie, así que el efecto es mínimo. Ventas de series distintas no se esperan entre sí.
- **El stock no se descuenta si NubeFact rechaza** (la transacción se deshace). Si en ese momento otra venta descuenta el mismo producto, el candado y el control de stock existentes siguen aplicando.
- **Correlativos:** un número rechazado por NubeFact no se registró allá, así que reutilizarlo es correcto y no deja huecos.

## Qué cambia en la pantalla
- **"Emitir"** hace una sola llamada. Mensajes posibles:
  - "Factura F020-000215 emitida y recibida por NubeFact" (con PDF);
  - "NO se emitió: <motivo de NubeFact>. No se registró nada";
  - "Por verificar", en el caso raro.
- **Se quitan los pasos separados de la pantalla:** guardar, validar, enviar y contabilizar.
- **Se mantiene el bloqueo de doble clic** (botón "Procesando…" y candado en el servidor).

## Qué se mantiene del diseño anterior
- La tabla de intentos (B1) y la lista para Sistema, Gerente y Administrador. Ahora solo muestra:
  - los "Por verificar";
  - los "Recibido en NubeFact pero no registrado";
  - las aceptadas sin PDF o CDR;
  - los **27 documentos viejos**, que se resuelven uno por uno con "Consultar", "Enviar" o "Descartar".
- B3 (leer bien el estado de SUNAT), B4 (token) y B5 (clave de sesiones).
- **Nada de lo ya emitido se modifica al instalar.**

## Alcance
| Flujo | Cambia a "solo si llegó a NubeFact" |
|---|---|
| Venta y venta de tienda (`createQuickSale`) | Sí |
| Emitir desde cotización (`wf-emit`) | Sí |
| Nota de crédito y nota de débito | Sí |
| Venta dividida por DIGEMID | Sí: cada parte se emite por separado; si la segunda falla, la primera queda emitida y se avisa claramente |
| Guías | Segunda etapa (tienen su propia recuperación) |
| Baja | Sin cambio en esta etapa |
