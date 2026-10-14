"""Dos envios al mismo tiempo contra el servidor real (doble clic y dos usuarios por el mismo stock)."""
import sys, json, threading, urllib.request
PORT = sys.argv[1]; FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; BASE = f'http://127.0.0.1:{PORT}'
def call(method, path, body=None, tok=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + tok} if tok else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
st, d = call('POST', '/api/auth/login', {'email': 'admin@t.pe', 'password': 'p', 'company_id': FIKA})
tok = d['data']['tokens']['access_token']
o = call('GET', f'/api/free-transfers/{FIKA}/options', tok=tok)[1]['data']
wh = next(w['id'] for w in o['warehouses'] if w['code'] == 'ALMFIKA')
items = call('GET', f'/api/inventory/{FIKA}/items?per_page=20000', tok=tok)[1]['data']['data']
p3 = next(i['id'] for i in items if i['item_code'] == 'P0003')
stock = call('GET', f'/api/free-transfers/{FIKA}/stock?warehouse_id={wh}', tok=tok)[1]['data']
print('stock P0003 en ALMFIKA:', stock.get(p3))
def body(rid, qty): return {'client_request_id': rid, 'transfer_date': o['today'], 'warehouse_id': wh, 'reason': 'muestra',
                            'recipient_name': 'cliente generico', 'responsible_name': 'Prueba', 'lines': [{'item_id': p3, 'quantity': qty}]}
def paralelo(bodies):
    res = [None] * len(bodies)
    def run(i): res[i] = call('POST', f'/api/free-transfers/{FIKA}', bodies[i], tok)
    ts = [threading.Thread(target=run, args=(i,)) for i in range(len(bodies))]
    [t.start() for t in ts]; [t.join() for t in ts]
    return [(s, d.get('data', {}).get('document_number'), d.get('data', {}).get('idempotent'), (d.get('error') or {}).get('code')) for s, d in res]
print('doble clic simultaneo (mismo envio, 2 cant.):', paralelo([body('dbl-1', 2), body('dbl-1', 2)]))
print('stock P0003 tras doble clic:', call('GET', f'/api/free-transfers/{FIKA}/stock?warehouse_id={wh}', tok=tok)[1]['data'].get(p3))
print('dos envios distintos de 4 c/u con stock 6:', paralelo([body('a-1', 4), body('b-1', 4)]))
print('stock P0003 final (nunca negativo):', call('GET', f'/api/free-transfers/{FIKA}/stock?warehouse_id={wh}', tok=tok)[1]['data'].get(p3))
