"""Cobros de varias facturas: editar desde una y quitar facturas. Uso: api_test.py <backend> <db> <salida.json>"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
B, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
os.environ['CEA_REINTENTO_AUTOMATICO'] = '0'
sys.path.insert(0, B); os.chdir(B)
from app import create_app, db
from app.models import Sale, BankAccount, BankTransaction, JournalEntry, JournalEntryLine
from app.models.bank import PaymentRecord
from app.models.user import User
from flask_jwt_extended import create_access_token
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client(); R = {}
DOCS = ('F001-000003', 'F001-000005', 'B001-000001')
with app.app_context():
    h = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='tesoreria@t.pe', company_id=F).first().id)}
    acc = BankAccount.query.filter_by(company_id=F, account_number='191-1111111-0-11').first().id
    sid = {d: Sale.query.filter_by(company_id=F, document_number=d).first().id for d in DOCS}
def J(r):
    j = r.get_json(silent=True) or {}; e = j.get('error') if isinstance(j.get('error'), dict) else {}
    return f"{r.status_code} {e.get('code') or ''} {(e.get('message') or j.get('message') or '')[:140]}".strip()
def estado(pid):
    with app.app_context():
        db.session.expire_all()
        p = PaymentRecord.query.get(pid)
        tx = BankTransaction.query.filter_by(related_document_type='payment', related_document_id=pid).all()
        je = JournalEntry.query.filter(JournalEntry.company_id == F, JournalEntry.gloss.ilike('%888001%')).all()
        return {'cobro_estado': p.status, 'cobro_total': float(p.total_amount or 0),
                'facturas_del_cobro': sorted((l.document_number, float(l.amount_applied)) for l in p.lines),
                'cobrado_por_factura': {d: float(Sale.query.get(sid[d]).amount_paid or 0) for d in DOCS},
                'banco': [float(t.amount) for t in tx],
                'asiento_debe': [round(sum(float(l.debit_amount or 0) for l in e.lines), 2) for e in je if e.is_active]}
r = cl.post(f'/api/payments/{F}/collect', json=dict(bank_account_id=acc, payment_date='2026-10-16', payment_method='transfer', reference_number='888001',
            notes='Cobro varias', items=[dict(sale_id=sid[d], amount=a) for d, a in (('F001-000003', 354), ('F001-000005', 472), ('B001-000001', 118))]), headers=h)
pid = r.get_json()['data']['payment_id']
R['0_cobro_3_facturas'] = estado(pid)
R['1_editar_desde_F001-000003_a_300'] = J(cl.put(f'/api/payments/{F}/{pid}', json=dict(items=[dict(document_type='sale', document_id=sid['F001-000003'], amount_applied=300)]), headers=h))
R['1b_estado'] = estado(pid)
R['2_quitar_F001-000005'] = J(cl.post(f'/api/payments/{F}/{pid}/remove-document', json=dict(document_id=sid['F001-000005']), headers=h))
R['2b_estado'] = estado(pid)
R['3_quitar_B001-000001'] = J(cl.post(f'/api/payments/{F}/{pid}/remove-document', json=dict(document_id=sid['B001-000001']), headers=h))
R['3b_estado'] = estado(pid)
R['4_quitar_la_ultima_F001-000003'] = J(cl.post(f'/api/payments/{F}/{pid}/remove-document', json=dict(document_id=sid['F001-000003']), headers=h))
R['4b_estado'] = estado(pid)
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str); print('ok')
