import os, sys, json, warnings
warnings.filterwarnings('ignore')
DB = sys.argv[1]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
B = '/tmp/claude-0/wt_af/backend'; sys.path.insert(0, B); os.chdir(B)
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client()
with app.app_context():
    h = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)}
r = cl.get(f'/api/sales/{FIKA}?per_page=500', headers=h).get_json()['data']
docs = r['data']
cob = [d['document_number'] for d in docs if d['document_number'].startswith('F030') and d.get('status') != 'cancelled']
print('  Cobranza (lista de ventas sin anuladas, mismo filtro de la pantalla):', cob)
st = cl.get(f"/api/customers/{FIKA}/af-cust/statement", headers=h).get_json()['data']
rows = st.get('statement', st) if isinstance(st, dict) else st
print('  Cuentas por cobrar / estado de cuenta PONEDORAS (documento, pendiente):', [(x['document_number'], x.get('pending')) for x in rows], '| total pendiente', st['summary']['total_pending'])
r = cl.post(f'/api/sales/{FIKA}/reports/periodic', json={'period_year': 2026, 'period_month': 10}, headers=h).get_json()
txt = json.dumps(r)
print('  Reporte de ventas del periodo 10/2026: F030-000119 aparece:', 'F030-000119' in txt, '| F030-000120 aparece:', 'F030-000120' in txt)
