# Guía directa rechazada: línea BX sobre producto NIU

Corrige la premisa del mensaje anterior. Base: main `5b48984`. Pruebas con NubeFact simulada; nunca con la real.

## 1. ¿Hay alguna regla o conversión que compare la unidad de la línea con la del producto?
**No, ni en el servidor ni en la pantalla.**

**Servidor:**
- `build_guide_payload` (`nubecont_service.py`) arma cada ítem solo con `line.unit`, pasado por `_provider_unit_code`. Esa función solo traduce alias: UND/UN/UNIDAD a NIU; PAR a PR; DOCENA a DZN, etc.
- `BX` se envía tal cual.
- **La unidad del producto nunca forma parte del payload de la guía.**
- La única comparación con la unidad del producto está en `direct-guide` sin cotización: `row.unit or inv_item.unit_of_measure`. Solo se usa si la línea llega **sin** unidad.
- `app/utils/units.py` solo normaliza la unidad **al guardar el producto**.
- Este archivo no cambió desde el 01/10 (M1L).

**Pantalla:** no hay ninguna tabla de equivalencias ni factor de conversión. La unidad del producto solo se **muestra** ("Unidad del producto: …").

**Payload exacto enviado** (casos 1, 2, 3, 7 y 9 de `resultado_main.txt`):

| Caso | `unidad_de_medida` / `COD_UND_MEDIDA_ITEM` | `codigo` |
|---|---|---|
| Línea BX sobre producto NIU (como COT-000202), TTT1 | `BX` | BSTL260708NG65TL |
| Línea NIU sobre producto NIU, TTT1 | `NIU` | BSTL260708NG65TL |
| Línea BX sobre producto BX, TTT1 | `BX` | GDBX00000001 |
| issue-guide, línea BX sobre producto NIU | `BX` | BSTL260708NG65TL |
| DIGEMID, línea BX sobre producto NIU (como COT-000162-DIGEMID), TTT4 | `BX` | GDDIGNIU0001 |

**Para NubeFact, "BX sobre NIU" y "BX sobre BX" son el mismo dato de unidad.** Solo cambian el código y la descripción. Los demás campos del ítem son iguales: `cantidad`, `PESO_ITEM` = cantidad y precios.

## 2. ¿Quién produce el rechazo?
**El proveedor.**
- El texto "Despatch advice lines catalog unidad de medida incorrecto" no existe en el código ni en ningún commit del historial.
- Con la NubeFact simulada aceptando, el sistema envía la línea BX sobre producto NIU sin objetar nada: casos 1, 6 y 9, respuesta 201/200.
- Con la simulada devolviendo ese mensaje (caso 10), el sistema responde exactamente lo que vio la usuaria: **502 `NUBECONT_GUIDE_SEND_ERROR`** con el mensaje del proveedor tal cual. La cotización vuelve a `accepted`, sin número de guía y sin movimientos de stock.

**¿Desde qué commit es posible?** No hay un commit que introduzca el rechazo. Lo que sí cambió es que **una línea de cotización con unidad distinta de la del producto solo existe desde `ec01b87` (05/10 20:09, selector de unidad por línea)**. Antes, la línea tomaba siempre la unidad del producto (`data-unit`), salvo que el producto se editara después. Así se explica que la combinación "línea BX sobre producto NIU" no aparezca antes del 05/10.

**Por qué el proveedor distinguiría BX/NIU de BX/BX si recibe el mismo `BX`:**
- El payload no lleva la unidad del producto.
- La única diferencia que ve NubeFact es el `codigo` del producto.
- Hipótesis, compatible con la palabra "catalog" del mensaje: NubeFact valida la unidad contra **su propio catálogo de productos por código**. Ese catálogo se forma con los comprobantes ya emitidos con ese código.
- **No se puede confirmar desde el código.** Se confirma con NubeFact (soporte o su entorno de pruebas) o con el mensaje completo guardado. Hoy ese mensaje no se guarda; lo resuelve el registro de la función 3, que también cubre las guías.

## 3. Lo que se ve no es lo que se envía (defecto real, verificado)
- En la guía directa, la unidad es un campo de **solo lectura**, desde el 15/08.
  - Al traer una cotización, la pantalla muestra la unidad de la línea de la cotización (desde `ec01b87`; antes mostraba la del producto).
  - Al elegir un producto a mano, muestra la del producto.
  - Por eso la BX que se vio solo pudo venir de la línea guardada de la cotización o de la ficha del producto.
- **Tras "Traer cotización", la pantalla envía `source_workflow_id` y el servidor usa las líneas GUARDADAS de la cotización.** Ignora producto, unidad y cantidad de la pantalla.
- **Caso 7:** la pantalla mandó BX y cantidad 1; se envió a NubeFact NIU y 3800.
- Esto encaja con la línea de tiempo:
  - los tres 502 (14:06 a 14:12) usaron la línea guardada en ese momento;
  - la línea de la cotización se guardó en NIU a las 14:15:39;
  - la emisión de las 14:22:14 salió en NIU.

## 4. Comportamiento propuesto (no implementado; sin sustituir unidades en silencio)
1. **Aviso antes de emitir, en pantalla y en servidor,** en direct-guide (con o sin cotización), issue-guide y "→ Guía".
   - **Cuándo:** la unidad de alguna línea es distinta de la unidad del producto **y** distinta de NIU.
   - **Mensaje:** "La línea «<producto>» va en CAJA (BX) pero el producto está en UNIDAD (NIU). NubeFact rechazó guías así. Para la guía usa la unidad del producto (corrige la línea de la cotización) o corrige la ficha del producto."
   - **Opciones:** "Corregir la cotización" (abre la edición) y "Emitir igual" (con casilla de confirmación).
   - **El servidor lo valida ANTES de tomar número:** 400 `GUIDE_UNIT_MISMATCH` con las líneas, salvo que llegue la confirmación explícita.
   - **Nunca se cambia la unidad automáticamente.**
   - Se activa con el parámetro por empresa `guia_aviso_unidad_distinta`.
2. **Líneas traídas de una cotización, de solo lectura en la guía directa,** con la nota "vienen de COT-X; para cambiarlas edita la cotización".
   - Además, el servidor rechaza con un aviso si las líneas de la pantalla no coinciden con las guardadas, en lugar de ignorarlas en silencio.
3. **Se mantiene:**
   - guardar la respuesta exacta del proveedor también para guías (tabla de la función 3: todas las llamadas pasan por `_post_json`);
   - la protección contra clics repetidos en guías: hoy existe el bloqueo del botón y de la fila de la cotización; se agrega el candado de la función 1 por cotización;
   - COT-000202 y COT-000162-DIGEMID como casos de prueba: equivalen a los casos 1, 6 y 9, y con el aviso quedarían detenidos antes de NubeFact.
