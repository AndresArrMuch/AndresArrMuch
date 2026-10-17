import os, sys, json
B, DB = sys.argv[1:3]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, B); os.chdir(B)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
app = create_app(); cl = app.test_client()
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
with app.app_context():
    tok = create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)
r = cl.get(f'/api/vendedores/{FIKA}/comisiones?from=2026-10-01&to=2026-10-31', headers={'Authorization': 'Bearer ' + tok})
print(json.dumps([x for x in r.get_json()['data'] if x['vendedor_id'] == 'v-prueba'], ensure_ascii=False))
