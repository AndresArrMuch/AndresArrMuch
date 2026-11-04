"""Tope del deposito y facturas con cobro. Uso: api_test.py <backend> <db> <salida.json>"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
B, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
os.environ['CEA_REINTENTO_AUTOMATICO'] = '0'
sys.path.insert(0, B); os.chdir(B)
from app import create_app, db
from app.models import Sale, BankAccount
from app.models.user import User
from flask_jwt_extended import create_access_token
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app('development'); cl = app.test_client(); R = {}
with app.app_context():
    h = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='tesoreria@t.pe', company_id=F).first().id)}
    acc = BankAccount.query.filter_by(company_id=F, account_number='191-1111111-0-11').first().id
    sid = {d: Sale.query.filter_by(company_id=F, document_number=d).first().id for d in ('F001-000003', 'F001-000005', 'B001-000001', 'F030-000119')}
def J(r):
    j = r.get_json(silent=True) or {}; e = j.get('error') if isinstance(j.get('error'), dict) else {}
    return {'http': r.status_code, 'codigo': e.get('code'), 'mensaje': (e.get('message') or j.get('message') or '')[:260], 'data': j.get('data') if r.status_code < 300 else e.get('data')}
def paid(d):
    with app.app_context(): return float(Sale.query.get(sid[d]).amount_paid or 0)
def collect(op, items, notes='', date='2026-10-16'):
    return J(cl.post(f'/api/payments/{F}/collect', json=dict(bank_account_id=acc, payment_date=date, payment_method='transfer', reference_number=op, notes=notes,
             items=[dict(sale_id=sid[d], amount=a) for d, a in items]), headers=h))
# Extracto de octubre con dos depositos
rows = [dict(date='2026-10-16', description='DEP UNION DE NEGOCIOS', operation_number='777001', amount=900.0, type='in'),
        dict(date='2026-10-17', description='DEP OTRO', operation_number='777002', amount=100.0, type='in')]
R['0_subir_extracto'] = J(cl.post(f'/api/banks/{F}/conciliacion-import/{acc}', json=dict(rows=rows, filename='extracto.xlsx', periodo='2026-10'), headers=h))['http']
R['1_cobro_dentro_del_deposito_672'] = collect('777001', [('F001-000003', 200), ('F001-000005', 472)])
pid1 = (R['1_cobro_dentro_del_deposito_672']['data'] or {}).get('payment_id')
R['2_cobro_que_pasa_lo_disponible_540'] = collect('777001', [('F030-000119', 540)])
R['2b_F030-000119_cobrado_despues_del_rechazo'] = paid('F030-000119')
R['3_cobro_que_cabe_118'] = collect('777001', [('B001-000001', 118)])
R['4_consulta_tope'] = J(cl.get(f'/api/payments/{F}/deposit-cap?bank_account_id={acc}&reference=777001&date=2026-10-16', headers=h))
if pid1:
    R['5_editar_cobro_1_a_826_supera'] = J(cl.put(f'/api/payments/{F}/{pid1}', json=dict(items=[dict(document_type='sale', document_id=sid['F001-000003'], amount_applied=354), dict(document_type='sale', document_id=sid['F001-000005'], amount_applied=472)]), headers=h))
    R['5b_F001-000003_cobrado_tras_edicion'] = paid('F001-000003')
    R['6_editar_cobro_1_a_782_cabe'] = J(cl.put(f'/api/payments/{F}/{pid1}', json=dict(items=[dict(document_type='sale', document_id=sid['F001-000003'], amount_applied=310), dict(document_type='sale', document_id=sid['F001-000005'], amount_applied=472)]), headers=h))
R['7_comision_deposito_100_mas_comision_5'] = collect('777002', [('F030-000119', 105)], notes='Comision: 5.00', date='2026-10-17')
R['8_operacion_que_no_esta_en_el_extracto'] = collect('999999', [('F001-000003', 10)])
# Factura con cobro: no se puede eliminar
nv = cl.post(f'/api/sales/{F}', json=dict(customer_id='cli-1', document_type='01', series='F050', emission_date='2026-10-16', due_date='2026-10-16', currency='PEN',
              lines=[dict(description='SERV', quantity=1, unit='ZZ', unit_price=100, igv_percentage=18)], price_includes_igv=True, confirmar_repetida=True), headers=h).get_json()
nid = (nv.get('data') or {}).get('id')
with app.app_context(): sid['F060'] = nid
R['9_cobro_factura_nueva'] = collect('555555', [('F060', 118)])['http']
R['9b_eliminar_factura_con_cobro'] = J(cl.delete(f'/api/sales/{F}/{nid}', headers=h))
with app.app_context():
    R['9c_factura_sigue_existiendo'] = Sale.query.get(nid) is not None
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str); print('ok')
