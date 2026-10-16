"""Bancos > Movimiento entre cuentas: pruebas de servidor (main y rama).
Uso: python bm_api_test.py <backend_dir> <db> <salida.json>
"""
import os, sys, json, hashlib
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
    CODE = {v: k[1] for k, v in ACC.items()}

def H(u): return {'Authorization': 'Bearer ' + TOK[u][0]}
def get(u, url): r = cl.get(url, headers=H(u)); return r.status_code, (r.get_json(silent=True) or {}), r
def post(u, url, body): r = cl.post(url, headers=H(u), json=body); return r.status_code, (r.get_json(silent=True) or {})
def put(u, url, body): r = cl.put(url, headers=H(u), json=body); return r.status_code, (r.get_json(silent=True) or {})
def h(b): return hashlib.sha256(b).hexdigest()[:16]
def sql(q, **p):
    with app.app_context():
        res = db.session.execute(text(q), p)
        rows = [list(x) for x in res] if res.returns_rows else []
        db.session.commit()
        return rows
def err(res): st, d = res; return [st, (d.get('error') or {}).get('code'), (d.get('error') or {}).get('message')]

def snapshot():
    out = {}
    for u in ('admin_fika', 'admin_flu'):
        cid = TOK[u][1]
        bk = 'bk-fika-bcp-mn' if cid == FIKA else 'bk-flu-bcp-mn'
        for name, url in [('diario', f'/api/journal-entries/{cid}?per_page=20000'), ('libro_paginado', f'/api/journal-entries/{cid}/book?all=1&tz=300'),
                          ('resumen_dashboard', f'/api/journal-entries/{cid}/summary'),
                          ('movimientos_banco', f'/api/banks/{cid}/transactions?per_page=20000'),
                          ('cuentas_banco', f'/api/banks/{cid}/accounts?per_page=20000'), ('pagos_historial', f'/api/payments/{cid}/history'),
                          ('dashboard', f'/api/dashboard/{cid}'), ('periodos', f'/api/companies/{cid}/fiscal-periods'),
                          ('parametros', f'/api/companies/{cid}/parameters'),
                          ('extracto_oct', f'/api/banks/{cid}/conciliacion-import/{bk}?periodo=2026-10'),
                          ('marcas_pagar', f'/api/banks/{cid}/conciliacion-pago/{bk}')]:
            st, _, r = get(u, url); out[f'{u}:{name}'] = [st, h(r.data)]
    return out

def lines_of(meta):
    return [(CODE.get(l['chart_account_id']), l['debit_amount'], l['credit_amount'], l['debit_amount_me'], l['credit_amount_me'], l['reference_document']) for l in meta.get('lines', [])]
def txs(account_id):
    return sql("select transaction_date::text, transaction_type, amount::text, reference_number from bank_transaction where account_id=:a order by created_at", a=account_id)

R['antes'] = snapshot()
st, _, _ = get('admin_fika', f'/api/manual-journal/{FIKA}/bank-movement/options')
R['tiene_pestana'] = st == 200
if R['tiene_pestana']:
    BM = lambda u: f'/api/manual-journal/{TOK[u][1]}/bank-movement'
    def mov(u, rid=None, **kw):
        body = dict(kw); body.setdefault('client_request_id', rid)
        return post(u, BM(u), body)
    st, o, _ = get('admin_fika', BM('admin_fika') + '/options'); d = o['data']
    R['opciones_fika'] = {'puede': d['can_register'], 'roles': d['allowed_roles'],
                          'bancos_ofrecidos': [(b['bank_name'], b['currency'], b['chart_account_code']) for b in d['bank_accounts']],
                          'contrapartidas': d['counterparts']}
    R['opciones_ventas_puede'] = get('ventas_fika', BM('ventas_fika') + '/options')[1]['data']['can_register']
    # Sin lista del contador no se registra el tipo con contrapartida
    R['sin_lista_contrapartidas'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=3000, bank_account_id='bk-fika-bcp-mn',
                                            direction='out', operation_number='01117932', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['lista_por_ventas'] = err(put('ventas_fika', BM('ventas_fika') + '/counterparts', {'codes': ['103101']}))
    R['lista_con_104'] = err(put('admin_fika', BM('admin_fika') + '/counterparts', {'codes': ['104101']}))
    st, d = put('admin_fika', BM('admin_fika') + '/counterparts', {'codes': ['103101']})
    R['lista_fika'] = [st, [c['account_code'] for c in d['data']['counterparts']]]
    st, d = put('admin_flu', BM('admin_flu') + '/counterparts', {'codes': ['103101']})
    R['lista_flumisa'] = [st, [c['account_code'] for c in d['data']['counterparts']]]

    # Casos reales del 14/10: FIKA salidas por BCP MN (contrapartida 103101), cada una con su N. de operacion
    R['fika_salidas'] = {}
    for amount, op in ((3000, '01117932'), (975, '01104038'), (100, '01108170')):
        st, d = mov('admin_fika', rid='fika-' + op, kind='counterpart', entry_date='2026-10-14', amount=amount, bank_account_id='bk-fika-bcp-mn',
                    direction='out', operation_number=op, counterpart_account_id=ACC[(FIKA, '103101')],
                    gloss=f'Transferencia a FLUMISA S/ {amount}', reference='Pendiente de definir por el contador')
        m = d.get('data', {})
        R['fika_salidas'][op] = [st, m.get('entry_number'), m.get('origin'), lines_of(m)]
    R['fika_banco_bcp'] = txs('bk-fika-bcp-mn')
    # FLUMISA: entradas por su BCP MN, cada una con su numero
    R['flumisa_entradas'] = {}
    for amount, op in ((3000, '02117932'), (975, '02104038'), (100, '02108170')):
        st, d = mov('admin_flu', rid='flu-' + op, kind='counterpart', entry_date='2026-10-14', amount=amount, bank_account_id='bk-flu-bcp-mn',
                    direction='in', operation_number=op, counterpart_account_id=ACC[(FLU, '103101')], gloss=f'Ingreso de FIKA S/ {amount}')
        m = d.get('data', {})
        R['flumisa_entradas'][op] = [st, m.get('entry_number'), lines_of(m)]
    R['flumisa_banco_bcp'] = txs('bk-flu-bcp-mn')
    # Transferencia entre cuentas propias de FIKA: BCP MN -> Interbank MN, dos N. de operacion
    st, d = mov('admin_fika', rid='fika-propia', kind='own_transfer', entry_date='2026-10-14', amount=500, from_bank_account_id='bk-fika-bcp-mn',
                to_bank_account_id='bk-fika-ibk-mn', out_operation_number='01200001', in_operation_number='33300001', gloss='Traspaso BCP a Interbank')
    PROPIA = d.get('data', {})
    R['propia'] = [st, PROPIA.get('entry_number'), PROPIA.get('operation_number'), lines_of(PROPIA)]
    R['propia_bancos'] = {'bcp': txs('bk-fika-bcp-mn')[-1:], 'interbank': txs('bk-fika-ibk-mn')}
    # Doble clic / doble envio: mismo envio -> un solo asiento
    st1, d1 = mov('admin_fika', rid='fika-propia', kind='own_transfer', entry_date='2026-10-14', amount=500, from_bank_account_id='bk-fika-bcp-mn',
                  to_bank_account_id='bk-fika-ibk-mn', out_operation_number='01200001', in_operation_number='33300001', gloss='Traspaso BCP a Interbank')
    R['doble_envio'] = [st1, d1.get('data', {}).get('idempotent'), d1.get('data', {}).get('entry_number') == PROPIA.get('entry_number'),
                        sql("select count(*) from bank_transaction where reference_number in ('01200001','33300001')")[0][0]]
    # Bloqueos
    R['op_repetido'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-15', amount=3000, bank_account_id='bk-fika-bcp-mn',
                               direction='out', operation_number='01117932', counterpart_account_id=ACC[(FIKA, '103101')], gloss='otra vez'))
    R['op_repetido_destino'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-10-14', amount=10, from_bank_account_id='bk-fika-bcp-mn',
                                       to_bank_account_id='bk-fika-ibk-mn', out_operation_number='NUEVO-1', in_operation_number='33300001', gloss='x'))
    R['julio_cerrado'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-07-15', amount=50, bank_account_id='bk-fika-bcp-mn',
                                 direction='in', operation_number='J-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['agosto_cerrado'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-08-03', amount=50, from_bank_account_id='bk-fika-bcp-mn',
                                  to_bank_account_id='bk-fika-ibk-mn', out_operation_number='A-1', in_operation_number='A-2', gloss='x'))
    R['periodo_inexistente'] = err(mov('admin_fika', kind='counterpart', entry_date='2025-03-10', amount=50, bank_account_id='bk-fika-bcp-mn',
                                       direction='in', operation_number='X-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['dolares_sin_tc'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-13', amount=100, bank_account_id='bk-fika-bcp-me',
                                  direction='in', operation_number='USD-13', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    st, d = mov('admin_fika', rid='fika-usd', kind='counterpart', entry_date='2026-10-15', amount=100, bank_account_id='bk-fika-bcp-me',
                direction='in', operation_number='USD-15', counterpart_account_id=ACC[(FIKA, '103101')], gloss='Deposito en dolares (prueba)')
    R['dolares'] = [st, d.get('data', {}).get('input_currency'), d.get('data', {}).get('exchange_rate'), lines_of(d.get('data', {})), txs('bk-fika-bcp-me')]
    R['monedas_distintas'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-10-14', amount=100, from_bank_account_id='bk-fika-bcp-mn',
                                     to_bank_account_id='bk-fika-bcp-me', out_operation_number='M-1', in_operation_number='M-2', gloss='x'))
    R['misma_cuenta'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-10-14', amount=100, from_bank_account_id='bk-fika-bcp-mn',
                                to_bank_account_id='bk-fika-bcp-mn', out_operation_number='S-1', in_operation_number='S-2', gloss='x'))
    R['un_solo_numero'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-10-14', amount=100, from_bank_account_id='bk-fika-bcp-mn',
                                  to_bank_account_id='bk-fika-ibk-mn', out_operation_number='S-3', gloss='x'))
    R['cuenta_comisiones'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=5, bank_account_id='bk-fika-comis',
                                     direction='out', operation_number='C-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['caja'] = err(mov('admin_fika', kind='own_transfer', entry_date='2026-10-14', amount=5, from_bank_account_id='bk-fika-bcp-mn',
                        to_bank_account_id='bk-fika-caja', out_operation_number='K-1', in_operation_number='K-2', gloss='x'))
    R['contrapartida_fuera_de_lista'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=5, bank_account_id='bk-fika-bcp-mn',
                                                direction='out', operation_number='F-1', counterpart_account_id=ACC[(FIKA, '103103')], gloss='x'))
    R['sin_glosa'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=5, bank_account_id='bk-fika-bcp-mn',
                             direction='out', operation_number='G-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss=''))
    R['sin_op'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=5, bank_account_id='bk-fika-bcp-mn',
                          direction='out', operation_number='', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['monto_cero'] = err(mov('admin_fika', kind='counterpart', entry_date='2026-10-14', amount=0, bank_account_id='bk-fika-bcp-mn',
                              direction='out', operation_number='Z-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    R['sin_permiso'] = err(mov('ventas_fika', kind='counterpart', entry_date='2026-10-14', amount=5, bank_account_id='bk-fika-bcp-mn',
                               direction='out', operation_number='P-1', counterpart_account_id=ACC[(FIKA, '103101')], gloss='x'))
    # Anular la transferencia propia: reversa, los dos movimientos con -ANUL, saldos en cero y numeros libres
    MJ = f'/api/manual-journal/{FIKA}'
    R['anular_sin_permiso'] = err(post('ventas_fika', MJ + f"/{PROPIA['id']}/void", {'reason': 'x'}))
    st, d = post('admin_fika', MJ + f"/{PROPIA['id']}/void", {'reason': 'Prueba de anulacion', 'date': '2026-10-16'})
    R['anular'] = [st, d.get('data', {}).get('status'), d.get('message')]
    R['anular_saldos'] = sql("""select a.account_code, sum(l.debit_amount)-sum(l.credit_amount) from journal_entry_line l join journal_entry e on e.id=l.entry_id
        join chart_of_account a on a.id=l.chart_account_id where e.attachment_path = 'manual:' || :m group by 1 order by 1""", m=PROPIA['id'])
    R['anular_bancos'] = sql("select account_id, transaction_type, amount::text, reference_number from bank_transaction where related_document_id=:m order by created_at", m=PROPIA['id'])
    st, d = mov('admin_fika', rid='fika-propia-2', kind='own_transfer', entry_date='2026-10-14', amount=500, from_bank_account_id='bk-fika-bcp-mn',
                to_bank_account_id='bk-fika-ibk-mn', out_operation_number='01200001', in_operation_number='33300001', gloss='Traspaso BCP a Interbank (corregido)')
    R['re_registrar_tras_anular'] = [st, d.get('data', {}).get('entry_number')]
    # El asiento manual del Libro Diario sigue igual (un solo N. de operacion para el asiento)
    st, d = post('admin_fika', MJ, {'entry_date': '2026-10-15', 'gloss': 'Asiento manual del diario (prueba)', 'currency': 'PEN', 'operation_number': 'DIARIO-1',
                                     'lines': [{'chart_account_id': ACC[(FIKA, '103103')], 'debit': 20}, {'chart_account_id': ACC[(FIKA, '104101')], 'credit': 20, 'bank_account_id': 'bk-fika-bcp-mn'}]})
    R['diario_sigue_igual'] = [st, d.get('data', {}).get('origin'), d.get('data', {}).get('operation_number'), lines_of(d.get('data', {}))]
    R['lista_origenes'] = sorted(set((m['origin'], m['status']) for m in get('admin_fika', MJ)[1]['data']))
    R['puente_103101_fika'] = sql("""select sum(l.debit_amount)-sum(l.credit_amount) from journal_entry_line l join journal_entry e on e.id=l.entry_id
        join chart_of_account a on a.id=l.chart_account_id where e.company_id=:c and a.account_code='103101'""", c=FIKA)
    R['numeros_octubre_fika'] = sql("select entry_number from journal_entry e join fiscal_period p on p.id=e.fiscal_period_id where e.company_id=:c and p.period_year=2026 and p.period_month=10 order by entry_number", c=FIKA)
    R['periodos'] = sql("select count(*), sum((status='closed')::int) from fiscal_period")
R['despues'] = snapshot()
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('listo', OUT)
