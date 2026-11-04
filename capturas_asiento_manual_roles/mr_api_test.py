"""Roles del asiento manual y cuenta bancaria sin 104 propia (main y rama).
Uso: python mr_api_test.py <backend_dir> <db> <salida.json>
"""
import os, sys, json
BACKEND, DB, OUT = sys.argv[1:4]
OUT = os.path.abspath(OUT)
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text

FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
ROLES = ['Administrador-FIKA', 'Administrador-FLUMISA', 'AlmacenGuias-FIKA', 'AlmacenGuias-FLUMISA', 'Almacenero-FLUMISA', 'Gerente-FIKA',
         'Gerente-FLUMISA', 'Sistema-FIKA', 'Sistema-FLUMISA', 'TiendaCapon-FIKA', 'TiendaCapon-FLUMISA', 'TiendaMalvinas-FIKA',
         'TiendaMalvinas-FLUMISA', 'Vendedor-FIKA', 'Vendedor-FLUMISA', 'Tesoreria', 'Encargado-FIKA', 'Encargado-FLUMISA',
         'Sistemas', 'Gerente', 'Administrador']
app = create_app(); cl = app.test_client()
R = {'roles': {}}
with app.app_context():
    TOK, ACC = {}, {}
    for name in ROLES:
        u = User.query.filter_by(email=name.lower().replace('-', '.') + '@t.pe').first()
        TOK[name] = (create_access_token(identity=u.id), u.company_id)
    for cid in (FIKA, FLU):
        a = User.query.filter_by(email='admin@t.pe', company_id=cid).first()
        TOK['admin@' + cid] = (create_access_token(identity=a.id), cid)
        for code, aid in db.session.execute(text("select account_code, id from chart_of_account where company_id=:c"), {'c': cid}):
            ACC[(cid, code)] = aid
BANK = {FIKA: 'bk-fika-bcp-mn', FLU: 'bk-flu-bcp-mn'}
def H(k): return {'Authorization': 'Bearer ' + TOK[k][0]}
def call(k, method, url, body=None):
    r = getattr(cl, method)(url, headers=H(k), json=body)
    d = r.get_json(silent=True) or {}
    return r.status_code, d
def code(res): st, d = res; return f"{st} {(d.get('error') or {}).get('code') or ''}".strip()

has_bank_tab = call('admin@' + FIKA, 'get', f'/api/manual-journal/{FIKA}/bank-movement/options')[0] == 200
R['tiene_pestana_bancos'] = has_bank_tab
for cid in (FIKA, FLU):   # la lista de contrapartidas la define el administrador antes de la prueba
    if has_bank_tab:
        call('admin@' + cid, 'put', f'/api/manual-journal/{cid}/bank-movement/counterparts', {'codes': ['103101']})
for n, name in enumerate(ROLES, start=1):
    cid = TOK[name][1]; MJ = f'/api/manual-journal/{cid}'
    row = {'empresa': 'FIKA' if cid == FIKA else 'FLUMISA'}
    st, d = call(name, 'get', MJ + '/options')
    row['pantalla_diario_puede'] = d.get('data', {}).get('can_register'); row['allowed_roles'] = d.get('data', {}).get('allowed_roles')
    row['diario_registrar'] = code(call(name, 'post', MJ, {'entry_date': '2026-10-14', 'gloss': f'Prueba de rol {name}', 'currency': 'PEN',
        'client_request_id': f'rol-{n}', 'lines': [{'chart_account_id': ACC[(cid, '103103')], 'debit': 1}, {'chart_account_id': ACC[(cid, '103105')], 'credit': 1}]}))
    # asiento del administrador para probar la anulacion con cada rol
    st, d = call('admin@' + cid, 'post', MJ, {'entry_date': '2026-10-14', 'gloss': f'Para anular ({name})', 'currency': 'PEN', 'client_request_id': f'adm-{n}',
        'lines': [{'chart_account_id': ACC[(cid, '103103')], 'debit': 2}, {'chart_account_id': ACC[(cid, '103105')], 'credit': 2}]})
    row['diario_anular'] = code(call(name, 'post', MJ + f"/{d['data']['id']}/void", {'reason': 'Prueba de rol'}))
    if has_bank_tab:
        st, d = call(name, 'get', MJ + '/bank-movement/options')
        row['pantalla_bancos_puede'] = d.get('data', {}).get('can_register')
        row['bancos_registrar'] = code(call(name, 'post', MJ + '/bank-movement', {'kind': 'counterpart', 'entry_date': '2026-10-14', 'amount': 1,
            'bank_account_id': BANK[cid], 'direction': 'out', 'operation_number': f'ROL-{n}', 'counterpart_account_id': ACC[(cid, '103101')],
            'gloss': f'Prueba de rol {name}', 'client_request_id': f'bm-rol-{n}'}))
        row['bancos_contrapartidas'] = code(call(name, 'put', MJ + '/bank-movement/counterparts', {'codes': ['103101']}))
    R['roles'][name] = row

# Cuenta bancaria sin 104 propia en el asiento manual del Libro Diario
MJF = f'/api/manual-journal/{FIKA}'
def con_banco(bank_id, op):
    return call('admin@' + FIKA, 'post', MJF, {'entry_date': '2026-10-14', 'gloss': 'Prueba cuenta sin 104 propia', 'currency': 'PEN', 'operation_number': op,
        'lines': [{'chart_account_id': ACC[(FIKA, '103103')], 'debit': 5}, {'chart_account_id': ACC[(FIKA, '104101')], 'credit': 5, 'bank_account_id': bank_id}]})
R['sin_104'] = {}
for bank_id, label in (('bk-fika-comis', 'Cuenta Comisiones'), ('bk-fika-ret', 'Cuenta Retenciones 3%'), ('bk-fika-caja', 'Efectivo / Caja')):
    st, d = con_banco(bank_id, 'S104-' + bank_id)
    R['sin_104'][label] = [st, (d.get('error') or {}).get('code'), (d.get('error') or {}).get('message') or d.get('message')]
R['bcp_sigue_igual'] = code(con_banco('bk-fika-bcp-mn', 'S104-BCP'))
st, d = call('admin@' + FIKA, 'get', MJF + '/options')
R['opciones_bancos_asiento_manual'] = [(b['bank_name'], b['currency'], b['chart_account_id'] and next(k[1] for k, v in ACC.items() if v == b['chart_account_id'])) for b in d['data']['bank_accounts']]
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('listo', OUT)
