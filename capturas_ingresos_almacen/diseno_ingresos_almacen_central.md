# Ingresos al almacén central: cómo se hace hoy y diseño propuesto

Solo diseño: no se programa ni se instala nada hasta tu OK. Base: main `5b48984`.

---
## 1. Cómo se hace hoy (leído del código)

### 1.1 Crear un producto (Inventario › Crear ítem → `POST /api/inventory/<cid>/items`)
- **Datos:**
  - **obligatorios:** código, descripción (Producto), categoría y unidad;
  - **opcionales:** código de barras, marca, "Descripción" (`secondary_description`, por ejemplo "L, VERDE"), costo, precio por menor, cantidad y precio por mayor, y DIGEMID.
  - Las cuentas contables existen en el formulario pero ocultas.
- **Validaciones:**
  - La unidad debe ser NIU, BX, PK, DZN, PR, PAR, KGM o LTR.
  - El código de barras no puede repetirse.
  - **El código del producto no se valida**: si se repite, falla la restricción única de la base y la persona ve un error 500 genérico.
- **El campo "Modelo" de la pantalla no se guarda**: el servidor lo ignora al crear.
- **Uno por uno.** No crea stock.
- **Roles:**
  - la pantalla oculta el formulario a Vendedor y a las tiendas (TiendaCapon, TiendaMalvinas);
  - el servidor no revisa el rol: cualquier usuario con sesión puede crear.
- **Usuario:** no se guarda (`created_by` vacío).

### 1.2 Ingreso manual de stock (Inventario › Registrar movimiento → `POST /api/inventory/<cid>/movements`)
- **Una línea por vez:** producto, almacén, tipo (Entrada, Salida o Ajuste), fecha, cantidad, costo unitario (**por defecto 0**) y un comentario libre **opcional**.
- **No pide documento de origen**: ni tipo, ni número, ni proveedor. `reference_type` queda vacío.
- **Validaciones:**
  - el periodo de la fecha debe estar abierto;
  - la cantidad debe ser mayor que 0 y el costo mayor o igual a 0;
  - en una salida, debe haber stock suficiente.
- **Costo:**
  - el movimiento suma `cantidad × costo` al saldo valorizado (`balance_cost`);
  - **reemplaza el `current_cost` del producto por el costo de ese ingreso**: no es promedio, es el último costo.
  - Un ingreso a 0.01 deja el costo del producto en 0.01, y las ventas siguientes descuentan stock a 0.01.
- **Asiento contable:** ninguno.
- **Roles:**
  - la pantalla lo oculta a Vendedor y a las tiendas;
  - el servidor solo bloquea a quien tiene el kardex de tienda en solo lectura;
  - Almacén, Tesorería, Ventas, Encargado, etc. pueden registrar.
- **Usuario:** no se guarda.
- **Sin protección contra doble clic** en este botón: dos clics pueden crear dos ingresos.

### 1.3 Carga masiva (Configuración › Carga masiva → `POST /api/bulk-loads/<cid>`, tipo `inventory_items`)
- **Formato:** CSV o XLSX, primera fila con encabezados. Se aceptan nombres alternativos:

  | Dato | Encabezados aceptados | Si falta |
  |---|---|---|
  | Código | `item_code` / `code` / `codigo` | obligatorio |
  | Descripción | `description` / `descripcion` | obligatorio |
  | Categoría | `category` / `categoria` | `General` |
  | Unidad | `unit` / `unidad` | NIU |
  | Costo | `cost` / `costo` | 0 |
  | Precio | `price` / `precio` | 0 |

- **No lee** `secondary_description`, código de barras, marca, DIGEMID ni cuentas.
- **Si el código ya existe, LO SOBRESCRIBE sin avisar:** descripción, categoría, unidad, costo y precio.
- **No crea stock.**
- **Guarda fila por fila.** Si una fila falla, las anteriores quedan grabadas: no es todo o nada.
- **Sin vista previa, sin límite de filas y sin control de rol.** Sí guarda el usuario de la carga.
- Hay tipos de carga para compras, ventas y asientos, pero ninguno crea stock.

### 1.4 Compras (Compras › Registrar compra)
- **El asiento se crea al registrar la compra:**
  - Debe 60111/601 (Compras) y 40111 (IGV);
  - Haber 4212 (Facturas por pagar);
  - más detracción o retención si aplica.
- **La compra NO genera stock:**
  - las líneas se guardan **sin el producto** (`item_id` vacío), aunque la pantalla tenga un campo de producto;
  - la función `_update_inventory_from_purchase` solo se llama desde "Contabilizar" (`/post`). Allí usaría el primer almacén activo que encuentre, pero falla siempre porque lee `item.qty_on_hand`, un campo que no existe. El error se descarta sin aviso, así que no se crea ningún movimiento.
- **Consecuencia:** hoy toda mercadería comprada entra al stock por el ingreso manual (1.2), sin vínculo con la factura de compra.
- **No existe asiento de destino ni de inventario:** no hay 20 (Mercaderías) contra 61 (Variación de existencias), ni costo de ventas 69 contra 20. Eso lo decide el contador.

### 1.5 Traslados entre almacenes (Inventario › Transferencias)
- Salida del origen y entrada al destino, con el `current_cost` del producto y referencia `transfer`.
- Guardan quién crea y quién recibe.
- **Discrepancia del saldo valorizado:** en los traslados, `balance_cost` guarda el costo **unitario**; en ventas y en el ingreso manual guarda el valor **total**. El "stock valorizado" no es comparable entre tipos de movimiento.

### 1.6 Resumen del costo hoy
- **No existe un costo promedio real en el kardex.** `current_cost` es el último costo ingresado a mano.
- **El costo de salida de las ventas es ese `current_cost`.**
- **Un ingreso a 0.01 o a 0 contamina** el costo del producto y el de todas sus ventas siguientes.

---
## 2. Diseño propuesto

### (a) Crear un producto con varias tallas en un paso
**Pantalla "Nuevo producto con tallas" (Inventario):**
- **Datos comunes, una vez:**
  - descripción, marca, categoría, unidad y DIGEMID;
  - precio por menor y por mayor, y cantidad por mayor;
  - cuentas contables (las predeterminadas de la empresa).
- **Código base:** la parte común, por ejemplo `BSTL260708NG65`.
- **Tallas, de 1 a 6 filas:** sufijo, detalle y código de barras opcional. Por ejemplo:
  - `TS` con "S, VERDE";
  - `TM` con "M, VERDE";
  - `TL` con "L, VERDE".
  - Atajo "S/M/L", que llena TS, TM y TL.
- **Código final = base + sufijo**, la convención actual con la talla al final.
  - Regla configurable por empresa en el parámetro `codigo_talla_formato`, por defecto `{base}{sufijo}`.
- **Validación antes de guardar, todo en el servidor:**
  - código o código de barras ya existente: se bloquea esa fila con un mensaje claro, no un 500;
  - unidad permitida;
  - **aviso** si la misma descripción ya existe con otros códigos, mostrando cuáles tienen stock.
- **Vista previa** de los códigos que se crearán. **Todo o nada.**
- **Se guarda el usuario y la hora.** El costo no se pide aquí: lo da el ingreso (b).

### (b) Ingreso al almacén central con varias líneas en un movimiento
**Pantalla "Ingreso a almacén central"** (solo almacenes centrales: ALMFIKA y ALMFLU).

**Cabecera obligatoria:**
- almacén y fecha (con el periodo abierto);
- **tipo de origen:** compra, importación, traslado, devolución de cliente o conteo físico;
- **número de documento de origen;**
- **proveedor**, si el tipo es compra o importación;
- comentario.

**Documento que exige cada tipo de origen:**

| Tipo de origen | Documento obligatorio | Vínculo |
|---|---|---|
| Compra | Factura de compra registrada en Compras | Se elige de la lista: el ingreso queda vinculado (ver d) |
| Importación | DUA o DAM, más factura comercial | Número y fecha |
| Traslado | Guía de remisión del remitente | Número de guía |
| Devolución de cliente | Nota de crédito emitida | Se elige la NC |
| Conteo físico | Acta de inventario, firmada por quien lo aprueba | Número de acta, más un rol aprobador |

- **No se aceptan textos libres** como "corrección de stock", "para facturar" o "ajuste" en lugar del documento. El comentario es adicional, nunca sustituye al documento.

**Líneas, de 1 a 30:**
- producto (con búsqueda por código o descripción), cantidad mayor que 0;
- **costo unitario obligatorio, mayor que 0 y distinto de 0.01** (valor de relleno);
- **aviso si se aparta más del ±50 % del último costo**, con confirmación;
- **aviso si el producto tiene otro código con la misma descripción y stock** ("¿es el mismo producto?").

**Al confirmar:**
- **vista previa** con stock antes y después por línea, valor total y costo nuevo de cada producto;
- **una sola transacción**, todo o nada;
- un **número de ingreso** propio (ING-000001) y una tabla nueva `stock_receipt` con sus líneas; cada línea crea su movimiento `in` con `reference_type='stock_receipt'`;
- se guarda el usuario;
- protegido contra doble clic con el **candado de la función 1** (por ingreso) y un `client_request_id` idempotente.

**Costo:**
- **costo promedio ponderado por producto:** (stock × costo actual + cantidad × costo de entrada) ÷ (stock + cantidad);
- `balance_cost` = valor total, como en ventas.

**Anulación:**
- solo por los roles autorizados y con motivo;
- crea las salidas inversas; no se borra nada;
- se bloquea si ya no hay stock suficiente.

### (c) Carga por Excel que hace (a) y (b) juntas
- **Plantilla descargable:** una fila por producto y talla.
  - **Columnas de producto:** código base, sufijo de talla, detalle, descripción, marca, categoría, unidad, DIGEMID, precio por menor, precio por mayor, cantidad por mayor y código de barras.
  - **Columnas de ingreso:** cantidad y costo unitario.
  - **La cabecera del ingreso** (almacén, fecha, tipo y número de documento, proveedor) se llena **en la pantalla, no en el Excel**.
- **Procesamiento:**
  - **paso 1, validar:** el servidor revisa cada fila y responde una tabla con OK o el error de cada una (por ejemplo "Fila 7: costo 0.01 no permitido", "Fila 9: el código BSTL260708NG65TL ya existe con otra descripción"). **No guarda nada.**
  - Los **códigos existentes** se aceptan solo si la descripción coincide. Nunca se sobrescribe un producto: si hay diferencias, se muestran y se rechaza la fila.
  - **paso 2, confirmar:** crea los productos nuevos y el ingreso en **una transacción**; si algo falla, no queda nada.
- **Límite:** 200 filas por carga, configurable. Lo pedido son 21.
- **Archivo:** se guarda junto al ingreso, para auditoría.

### (d) Relación con Compras
- **Si la mercadería tiene factura de compra:** el ingreso de tipo "Compra" se vincula a esa compra.
  - Una compra solo puede tener ingresos hasta sus cantidades.
  - Se avisa si el ingreso supera lo facturado.
  - El costo sale del precio sin IGV de la compra, convertido a soles si fue en dólares.
- **No se crea stock al registrar la compra.** Se mantiene el comportamiento actual (sin stock), con el ingreso vinculado. Así no hay doble stock aunque alguien registre las dos cosas.
  - La función rota `_update_inventory_from_purchase` se deja como está, porque nunca crea nada. Desactivarla o quitarla se propone aparte.
- **Ingresos sin factura** (importación, devolución, conteo): exigen su documento (tabla de b).
- **Contabilidad, para que decida el contador:**
  - hoy la compra va a 60111 y no hay asiento por el ingreso;
  - **opción A** (recomendada para empezar): sin asiento en el ingreso, como hoy;
  - **opción B:** al confirmar el ingreso se genera el asiento de destino, Debe 20 (Mercaderías) y Haber 61 (Variación de existencias), por el valor del ingreso; más adelante, el costo de ventas 69 contra 20.

### (e) Controles
- **Roles:**
  - la misma constante del asiento manual (`MANUAL_JOURNAL_ROLE_PREFIXES`: sistema, administrador, gerente);
  - **más** el rol del almacenero central (hoy `AlmacenGeneral`), en el parámetro por empresa `ingreso_almacen_roles_extra`;
  - el conteo físico exige, además, aprobación de un rol de la constante;
  - crear productos usa los mismos roles.
- **Usuario y hora** en el producto, el ingreso y cada línea.
- **Reporte "Ingresos de los últimos días"** para administración y gerencia:
  - número, fecha, almacén, tipo y documento, usuario, líneas, unidades y valor;
  - marcas de costo atípico y de producto con otro código con stock;
  - exportable a Excel.
- **La pantalla actual de "Registrar movimiento":**
  - con el parámetro encendido, deja de permitir **entradas** en almacenes centrales, que pasan por el ingreso nuevo;
  - las salidas y ajustes siguen igual hasta decidir;
  - en el resto de almacenes, un ingreso exige documento y costo mayor que 0.01.

---
## 3. Riesgos
1. **Costo promedio:**
   - cambiar de "último costo" a promedio ponderado cambia el costo de salida de las ventas siguientes;
   - los productos con costo 0.01 o 0 arrastran un promedio bajo hasta que entre stock con costo real;
   - el reporte de la consulta (sección 2 del SQL) muestra cuáles son, para que el contador corrija con un conteo físico documentado.
2. **Códigos duplicados:**
   - el mismo producto con muchos códigos (13 en el nitrilo 6.5) hace que se venda el código equivocado y que el stock quede repartido;
   - el aviso de "misma descripción con stock" lo hace visible, pero no lo resuelve; unificar códigos es otra decisión.
3. **Doble ingreso:** lo cubren el candado de la función 1 y el `client_request_id`. Hoy el botón de movimientos no tiene protección.
4. **Saldo valorizado inconsistente:** el de los traslados es unitario. Corregirlo afecta reportes de valor; se propone aparte.
5. **Ingreso vinculado a compra en dólares:** el tipo de cambio de la compra decide el costo.
6. **Carga de Excel grande:** el límite y la validación previa evitan cargas a medias.

## 4. Activación y migración
- **Parámetro por empresa `ingreso_almacen_nuevo`, apagado por defecto.** Apagado, todo queda como hoy.
  - Encendido: aparecen las pantallas (a), (b) y (c) y se restringen las entradas manuales en almacenes centrales.
- **Migración:**
  - no se toca ningún producto ni movimiento existente;
  - las tablas son nuevas (`stock_receipt`, `stock_receipt_line`);
  - los movimientos nuevos usan una referencia nueva;
  - el kardex histórico sigue igual.
- **Orden sugerido:**
  1. consulta en producción;
  2. respuestas de almacén;
  3. rama de (a) y (b);
  4. rama de (c);
  5. decisión del contador sobre (d) opción B.

---
## 5. Preguntas para la persona de almacén
1. ¿Con qué documento llega hoy la mercadería al almacén central? ¿Factura de compra local, DUA de importación, guía del proveedor, o varias? ¿La factura llega el mismo día que la mercadería?
2. ¿Quién registra la compra en Compras, ella o contabilidad? ¿Antes o después de recibir la mercadería?
3. **Costo:** ¿conoce el costo unitario al recibir? Si no, ¿quién se lo da y cuándo? (Hoy se pone 0.01.)
4. **Tallas:** ¿son siempre S, M y L (TS, TM, TL)? ¿Hay XS o XL? ¿Las tallas de un mismo lote comparten precio de venta?
5. **Lote en el código:** ¿cada lote nuevo necesita un código nuevo, o podría reutilizarse el código con el lote aparte? (Hoy BSTL… y SCIC… son lotes distintos del mismo guante.)
6. ¿Qué parte del código es fija y cuál cambia? Por ejemplo, en `BSTL260708NG65TL`: ¿`BSTL` es el proveedor, `260708` la fecha o el lote, `NG65` el modelo y `TL` la talla?
7. ¿Cuántas líneas tiene un ingreso típico y el más grande del mes? (Para el límite de filas.)
8. ¿Recibe solo en ALMFIKA y ALMFLU, o también en las tiendas?
9. ¿Qué pasó con los dos ingresos de hoy (455 y 310): con qué documento debieron registrarse?
10. ¿Quién debería aprobar un conteo físico o una corrección?
