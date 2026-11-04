"""Destinatario de transferencias gratuitas: clientes compartidos (main y rama).
Uso: python dest_api_test.py <backend_dir> <db> <salida.json>
"""
import os, sys, json, hashlib
BACKEND, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models import InventoryItem, InventoryWarehouse
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text

FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
app = create_app(); cl = app.test_client()
R = {}
with app.app_context():
    TOK = {}
    for key, email, cid in [('gerencia_fika', 'admin@t.pe', FIKA), ('gerencia_flumisa', 'admin@t.pe', FLU),
                            ('tienda_fika_nilton', 'ventas2@fikaperu.com', FIKA), ('tienda_flumisa_francisco', 'ventas1@fikaperu.com', FLU)]:
        u = User.query.filter_by(email=email, company_id=cid).first()
        TOK[key] = (create_access_token(identity=u.id), cid)
    WH = {(w.company_id, w.code): w.id for w in InventoryWarehouse.query.all()}
    IT = {(i.company_id, i.item_code): i.id for i in InventoryItem.query.all()}

def H(u): return {'Authorization': 'Bearer ' + TOK[u][0]}
def jget(u, url): r = cl.get(url, headers=H(u)); return r.status_code, (r.get_json(silent=True) or {})
def jpost(u, url, body): r = cl.post(url, headers=H(u), json=body); return r.status_code, (r.get_json(silent=True) or {})
def h(b): return hashlib.sha256(b).hexdigest()[:16]

# Ventas y el resto: deben responder igual en main y rama
R['sin_cambios'] = {}
for u in ('gerencia_fika', 'gerencia_flumisa'):
    cid = TOK[u][1]
    for name, url in [('clientes_ventas', f'/api/customers/{cid}?per_page=20000'), ('ventas', f'/api/sales/{cid}?per_page=20000'),
                      ('cotizaciones', f'/api/sales/{cid}/workflow?per_page=20000'), ('items', f'/api/inventory/{cid}/items?per_page=20000'),
                      ('movimientos', f'/api/inventory/{cid}/movements?per_page=20000'), ('transferencias', f'/api/inventory/{cid}/transfers'),
                      ('requerimientos', f'/api/inventory/{cid}/stock-requests')]:
        r = cl.get(url, headers=H(u)); R['sin_cambios'][f'{u}:{name}'] = [r.status_code, h(r.data)]
    R[f'clientes_que_ve_ventas_{u}'] = len(jget(u, f'/api/customers/{cid}?per_page=20000')[1]['data']['data'])

for u in TOK:
    cid = TOK[u][1]
    st, o = jget(u, f'/api/free-transfers/{cid}/options')
    d = o.get('data') or {}
    R[f'opciones_{u}'] = {'status': st, 'clientes_en_lista_fija': len(d['customers']) if 'customers' in d else '(ya no se manda)',
                          'busqueda_desde': d.get('customer_search_min_chars')}
    busq = {}
    for q in ('1045', 'SANDOVAL', 'sandoval santis', 'flumisa eirl', '20557450565', 'San Pablo', 'fl', 'CLIENTE 01', 'zzzz%'):
        st, r = jget(u, f'/api/free-transfers/{cid}/customers?q=' + q)
        rows = r.get('data') or []
        busq[q] = [st, len(rows), [x['document'] + ' - ' + x['name'] for x in rows[:3]]] if st == 200 else [st]
    R[f'busqueda_{u}'] = busq

def crear(u, wh_code, item_code, body):
    cid = TOK[u][1]
    base = {'transfer_date': '2026-10-15', 'reason': 'muestra', 'responsible_name': 'Prueba', 'warehouse_id': WH[(cid, wh_code)],
            'lines': [{'item_id': IT[(cid, item_code)], 'quantity': 1}]}
    st, d = jpost(u, f'/api/free-transfers/{cid}', dict(base, **body))
    if st >= 400:
        return [st, (d.get('error') or {}).get('code'), (d.get('error') or {}).get('message')]
    x = d['data']
    with app.app_context():
        row = db.session.execute(text('select customer_id, recipient_name, recipient_document from free_transfer where id=:i'), {'i': x['id']}).first()
    return [st, x['document_number'], {'customer_id': row[0], 'recipient_name': row[1], 'recipient_document': row[2]}]

R['crear_fika_cliente_sandoval'] = crear('gerencia_fika', 'ALMFIKA', 'P0001', {'customer_id': 'cli-sandoval', 'recipient_name': 'SANDOVAL SANTISTEBAN JOSE DEL CARMEN'})
R['crear_fika_cliente_flumisa_eirl'] = crear('gerencia_fika', 'ALMFIKA', 'P0001', {'customer_id': 'cli-flu-eirl-fika', 'recipient_name': 'FLUMISA EIRL'})
R['crear_fika_texto_libre'] = crear('gerencia_fika', 'ALMFIKA', 'P0001', {'recipient_name': 'cliente generico'})
R['crear_tienda_fika_cliente_sandoval'] = crear('tienda_fika_nilton', 'TDAFIKAMALVINAS', 'P0001', {'customer_id': 'cli-sandoval', 'recipient_name': 'x'})
R['crear_flumisa_cliente_sandoval'] = crear('gerencia_flumisa', 'ALMFLU', 'P0001', {'customer_id': 'cli-sandoval', 'recipient_name': 'x'})
R['crear_flumisa_cliente_propio_de_fika'] = crear('gerencia_flumisa', 'ALMFLU', 'P0001', {'customer_id': 'cli-flu-eirl-fika', 'recipient_name': 'x'})
R['crear_flumisa_texto_libre'] = crear('tienda_flumisa_francisco', 'TDAFLUMALVINAS', 'P0001', {'recipient_name': 'cliente generico'})
with app.app_context():
    R['clientes_en_bd_despues'] = [list(x) for x in db.session.execute(text('select company_id, count(*) from customer group by 1 order by 1'))]
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('listo', OUT)
