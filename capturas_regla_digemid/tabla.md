| Caso | main (ddeb0e8) | rama |
|---|---|---|
| IG issue-guide | solo DIGEMID | 200  guias=TTT1-000020 | NubeCont: TTT1-000020 | 200  guias=TTT4-000001 | NubeCont: TTT4-000001 |
| IG issue-guide | mezclada | 200  guias=TTT1-000021,TTT4-000001 | NubeCont: TTT1-000021,TTT4-000001 | 200  guias=TTT1-000020,TTT4-000002 | NubeCont: TTT1-000020,TTT4-000002 |
| IG issue-guide | sin DIGEMID | 200  guias=TTT1-000022 | NubeCont: TTT1-000022 | 200  guias=TTT1-000021 | NubeCont: TTT1-000021 |
| IG issue-guide | pantalla vieja: TTT1 con producto DIGEMID, sin partida DIGEMID | 200  guias=TTT1-000023,TTT4-000002 | NubeCont: TTT1-000023,TTT4-000002 | 400 DIGEMID_DEPARTURE_REQUIRED guias=- (sin usar numero) | sin llamar a NubeCont |
| IG issue-guide | TTT4 con producto NO DIGEMID | 200  guias=TTT4-000003 | NubeCont: TTT4-000003 | 400 TTT4_ONLY_DIGEMID guias=- (sin usar numero) | sin llamar a NubeCont |
| TC direct-guide Traer cotizacion | solo DIGEMID | 201  guias=TTT1-000024 | NubeCont: TTT1-000024 | 201  guias=TTT4-000003 | NubeCont: TTT4-000003 |
| TC direct-guide Traer cotizacion | mezclada | 201  guias=TTT1-000025,TTT4-000004 | NubeCont: TTT1-000025,TTT4-000004 | 201  guias=TTT1-000022,TTT4-000004 | NubeCont: TTT1-000022,TTT4-000004 |
| TC direct-guide Traer cotizacion | sin DIGEMID | 201  guias=TTT1-000026 | NubeCont: TTT1-000026 | 201  guias=TTT1-000023 | NubeCont: TTT1-000023 |
| TC direct-guide Traer cotizacion | pantalla vieja: TTT1 con producto DIGEMID, sin partida DIGEMID | 201  guias=TTT1-000027,TTT4-000005 | NubeCont: TTT1-000027,TTT4-000005 | 400 DIGEMID_DEPARTURE_REQUIRED guias=- (sin usar numero) | sin llamar a NubeCont |
| TC direct-guide Traer cotizacion | TTT4 con producto NO DIGEMID | 201  guias=TTT4-000006 | NubeCont: TTT4-000006 | 400 TTT4_ONLY_DIGEMID guias=- (sin usar numero) | sin llamar a NubeCont |
| GD guia directa sin cotizacion | solo DIGEMID | 201  guias=TTT1-000028 | NubeCont: TTT1-000028 | 201  guias=TTT4-000005 | NubeCont: TTT4-000005 |
| GD guia directa sin cotizacion | mezclada | 201  guias=TTT1-000029 | NubeCont: TTT1-000029 | 201  guias=TTT4-000006,TTT1-000024 | NubeCont: TTT4-000006,TTT1-000024 |
| GD guia directa sin cotizacion | sin DIGEMID | 201  guias=TTT1-000030 | NubeCont: TTT1-000030 | 201  guias=TTT1-000025 | NubeCont: TTT1-000025 |
| GD guia directa sin cotizacion | pantalla vieja: TTT1 con producto DIGEMID, sin partida DIGEMID | 201  guias=TTT1-000031 | NubeCont: TTT1-000031 | 400 DIGEMID_SERIES_REQUIRED guias=- (sin usar numero) | sin llamar a NubeCont |
| GD guia directa sin cotizacion | TTT4 con producto NO DIGEMID | 201  guias=TTT4-000007 | NubeCont: TTT4-000007 | 400 TTT4_ONLY_DIGEMID guias=- (sin usar numero) | sin llamar a NubeCont |
| GF guia desde factura | solo DIGEMID | 201  guias=TTT1-000032 | NubeCont: TTT1-000032 | 201  guias=TTT4-000007 | NubeCont: TTT4-000007 |
| GF guia desde factura | mezclada | 201  guias=TTT1-000033 | NubeCont: TTT1-000033 | 201  guias=TTT4-000008,TTT1-000026 | NubeCont: TTT4-000008,TTT1-000026 |
| GF guia desde factura | sin DIGEMID | 201  guias=TTT1-000034 | NubeCont: TTT1-000034 | 201  guias=TTT1-000027 | NubeCont: TTT1-000027 |
| GF guia desde factura | pantalla vieja: TTT1 con producto DIGEMID, sin partida DIGEMID | 201  guias=TTT1-000035 | NubeCont: TTT1-000035 | 400 DIGEMID_SERIES_REQUIRED guias=- (sin usar numero) | sin llamar a NubeCont |
| GF guia desde factura | TTT4 con producto NO DIGEMID | 201  guias=TTT4-000008 | NubeCont: TTT4-000008 | 400 TTT4_ONLY_DIGEMID guias=- (sin usar numero) | sin llamar a NubeCont |
| GD | TTT4 con producto NO DIGEMID, interruptor desactivado (=0) | 201  guias=TTT4-000009 | NubeCont: TTT4-000009 | 201  guias=TTT4-000009 | NubeCont: TTT4-000009 |
| IG | mezclada: falla la segunda guia (TTT4) | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT1-000036,TTT4-000010 | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT1-000028,TTT4-000010 |
| IG | reintento: solo la parte TTT4 pendiente | 200  guias=TTT4-000010 | NubeCont: TTT4-000010 | 200  guias=TTT4-000010 | NubeCont: TTT4-000010 |
| TC | mezclada: falla la segunda guia (TTT4) | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT1-000037,TTT4-000011 | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT1-000029,TTT4-000011 |
| TC | reintento: solo la parte TTT4 pendiente | 201  guias=TTT4-000011 | NubeCont: TTT4-000011 | 201  guias=TTT4-000011 | NubeCont: TTT4-000011 |
| GD | mezclada: falla la segunda guia (la no DIGEMID) | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT1-000038 | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT4-000012,TTT1-000030 |
| GD | reintento con los productos que quedaron en el formulario (solo P0001) | 201  guias=TTT1-000038 | NubeCont: TTT1-000038 | 201  guias=TTT1-000030 | NubeCont: TTT1-000030 |
| GF | mezclada F001-000006: falla la segunda guia | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT1-000039 | 502 PARTIAL_GUIDE_SPLIT_FAILURE guias=- | NubeCont: TTT4-000013,TTT1-000031 |
| GF | reintento F001-000006 con lo pendiente (solo P0001) | 201  guias=TTT1-000039 | NubeCont: TTT1-000039 | 201  guias=TTT1-000031 | NubeCont: TTT1-000031 |
| GF | tercer intento F001-000006 con todo otra vez (no debe duplicar) | 400 SALE_ALREADY_HAS_GUIDE guias=- (sin usar numero) | sin llamar a NubeCont | 400 SALE_ALREADY_HAS_GUIDE guias=- (sin usar numero) | sin llamar a NubeCont |
| IG solo DIGEMID | NubeCont rechaza | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT1-000040 | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT4-000014 |
| IG solo DIGEMID | reintento tras rechazo | 200  guias=TTT1-000040 | NubeCont: TTT1-000040 | 200  guias=TTT4-000014 | NubeCont: TTT4-000014 |
| GD solo DIGEMID | NubeCont rechaza | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT1-000041 | 502 NUBECONT_GUIDE_SEND_ERROR guias=- (sin usar numero) | NubeCont: TTT4-000015 |
| IG solo DIGEMID | NubeCont dice ya existe (TTT4-000012 ocupado) | 200  guias=TTT1-000041 | NubeCont: TTT1-000041 | 200  guias=TTT4-000016 | NubeCont: TTT4-000015,TTT4-000016 |
| TC mezclada | tiempo de espera pero NubeCont SI creo las guias | 201  guias=TTT1-000042,TTT4-000013 | NubeCont: TTT1-000042,TTT4-000012,TTT4-000013 | 201  guias=TTT1-000032,TTT4-000017 | NubeCont: TTT1-000032,TTT4-000017 |
| IG | dos usuarios a la vez, misma cotizacion mezclada | 200 TTT1-000043,TTT4-000014 / 200 TTT1-000043,TTT4-000014 (NubeCont: 2 envios) | 200 TTT1-000033,TTT4-000018 / 200 TTT1-000033,TTT4-000018 (NubeCont: 2 envios) |
| TC | dos usuarios a la vez, misma cotizacion mezclada | 201 TTT1-000044,TTT4-000015 / 201 TTT1-000044,TTT4-000015 (NubeCont: 2 envios) | 201 TTT1-000034,TTT4-000019 / 201 TTT1-000034,TTT4-000019 (NubeCont: 2 envios) |
| GD | stock insuficiente de P0003 (pide 999) | 400 INSUFFICIENT_STOCK_FOR_GUIDE guias=- (sin usar numero) | sin llamar a NubeCont | 400 INSUFFICIENT_STOCK_FOR_GUIDE guias=- (sin usar numero) | sin llamar a NubeCont |
| GF | factura F001-000007 mezclada: dos guias vinculadas | 201  guias=TTT1-000045 | NubeCont: TTT1-000045 | 201  guias=TTT4-000020,TTT1-000035 | NubeCont: TTT4-000020,TTT1-000035 |
| reporte sale-guides: guias de F001-000007 | TTT1-000045 | TTT1-000035, TTT4-000020 |
| reporte Guias para DIGEMID: filas de F001-000007 | 1 fila(s): TTT1-000045 | 1 fila(s): TTT4-000020 |
| IG | serie TTT5 (reservada a traslados) | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont |
| GD | serie TTT5 (reservada a traslados) | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont |
| GD | serie TTT5 con producto DIGEMID | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont | 400 GUIDE_SERIES_RESERVED_FOR_TRANSFERS guias=- (sin usar numero) | sin llamar a NubeCont |
