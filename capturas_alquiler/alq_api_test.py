"""Pruebas por API del submodulo Alquiler (rama) y de que compras normales y RxH quedan iguales (main vs rama).
Uso: python alq_api_test.py <backend_dir> <db> <rama|main> <salida.json>
"""
import os, sys, json
from decimal import Decimal

BACKEND, DB, MODE, OUT = sys.argv[1:5]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
import app.routes.purchase_routes as pr
# Sin red: la validacion SUNAT de RUC y comprobante se da por buena (solo afecta a compras normales)
pr.validate_ruc_with_sunat = lambda ruc: {'valid': True}
pr.verify_purchase_document_with_sunat = lambda *a, **k: {'authorized': True}
from app.models import Purchase, JournalEntry, BankTransaction
from app.models.bank import PaymentRecord
from app.models.user import User
from flask_jwt_extended import create_access_token

CID = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app()
with app.app_context():
    tok = create_access_token(identity=User.query.filter_by(email='admin@t.pe').first().id)
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}
results = []

def call(method, url, body=None):
    r = getattr(cl, method)(url, headers=H, json=body)
    data = r.get_json(silent=True) or {}
    return r.status_code, data

def check(name, ok, detail=''):
    results.append({'prueba': name, 'ok': bool(ok), 'detalle': detail})
    print(('OK   ' if ok else 'FALLA') + ' | ' + name + (' | ' + str(detail) if detail else ''))

def entry_dump(entry):
    return {
        'tipo': entry.entry_type, 'fecha': entry.entry_date.isoformat(), 'periodo': entry.fiscal_period.period_month if entry.fiscal_period else None,
        'glosa': entry.gloss,
        'lineas': [(l.chart_account.account_code, float(l.debit_amount or 0), float(l.credit_amount or 0),
                    float(l.debit_amount_me or 0), float(l.credit_amount_me or 0), l.description) for l in entry.lines],
    }

def entry_for(marker):
    with app.app_context():
        e = JournalEntry.query.filter_by(company_id=CID, attachment_path=marker).first()
        return entry_dump(e) if e else None

def purchase(pid):
    with app.app_context():
        p = db.session.get(Purchase, pid)
        return p.to_dict() if p else None

def pay(items, ref, date, bank='bank-pen', commission=0, rate=None):
    body = {'bank_account_id': bank, 'payment_date': date, 'reference_number': ref, 'items': items,
            'commission_amount': commission}
    if rate:
        body['exchange_rate'] = rate
    return call('post', f'/api/payments/{CID}/pay', body)

# ---------------- Escenario comun: compra normal y RxH (debe ser igual en main y en la rama) ----------------
common = {}
st, d = call('post', f'/api/purchases/{CID}', {
    'supplier_id': 'sup-sac', 'document_type': '01', 'series': 'F001', 'correlative': '0000100',
    'emission_date': '2026-10-06', 'due_date': '2026-10-30', 'currency': 'PEN', 'exchange_rate': 1,
    'auto_detraction': False, 'detraction_percentage': 0, 'auto_retention': False,
    'lines': [{'description': 'Mercaderia', 'quantity': 1, 'unit': 'NIU', 'unit_price': 1000, 'igv_percentage': 18}]})
check('Compra normal 01 registrada', st == 201, st)
normal_id = d.get('data', {}).get('id')
st, d = call('post', f'/api/purchases/{CID}', {
    'supplier_id': 'sup-rxh', 'document_type': '02', 'series': 'E001', 'correlative': '55',
    'emission_date': '2026-10-06', 'due_date': '2026-10-30', 'currency': 'PEN', 'exchange_rate': 1,
    'rxh_retention': True, 'lines': [{'description': 'Asesoria', 'quantity': 1, 'unit': 'UND', 'unit_price': 1000, 'igv_percentage': 0}]})
check('RxH 02 registrado', st == 201, st)
rxh_id = d.get('data', {}).get('id')
st, d = pay([{'purchase_id': normal_id, 'amount': 500}], 'N-001', '2026-10-10')
common['pago_normal_parcial'] = (st, d.get('data', {}).get('lines'))
st, d = pay([{'purchase_id': normal_id, 'amount': 680}, {'purchase_id': rxh_id, 'amount': 920}], 'N-002', '2026-10-12', commission=3.5)
common['pago_varios'] = (st, d.get('data', {}).get('lines'))
pay_multi_id = d.get('data', {}).get('payment_id')
st, d = pay([{'purchase_id': normal_id, 'amount': 1}], 'N-002', '2026-10-12')
common['ref_repetida'] = (st, d.get('error', {}).get('code') if isinstance(d.get('error'), dict) else d.get('code') or d.get('message'))
st, d = call('post', f'/api/payments/{CID}/{pay_multi_id}/void')
common['anular_pago'] = st
with app.app_context():
    common['asientos'] = sorted([entry_dump(e) for e in JournalEntry.query.filter_by(company_id=CID).all()],
                                key=lambda x: (x['tipo'], x['glosa']))
    common['compras'] = sorted([(p.document_number, p.document_type, float(p.total), float(p.amount_paid or 0), p.payment_status)
                                for p in Purchase.query.filter_by(company_id=CID).all()])
    common['pagos'] = sorted([(p.reference_number, float(p.total_amount or 0), p.status, p.currency)
                              for p in PaymentRecord.query.filter_by(company_id=CID).all()])
st, d = call('get', f'/api/purchases/{CID}?per_page=500')
common['lista_compras'] = sorted([(x['document_number'], x['document_type'], x['balance_due'], x['payment_status'])
                                  for x in d.get('data', {}).get('data', [])])

# ---------------- Escenario Alquiler (solo rama; en main la ruta no existe) ----------------
rent = {}
RENT = f'/api/purchases/{CID}/rentals'
if MODE == 'main':
    st, d = call('post', RENT, {'supplier_id': 'sup-arr1', 'correlative': '000123', 'emission_date': '2026-10-05', 'amount': 1500, 'description': 'x'})
    check('main: la ruta de alquiler no existe', st in (404, 405), st)
else:
    body = {'supplier_id': 'sup-arr1', 'correlative': '000123', 'emission_date': '2026-10-05', 'due_date': '2026-10-15',
            'currency': 'PEN', 'amount': 1500, 'description': 'Alquiler local Malvinas octubre 2026'}
    st, d = call('post', RENT, body)
    a1 = d.get('data', {}); a1_id = a1.get('id')
    check('1. Alquiler en soles registrado', st == 201 and a1.get('document_type') == 'AL', (st, a1.get('document_number')))
    e = entry_for(f'purchase:{a1_id}'); rent['asiento_alquiler_pen'] = e
    check('1. Asiento Debe 635201 / Haber 469901 por 1500',
          e and [(l[0], l[1], l[2]) for l in e['lineas']] == [('635201', 1500.0, 0.0), ('469901', 0.0, 1500.0)], e and e['lineas'])
    check('1. Asiento con fecha de emision, periodo octubre y glosa con proveedor, correlativo y detalle',
          e and e['fecha'] == '2026-10-05' and e['periodo'] == 10 and 'JUAN PEREZ' in e['glosa'] and '000123' in e['glosa'] and 'Malvinas' in e['glosa'], e and e['glosa'])
    with app.app_context():
        _p = db.session.get(Purchase, a1_id)
        _tax = [float(x or 0) for x in (_p.igv, _p.detraction_amount, _p.retention_amount, _p.perception_amount, _p.rxh_retention_amount)]
    check('1. Sin IGV, detraccion, retencion ni percepcion (todo 0 en la compra)', _tax == [0.0] * 5, _tax)
    st, d = call('get', f'/api/purchases/{CID}?per_page=500')
    row = next((x for x in d.get('data', {}).get('data', []) if x['id'] == a1_id), None)
    check('2. Aparece en la lista de pendientes con saldo, vencimiento y estado', row and row['balance_due'] == 1500.0 and row['due_date'] == '2026-10-15' and row['payment_status'] == 'unpaid',
          row and (row['balance_due'], row['due_date'], row['payment_status']))

    # Duplicados y periodo cerrado
    st, d = call('post', RENT, body)
    check('9. Duplicado (mismo proveedor y correlativo) bloqueado', st == 400 and 'Ya existe' in json.dumps(d), (st, d.get('message')))
    st, d = call('post', RENT, dict(body, supplier_id='sup-arr2'))
    a_other = d.get('data', {}).get('id')
    check('9. Mismo correlativo con OTRO arrendador permitido', st == 201, st)
    st, d = call('post', RENT, dict(body, correlative='000200', emission_date='2026-09-10'))
    check('8. Periodo cerrado para compras bloqueado', st == 400 and 'cerrado' in json.dumps(d), (st, d.get('message')))
    st, d = call('post', f'/api/purchases/{CID}', {'supplier_id': 'sup-arr1', 'document_type': 'AL', 'series': 'X', 'correlative': '1',
                                                     'emission_date': '2026-10-05', 'lines': []})
    check('Alquiler por la ruta generica de compras rechazado', st == 400, st)

    # Pagos: parcial, total con comision, referencia repetida
    st, d = pay([{'purchase_id': a1_id, 'amount': 500}], 'OP-111', '2026-10-10')
    p1 = d.get('data', {}); e = entry_for(f"payment:{p1.get('payment_id')}"); rent['pago_parcial'] = e
    check('3. Pago parcial 500: Debe 469901 / Haber 104101', st == 201 and e and [(l[0], l[1], l[2]) for l in e['lineas']] == [('469901', 500.0, 0.0), ('104101', 0.0, 500.0)], e and e['lineas'])
    check('3. Saldo 1000 y estado parcial', purchase(a1_id)['payment_status'] == 'partial' and purchase(a1_id)['balance_due'] == 1000.0)
    st, d = pay([{'purchase_id': a1_id, 'amount': 1000}], 'OP-112', '2026-10-11', commission=5)
    p2 = d.get('data', {}); e = entry_for(f"payment:{p2.get('payment_id')}"); rent['pago_total'] = e
    check('4. Pago del saldo con comision: Debe 469901 1000 + 639101 5 / Haber 104101 1005',
          st == 201 and e and [(l[0], l[1], l[2]) for l in e['lineas']] == [('469901', 1000.0, 0.0), ('639101', 5.0, 0.0), ('104101', 0.0, 1005.0)], e and e['lineas'])
    check('4. Estado pagado', purchase(a1_id)['payment_status'] == 'paid')
    st, d = pay([{'purchase_id': a_other, 'amount': 10}], 'OP-112', '2026-10-11')
    check('4. N. de operacion repetido bloqueado', st == 400 and 'ya fue registrado' in json.dumps(d), st)

    # Conciliacion: el extracto trae OP-111 por 500 el 10/10
    with app.app_context():
        from app.routes.bank_routes import _find_linked_payment
        stmt = BankTransaction(account_id='bank-pen', company_id=CID, transaction_date=Decimal and __import__('datetime').date(2026, 10, 10),
                               transaction_type='withdrawal', amount=Decimal('500'), reference_number='OP-111')
        found, explicit = _find_linked_payment(CID, stmt)
        check('5. Conciliacion (servidor): el extracto OP-111 / 500 / 10-10 encuentra el pago del alquiler',
              found is not None and found.id == p1.get('payment_id'), found and found.reference_number)
        tx = BankTransaction.query.filter_by(company_id=CID, reference_number='OP-111').first()
        check('5. Movimiento bancario del pago con N. de operacion OP-111 (match "sistema")', tx is not None and float(tx.amount) == 500.0, tx and float(tx.amount))
    st, d = call('get', f'/api/payments/{CID}/history?date_from=2026-01-01&date_to=2026-12-31')
    hist = [x for x in (d.get('data') or []) if x.get('reference_number') == 'OP-111']
    check('5. Conciliacion (pantalla): historial de Cobranzas trae OP-111, 500, 2026-10-10, cuenta BCP',
          hist and abs(hist[0]['total_amount'] - 500) < 0.01 and str(hist[0]['payment_date'])[:10] == '2026-10-10' and hist[0]['bank_account_id'] == 'bank-pen',
          hist and {k: hist[0][k] for k in ('reference_number', 'total_amount', 'payment_date', 'bank_account_id')})

    # Eliminar pago revierte saldo y asiento
    st, d = call('post', f"/api/payments/{CID}/{p2.get('payment_id')}/void")
    check('7. Eliminar el pago total: saldo vuelve a 1000 y estado parcial', st == 200 and purchase(a1_id)['balance_due'] == 1000.0 and purchase(a1_id)['payment_status'] == 'partial',
          (st, purchase(a1_id)['balance_due']))
    check('7. Eliminar el pago borra su asiento', entry_for(f"payment:{p2.get('payment_id')}") is None)

    # Editar y eliminar el alquiler
    st, d = call('put', f'{RENT}/{a1_id}', dict(body, amount=1600))
    check('Editar un alquiler con pagos bloqueado', st == 400, st)
    st, d = call('put', f'/api/purchases/{CID}/{a1_id}', {'notes': 'x'})
    check('Editar un alquiler por la ruta generica bloqueado', st == 400 and 'Alquiler' in json.dumps(d), st)
    before = entry_for(f'purchase:{a_other}')
    st, d = call('put', f'{RENT}/{a_other}', {'supplier_id': 'sup-arr2', 'correlative': '000123', 'emission_date': '2026-10-05',
                                               'currency': 'PEN', 'amount': 1650, 'description': 'Alquiler local Capon octubre'})
    after = entry_for(f'purchase:{a_other}')
    with app.app_context():
        nums = [e.entry_number for e in JournalEntry.query.filter_by(company_id=CID, attachment_path=f'purchase:{a_other}').all()]
    check('Editar un alquiler sin pagos regenera su asiento (1650) y conserva el numero',
          st == 200 and [(l[0], l[1], l[2]) for l in after['lineas']] == [('635201', 1650.0, 0.0), ('469901', 0.0, 1650.0)] and len(nums) == 1, (st, after and after['lineas'], nums))
    st, d = call('delete', f'/api/purchases/{CID}/{a1_id}')
    check('Eliminar un alquiler con pagos bloqueado', st == 400, st)
    st, d = call('delete', f'/api/purchases/{CID}/{a_other}')
    check('Eliminar un alquiler sin pagos borra el alquiler y su asiento', st == 200 and purchase(a_other) is None and entry_for(f'purchase:{a_other}') is None, st)

    # Alquiler en dolares
    st, d = call('post', RENT, {'supplier_id': 'sup-arr2', 'correlative': 'OCT-2026', 'emission_date': '2026-10-05', 'currency': 'USD',
                                'exchange_rate': 0, 'amount': 400, 'description': 'Alquiler almacen octubre (USD)'})
    au = d.get('data', {}); au_id = au.get('id'); e = entry_for(f'purchase:{au_id}'); rent['asiento_alquiler_usd'] = e
    check('6. Alquiler USD 400 con TC del dia 3.75 (de la tabla): total S/ 1500', st == 201 and au.get('total') == 1500.0 and au.get('exchange_rate') == 3.75, (st, au.get('total'), au.get('exchange_rate')))
    check('6. Asiento USD: Debe 635201 1500 (US$ 400) / Haber 469903 1500 (US$ 400)',
          e and [(l[0], l[1], l[2], l[3], l[4]) for l in e['lineas']] == [('635201', 1500.0, 0.0, 400.0, 0.0), ('469903', 0.0, 1500.0, 0.0, 400.0)], e and e['lineas'])
    st, d = pay([{'purchase_id': au_id, 'amount': 400, 'currency': 'USD'}], 'OP-USD-1', '2026-10-20', bank='bank-usd', rate=3.80)
    e = entry_for(f"payment:{d.get('data', {}).get('payment_id')}"); rent['pago_usd'] = e
    check('6. Pago US$ 400 al TC 3.80: Debe 469903 1500 (US$ 400) + 676101 20 / Haber 104102 1520 (US$ 400)',
          st == 201 and e and [(l[0], l[1], l[2], l[3], l[4]) for l in e['lineas']] == [('469903', 1500.0, 0.0, 400.0, 0.0), ('676101', 20.0, 0.0, 0.0, 0.0), ('104102', 0.0, 1520.0, 0.0, 400.0)],
          e and e['lineas'])
    check('6. Alquiler USD pagado', purchase(au_id)['payment_status'] == 'paid')


    # Segundo alquiler en dolares con dos pagos posteriores: perdida y ganancia por diferencia de cambio
    st, d = call('post', RENT, {'supplier_id': 'sup-arr1', 'correlative': 'NOV-2026', 'emission_date': '2026-10-05', 'currency': 'USD',
                                'exchange_rate': 3.75, 'amount': 200, 'description': 'Alquiler cochera (USD)'})
    check('6b. Mensaje del alta en USD indica las cuentas del asiento (Debe 635201 / Haber 469903)', st == 201 and 'Haber 469903' in d.get('message', ''), d.get('message'))
    a2_id = d.get('data', {}).get('id'); e = entry_for(f'purchase:{a2_id}')
    check('6b. Asiento: Debe 635201 750 (US$ 200) / Haber 469903 750 (US$ 200)',
          e and [(l[0], l[1], l[2], l[3], l[4]) for l in e['lineas']] == [('635201', 750.0, 0.0, 200.0, 0.0), ('469903', 0.0, 750.0, 0.0, 200.0)], e and e['lineas'])
    st, d = pay([{'purchase_id': a2_id, 'amount': 100, 'currency': 'USD'}], 'OP-USD-2', '2026-10-20', bank='bank-usd', rate=3.80)
    e = entry_for(f"payment:{d.get('data', {}).get('payment_id')}"); rent['pago_usd_parcial_perdida'] = e
    check('6b. Pago parcial US$ 100 al 3.80: Debe 469903 375 (US$ 100) + 676101 5 / Haber 104102 380',
          st == 201 and e and [(l[0], l[1], l[2], l[3], l[4]) for l in e['lineas']] == [('469903', 375.0, 0.0, 100.0, 0.0), ('676101', 5.0, 0.0, 0.0, 0.0), ('104102', 0.0, 380.0, 0.0, 100.0)], e and e['lineas'])
    check('6b. Saldo US$ 100 (S/ 375) y estado parcial', purchase(a2_id)['payment_status'] == 'partial' and purchase(a2_id)['balance_due'] == 375.0, purchase(a2_id)['balance_due'])
    st, d = pay([{'purchase_id': a2_id, 'amount': 100, 'currency': 'USD'}], 'OP-USD-3', '2026-10-21', bank='bank-usd', rate=3.70)
    e = entry_for(f"payment:{d.get('data', {}).get('payment_id')}"); rent['pago_usd_saldo_ganancia'] = e
    check('6b. Pago del saldo US$ 100 al 3.70: Debe 469903 375 (US$ 100) / Haber 776101 5 + 104102 370',
          st == 201 and e and sorted([(l[0], l[1], l[2], l[3], l[4]) for l in e['lineas']]) == sorted([('469903', 375.0, 0.0, 100.0, 0.0), ('776101', 0.0, 5.0, 0.0, 0.0), ('104102', 0.0, 370.0, 0.0, 100.0)]), e and e['lineas'])
    check('6b. Alquiler USD pagado', purchase(a2_id)['payment_status'] == 'paid')

    # Sin respaldo: si 469903 no acepta movimiento, el alquiler en dolares no se registra (no cae a 469901 ni 469902)
    with app.app_context():
        from app.models import ChartOfAccount
        acc = ChartOfAccount.query.filter_by(company_id=CID, account_code='469903').first(); acc.accepts_movement = False; db.session.commit()
    st, d = call('post', RENT, {'supplier_id': 'sup-arr1', 'correlative': 'X-1', 'emission_date': '2026-10-05', 'currency': 'USD',
                                'exchange_rate': 3.75, 'amount': 10, 'description': 'x'})
    check('Sin 469903 con movimiento: alquiler en USD rechazado con mensaje de 469903', st == 400 and '469903' in json.dumps(d), (st, d.get('error', {}).get('message') if isinstance(d.get('error'), dict) else d))
    with app.app_context():
        acc = ChartOfAccount.query.filter_by(company_id=CID, account_code='469903').first(); acc.accepts_movement = True; db.session.commit()

    # Anticipos, PLE y registro de compras
    st, d = call('post', f'/api/payments/{CID}/anticipos/apply-to-purchase', {'purchase_id': a1_id, 'application_date': '2026-10-20', 'applications': [{'anticipo_id': 'x', 'amount': 1}]})
    check('Pagar con anticipo un alquiler bloqueado (cancelaria 4212 en vez de 469901)', st == 400 and 'alquiler' in json.dumps(d).lower(), (st, d.get('message')))
    st, d = call('post', f'/api/tax/{CID}/ple/export', {'register_type': 'purchases_register', 'period_year': 2026, 'period_month': 10})
    prev = d.get('data', {})
    check('Registro de Compras / PLE TXT: no incluye alquileres', st == 200 and prev.get('lines_count') == 2 and not any('|AL|' in l for l in prev.get('preview', [])),
          (st, prev.get('lines_count'), prev.get('preview')))

if MODE != 'main':
    with app.app_context():
        from app.models import JournalEntryLine, ChartOfAccount
        n = (JournalEntryLine.query.join(ChartOfAccount, ChartOfAccount.id == JournalEntryLine.chart_account_id)
             .filter(ChartOfAccount.company_id == CID, ChartOfAccount.account_code == '469902').count())
        exists = ChartOfAccount.query.filter_by(company_id=CID, account_code='469902').first() is not None
    check('Ninguna prueba usa 469902 (la cuenta existe en el plan de prueba y tiene 0 lineas)', exists and n == 0, (exists, n))
json.dump({'comun': common, 'alquiler': rent, 'resultados': results}, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('fallas:', sum(1 for r in results if not r['ok']), 'de', len(results))
