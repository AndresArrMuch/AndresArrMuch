import json, sys
from decimal import Decimal as D
BK = {'main': '/tmp/claude-0/wt_ple/backend', 'rama': '/tmp/claude-0/wt_plev/backend'}
def load(n):
    R = json.load(open(f'{n}.json'))
    assert not R['errores_js'], R['errores_js']
    ex = {}
    for f in R['excel']['filas']:
        if not f or not f[8]: continue
        doc = f"{f[8]}-{str(f[9]).zfill(6)}"
        ex[doc] = dict(P=f[15], R=f[17], AA=f[26], AD=f[29], AE=f[30], AF=f[31], AG=f[32], AJ=f[35], BF=(f[57] if len(f) > 57 else ''))
    ts = {}
    for l in R['txt_sunat']['texto'].strip().split('\n'):
        c = l.split('|'); ts[f"{c[7]}-{c[8]}"] = dict(base=c[14], igv=c[16], total=c[25], estado=c[34], ncampos=len(c))
    tt = {}
    path = BK[n] + '/' + R['txt_tributario']['file_path']
    for l in open(path).read().strip().split('\n'):
        c = l.split('|'); tt[f"{c[4]}-{c[5]}"] = dict(base=c[8], igv=c[9], total=c[10], estado=c[11], ncampos=len(c))
    return R, ex, ts, tt
out = []
pr = lambda *a: out.append(' '.join(str(x) for x in a))
data = {n: load(n) for n in ('main', 'rama')}
for n, (R, ex, ts, tt) in data.items():
    pr(f'===== {n.upper()} =====')
    pr('Excel:', R['excel']['archivo'], 'rango', R['excel']['ref'], 'autofiltro', R['excel']['autofilter'], 'encabezado BF:', R['excel']['encabezado_BF'])
    pr(f"{'Documento':13} {'P base':>9} {'R IGV':>8} {'AA total':>9} AJ  {'AD fecha':10} AE  AF    AG  BF observacion")
    for d, v in ex.items():
        pr(f"{d:13} {v['P']:>9} {v['R']:>8} {v['AA']:>9} {v['AJ']:<3} {str(v['AD']):10} {str(v['AE']):3} {str(v['AF']):5} {str(v['AG']):3} {v['BF']}")
    pr('TOTAL Excel  P=%s R=%s AA=%s' % tuple(round(sum(D(str(v[k] or 0)) for v in ex.values()), 2) for k in ('P', 'R', 'AA')))
    pr(f"TXT export-sunat (periodo contable 2026-10, {len(ts)} lineas, campos por linea: {sorted({v['ncampos'] for v in ts.values()})})")
    for d, v in ts.items(): pr(f"  {d:13} base {v['base']:>9} igv {v['igv']:>8} total {v['total']:>9} estado {v['estado']}")
    pr('TOTAL TXT export-sunat base=%s igv=%s total=%s' % tuple(sum(D(v[k]) for v in ts.values()) for k in ('base', 'igv', 'total')))
    pr(f"TXT Tributario ({len(tt)} lineas, campos por linea: {sorted({v['ncampos'] for v in tt.values()})})")
    for d, v in tt.items(): pr(f"  {d:13} base {v['base']:>9} igv {v['igv']:>8} total {v['total']:>9} estado '{v['estado']}'")
    pr('TOTAL TXT Tributario base=%s igv=%s total=%s' % tuple(sum(D(v[k]) for v in tt.values()) for k in ('base', 'igv', 'total')))
    pr()
print('\n'.join(out))
