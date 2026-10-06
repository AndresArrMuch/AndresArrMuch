# Pruebas de la rama cea-erp `claude/cobros-correccion` (2bb3e2f), sin instalar

Las pruebas comparan `main` (4cc58ec) con la rama.

| Archivo | Qué contiene |
|---|---|
| `res1.txt` | Periodo cerrado, fecha imposible, cobros en dólares (cuenta en US$, cuenta en soles, con comisión), soles y dólares juntos, COMISIONES como banco |
| `res2.txt` | Editar un cobro de 3 facturas, Editar con comisión (2 veces), Eliminar en periodo cerrado y en abierto, borrar el movimiento en Transacciones |
| `res3.txt` | Comisión; cobro antiguo editado (solo rama); cobro antiguo con fecha en un mes cerrado; venta en USD con provisión como la de producción |
| `ui_cob_res.txt` / `ui_main_res.txt` | Prueba en pantalla (Chromium) de la rama y de `main`: doble clic, comisión, Editar, USD, varias facturas con comisión |
| `pagos_sin_cambios.txt` | Las 9 pruebas de pagos a proveedores en `main` y en la rama: iguales, salvo una palabra del mensaje |

Los asientos de ejemplo están en `backend/scripts/cobros_correccion_ejemplos.md` (rama `claude/cobros-correccion`).

**Cómo repetir las pruebas:** `run.sh main|rama CASO` y `ui_run.sh main|cob PUERTO`.
