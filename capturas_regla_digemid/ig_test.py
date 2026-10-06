import sys, json, os, time, threading, subprocess, urllib.request
sys.path.insert(0, '/tmp/claude-0/repro/unidad'); from u import CID, ALM, CLI, IT, GUIA, msg
PORT, DB, LOG, TAG = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
CAP = 'd695c2f9-a9ad-4f71-96a7-5a184697a3e1'; P4 = '51f9f5d2-7e80-4263-9155-47883af75bcd'
B = f'http://127.0.0.1:{PORT}'; TOK = {}
def tok():
    if 'a' not in TOK:
        r = urllib.request.Request(B + '/api/auth/login', data=json.dumps({'email': 'admin@t.pe', 'password': 'p', 'company_id': CID}).encode(), headers={'Content-Type': 'application/json'})
        TOK['a'] = json.loads(urllib.request.urlopen(r).read())['data']['tokens']['access_token']
    return TOK['a']
def call(m, url, body=None, auth=True):
    h = {'Content-Type': 'application/json'}
    if auth: h['Authorization'] = 'Bearer ' + tok()
    r = urllib.request.Request(B + url.replace('{cid}', CID), method=m.upper(), data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        resp = urllib.request.urlopen(r, timeout=120); return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except Exception: return e.code, {}
def sql(q):
    return subprocess.run(['psql', '-h', '/var/run/postgresql', '-p', '5433', '-U', 'postgres', DB, '-Atc', q], capture_output=True, text=True).stdout.strip()
def setmode(m): open(LOG + '.mode', 'w').write(m)
def nube_calls():
    try: return [json.loads(l) for l in open(LOG)]
    except Exception: return []
def cot(lines):
    s, d = call('post', '/api/sales/{cid}/workflow/quotations', {'customer_id': CLI, 'quotation_date': '2026-10-06', 'lines': lines})
    w = d['data']['id']; call('post', f'/api/sales/{{cid}}/workflow/{w}/accept'); return w
def L(item, unit, qty=1, wh=ALM): return {'inventory_item_id': item, 'description': 'x', 'quantity': qty, 'unit': unit, 'unit_price': 50, 'warehouse_id': wh}
GD = dict(GUIA['guide_data'], punto_de_partida_direccion='AV PRUEBA 123', punto_de_llegada_direccion='JR CLIENTE 456', serie='TTT1', dispatch_date='2026-10-06')
def body(series='TTT1'):  # igual que wfIssueGuide() del frontend
    return {'dispatch_date': '2026-10-06', 'series': series, 'send_electronic': True, 'nubecont_environment': 'test', 'guide_data': GD, 'digemid_departure_address': 'ALMACEN DIGEMID 1'}
def issue(w, series='TTT1'):
    return call('post', f'/api/sales/{{cid}}/workflow/{w}/issue-guide', body(series))
def estado(w):
    return sql(f"select quotation_number||' status='||status||' guia='||coalesce(guide_number,'-')||' fecha='||coalesce(dispatch_date::text,'-') from sales_workflow where id='{w}' or parent_workflow_id='{w}' order by quotation_number")
def unidades(w):
    return sql(f"select string_agg(l.unit,',' order by l.description) from sales_workflow_line l join sales_workflow s on s.id=l.workflow_id where s.id='{w}' or s.parent_workflow_id='{w}'")
def movs(): return sql("select count(*)||' movs, saldo total '||coalesce(sum(case when movement_type='out' then -quantity else quantity end),0) from inventory_movement")
def res(s, d):
    data = d.get('data') or {}
    nums = [x.get('workflow', x).get('guide_number') for x in data.get('workflows', [])] if 'workflows' in data else [(data.get('workflow') or {}).get('guide_number')]
    es = data.get('electronic_send') or {}
    return {'http': s, 'mensaje': (d.get('message') or msg(d) or '')[:110], 'codigo': (d.get('error') or {}).get('code') if isinstance(d.get('error'), dict) else d.get('error_code') or d.get('code'), 'guias': nums, 'idempotente': es.get('idempotent'), 'recuperada': es.get('recovered_after_error')}
def out(caso, **kw): print(json.dumps(dict({'srv': TAG, 'caso': caso}, **kw), ensure_ascii=False, default=str))
def paso(caso, w, fn):
    n0 = len(nube_calls()); m0 = movs(); s, d = fn()
    nuevas = nube_calls()[n0:]
    out(caso, **res(s, d), nubecont=[(c['key'], c['mode']) for c in nuevas], estado=estado(w).split('\n'), unidades_lineas=unidades(w),
        unidades_enviadas=[[i.get('unidad_de_medida') for i in c['payload'].get('items', [])] for c in nuevas], stock_igual=(movs() == m0))
    return s, d
setmode('ok')
q1 = cot([L(IT['NIU'], 'BX', 2), L(IT['BX'], 'BX', 1)]); paso('1 normal (P0001 elegido CAJA + P0002 CAJA)', q1, lambda: issue(q1))
q2 = cot([L(IT['PAR'], 'PAR', 1), L(IT['NIU'], 'NIU', 1)]); paso('2 DIGEMID (P0003 DIGEMID + P0001)', q2, lambda: issue(q2))
q3 = cot([L(IT['BX'], 'BX', 1), L(P4, 'PAR', 1, CAP)]); paso('3 producto en caja y en par', q3, lambda: issue(q3))
paso('4 segundo intento sobre la cotizacion 1', q1, lambda: issue(q1))
q4 = cot([L(IT['NIU'], 'NIU', 1)]); setmode('fail'); paso('5a NubeCont rechaza', q4, lambda: issue(q4)); setmode('ok')
paso('5b reintento tras rechazo', q4, lambda: issue(q4))
nxt = int(sql("select coalesce(max(guide_correlative::int),0)+1 from sales_workflow where guide_series='TTT1'"))
open(LOG + '.occupy', 'w').write(f'TTT1-{str(nxt).zfill(6)}\n')
q5 = cot([L(IT['NIU'], 'NIU', 1)]); paso(f'6 NubeCont dice ya existe (TTT1-{str(nxt).zfill(6)} ocupado por otro documento)', q5, lambda: issue(q5))
q6 = cot([L(IT['NIU'], 'NIU', 1)]); setmode('timeout'); paso('7 tiempo de espera pero NubeCont SI la creo', q6, lambda: issue(q6)); setmode('ok')
q11 = cot([L(IT['PAR'], 'PAR', 1), L(IT['NIU'], 'BX', 1)]); setmode('failttt4'); paso('8a DIGEMID: falla solo la parte TTT4', q11, lambda: issue(q11)); setmode('ok')
paso('8b reintento: solo emite la parte TTT4 pendiente', q11, lambda: issue(q11))
# dos usuarios a la vez
q7 = cot([L(IT['NIU'], 'NIU', 1)]); n0 = len(nube_calls()); rs = []
th = [threading.Thread(target=lambda: rs.append(res(*issue(q7)))) for _ in range(2)]; [t.start() for t in th]; [t.join() for t in th]
out('9a dos usuarios emiten la MISMA cotizacion a la vez', respuestas=rs, nubecont=[c['key'] for c in nube_calls()[n0:]], estado=estado(q7))
qa, qb = cot([L(IT['NIU'], 'NIU', 1)]), cot([L(IT['NIU'], 'NIU', 1)]); n0 = len(nube_calls()); rs = []
th = [threading.Thread(target=lambda w=w: rs.append(res(*issue(w)))) for w in (qa, qb)]; [t.start() for t in th]; [t.join() for t in th]
out('9b dos usuarios, cotizaciones distintas a la vez', respuestas=rs, nubecont=[c['key'] for c in nube_calls()[n0:]])
# serie reservada a traslados
sql(f"insert into system_parameter (id, company_id, parameter_key, parameter_value, created_at, updated_at, is_active) values (gen_random_uuid()::text, '{CID}', 'transfer_guide_series', 'TTT5', now(), now(), true)")
q10 = cot([L(IT['NIU'], 'NIU', 1)])
paso('10a issue-guide con serie TTT5 (reservada a traslados)', q10, lambda: issue(q10, 'TTT5'))
paso('10b direct-guide con serie TTT5', q10, lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', dict(GUIA, series='TTT5', customer_id=CLI, dispatch_date='2026-10-06', lines=[L(IT['NIU'], 'NIU', 1)])))
paso('10c issue-guide con TTT1 teniendo TTT5 reservada', q10, lambda: issue(q10, 'TTT1'))
sql(f"delete from system_parameter where company_id='{CID}' and parameter_key='transfer_guide_series'")
# serie invalida, sin sesion, mantenimiento
q12 = cot([L(IT['NIU'], 'NIU', 1)])
paso('11a serie invalida X001', q12, lambda: issue(q12, 'X001'))
paso('11b sin sesion (sin token)', q12, lambda: call('post', f'/api/sales/{{cid}}/workflow/{q12}/issue-guide', body(), auth=False))
os.makedirs('/home/ubuntu/cea-erp/backend', exist_ok=True); open('/home/ubuntu/cea-erp/backend/MAINTENANCE_MODE', 'w').close()
try: paso('11c modo mantenimiento', q12, lambda: issue(q12))
finally: os.remove('/home/ubuntu/cea-erp/backend/MAINTENANCE_MODE')
