"""Prueba: ninguna respuesta (ni el registro del servicio) contiene el token ni la ruta de NubeFact.
Uso: python tk_test.py <backend> <db> <usuario> <salida.json> <log>"""
import os, sys, json, re, logging, warnings
warnings.filterwarnings('ignore')
B, DB, EMAIL, OUT, LOGF = sys.argv[1:6]
TOKEN = 'TKN-PRUEBA-7f3a9c1e5b2d'
RUTA = 'http://127.0.0.1:8931/api/ruta-secreta-0b9e4c'
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, B); os.chdir(B)
logging.basicConfig(filename=LOGF, filemode='w', level=logging.DEBUG, force=True)
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client()
with app.app_context():
    u = User.query.filter_by(email=EMAIL, company_id=FIKA).first()
    h = {'Authorization': 'Bearer ' + create_access_token(identity=u.id)}
ids = {'company_id': FIKA, 'from_company_id': FIKA, 'sale_id': 'af-s120', 'workflow_id': '66e16c23-de73-4f99-9650-17967490bd87',
       'transfer_id': 'ea5dcef0-7905-424b-ba7c-348ba364a34e', 'customer_id': 'af-cust'}
S119 = 'b20e1049-9875-4dce-aacc-a37cf275d4ce'
res = []

def call(method, path, body=None):
    r = cl.open(path, method=method, json=body, headers=h)
    raw = r.get_data()
    txt = raw.decode('utf-8', 'replace')
    j = r.get_json(silent=True) if r.is_json else None
    err = (j or {}).get('error') if isinstance((j or {}).get('error'), dict) else {}
    data = (j or {}).get('data')
    sale = data.get('sale') if isinstance(data, dict) and isinstance(data.get('sale'), dict) else {}
    res.append({'metodo': method, 'ruta': re.sub(r'[0-9a-f]{8}-[0-9a-f-]{27}', '<id>', path), 'http': r.status_code,
                'tiene_token': TOKEN in txt, 'tiene_ruta': RUTA in txt or 'ruta-secreta-0b9e4c' in txt,
                'codigo': err.get('code'), 'mensaje': (j or {}).get('message') or err.get('message'),
                'estado': [sale.get('status'), sale.get('sunat_status'), sale.get('document_number')] if sale else None,
                'bytes': len(raw)})

# --- Rutas que llaman a NubeFact (facturas, guias, traslados, reportes) ---
call('GET', f'/api/companies/{FIKA}')
call('GET', '/api/companies')
call('GET', f'/api/sales/{FIKA}/af-s120/electronic/status')
call('GET', f'/api/sales/{FIKA}/{S119}/electronic/status')
call('POST', f'/api/sales/{FIKA}/{S119}/electronic/send', {})
call('POST', f'/api/sales/{FIKA}/FN/electronic/send', {})
call('GET', f'/api/sales/{FIKA}/af-s120/electronic/download')
call('POST', f'/api/sales/{FIKA}/af-s120/electronic/generate-xml', {})
call('POST', f'/api/sales/{FIKA}/af-s120/electronic/void', {'void_reason': 'prueba'})
call('POST', f'/api/sales/{FIKA}/FU/void', {'void_reason': 'prueba'})
call('POST', f'/api/sales/{FIKA}/{S119}/electronic/void', {'void_reason': 'prueba'})
for wf in ('66e16c23-de73-4f99-9650-17967490bd87', '50b5e62b-5ddb-4778-8cbc-710564f918b0'):
    call('GET', f'/api/sales/{FIKA}/workflow/{wf}/electronic/guide-status')
    call('GET', f'/api/sales/{FIKA}/workflow/{wf}/electronic/guide-debug')
call('POST', f'/api/sales/{FIKA}/workflow/2f3a4c03-95b4-4326-ae2b-cae927d0a395/electronic/send-guide', {})
call('POST', f'/api/sales/{FIKA}/workflow/95deb679-31b1-472e-b275-2825100a4e13/issue-guide', {})
call('POST', f'/api/sales/{FIKA}/workflow/direct-guide', {})
call('POST', f'/api/sales/{FIKA}/workflow/aa16bc1c-ebe2-4a01-98d0-f6193dfdceb5/void-guide', {'reason': 'prueba'})
call('GET', f'/api/inventory/{FIKA}/transfers/ea5dcef0-7905-424b-ba7c-348ba364a34e/guide-document')
call('GET', f'/api/inventory/{FIKA}/transfers/ca55979b-187b-4ddb-806a-6dd57cd684ce/guide-document')
call('POST', f'/api/inventory/{FIKA}/transfers/8921503d-d20d-4106-8222-02b899b3fb63/dispatch', {})
call('POST', f'/api/inventory/{FIKA}/company-transfer', {})
for rule in app.url_map.iter_rules():
    if 'guide-places' in rule.rule:
        call('POST', rule.rule.replace('<company_id>', FIKA), {'guides': [{'workflow_id': '66e16c23-de73-4f99-9650-17967490bd87'}, {'workflow_id': '50b5e62b-5ddb-4778-8cbc-710564f918b0'}, {'transfer_id': 'ea5dcef0-7905-424b-ba7c-348ba364a34e'}]})
n_nube = len(res)
# --- Todas las rutas GET de la aplicacion ---
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if 'GET' not in rule.methods or rule.rule.startswith('/static') or '/dev/' in rule.rule:
        continue
    path = rule.rule
    for arg in rule.arguments:
        if arg not in ids:
            path = None; break
        path = path.replace(f'<{arg}>', ids[arg])
    if path:
        call('GET', path)
logging.shutdown()
log = open(LOGF, encoding='utf-8', errors='replace').read()
json.dump({'usuario': EMAIL, 'rutas_nubefact': res[:n_nube], 'rutas_get': res[n_nube:],
           'respuestas_con_token': [x['metodo'] + ' ' + x['ruta'] for x in res if x['tiene_token']],
           'respuestas_con_ruta': [x['metodo'] + ' ' + x['ruta'] for x in res if x['tiene_ruta']],
           'registro_con_token': log.count(TOKEN), 'registro_con_ruta': log.count('ruta-secreta-0b9e4c'),
           'total_respuestas': len(res)}, open(OUT, 'w'), ensure_ascii=False, indent=1)
