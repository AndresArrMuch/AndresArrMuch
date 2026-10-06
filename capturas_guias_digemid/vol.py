import os, sys, json, time, datetime
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.sale import SalesWorkflow, SalesWorkflowLine, Sale
from flask_jwt_extended import create_access_token
ids = json.load(open('/tmp/claude-0/repro/dig/ids.json')); CID = ids['CID']
app = create_app()
with app.app_context():
    g = SalesWorkflow.query.get(ids['G1']); s = Sale.query.get(ids['S1'])
    for k in range(3000):
        w = SalesWorkflow(company_id=CID, customer_id=g.customer_id, sale_id=s.id if k % 2 else None, quotation_number=f'VOL-{k}', quotation_date=g.quotation_date, status='delivered',
                          guide_series='TTT4', guide_correlative=f'{k+100:06d}', guide_number=f'TTT4-{k+100:06d}', dispatch_date=datetime.date(2026, 9, 1 + k % 28))
        db.session.add(w); db.session.flush()
        for it in (ids['I1'], ids['I2'], ids['I1']):
            db.session.add(SalesWorkflowLine(workflow_id=w.id, company_id=CID, inventory_item_id=it, description='X R.S. DM-1 LOTE L9', quantity=1, unit='NIU', unit_price=1))
    db.session.commit()
    tok = create_access_token(identity=ids['UID'])
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}
for url in [f'/api/guide-reports/{CID}/digemid-guides?from=2026-09-01&to=2026-09-30', f'/api/guide-reports/{CID}/sale-guides?from=2026-09-01&to=2026-09-30']:
    t = time.time(); r = cl.get(url, headers=H); d = r.get_json()['data']
    print(url.split('/')[-1][:40], r.status_code, 'filas' if 'rows' in d else 'facturas', d['count'] if 'rows' in d else len(d), f'{time.time()-t:.2f}s', f'{len(r.data)/1e6:.1f} MB')
