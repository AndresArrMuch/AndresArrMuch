"""Compra/venta de dolares entre cuentas propias. Uso: python api.py <backend> <db> <out.json>"""
import os, sys, json
BACKEND, DB, OUT = sys.argv[1:4]; OUT = os.path.abspath(OUT)
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app(); cl = app.test_client(); R = {}
with app.app_context():
    tok = create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)
    CODE = {aid: c for c, aid in db.session.execute(text("select account_code, id from chart_of_account where company_id=:c"), {'c': FIKA})}
    db.session.execute(text("insert into exchange_rate (id, company_id, currency, rate_date, buy_rate, sell_rate, created_at, updated_at, is_active) select gen_random_uuid()::text, :c, 'USD', '2026-10-12', 3.4400, 3.4480, now(), now(), true where not exists (select 1 from exchange_rate where company_id=:c and rate_date='2026-10-12')"), {'c': FIKA}); db.session.commit()
H = {'Authorization': 'Bearer ' + tok}
URL = f'/api/manual-journal/{FIKA}/bank-movement'
def post(body):
    r = cl.post(URL, headers=H, json=body); d = r.get_json(silent=True) or {}
    return r.status_code, d
def lines(d): return [(CODE.get(l['chart_account_id']), l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me'], l['reference_document']) for l in d['data'].get('lines', [])]
def sql(q, **p):
    with app.app_context():
        return [list(x) for x in db.session.execute(text(q), p)]
R['opciones_fx'] = cl.get(URL + '/options', headers=H).get_json()['data']['fx_accounts']
base = dict(kind='own_transfer', entry_date='2026-10-12', gloss='Compra de dolares Dollar House')
st, d = post(dict(base, client_request_id='c1', amount=70000, in_amount=20319.30, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='01054514', in_operation_number='08078079'))
R['compra'] = [st, d.get('message'), lines(d) if st == 201 else d]
R['compra_bancos'] = sql("select a.currency, t.transaction_type, t.amount::text, t.reference_number from bank_transaction t join bank_account a on a.id=t.account_id where t.reference_number in ('01054514','08078079') order by 1")
st, d = post(dict(base, client_request_id='c1', amount=70000, in_amount=20319.30, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='01054514', in_operation_number='08078079'))
R['mismo_envio'] = [st, d.get('message')]
st, d = post(dict(base, client_request_id='c2', amount=70000, in_amount=20319.30, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='01054514', in_operation_number='08078079'))
R['repetido'] = [st, (d.get('error') or {}).get('message')]
st, d = post(dict(base, client_request_id='v1', amount=1000, in_amount=3460, from_bank_account_id='bk-fika-bcp-me', to_bank_account_id='bk-fika-ibk-mn', out_operation_number='V-OUT', in_operation_number='V-IN', gloss='Venta de dolares'))
R['venta'] = [st, d.get('message'), lines(d) if st == 201 else d]
st, d = post(dict(base, client_request_id='x1', amount=70000, in_amount=2031.93, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='X1', in_operation_number='X2'))
R['monto_equivocado'] = [st, (d.get('error') or {}).get('message')]
st, d = post(dict(base, client_request_id='x2', amount=70000, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='X3', in_operation_number='X4'))
R['sin_monto_entrada'] = [st, (d.get('error') or {}).get('message')]
st, d = post(dict(base, client_request_id='x3', entry_date='2026-09-20', amount=700, in_amount=203, from_bank_account_id='bk-fika-bcp-mn', to_bank_account_id='bk-fika-bcp-me', out_operation_number='X5', in_operation_number='X6'))
R['sin_tc'] = [st, (d.get('error') or {}).get('message')]
# Asiento manual publico no acepta montos fijos en dolares (se recalculan)
R['cuadre_diario'] = sql("select e.entry_number, sum(l.debit_amount)-sum(l.credit_amount), sum(l.debit_amount_me)-sum(l.credit_amount_me) from journal_entry e join journal_entry_line l on l.entry_id=e.id where e.company_id=:c and e.gloss like '%dolares%' group by 1", c=FIKA)
json.dump(R, open(OUT, 'w'), indent=1, default=str, ensure_ascii=False)
