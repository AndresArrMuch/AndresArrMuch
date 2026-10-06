# Agrega 120 guias DIGEMID en setiembre a la base de prueba (SOLO PRUEBA)
import os, sys, json, datetime
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.sale import SalesWorkflow, SalesWorkflowLine
ids = json.load(open('/tmp/claude-0/repro/dig/ids.json')); CID = ids['CID']
app = create_app()
with app.app_context():
    g = SalesWorkflow.query.get(ids['G4'])
    for k in range(120):
        w = SalesWorkflow(company_id=CID, customer_id=g.customer_id, quotation_number=f'COT-V{k:03d}', quotation_date=g.quotation_date, status='delivered',
                          guide_series='TTT4', guide_correlative=f'{k + 200:06d}', guide_number=f'TTT4-{k + 200:06d}', dispatch_date=datetime.date(2026, 9, 1 + k % 28), notes='[DIGEMID]')
        db.session.add(w); db.session.flush()
        db.session.add(SalesWorkflowLine(workflow_id=w.id, company_id=CID, inventory_item_id=ids['I2'], description='MASCARILLA KN95', quantity=1, unit='NIU', unit_price=1))
    db.session.commit()
print('ok')
