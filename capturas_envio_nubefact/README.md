# Envío a NubeFact por autoservicio (rama `claude/envio-nubefact-autoservicio`, commit `529fc86`)

- **Base:** main del servidor `710e86b`.
- **Cómo se probó:** siempre con un NubeFact **simulado** (`fake_nubefact2.py`), en una copia de la base de prueba `af_base`. Nunca se usó NubeFact real ni producción.

## Archivos
| Archivo | Contenido |
|---|---|
| `comparacion_main_vs_rama.txt` | Los 11 casos del servidor, main contra la rama |
| `resultado_pantalla.json` y capturas `1_` a `5_` | La prueba en el navegador |
| `pytest.txt` | 44 pruebas automáticas aprobadas (49 junto con la rama del token) |
| `api_test.py`, `compare.py`, `ui.js`, `fake_nubefact2.py` | Los scripts de prueba |

## Capturas
1. **Facturación (gerente):** F030-000119 con "No enviado a SUNAT" y el botón rojo "Enviar a SUNAT". Arriba, "Pendientes de SUNAT (2)".
2. **Venta desde la pantalla con NubeFact caído:** "El comprobante F020-000001 QUEDÓ REGISTRADO pero NO llegó a SUNAT…", con "Reintentar ahora".
3. **La misma venta otra vez:** el sistema ofrece enviar la pendiente y no crea otra. Queda una sola F020, aceptada y contabilizada.
4. **"Enviar a SUNAT" desde la fila:** F030-000119 aceptada, con PDF, XML y CDR. Como es igual a F030-000120, ya aceptada, se le pidió confirmación al gerente.
5. **Lista de pendientes del gerente.**
