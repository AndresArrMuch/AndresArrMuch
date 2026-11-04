import os, sys, json
os.environ['DATABASE_URL'] = 'postgresql://postgres@/ventas_test?host=/var/run/postgresql&port=5433'
B = '/tmp/claude-0/wt_main/backend'; sys.path.insert(0, B); os.chdir(B)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
app = create_app()
with app.app_context():
    u = User.query.filter_by(email='admin@t.pe').first(); tok = create_access_token(identity=u.id)
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}
d = cl.post('/api/sales/976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433/reports/periodic', headers=H, json={'period_year': 2026, 'period_month': 10}).get_json()['data']
t = d['analysis']['totals']
print('Reporte por periodo (servidor real): documentos', t['documents'], '| subtotal', round(t['subtotal'], 2), '| IGV', round(t['igv'], 2), '| total', round(t['total'], 2), '| ticket promedio', d['analysis']['avg_ticket'], '| lineas SUNAT', len(d['sunat_ready_lines']))
print('por tipo:', {k: (v['count'], round(v['total'], 2)) for k, v in d['analysis']['by_document_type'].items()})
