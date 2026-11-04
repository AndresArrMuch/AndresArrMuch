"""NC no suman como ingreso. Uso: api_test.py <backend> <db> <salida.json>"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
B, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
os.environ['CEA_REINTENTO_AUTOMATICO'] = '0'
sys.path.insert(0, B); os.chdir(B)
from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client(); R = {}
with app.app_context():
    h = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='gerente.fika@t.pe', company_id=F).first().id)}
def j(r): return (r.get_json(silent=True) or {}).get('data') or {}
d = j(cl.post(f'/api/tax/{F}/declarations/generate', json=dict(declaration_type='621', period_year=2026, period_month=10), headers=h))
R['621_igv_ventas'] = (d.get('summary') or {}).get('ventas', {}).get('igv') if isinstance(d.get('summary'), dict) else d.get('sales_igv')
R['621_resumen'] = {k: d.get(k) for k in ('sales_base', 'sales_igv', 'purchases_igv', 'igv_to_pay')}
r = j(cl.post(f'/api/tax/{F}/registers/generate', json=dict(register_type='sales_register', period_year=2026, period_month=10), headers=h))
R['registro_ventas'] = {k: r.get(k) for k in ('total_base', 'total_igv', 'total_amount', 'base_amount', 'igv_amount')}
db_ = j(cl.get(f'/api/dashboard/{F}', headers=h))
R['dashboard_ventas'] = db_.get('sales_total') or (db_.get('kpis') or {}).get('sales_total')
t = j(cl.post(f'/api/sales/{F}/reports/periodic/trend', json=dict(period_year=2026, period_month=10, months_back=2), headers=h))
R['tendencia'] = [(x.get('period_label') or x.get('period'), x.get('total')) for x in (t.get('series') or [])][-2:]
c = j(cl.get(f'/api/customers/{F}/analysis/receivables', headers=h))
R['clientes_resumen'] = c.get('summary')
R['clientes'] = [(x['business_name'], x['total_billed'], x['total_pending'], x['pending_documents']) for x in (c.get('by_customer') or []) if x['documents']]
cm = j(cl.get(f'/api/vendedores/{F}/comisiones?date_from=2026-10-01&date_to=2026-10-31', headers=h))
R['comisiones'] = [(x.get('codigo') or x.get('vendedor_codigo'), x.get('total_vendido'), x.get('comision')) for x in (cm if isinstance(cm, list) else cm.get('rows') or cm.get('vendedores') or [])]
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str); print('ok')
