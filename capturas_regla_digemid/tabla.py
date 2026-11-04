import json
def load(f): return [json.loads(l) for l in open(f) if l.startswith('{')]
def corto(d):
    if 'respuestas' in d: return ' / '.join(f"{r['http']} {','.join(r['guias_en_respuesta'])}" for r in d['respuestas']) + f" (NubeCont: {len(d['nubecont'])} envios)"
    if 'filas' in d: return f"{len(d['filas'])} fila(s): " + ', '.join(f[0] for f in d['filas'])
    if 'guias' in d and 'nubecont' not in d: return ', '.join(d['guias'])
    g = ','.join(d['guias_en_respuesta']) or '-'
    cod = d['codigo'] or ''
    usado = d['contadores_antes'] != d['contadores_despues']
    envios = ','.join(e['guia'] for e in d['nubecont'])
    return f"{d['http']} {cod} guias={g}" + ('' if usado or d['http'] < 300 else ' (sin usar numero)') + (f" | NubeCont: {envios}" if envios else ' | sin llamar a NubeCont')
m, r = load('out_main_regla_test.txt'), load('out_rama_regla_test.txt')
print('| Caso | main (ddeb0e8) | rama |\n|---|---|---|')
for a, b in zip(m, r):
    print(f"| {a['caso']} | {corto(a)} | {corto(b)} |")
