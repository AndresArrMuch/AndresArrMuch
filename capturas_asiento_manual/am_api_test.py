"""Asiento manual por diario: pruebas de servidor (main y rama).
Uso: python am_api_test.py <backend_dir> <db> <salida.json>
"""
import os, sys, json, hashlib
BACKEND, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text

FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
app = create_app(); cl = app.test_client()
R = {}
with app.app_context():
    TOK = {}
    for key, email, cid in [('admin_fika', 'admin@t.pe', FIKA), ('admin_flu', 'admin@t.pe', FLU), ('ventas_fika', 'ventas@t.pe', FIKA)]:
        TOK[key] = (create_access_token(identity=User.query.filter_by(email=email, company_id=cid).first().id), cid)
    ACC = {}
    for cid in (FIKA, FLU):
        for code, aid in db.session.execute(text("select account_code, id from chart_of_account where company_id=:c"), {'c': cid}):
            ACC[(cid, code)] = aid
    HAS = 'manual_journal' in app.blueprints

def H(u): return {'Authorization': 'Bearer ' + TOK[u][0]}
def get(u, url): r = cl.get(url, headers=H(u)); return r.status_code, (r.get_json(silent=True) or {}), r
def post(u, url, body): r = cl.post(url, headers=H(u), json=body); return r.status_code, (r.get_json(silent=True) or {})
def h(b): return hashlib.sha256(b).hexdigest()[:16]
def sql(q, **p):
    with app.app_context():
        res = db.session.execute(text(q), p)
        rows = [list(x) for x in res] if res.returns_rows else []
        db.session.commit()
        return rows

def snapshot():
    out = {}
    for u in ('admin_fika', 'admin_flu'):
        cid = TOK[u][1]
        for name, url in [('diario', f'/api/journal-entries/{cid}?per_page=20000'), ('movimientos_banco', f'/api/banks/{cid}/transactions?per_page=20000'),
                          ('cuentas_banco', f'/api/banks/{cid}/accounts?per_page=20000'), ('pagos_historial', f'/api/payments/{cid}/history'),
                          ('dashboard', f'/api/dashboard/{cid}'), ('periodos', f'/api/companies/{cid}/fiscal-periods'),
                          ('extracto_oct', f'/api/banks/{cid}/conciliacion-import/{"bk-fika-bcp-mn" if cid == FIKA else "bk-flu-bcp-mn"}?periodo=2026-10'),
                          ('marcas_pagar', f'/api/banks/{cid}/conciliacion-pago/{"bk-fika-bcp-mn" if cid == FIKA else "bk-flu-bcp-mn"}')]:
            st, _, r = get(u, url); out[f'{u}:{name}'] = [st, h(r.data)]
    return out

R['tiene_asiento_manual'] = HAS
R['antes'] = snapshot()
if HAS:
    B = lambda u: f'/api/manual-journal/{TOK[u][1]}'
    st, o, _ = get('admin_fika', B('admin_fika') + '/options'); d = o['data']
    R['opciones_fika'] = {'puede': d['can_register'], 'roles': d['allowed_roles'],
                          'bancos': [(b['bank_name'], b['currency'], next((k[1] for k, v in ACC.items() if v == b['chart_account_id']), None)) for b in d['bank_accounts']],
                          'periodos_cerrados': [f"{p['month']:02d}/{p['year']}" for p in d['periods'] if p['status'] != 'open'],
                          'puente': [(x['account_code'], x['balance']) for x in d['bridge_balances']]}
    st, o, _ = get('ventas_fika', B('ventas_fika') + '/options'); R['opciones_ventas_puede'] = o['data']['can_register']
    R['tc_14_10'] = get('admin_fika', B('admin_fika') + '/rate?date=2026-10-14')[1].get('data')
    st, o, _ = get('admin_fika', B('admin_fika') + '/rate?date=2026-10-13'); R['tc_13_10'] = [st, (o.get('error') or {}).get('message')]

    def ln(cid, code, d=0, c=0, bank=None, desc=None):
        return {'chart_account_id': ACC[(cid, code)], 'debit': d, 'credit': c, 'bank_account_id': bank, 'description': desc}
    def crear(u, fecha, glosa, lines, op=None, cur='PEN', ref=None, rid=None):
        return post(u, B(u), {'entry_date': fecha, 'gloss': glosa, 'currency': cur, 'operation_number': op, 'reference': ref, 'lines': lines, 'client_request_id': rid})
    def err(res): st, d = res; return [st, (d.get('error') or {}).get('code'), (d.get('error') or {}).get('message')]

    # Ingreso original en julio (cerrado) -> bloqueado con mensaje; periodo inexistente -> bloqueado
    R['original_en_julio_cerrado'] = err(crear('admin_fika', '2026-07-01', 'Ingreso de dinero de FLUMISA', [ln(FIKA, '104101', d=3000, bank='bk-fika-bcp-mn'), ln(FIKA, '103101', c=3000)], op='ORIG-0001'))
    R['periodo_inexistente'] = err(crear('admin_fika', '2025-03-10', 'x', [ln(FIKA, '103101', d=1), ln(FIKA, '103103', c=1)]))
    # Para la prueba el ingreso original se registra en junio (abierto); el periodo real lo decide el contador
    sql("insert into exchange_rate (id, company_id, rate_date, currency, buy_rate, sell_rate, created_at, updated_at, is_active) values (md5('tc0630'), :c, '2026-06-30', 'USD', 3.55, 3.56, now(), now(), true) on conflict do nothing", c=FIKA)
    st, d = crear('admin_fika', '2026-06-30', 'Ingreso de dinero de FLUMISA (prueba)', [ln(FIKA, '104101', d=3000, bank='bk-fika-bcp-mn'), ln(FIKA, '103101', c=3000)], op='ORIG-0001', ref='Deposito de FLUMISA a FIKA', rid='r-orig')
    R['original_junio'] = [st, d.get('data', {}).get('entry_number'), [(l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me']) for l in d.get('data', {}).get('lines', [])]]
    st, d = crear('admin_fika', '2026-10-14', 'Devolucion a FLUMISA de dinero depositado por error', [ln(FIKA, '103101', d=3000), ln(FIKA, '104101', c=3000, bank='bk-fika-bcp-mn')], op='01117932', ref='Devolucion a FLUMISA', rid='r-dev')
    DEV = d.get('data', {})
    R['devolucion_14_10'] = [st, DEV.get('entry_number'), DEV.get('exchange_rate'), [(l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me'], l['reference_document']) for l in DEV.get('lines', [])]]
    R['puente_103101_tras_par'] = [x for x in get('admin_fika', B('admin_fika') + '/bridge-balances')[1]['data'] if x['account_code'] == '103101']
    R['banco_movimientos_del_par'] = sql("select transaction_date::text, transaction_type, amount::text, reference_number from bank_transaction where related_document_type='manual_journal' and account_id='bk-fika-bcp-mn' order by transaction_date")
    # Doble envio (mismo id): un solo asiento
    st2, d2 = crear('admin_fika', '2026-10-14', 'Devolucion a FLUMISA de dinero depositado por error', [ln(FIKA, '103101', d=3000), ln(FIKA, '104101', c=3000, bank='bk-fika-bcp-mn')], op='01117932', rid='r-dev')
    R['doble_envio'] = [st2, d2.get('data', {}).get('idempotent'), sql("select count(*) from manual_journal_entry where client_request_id='r-dev'")[0][0]]
    # N. de operacion repetido (misma cuenta y mes)
    R['op_repetido'] = err(crear('admin_fika', '2026-10-15', 'otra vez', [ln(FIKA, '103101', d=3000), ln(FIKA, '104101', c=3000, bank='bk-fika-bcp-mn')], op='01117932'))
    # Los otros casos reales (contrapartida de prueba 103101: el contador aun no definio las cuentas)
    for u, cid, bank, op, monto, sal in [('admin_fika', FIKA, 'bk-fika-bcp-mn', '01104038', 975, True), ('admin_fika', FIKA, 'bk-fika-bcp-mn', '01108170', 100, True),
                                          ('admin_flu', FLU, 'bk-flu-bcp-mn', '02117932', 3000, False), ('admin_flu', FLU, 'bk-flu-bcp-mn', '02104038', 975, False),
                                          ('admin_flu', FLU, 'bk-flu-bcp-mn', '02108170', 100, False)]:
        lines = [ln(cid, '103101', d=monto), ln(cid, '104101', c=monto, bank=bank)] if sal else [ln(cid, '104101', d=monto, bank=bank), ln(cid, '103101', c=monto)]
        R[f'caso_{op}'] = err(crear(u, '2026-10-14', f'Prueba op {op}', lines, op=op))[:1] or None
        R[f'caso_{op}'] = sql("select transaction_type, amount::text from bank_transaction where reference_number=:o and transaction_date='2026-10-14'", o=op)
    # Dolares: banco ME 100 US$ con TC 3.759
    st, d = crear('admin_fika', '2026-10-14', 'Ingreso en dolares (prueba)', [ln(FIKA, '104102', d=100, bank='bk-fika-bcp-me'), ln(FIKA, '103103', c=100)], op='USD-0001', cur='USD')
    USD = d.get('data', {})
    R['dolares'] = [st, [(l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me']) for l in USD.get('lines', [])],
                    sql("select transaction_type, amount::text from bank_transaction where reference_number='USD-0001'")]
    # Soles con redondeo: 100 = 33.33 + 66.67 -> en dolares tambien cuadra
    st, d = crear('admin_fika', '2026-10-14', 'Redondeo (prueba)', [ln(FIKA, '103103', d=100), ln(FIKA, '103101', c=33.33), ln(FIKA, '103105', c=66.67)])
    lines = d.get('data', {}).get('lines', [])
    R['redondeo'] = [st, [(l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me']) for l in lines],
                     round(sum(l['debit_amount_me'] for l in lines), 2), round(sum(l['credit_amount_me'] for l in lines), 2)]
    # Bloqueos
    R['sin_tc_13_10'] = err(crear('admin_fika', '2026-10-13', 'x', [ln(FIKA, '103101', d=1), ln(FIKA, '103103', c=1)]))
    R['descuadrado'] = err(crear('admin_fika', '2026-10-14', 'x', [ln(FIKA, '103101', d=10), ln(FIKA, '103103', c=9)]))
    R['sin_glosa'] = err(crear('admin_fika', '2026-10-14', '', [ln(FIKA, '103101', d=1), ln(FIKA, '103103', c=1)]))
    R['banco_sin_op'] = err(crear('admin_fika', '2026-10-14', 'x', [ln(FIKA, '103101', d=1), ln(FIKA, '104101', c=1, bank='bk-fika-bcp-mn')]))
    R['banco_que_no_corresponde'] = err(crear('admin_fika', '2026-10-14', 'x', [ln(FIKA, '103101', d=1), ln(FIKA, '104101', c=1, bank='bk-fika-bcp-me')], op='X-1'))
    R['debe_y_haber_en_una_linea'] = err(crear('admin_fika', '2026-10-14', 'x', [{**ln(FIKA, '103101', d=1), 'credit': 1}, ln(FIKA, '103103', c=1)]))
    R['sin_permiso_crear'] = err(crear('ventas_fika', '2026-10-14', 'x', [ln(FIKA, '103101', d=1), ln(FIKA, '103103', c=1)]))
    # Marca del boton Pagar con el mismo N. de operacion -> bloqueado
    post('admin_fika', f'/api/banks/{FIKA}/conciliacion-pago/bk-fika-bcp-mn', {'fecha': '2026-10-14', 'operation_number': 'ITF-55', 'monto': 0.15, 'descripcion': 'ITF'})
    R['op_ya_pagado_en_conciliacion'] = err(crear('admin_fika', '2026-10-14', 'x', [ln(FIKA, '103101', d=0.15), ln(FIKA, '104101', c=0.15, bank='bk-fika-bcp-mn')], op='ITF-55'))
    # Anular: el de dolares -> reversa, saldos en cero, banco neto cero
    lst = get('admin_fika', B('admin_fika'))[1]['data']
    usd_meta = next(m for m in lst if m['operation_number'] == 'USD-0001')
    R['anular_sin_permiso'] = err(post('ventas_fika', B('ventas_fika') + f"/{usd_meta['id']}/void", {'reason': 'x'}))
    R['anular_sin_motivo'] = err(post('admin_fika', B('admin_fika') + f"/{usd_meta['id']}/void", {'reason': ''}))
    st, d = post('admin_fika', B('admin_fika') + f"/{usd_meta['id']}/void", {'reason': 'Prueba de anulacion', 'date': '2026-10-15'})
    R['anular'] = [st, d.get('data', {}).get('status'), d.get('data', {}).get('reversal_entry_number'), d.get('message')]
    R['anular_saldos'] = sql("""select a.account_code, sum(l.debit_amount)-sum(l.credit_amount), sum(l.debit_amount_me)-sum(l.credit_amount_me)
        from journal_entry_line l join journal_entry e on e.id=l.entry_id join chart_of_account a on a.id=l.chart_account_id
        where e.attachment_path = 'manual:' || :m group by 1 order by 1""", m=usd_meta['id'])
    R['anular_banco'] = sql("select transaction_date::text, transaction_type, amount::text, reference_number from bank_transaction where account_id='bk-fika-bcp-me' order by created_at")
    R['anular_otra_vez'] = err(post('admin_fika', B('admin_fika') + f"/{usd_meta['id']}/void", {'reason': 'x'}))
    # Anular el de 975 libera su N. de operacion y se puede volver a registrar
    m975 = next(m for m in lst if m['operation_number'] == '01104038')
    post('admin_fika', B('admin_fika') + f"/{m975['id']}/void", {'reason': 'Cuenta equivocada'})
    st, d = crear('admin_fika', '2026-10-14', 'Prueba op 01104038 (corregido)', [ln(FIKA, '103105', d=975), ln(FIKA, '104101', c=975, bank='bk-fika-bcp-mn')], op='01104038')
    R['re_registrar_tras_anular'] = [st, d.get('data', {}).get('entry_number')]
    # Numeracion de octubre sin huecos
    R['numeros_octubre'] = sql("select entry_number from journal_entry e join fiscal_period p on p.id=e.fiscal_period_id where e.company_id=:c and p.period_year=2026 and p.period_month=10 order by entry_number", c=FIKA)
    R['tipo_manual'] = sql("select entry_type, status, count(*) from journal_entry where entry_type='manual' group by 1,2")
R['despues'] = snapshot()
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('listo', OUT)
