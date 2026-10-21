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
- **El 21/10 hubo varias instalaciones con reinicio:** commits a las 15:53, 16:21, 16:26, 17:59, 18:09, 16:23 y 18:17 UTC, es decir de 10:53 a 13:17 hora de Lima.
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
| nginx | No está en el repositorio. Si no se definió, `proxy_read_timeout` vale **60 s** | script 2, sección 1 |

¿Puede cortarse una emisión lenta sin dejar error? **Sí, de dos maneras:**
1. **nginx corta a los 60 s** mientras el envío y la descarga siguen. El navegador recibe un 504 en HTML, `api()` no puede leerlo (`payload = {}`) y muestra "Error en solicitud". Pero el servidor **sigue y hace commit**: el documento queda aceptado aunque la pantalla dijo error, y la persona puede repetir la venta. La sección a3) del SQL busca estos pares.
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
3. **Descargas fuera del camino crítico:** hacer commit del ticket y del estado **antes** de descargar PDF/XML/CDR. Las descargas pasan a un segundo paso que se puede reintentar. Así el envío baja de 130 s a unos 40 s como máximo, por debajo de nginx.
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
7. **¿El timeout de nginx está en 60 s?** Si el script 2 lo confirma, ¿lo subimos a 150 s mientras se programa B1.3?
