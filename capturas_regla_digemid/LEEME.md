# Pruebas de la regla DIGEMID: rama cea-erp `claude/guias-serie-digemid` (03aafe4) contra main (ddeb0e8)

**Sin instalar.** NubeCont está simulado (`serve_regla.py`) y cada corrida usa una base PostgreSQL nueva creada desde `igbase`.

| Archivo | Qué contiene |
|---|---|
| `tabla.md` | Cuadro main contra rama: 44 casos (cuatro rutas × solo DIGEMID / mezclada / sin DIGEMID / pantalla vieja con TTT1 / TTT4 con producto no DIGEMID; interruptor; falla de la segunda guía y reintento; NubeCont rechaza; "ya existe"; tiempo de espera; dos usuarios a la vez; stock; factura con dos guías y reporte; TTT5) |
| `legible_*_regla_test.txt` | El mismo detalle, por caso: guías, contadores antes y después, envíos a NubeCont con la partida y las unidades |
| `out_*_json_cmp.txt`, `nube_*_json_cmp.jsonl` | Casos SIN productos DIGEMID: 11 envíos idénticos a main, campo por campo (69 campos cada uno) |
| `legible_*_extra_test.txt` | Cotización mezclada ya facturada: main emite una TTT1 con el producto DIGEMID; la rama la rechaza y emite las dos guías desde la factura |
| `out_*_ig_test.txt` | Protecciones ya instaladas (bfbf9c8 / ec281d0): 16 de 18 iguales; en 8a solo cambia el mensaje (ahora legible) y en 9a solo el orden de las dos respuestas simultáneas |
| `ui_rama.txt`, `ui_main.txt`, `*.png` | Pantalla con Chromium: panel de partida DIGEMID sin valor por defecto, error rojo, modal que no se cierra, y el formulario queda solo con lo pendiente si falla una guía |
