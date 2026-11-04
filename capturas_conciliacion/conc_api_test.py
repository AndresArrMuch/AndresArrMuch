"""Conciliacion: guardado de extracto con cuenta de otra empresa y estado por mes (main y rama)."""
import os, sys, json
BACKEND, DB = sys.argv[1:3]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text
from app import db
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
app = create_app(); cl = app.test_client()
with app.app_context():
    tok = create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)
    H = {'Authorization': 'Bearer ' + tok}
    rows = [{'date': '2026-11-03', 'description': 'X', 'operation_number': 'N1', 'amount': 10, 'type': 'in'}]
    r = cl.post(f'/api/banks/{FIKA}/conciliacion-import/bank-flu', headers=H, json={'filename': 'x.xlsx', 'rows': rows})
    print('POST cuenta FLUMISA bajo FIKA:', r.status_code, (r.get_json() or {}).get('error'))
    r = cl.post(f'/api/banks/{FIKA}/conciliacion-import/bank-pen', headers=H, json={'filename': 'vacio.xlsx', 'rows': []})
    print('POST sin filas:', r.status_code, (r.get_json() or {}).get('error'))
    r = cl.get(f'/api/banks/{FIKA}/conciliacion-import-status?periodo=2026-10', headers=H)
    print('GET estado octubre:', r.status_code, json.dumps((r.get_json() or {}).get('data'), ensure_ascii=False)[:600])
    print('BD importes:', [tuple(x) for x in db.session.execute(text("select company_id=:f, bank_account_id, periodo, filename, json_array_length(rows_json::json) from conciliacion_excel_import order by periodo, bank_account_id"), {'f': FIKA})])
