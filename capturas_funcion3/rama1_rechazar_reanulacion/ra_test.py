import os, sys, json, warnings
warnings.filterwarnings('ignore')
B, DB, LOG = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, B); os.chdir(B)
from app import create_app, db
from app.models import Sale, InventoryMovement
from app.models.user import User
from flask_jwt_extended import create_access_token
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client()
nf = lambda: sum(1 for _ in open(LOG))
with app.app_context():
    h = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)}
    docs = {s.document_number: s.id for s in Sale.query.filter(Sale.document_number.in_(['F030-000119', 'F001-000002'])).all()}
out = {}
for num, sid in sorted(docs.items()):
    for ruta in ('electronic/void', 'void'):
        with app.app_context():
            m0 = InventoryMovement.query.filter_by(reference_id=sid).count()
        n0 = nf()
        r = cl.post(f'/api/sales/{FIKA}/{sid}/{ruta}', json={'void_reason': 'prueba'}, headers=h)
        j = r.get_json() or {}
        with app.app_context():
            s = Sale.query.get(sid); m1 = InventoryMovement.query.filter_by(reference_id=sid).count()
            st = (s.status, s.sunat_status)
        out[f'{num} /{ruta}'] = dict(http=r.status_code, codigo=j.get('error_code') or j.get('code') or (j.get('error') or {}).get('code') if isinstance(j.get('error'), dict) else j.get('error_code'),
                                     mensaje=j.get('message'), llamadas_nubefact=nf() - n0, movimientos_stock_nuevos=m1 - m0, estado=st)
print(json.dumps(out, ensure_ascii=False, indent=1))
