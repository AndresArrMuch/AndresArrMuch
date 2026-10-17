import json, sys
S = sys.argv[1]; T = 'TKN-PRUEBA-7f3a9c1e5b2d'; R = 'http://127.0.0.1:8931/api/ruta-secreta-0b9e4c'
def norm(m): return None if m is None else str(m).replace(T, '***').replace(R, '***').replace('/api/ruta-secreta-0b9e4c', '***')
lines = []
for u in ('vendedor.fika', 'central', 'sistema.fika'):
    m = json.load(open(f'{S}/r_main_{u}.json')); r = json.load(open(f'{S}/r_rama_{u}.json'))
    lines.append(f"\n=== {u}: respuestas {r['total_respuestas']} | MAIN con token {len(m['respuestas_con_token'])}, con ruta {len(m['respuestas_con_ruta'])} | RAMA con token {len(r['respuestas_con_token'])}, con ruta {len(r['respuestas_con_ruta'])} | registro RAMA: token {r['registro_con_token']}, ruta {r['registro_con_ruta']} (MAIN: token {m['registro_con_token']}, ruta {m['registro_con_ruta']})")
    diff = 0
    for a, b in zip(m['rutas_nubefact'] + m['rutas_get'], r['rutas_nubefact'] + r['rutas_get']):
        same = (a['ruta'], a['http'], a['codigo'], norm(a['mensaje']), a['estado']) == (b['ruta'], b['http'], b['codigo'], norm(b['mensaje']), b['estado'])
        if not same:
            diff += 1; lines.append(f"  DISTINTO {a['metodo']} {a['ruta']}: main {a['http']} {a['codigo']} {norm(a['mensaje'])} {a['estado']} | rama {b['http']} {b['codigo']} {b['mensaje']} {b['estado']}")
    lines.append(f"  rutas con http/codigo/mensaje/estado distintos (token reemplazado por ***): {diff}")
    if u == 'sistema.fika':
        lines.append('  Rutas que llaman a NubeFact (rama):')
        for b in r['rutas_nubefact']:
            lines.append(f"    {b['metodo']:4} {b['ruta'][:75]:75} {b['http']} {str(b['codigo'] or ''):32} {str(b['mensaje'] or '')[:70]} {b['estado'] or ''}")
    if m['respuestas_con_token'] and u == 'vendedor.fika':
        lines.append('  MAIN, respuestas con el token (Vendedor): ' + '; '.join(m['respuestas_con_token']))
print('\n'.join(lines))
