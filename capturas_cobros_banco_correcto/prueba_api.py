"""Escenario F010-000198: deposito en el BCP MN, cobro registrado en el BCP ME. Uso: python prueba.py <backend> <db> <etiqueta> <accion>"""
import os, sys, json
BACKEND, DB, TAG, ACCION = sys.argv[1:5]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app(); cl = app.test_client()
with app.app_context():
    H = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=F).first().id)}
def post(url, body):
    r = cl.post(url, headers=H, json=body); d = r.get_json() or {}
    return r.status_code, (d.get('error') or {}).get('code'), (d.get('error') or {}).get('message') or d.get('message')
if ACCION == 'extracto':
    rows = [{'date': '2026-10-08', 'operation_number': '00005060', 'amount': 540, 'description': 'BCO.BBVA'},
            {'date': '2026-10-08', 'operation_number': '00869132', 'amount': 100, 'description': 'LETRAS'},
            {'date': '2026-10-04', 'operation_number': '05916188', 'amount': 50, 'description': 'Yape'}]
    print(f'[{TAG}] extracto BCP MN:', post(f'/api/banks/{F}/conciliacion-import/bk-fika-bcp-mn', {'filename': 'oct.xlsx', 'rows': rows})[0])
else:
    for banco, sale, monto, op, fecha in json.loads(ACCION):
        print(f'[{TAG}] cobro op {op} {fecha} en {banco}:', post(f'/api/payments/{F}/collect', {'bank_account_id': banco, 'payment_date': fecha,
              'reference_number': op, 'items': [{'sale_id': sale, 'amount': monto}]}))
