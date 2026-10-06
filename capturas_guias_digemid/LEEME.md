# Pruebas de la rama cea-erp `claude/guias-digemid` (a0e490f), sin instalar

Las pruebas se hicieron en una base PostgreSQL de prueba armada con `datos.py`:

- **Facturas:**
  - F001-1, con una guía;
  - F001-2, con dos guías (de venta + parte DIGEMID);
  - F001-3, DIGEMID sin guía (la nota menciona TTT4-000009 y hay una candidata TTT4-000002);
  - F001-4, sin productos DIGEMID;
  - F001-5, con una línea sin producto;
  - F001-6, anulada.
- **Guías:**
  - de venta sin DIGEMID;
  - directa dada de baja internamente;
  - TTT4 anulada en SUNAT;
  - de traslado TTT5;
  - una de otra empresa (no debe verse).

| Archivo | Qué contiene |
|---|---|
| `cobertura_resultado.txt` | Salida de `cobertura_guias_digemid.sql` |
| `api_res.txt` | Rutas del servidor: filtros, partida/llegada y PDF (NubeFact simulado), caché, tope, acceso de otra empresa (403) y sin sesión (401) |
| `dig_ventas.xlsx` / `main_ventas.xlsx` | Excel de facturas de la rama (16 columnas) y de main (12) |
| `dig_digemid.xlsx` | Excel "Guías para DIGEMID" |
| `excels_leidos.txt` | Contenido de los tres Excel |
| `dig_digemid_1.png` / `dig_digemid_2.png` | Pantalla del reporte, antes y después de traer partida/llegada y PDF |
| `vol.py` | Prueba de volumen: 3,000 guías (9,005 filas) en 0.86 s |

En estas pruebas NubeFact está simulado (`serve_dig.py`, `api_test.py`); las direcciones de partida y llegada que aparecen son de prueba.

## Ajustes (bd65fb7)

| Archivo | Qué contiene |
|---|---|
| `api_ajustes_res.txt` | Reporte del periodo 09/2026: solo productos DIGEMID; lote, F.F. y F.V. tomados del nombre completo aunque la línea esté recortada; factura y guía sugeridas |
| `conteo_lote_vencimiento_resultado.txt` | `conteo_lote_vencimiento_digemid.sql` en la base de prueba |
| `comparacion_python_vs_sql.txt` | Mismas reglas en el reporte y en el SQL: 13 textos, 0 diferencias |
| `dig_digemid_periodo.xlsx` | Excel bajado eligiendo solo el periodo |
| `dig_ventas.xlsx` | Excel de facturas, con la columna de guía sugerida |
| `excels_ajustes_leidos.txt` | Contenido de esos dos Excel |
