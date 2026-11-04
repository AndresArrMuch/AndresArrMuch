import json, sys
for line in open(sys.argv[1]):
    if not line.startswith('{'): print('  !!', line.strip()[:200]); continue
    d = json.loads(line)
    c = d.pop('caso'); d.pop('srv')
    if 'respuestas' in d:
        print(f"* {c}\n    respuestas={[(r['http'], r['codigo'], r['guias_en_respuesta']) for r in d['respuestas']]} nubecont={d['nubecont']} registradas={d['guias_registradas']}"); continue
    if False:
        print(f"* {c}\n    respuestas={[(r['http'], r['codigo'], r['guias_en_respuesta']) for r in d['respuestas']]} nubecont={d['nubecont']} registradas={d['guias_registradas']}"); continue
    if 'filas' in d or 'guias' in d and 'http' in d and 'nubecont' not in d:
        print(f"* {c}\n    {d}"); continue
    env = '; '.join(f"{e['guia']}({e['modo']}) partida={e['partida']} items={e['items']}" for e in d.get('nubecont', []))
    print(f"* {c}\n    HTTP {d['http']} {d['codigo'] or ''} | guias={d['guias_en_respuesta']} | registradas={d.get('guias_registradas')}\n    contadores {d.get('contadores_antes')} -> {d.get('contadores_despues')}\n    nubecont: {env or '(ninguna llamada)'}"
          + (f"\n    mensaje: {d['mensaje']}" if d['codigo'] or d['http'] >= 300 else ''))
