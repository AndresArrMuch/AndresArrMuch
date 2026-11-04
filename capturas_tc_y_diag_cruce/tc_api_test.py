"""Limite de antiguedad del tipo de cambio (main y rama). Uso: python tc_api_test.py <backend> <db> <salida.json>"""
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
app = create_app(); cl = app.test_client()
with app.app_context():
    TOK = create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=FIKA).first().id)
    ACC = {c: i for c, i in db.session.execute(text("select account_code, id from chart_of_account where company_id=:c"), {'c': FIKA})}
H = {'Authorization': 'Bearer ' + TOK}
def get(u): r = cl.get(u, headers=H); return r.status_code, r.get_json(silent=True) or {}
def post(u, b): r = cl.post(u, headers=H, json=b); return r.status_code, r.get_json(silent=True) or {}
MJ = f'/api/manual-journal/{FIKA}'
with app.app_context():
    R = {'tc_registrados': [list(map(str, x)) for x in db.session.execute(text("select rate_date, sell_rate from exchange_rate where company_id=:c order by 1"), {'c': FIKA})]}
R['rate'] = {}
for label, d in [('sabado 17/10', '2026-10-17'), ('domingo 18/10', '2026-10-18'), ('feriado jueves 08/10', '2026-10-08'), ('martes 13/10', '2026-10-13'),
                 ('7 dias exactos 22/10', '2026-10-22'), ('8 dias 23/10', '2026-10-23'), ('sin ningun TC 20/06', '2026-06-20')]:
    st, d2 = get(MJ + '/rate?date=' + d)
    R['rate'][label] = [st, (d2.get('data') or {}).get('date'), (d2.get('data') or {}).get('age_days'), (d2.get('error') or {}).get('message')]
def bancos(fecha, bank, direction, op):
    st, d = post(MJ + '/bank-movement', {'kind': 'counterpart', 'entry_date': fecha, 'amount': 100, 'bank_account_id': bank, 'direction': direction,
        'operation_number': op, 'counterpart_account_id': ACC['103101'], 'gloss': 'Prueba TC ' + fecha, 'client_request_id': 'tc-' + op})
    m = d.get('data') or {}
    return [st, (d.get('error') or {}).get('message'), m.get('exchange_rate'), m.get('rate_date'), [(l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me']) for l in m.get('lines', [])]]
def diario(fecha, currency, op):
    st, d = post(MJ, {'entry_date': fecha, 'gloss': 'Diario TC ' + fecha, 'currency': currency, 'client_request_id': 'dj-' + op,
        'lines': [{'chart_account_id': ACC['103103'], 'debit': 10}, {'chart_account_id': ACC['103105'], 'credit': 10}]})
    m = d.get('data') or {}
    return [st, (d.get('error') or {}).get('message'), m.get('exchange_rate'), m.get('rate_date')]
R['bancos'] = {
    'dolares sabado 17/10': bancos('2026-10-17', 'bk-fika-bcp-me', 'in', 'T-SAB'),
    'dolares domingo 18/10': bancos('2026-10-18', 'bk-fika-bcp-me', 'in', 'T-DOM'),
    'dolares feriado 08/10': bancos('2026-10-08', 'bk-fika-bcp-me', 'in', 'T-FER'),
    'dolares 7 dias 22/10': bancos('2026-10-22', 'bk-fika-bcp-me', 'in', 'T-7D'),
    'dolares 8 dias 23/10': bancos('2026-10-23', 'bk-fika-bcp-me', 'in', 'T-8D'),
    'soles 8 dias 23/10': bancos('2026-10-23', 'bk-fika-bcp-mn', 'out', 'T-8S'),
    'soles sin ningun TC 20/06': bancos('2026-06-20', 'bk-fika-bcp-mn', 'out', 'T-SIN'),
}
R['diario'] = {'dolares 8 dias 23/10': diario('2026-10-23', 'USD', 'D8'), 'dolares 7 dias 22/10': diario('2026-10-22', 'USD', 'D7'),
               'soles 8 dias 23/10': diario('2026-10-23', 'PEN', 'S8')}
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str); print('listo', OUT)
