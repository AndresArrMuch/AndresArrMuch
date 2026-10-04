# Anticipos a proveedores - asientos de ejemplo (prueba del 04/10/2026, datos de prueba)

Tipos de cambio venta usados en la prueba: 04/09 = 3.512, 10/09 = 3.480, 23/09 = 3.458. Facturas: TC propio de cada una.
Criterio vigente: OPCION A (42 y 422 a su valor en libros; la diferencia a 676101 / 776101).

## 1. Registro del anticipo (23/09, TRANSF.EXT N791049, Op 00112935, TC 3.458)
| Cuenta | Descripcion | Debe S/ | Haber S/ | Debe US$ | Haber US$ |
|---|---|---:|---:|---:|---:|
| 422102 | Anticipos a proveedores M.E. | 146,177.44 | | 42,272.25 | |
| 104102 | Banco de Credito M.E. | | 146,177.44 | | 42,272.25 |

## 2. Aplicacion a la factura F001-1001 (US$ 42,272.25 a TC 3.571) - ganancia
| Cuenta | Descripcion | Debe S/ | Haber S/ | Debe US$ | Haber US$ |
|---|---|---:|---:|---:|---:|
| 421202 | Facturas por pagar M.E. (valor en libros 42,272.25 x 3.571) | 150,954.20 | | 42,272.25 | |
| 422102 | Anticipo Op 00112935 (valor en libros 42,272.25 x 3.458) | | 146,177.44 | | 42,272.25 |
| 776101 | Ganancia por diferencia de cambio | | 4,776.76 | | |
| | **Totales** | **150,954.20** | **150,954.20** | **42,272.25** | **42,272.25** |

## 3. Aplicacion con perdida: factura F001-1002 (US$ 6,000 a TC 3.450) con anticipo de 10/09 (TC 3.480)
| Cuenta | Descripcion | Debe S/ | Haber S/ | Debe US$ | Haber US$ |
|---|---|---:|---:|---:|---:|
| 421202 | Facturas por pagar M.E. (6,000 x 3.450) | 20,700.00 | | 6,000.00 | |
| 676101 | Perdida por diferencia de cambio | 180.00 | | | |
| 422102 | Anticipo Op OP-A2 (6,000 x 3.480) | | 20,880.00 | | 6,000.00 |
| | **Totales** | **20,880.00** | **20,880.00** | **6,000.00** | **6,000.00** |
El anticipo de US$ 10,000 queda con saldo US$ 4,000 (S/ 13,920.00), que luego se aplico a otra factura.

## 4. Dos anticipos para una factura: F001-1004 (US$ 92,272.25 a TC 3.571)
Anticipos: US$ 50,000.00 del 04/09 (TC 3.512 = S/ 175,600.00) y US$ 42,272.25 del 23/09 (TC 3.458 = S/ 146,177.44).
| Cuenta | Descripcion | Debe S/ | Haber S/ | Debe US$ | Haber US$ |
|---|---|---:|---:|---:|---:|
| 421202 | Facturas por pagar M.E. (92,272.25 x 3.571) | 329,504.20 | | 92,272.25 | |
| 422102 | Anticipo Op OP-A4 (04/09) | | 175,600.00 | | 50,000.00 |
| 422102 | Anticipo Op OP-A3 (23/09) | | 146,177.44 | | 42,272.25 |
| 776101 | Ganancia por diferencia de cambio | | 7,726.76 | | |
| | **Totales** | **329,504.20** | **329,504.20** | **92,272.25** | **92,272.25** |

## Si se elige otra opcion (con el ejemplo 2)
- **Opcion B (sin diferencia de cambio; NIC 21 / CINIIF 22):** la 776101 se reemplaza por la cuenta de costo o gasto de la compra:
  Debe 421202 150,954.20 / Haber 422102 146,177.44 / Haber <costo de la compra> 4,776.76.
  Si la compra es mercaderia, el kardex ya entro a 3.571 y este ajuste no lo corrige.
- **Opcion C (todo al TC de la factura):** Debe 421202 150,954.20 / Haber 422102 150,954.20 (US$ 42,272.25 en ambas).
  La 422102 queda con US$ 0 pero con S/ 4,776.76 acreedor, que hay que ajustar a mano (en la practica, el mismo 776 de la opcion A, mas tarde).
