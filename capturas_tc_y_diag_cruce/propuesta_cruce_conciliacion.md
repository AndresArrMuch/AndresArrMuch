# Propuesta: cruce de la Conciliación con monto y sentido (sin implementar)

## Regla actual (sin cambios)
Una fila del extracto queda **Registrado** si se cumple cualquiera de estas condiciones:
- **A.** Hay un movimiento bancario con el mismo N.° de operación y la misma fecha, en cualquier cuenta de la empresa. No compara monto, sentido ni cuenta.
- **B.** Hay una marca del botón Pagar, Cambio o Anticipo con la misma cuenta, N.°, fecha y monto con signo. Ya compara todo.
- **C.** Hay un cobro o pago de la misma cuenta, con el mismo N.°, a ±5 días y con el mismo monto (o con la suma de varios). Compara el monto, pero no si es cobro o pago.

## Regla propuesta
| Estado | Cuándo |
|---|---|
| **Registrado** | A estricta (ver abajo), B sin cambios, o C con el sentido correcto (cobro con abono, pago con cargo). |
| **Revisar** (ámbar, nuevo) | Solo existe una coincidencia floja: mismo N.° y fecha, pero con monto distinto, sentido contrario u otra cuenta, o un cobro/pago de sentido contrario. Muestra el motivo, por ejemplo: "Revisar: monto distinto (sistema S/ 2,999.00)". |
| **Error** / **Duplicado** | Sin cambios. |

**A estricta:** movimientos de la **misma cuenta** del extracto, con el mismo N.° y la misma fecha, del **mismo sentido** (abono = depósito; cargo = cualquier otro tipo), cuya **suma** sea igual al monto de la fila, con una tolerancia de **0.01** que se puede configurar.
- Se suman porque un cobro dividido crea un depósito por cada cobro con el mismo N.°.
- Los movimientos de otras cuentas se ignoran, por ejemplo el que crea Pagos en "Cuenta Comisiones" con el mismo N.°.

## Filas actuales que cambiarían de Registrado a Revisar
Son exactamente las que lista `diag_cruce_conciliacion.sql` en producción.
- En la base de prueba fueron 4 de 6: monto distinto, sentido contrario, otra cuenta, y un pago que cruzaba con un abono.
- La consulta y la pantalla dan el mismo estado en las 8 filas.

## Casos especiales
- **Redondeo:** una tolerancia de 0.01 por defecto, configurable (por ejemplo 0.05) en un parámetro. Los movimientos del sistema se guardan en la moneda del banco, así que no hay conversión entre monedas en el cruce.
- **Pagos de varios documentos:** Pagos crea un solo movimiento con el total (documentos + comisión) y el mismo N.°, y cruza bien. Los depósitos divididos en varios cobros cruzan por la suma (en A estricta y en C, que ya lo hace).
- **Dólares:** el extracto y el movimiento bancario están ambos en US$, así que no cambia nada.
  - Ya existe un riesgo en C: en pagos en dólares, `total_amount` puede estar en soles.
  - Propuesta: comparar `total_amount_me` cuando la cuenta es en dólares.
- **Cobros a ±5 días:** se mantiene la tolerancia de fecha y solo se agrega el sentido (cobro con abono, pago con cargo).
- **Marcas de Pagar:** sin cambios.

## Riesgos
1. Filas correctas en la realidad que pasarían a "Revisar":
   - depósitos netos de comisión del banco, donde el monto del cobro es distinto del abono;
   - movimientos cargados antes con otro monto.

   El diagnóstico permite verlas y corregirlas antes de activar la regla.
2. Totales y contadores:
   - los totales de "registrado" y "error" de la Conciliación y la lista "Error" de Bancos › Movimiento entre cuentas cambian;
   - las filas en "Revisar" no deben ofrecerse para registrar otra vez, porque eso duplicaría un movimiento.
3. Una sola función:
   - la pantalla de Conciliación y la guía de Bancos (`concEstadoFilasExtracto`) deben pasar a usar la misma función, para que no diverjan.

## Activación segura
1. Ejecutar el diagnóstico en producción y corregir o aceptar cada fila.
2. Crear el parámetro por empresa `conciliacion_cruce_estricto`, **apagado por defecto**. Mientras esté apagado, la pantalla queda idéntica a hoy.
3. Modo "sombra" opcional: con el parámetro apagado, mostrar solo un contador informativo, "N filas se marcarían Revisar", sin cambiar estados.
4. Encender el parámetro en una empresa, revisar un mes conciliado y luego encenderlo en la otra.
5. Para volver atrás basta con apagar el parámetro. No se modifica ningún dato.
