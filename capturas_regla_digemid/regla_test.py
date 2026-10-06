# Pruebas de la regla DIGEMID (main contra la rama). SOLO PRUEBA, NubeCont simulado (serve_regla.py).
# Uso: python regla_test.py PORT DB LOG TAG
import sys, json, os, threading, subprocess, urllib.request
sys.path.insert(0, '/tmp/claude-0/repro/unidad'); from u import CID, ALM, CLI, IT, GUIA, msg
PORT, DB, LOG, TAG = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
DIG, N1, N2 = IT['PAR'], IT['NIU'], IT['BX']          # P0003 OXIMETRO (DIGEMID, PAR), P0001 TERMOMETRO (NIU), P0002 TENSIOMETRO (BX)
PARTIDA_DIG = 'JR. HUALLAGA 767 Int 111'
B = f'http://127.0.0.1:{PORT}'; TOK = {}
def tok():
    if 'a' not in TOK:
        r = urllib.request.Request(B + '/api/auth/login', data=json.dumps({'email': 'admin@t.pe', 'password': 'p', 'company_id': CID}).encode(), headers={'Content-Type': 'application/json'})
        TOK['a'] = json.loads(urllib.request.urlopen(r).read())['data']['tokens']['access_token']
    return TOK['a']
def call(m, url, body=None):
    r = urllib.request.Request(B + url.replace('{cid}', CID), method=m.upper(), data=json.dumps(body).encode() if body is not None else None,
                               headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok()})
    try:
        resp = urllib.request.urlopen(r, timeout=120); return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except Exception: return e.code, {}
def sql(q): return subprocess.run(['psql', '-h', '/var/run/postgresql', '-p', '5433', '-U', 'postgres', DB, '-Atc', q], capture_output=True, text=True).stdout.strip()
def setmode(m): open(LOG + '.mode', 'w').write(m)
def nube():
    try: return [json.loads(l) for l in open(LOG)]
    except Exception: return []
def out(caso, **kw): print(json.dumps(dict({'srv': TAG, 'caso': caso}, **kw), ensure_ascii=False, default=str), flush=True)
def L(item, unit, qty=1, wh=ALM): return {'inventory_item_id': item, 'description': 'x', 'quantity': qty, 'unit': unit, 'unit_price': 50, 'warehouse_id': wh}
def cot(lines):
    s, d = call('post', '/api/sales/{cid}/workflow/quotations', {'customer_id': CLI, 'quotation_date': '2026-10-07', 'lines': lines})
    w = d['data']['id']; call('post', f'/api/sales/{{cid}}/workflow/{w}/accept'); return w
FP = sql(f"select id from fiscal_period where company_id='{CID}' and period_year=2026 and period_month=10")
NF = [0]
def factura(items):
    NF[0] += 1; num = f'{NF[0]:06d}'; sid = sql("select gen_random_uuid()::text")
    sql(f"insert into sale (id, company_id, customer_id, fiscal_period_id, document_type, series, correlative, document_number, emission_date, due_date, registration_date, currency, exchange_rate, subtotal, igv, total, status, created_at, updated_at, is_active) "
        f"values ('{sid}', '{CID}', '{CLI}', '{FP}', '01', 'F001', '{num}', 'F001-{num}', '2026-10-07', '2026-10-07', '2026-10-07', 'PEN', 1, 100, 18, 118, 'emitted', now(), now(), true)")
    for it, unit in items:
        sql(f"insert into sale_line (id, sale_id, company_id, inventory_item_id, description, quantity, unit, unit_price, subtotal, igv, total, created_at, updated_at, is_active) "
            f"values (gen_random_uuid()::text, '{sid}', '{CID}', '{it}', (select description from inventory_item where id='{it}'), 1, '{unit}', 50, 50, 9, 59, now(), now(), true)")
    return sid, f'F001-{num}'
GD = dict(GUIA['guide_data'], punto_de_partida_direccion='AV PRUEBA 123', punto_de_llegada_direccion='JR CLIENTE 456', serie='TTT1', dispatch_date='2026-10-07')
def body_ig(series='TTT1', partida=PARTIDA_DIG):       # igual que wfIssueGuide() de la pantalla
    b = {'dispatch_date': '2026-10-07', 'series': series, 'send_electronic': True, 'nubecont_environment': 'test', 'guide_data': GD}
    if partida: b['digemid_departure_address'] = partida
    return b
def body_dg(lines, series='TTT1', partida=PARTIDA_DIG, src_wf=None, src_sale=None):   # igual que wfCreateDirectGuide()
    b = {'customer_id': CLI, 'dispatch_date': '2026-10-07', 'series': series, 'currency': 'PEN', 'notes': '', 'vendedor_id': None, 'lines': lines,
         'guide_data': GD, 'send_electronic': True, 'source_workflow_id': src_wf, 'source_sale_id': src_sale, 'sale_id': src_sale,
         'digemid_departure_address': partida or ''}
    return b
def ruta(r, items, series='TTT1', partida=PARTIDA_DIG):
    """Emite por la ruta r con los productos items [(id, unidad)]. Devuelve (llamada, id de referencia)."""
    lines = [L(i, u) for i, u in items]
    if r == 'IG':
        w = cot(lines); return (lambda: call('post', f'/api/sales/{{cid}}/workflow/{w}/issue-guide', body_ig(series, partida))), w
    if r == 'TC':
        w = cot(lines); return (lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines, series, partida, src_wf=w))), w
    if r == 'GD':
        return (lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines, series, partida))), None
    if r == 'GF':
        sid, _ = factura(items); return (lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines, series, partida, src_sale=sid))), sid
def contadores(): return sql("select string_agg(guide_series||'='||m, ' ' order by guide_series) from (select guide_series, max(guide_correlative::int) m from sales_workflow where guide_series is not null group by 1) x")
def guias_de(ref):
    if not ref: return []
    q = (f"select guide_number||' ['||(select string_agg(i.item_code||'/'||l.unit, ',' order by i.item_code) from sales_workflow_line l join inventory_item i on i.id=l.inventory_item_id where l.workflow_id=w.id)||']'"
         f"||case when sale_id is not null then ' factura' else '' end from sales_workflow w where (id='{ref}' or parent_workflow_id='{ref}' or sale_id='{ref}') and guide_number is not null order by guide_number")
    return [x for x in sql(q).split('\n') if x]
def res(s, d):
    data = d.get('data') or {}
    if 'workflows' in data: nums = [(x.get('workflow') or x).get('guide_number') for x in data['workflows']]
    else: nums = [(data.get('workflow') or {}).get('guide_number')] if data.get('workflow') else []
    err = d.get('error') if isinstance(d.get('error'), dict) else {}
    return {'http': s, 'codigo': err.get('code'), 'mensaje': (d.get('message') or msg(d) or '')[:230], 'guias_en_respuesta': nums}
def caso(nombre, fn, ref=None):
    n0, c0 = len(nube()), contadores(); s, d = fn(); nuevas = nube()[n0:]
    envios = [{'guia': c['key'], 'modo': c['mode'], 'partida': c['payload'].get('punto_de_partida_direccion'),
               'items': [(i.get('codigo'), i.get('unidad_de_medida')) for i in c['payload'].get('items', [])]} for c in nuevas]
    out(nombre, **res(s, d), nubecont=envios, contadores_antes=c0, contadores_despues=contadores(), guias_registradas=guias_de(ref))
    return s, d

setmode('ok')
RUTAS = {'IG': 'issue-guide', 'TC': 'direct-guide Traer cotizacion', 'GD': 'guia directa sin cotizacion', 'GF': 'guia desde factura'}
for r, rn in RUTAS.items():
    for nombre, items in (('solo DIGEMID', [(DIG, 'PAR')]), ('mezclada', [(DIG, 'PAR'), (N1, 'NIU')]), ('sin DIGEMID', [(N1, 'NIU'), (N2, 'BX')])):
        fn, ref = ruta(r, items); caso(f'{r} {rn} | {nombre}', fn, ref)
    # pantalla vieja: serie TTT1 con producto DIGEMID y sin direccion de partida DIGEMID
    fn, ref = ruta(r, [(DIG, 'PAR'), (N1, 'NIU')] if r in ('IG', 'TC') else [(DIG, 'PAR')], 'TTT1', partida=None)
    caso(f'{r} {rn} | pantalla vieja: TTT1 con producto DIGEMID, sin partida DIGEMID', fn, ref)
    # TTT4 con producto no DIGEMID
    fn, ref = ruta(r, [(N1, 'NIU')], 'TTT4'); caso(f'{r} {rn} | TTT4 con producto NO DIGEMID', fn, ref)

# Interruptor: guide_ttt4_only_digemid = 0 permite TTT4 con productos no DIGEMID
sql(f"insert into system_parameter (id, company_id, parameter_key, parameter_value, created_at, updated_at, is_active) values (gen_random_uuid()::text, '{CID}', 'guide_ttt4_only_digemid', '0', now(), now(), true)")
fn, ref = ruta('GD', [(N1, 'NIU')], 'TTT4'); caso('GD | TTT4 con producto NO DIGEMID, interruptor desactivado (=0)', fn, ref)
sql(f"delete from system_parameter where company_id='{CID}' and parameter_key='guide_ttt4_only_digemid'")

# Falla de la segunda guia y reintento
for r in ('IG', 'TC'):
    fn, ref = ruta(r, [(DIG, 'PAR'), (N1, 'NIU')]); setmode('failttt4'); caso(f'{r} | mezclada: falla la segunda guia (TTT4)', fn, ref); setmode('ok')
    caso(f'{r} | reintento: solo la parte TTT4 pendiente', fn, ref)
lines_mix = [L(DIG, 'PAR'), L(N1, 'NIU')]
setmode('failnot4'); caso('GD | mezclada: falla la segunda guia (la no DIGEMID)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines_mix))); setmode('ok')
caso('GD | reintento con los productos que quedaron en el formulario (solo P0001)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(N1, 'NIU')])))
sid, fnum = factura([(DIG, 'PAR'), (N1, 'NIU')])
setmode('failnot4'); caso(f'GF | mezclada {fnum}: falla la segunda guia', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines_mix, src_sale=sid)), sid); setmode('ok')
caso(f'GF | reintento {fnum} con lo pendiente (solo P0001)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(N1, 'NIU')], src_sale=sid)), sid)
caso(f'GF | tercer intento {fnum} con todo otra vez (no debe duplicar)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg(lines_mix, src_sale=sid)), sid)

# NubeCont rechaza, 'ya existe', tiempo de espera con guia creada
fn, ref = ruta('IG', [(DIG, 'PAR')]); setmode('fail'); caso('IG solo DIGEMID | NubeCont rechaza', fn, ref); setmode('ok'); caso('IG solo DIGEMID | reintento tras rechazo', fn, ref)
fn, ref = ruta('GD', [(DIG, 'PAR')]); setmode('fail'); caso('GD solo DIGEMID | NubeCont rechaza', fn, ref); setmode('ok')
nxt = int(sql("select coalesce(max(guide_correlative::int),0)+1 from sales_workflow where guide_series='TTT4'") or 1)
open(LOG + '.occupy', 'w').write(f'TTT4-{str(nxt).zfill(6)}\n')
fn, ref = ruta('IG', [(DIG, 'PAR')]); caso(f'IG solo DIGEMID | NubeCont dice ya existe (TTT4-{str(nxt).zfill(6)} ocupado)', fn, ref)
fn, ref = ruta('TC', [(DIG, 'PAR'), (N1, 'NIU')]); setmode('timeout'); caso('TC mezclada | tiempo de espera pero NubeCont SI creo las guias', fn, ref); setmode('ok')

# Dos usuarios a la vez con la misma cotizacion (mezclada)
for r in ('IG', 'TC'):
    fn, ref = ruta(r, [(DIG, 'PAR'), (N1, 'NIU')]); n0 = len(nube()); rs = []
    th = [threading.Thread(target=lambda: rs.append(res(*fn()))) for _ in range(2)]; [t.start() for t in th]; [t.join() for t in th]
    out(f'{r} | dos usuarios a la vez, misma cotizacion mezclada', respuestas=rs, nubecont=[c['key'] for c in nube()[n0:]], guias_registradas=guias_de(ref))

# Guia directa con stock insuficiente
caso('GD | stock insuficiente de P0003 (pide 999)', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(DIG, 'PAR', 999), L(N1, 'NIU')])))

# Factura con dos guias + reporte DIGEMID
sid, fnum = factura([(DIG, 'PAR'), (N2, 'BX')])
caso(f'GF | factura {fnum} mezclada: dos guias vinculadas', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(DIG, 'PAR'), L(N2, 'BX')], src_sale=sid)), sid)
s, d = call('get', '/api/guide-reports/{cid}/sale-guides?from=2026-10-01&to=2026-10-31')
g = (d.get('data') or {}).get('guides', d.get('data') or {}).get(sid, []) if s == 200 else []
out(f'reporte sale-guides: guias de {fnum}', http=s, guias=[x.get('guide_number') for x in g])
s, d = call('get', '/api/guide-reports/{cid}/digemid-guides?from=2026-10-01&to=2026-10-31')
rows = [r for r in ((d.get('data') or {}).get('rows') or []) if r.get('factura') == fnum] if s == 200 else []
out(f'reporte Guias para DIGEMID: filas de {fnum}', http=s, filas=[(r['guia'], r['codigo'], r['factura'], r['estado']) for r in rows])

# TTT5 reservada a traslados
sql(f"insert into system_parameter (id, company_id, parameter_key, parameter_value, created_at, updated_at, is_active) values (gen_random_uuid()::text, '{CID}', 'transfer_guide_series', 'TTT5', now(), now(), true)")
fn, ref = ruta('IG', [(N1, 'NIU')], 'TTT5'); caso('IG | serie TTT5 (reservada a traslados)', fn, ref)
fn, ref = ruta('GD', [(N1, 'NIU')], 'TTT5'); caso('GD | serie TTT5 (reservada a traslados)', fn, ref)
fn, ref = ruta('GD', [(DIG, 'PAR')], 'TTT5'); caso('GD | serie TTT5 con producto DIGEMID', fn, ref)
sql(f"delete from system_parameter where company_id='{CID}' and parameter_key='transfer_guide_series'")
