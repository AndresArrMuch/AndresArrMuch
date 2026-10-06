# Base de prueba (SQLite) para pagos/cobros con comision. Uso: from base import *  con BACK y DB en el entorno.
import os, sys, datetime
BACK = os.environ['BACK']; DBP = os.environ['DBP']
if DBP.startswith('postgresql'):
    os.environ['DATABASE_URL'] = DBP
else:
    os.environ['DATABASE_URL'] = 'sqlite:///' + DBP
    if os.path.exists(DBP): os.remove(DBP)
sys.path.insert(0, BACK); os.chdir('/tmp/claude-0/repro/com')
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.company import Company, FiscalPeriod
from app.models.chart_of_accounts import ChartOfAccount
from app.models.purchase import Supplier, Purchase
from app.models.sale import Customer, Sale
from app.models.journal_entry import JournalEntry
from app.models.bank import BankAccount, BankTransaction, PaymentRecord
from app.models.exchange import ExchangeRate
from flask_jwt_extended import create_access_token
D = datetime.date
app = create_app()
codes = {}
with app.app_context():
    c = Company(ruc='20000000001', business_name='X', address='x', district_ubigeo='150101', tax_regime='RG', economic_activity_ciiu='0000')
    db.session.add(c); db.session.flush()
    for code, name in [('601101','MERC'),('401111','IGV'),('421201','FACT MN'),('421202','FACT ME'),('104101','BANCO DE CREDITO MN'),('104102','BANCO DE CREDITO ME'),
                       ('639101','COMISIONES BANCARIAS'),('676101','DIF CAMBIO P'),('776101','DIF CAMBIO G'),('121201','FACT X COBRAR MN'),('701101','VENTAS')]:
        a = ChartOfAccount(company_id=c.id, account_code=code, account_name=name, account_level=6, account_type='x', account_category='x', accepts_movement=True)
        if code == '104102': a.currency_type = 'USD'
        db.session.add(a); db.session.flush(); codes[a.id] = code
    if os.environ.get('JAN_FIRST'):
        db.session.add(FiscalPeriod(company_id=c.id, period_year=2026, period_month=1, start_date=D(2026,1,1), end_date=D(2026,1,31), status='open')); db.session.flush()
    db.session.add(FiscalPeriod(company_id=c.id, period_year=2026, period_month=9, start_date=D(2026,9,1), end_date=D(2026,9,30), status='closed'))
    p10 = FiscalPeriod(company_id=c.id, period_year=2026, period_month=10, start_date=D(2026,10,1), end_date=D(2026,10,31), status='open'); db.session.add(p10)
    s1 = Supplier(company_id=c.id, ruc_or_dni='20100000001', business_name='PROV UNO', address='x')
    s2 = Supplier(company_id=c.id, ruc_or_dni='20100000002', business_name='PROV DOS', address='x')
    cu = Customer(company_id=c.id, ruc_or_dni='20200000001', business_name='CLIENTE UNO', address='x')
    bpen = BankAccount(company_id=c.id, bank_name='BCP', account_type='checking', account_number='191-PEN', currency='PEN', account_holder='X', opening_date=D(2026,1,1))
    busd = BankAccount(company_id=c.id, bank_name='BCP ME', account_type='checking', account_number='191-USD', currency='USD', account_holder='X', opening_date=D(2026,1,1))
    bcom = BankAccount(company_id=c.id, bank_name='Cuenta Comisiones', account_type='checking', account_number='COMISIONES', currency='PEN', account_holder='X', opening_date=D(2026,1,1))
    db.session.add_all([s1, s2, cu, bpen, busd, bcom, ExchangeRate(company_id=c.id, rate_date=D(2026,10,1), currency='USD', buy_rate=3.39, sell_rate=3.40)])
    from app.models.user import User, Role
    rol = Role(name='Administrador', company_id=c.id); db.session.add(rol); db.session.flush()
    u = User(email='admin@t.pe', username='admin', password_hash='x', first_name='A', last_name='B', role_id=rol.id, company_id=c.id, is_active=True); db.session.add(u)
    db.session.commit()
    UID = u.id
    CID, P10, S1, S2, CU, BPEN, BUSD, BCOM = c.id, p10.id, s1.id, s2.id, cu.id, bpen.id, busd.id, bcom.id
    TOK = create_access_token(identity=UID, additional_claims={'company_id': CID, 'role_id': 'r'})
cl = app.test_client(); H = {'Authorization': 'Bearer ' + TOK}
if os.environ.get('IDS_OUT'):
    import json as _j; _j.dump(dict(CID=CID, P10=P10, S1=S1, S2=S2, CU=CU, BPEN=BPEN, BUSD=BUSD, BCOM=BCOM, UID=UID), open(os.environ['IDS_OUT'], 'w'))

def compra(sid, corr, total_sin_igv, currency='PEN', rate=1.0):
    r = cl.post(f'/api/purchases/{CID}', headers=H, json=dict(supplier_id=sid, document_type='01', series='F001', correlative=corr, emission_date='2026-10-01', due_date='2026-10-30',
        currency=currency, exchange_rate=rate, amounts_in_document_currency=(currency == 'USD'), lines=[dict(description='Merc', quantity=1, unit='UND', unit_price=total_sin_igv, igv_percentage=18)]))
    assert r.status_code in (200, 201), r.get_json()
    return r.get_json()['data']['id']
def venta(corr, total, currency='PEN'):
    with app.app_context():
        s = Sale(company_id=CID, customer_id=CU, fiscal_period_id=P10, document_type='01', series='F001', correlative=corr, document_number='F001-'+corr, emission_date=D(2026,10,1), due_date=D(2026,10,30), registration_date=D(2026,10,1),
                 currency=currency, exchange_rate=1, subtotal=round(total/1.18, 2), igv=round(total - total/1.18, 2), total=total, status='emitted', amount_paid=0, payment_status='pending')
        db.session.add(s); db.session.commit(); return s.id
def asientos(desde=0):
    out = []
    with app.app_context():
        for e in JournalEntry.query.filter_by(entry_type='payment').order_by(JournalEntry.created_at).all()[desde:]:
            d = sum(float(l.debit_amount) for l in e.lines); h = sum(float(l.credit_amount) for l in e.lines)
            out.append({'asiento': e.entry_number, 'glosa': e.gloss, 'cuadra': abs(d - h) < 0.005, 'lineas': [f"{codes[l.chart_account_id]} D {float(l.debit_amount):.2f} H {float(l.credit_amount):.2f}" + (f" ME {float(l.debit_amount_me or 0) or float(l.credit_amount_me or 0):.2f}" if l.currency_me else '') for l in e.lines]})
    return out
def n_asientos():
    with app.app_context(): return JournalEntry.query.filter_by(entry_type='payment').count()
def banco(acc_id):
    with app.app_context():
        return [(t.transaction_type, float(t.amount), t.description) for t in BankTransaction.query.filter_by(account_id=acc_id).order_by(BankTransaction.created_at).all()]
def doc(model, i):
    with app.app_context():
        x = db.session.get(model, i); return f"pagado={float(x.amount_paid):.2f} estado={x.payment_status}"
