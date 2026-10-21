# Registro de Ventas: anulados en cero y notas de crédito en negativo (implementado, sin instalar)

Rama `claude/ple-ventas-nc-anulados`, commit `02d1d29`, sobre main `2d95f94`.

## Qué cambia
| Exportación | Cambio |
|---|---|
| Excel "Exportar Detallado PLE" | NC con base, IGV y total en negativo. Anulados con importes en 0 y los datos del cliente conservados. AJ = `PLE_ESTADO_ANULADO` para los anulados. AD a AG con el documento modificado de las NC y ND. Columna nueva BF "Observación". |
| TXT export-sunat (reporte periódico) | Solo los signos de las NC y los ceros de los anulados. Mismos 57 campos; el estado sigue en 1. |
| TXT de Tributario (`exportPleTxt`) | Solo los signos de las NC y los ceros de los anulados. Mismos 12 campos; el estado sigue siendo el texto de `sunat_status`. |

- **Estado de anulado:** constante `PLE_ESTADO_ANULADO = 2` en `backend/index.html`, justo antes de `async function exportSalesPle()`. Es provisional y está en un solo lugar. Hoy solo la usa el Excel, porque en los TXT no se tocó el estado.
- **Regla de los TXT:** `backend/app/utils/ple_rules.py`.
- **B030-000016 (boleta sin estado SUNAT):** se incluye con sus importes y la observación "Sin estado SUNAT (no enviado o sin respuesta)".
- **Sin cambios:** el criterio de cada exportación (Excel por mes de emisión, TXT por periodo contable), las 8 NC sin asiento y el formato del TXT de Tributario.

## Pruebas
- **Base:** `ple_test` es una copia de la base de pruebas `af_base` con FIKA, octubre 2026, más los 3 documentos de `datos_prueba.sql`.
- **Cómo se corrieron:** la misma pantalla y las mismas rutas en main `2d95f94` y en la rama. Se compararon el Excel descargado y los dos TXT. Detalle en `comparacion_main_vs_rama.txt`.

| | Main | Rama | Diferencia |
|---|---|---|---|
| Excel, total CP (AA) | 5,291.80 | 4,088.20 | 1,203.60 |
| TXT export-sunat, total | 4,819.80 | 3,616.20 | 1,203.60 |
| TXT Tributario, total | 5,019.80 | 3,816.20 | 1,203.60 |

- **De dónde sale la diferencia:** 1,203.60 = 2 × (236.00 + 59.00 + 11.80) de las tres NC, que antes sumaban y ahora restan, + 590.00 del anulado F001-000002. Es lo esperado.
- **Casos probados:**
  - factura normal F001-000001: sin cambio;
  - nota de débito FD01-000001: positiva, con AD a AG llenas;
  - NC FC01-000001 y BC40-000001: en negativo, con AD a AG. Al tipo vacío de FC01 se le toma el tipo de la venta referida;
  - anulado F001-000002: en 0 y AJ = 2, con los datos del cliente;
  - boletas o facturas sin estado SUNAT (B030-000016, F001-000003, F030-000119): incluidas y marcadas;
  - NC FC50-000001 a un documento que no existe en el sistema: AD vacía y una observación que lo dice.
- **Pruebas automáticas:** `pytest backend/tests` da 37 aprobadas, 5 de ellas nuevas en `test_ple_ventas_regla.py`.

## Observaciones vistas en la prueba (no se cambiaron)
- **El TXT de Tributario no filtra `is_active`:** incluye F001-000007, que está inactiva. Excel y export-sunat no la incluyen.
- **F001-000005 está en el Excel pero no en los TXT:** se emitió en octubre pero está en el periodo de septiembre. Es el criterio de cada exportación, que no se cambió.

## TXT de Tributario frente al formato oficial PLE 14.1 (solo documentado, sin cambios)
Para decidirlo con el contador. **La estructura oficial la cito de memoria** (Anexo N.° 2 de la RS 286-2009/SUNAT y modificatorias, Registro de Ventas e Ingresos 14.1). No pude verificarla en línea desde este entorno, así que debe confirmarse contra la versión vigente.

| | TXT de Tributario hoy | PLE 14.1 oficial (de memoria) |
|---|---|---|
| Cantidad de campos | 12 | Unos 35 o 36, según la versión |
| Campo 1 | Periodo `AAAAMM00` | Periodo `AAAAMM00` (coincide) |
| Campo 2 | Número de orden `000001` | CUO (código único de la operación) |
| Campo 3 | Fecha de emisión | Correlativo del asiento (M/A/C + número) |
| Fecha de vencimiento o pago | No está | Campo 5 |
| Número final (resúmenes de boletas) | No está | Campo 9 |
| Tipo de documento del cliente | No está (solo el número) | Campo 10 (1 = DNI, 6 = RUC, etc.) |
| Exportación, exonerada, inafecta, ISC, IVAP, ICBPER, otros tributos | No están | Campos propios |
| Moneda y tipo de cambio | No están | Campos propios |
| Documento modificado de NC y ND (fecha, tipo, serie, número) | No está | 4 campos |
| Estado | Texto de `sunat_status` ("aceptada", "anulada", vacío) | Código numérico (1, 2, 8, 9) |
| Nombre del archivo | `LE<RUC><AAAAMM00>140100` + `00111.txt` | Mismo patrón; los últimos dígitos indican la oportunidad, si hay contenido, la moneda y el origen |
| Separador final | Sin `|` al final | Cada línea termina en `|` |
| Ventas inactivas | Incluidas | — |

**Conclusión:** el TXT de Tributario no se puede subir al PLE tal como está. El TXT export-sunat se parece más al Excel (57 campos, al estilo del SIRE) que al 14.1. Antes de tocar cualquiera de los dos, el contador debe definir qué archivo se declara (PLE 14.1 o SIRE RVIE).
