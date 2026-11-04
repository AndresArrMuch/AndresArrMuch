# Casos SIN productos DIGEMID: el JSON enviado a NubeCont debe ser identico en main y en la rama. SOLO PRUEBA.
import sys
sys.argv = sys.argv[:5]
exec(open('/tmp/claude-0/repro/regla/regla_test.py').read().split("setmode('ok')\nRUTAS")[0])
setmode('ok')
SIN = [(N1, 'NIU'), (N2, 'BX')]
for r in ('IG', 'TC', 'GD', 'GF'):
    fn, ref = ruta(r, SIN, partida=None); caso(f'{r} sin DIGEMID', fn, ref)
fn, ref = ruta('GD', [(N1, 'NIU')], 'TTT2', partida=None); caso('GD serie del vendedor TTT2', fn, ref)
fn, ref = ruta('TC', SIN, partida=None); setmode('fail'); caso('TC NubeCont rechaza', fn, ref); setmode('ok'); caso('TC reintento', fn, ref)
nxt = int(sql("select coalesce(max(guide_correlative::int),0)+1 from sales_workflow where guide_series='TTT1'"))
open(LOG + '.occupy', 'w').write(f'TTT1-{str(nxt).zfill(6)}\n')
fn, ref = ruta('IG', SIN, partida=None); caso('IG ya existe', fn, ref)
fn, ref = ruta('GD', SIN, partida=None); setmode('timeout'); caso('GD tiempo de espera con guia creada', fn, ref); setmode('ok')
sid, fnum = factura(SIN); body = body_dg([L(N1, 'NIU'), L(N2, 'BX')], partida=None, src_sale=sid)
caso('GF dos veces la misma factura (1)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body), sid)
caso('GF dos veces la misma factura (2)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body), sid)
