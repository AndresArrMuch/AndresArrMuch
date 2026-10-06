# Cobros: main vs rama. MODO=main|rama, CASO=...  (lo que envia la pantalla de cada version)
import json
from base import *
from app.models.bank import PaymentLine
MODO, CASO = os.environ['MODO'], os.environ['CASO']
def out(**kw): print(json.dumps(dict({'srv': MODO, 'caso': CASO}, **kw), ensure_ascii=False))
def venta_usd(corr, total, rate):
    sid = venta(corr, total, 'USD')
    with app.app_context():
        s = db.session.get(Sale, sid); s.exchange_rate = rate; db.session.commit()
    return sid
def provision(sid):
    # Provision como la de produccion: la venta en USD carga los dolares en la columna de soles
    from app.models.journal_entry import JournalEntryLine
    with app.app_context():
        s = db.session.get(Sale, sid); acc = {v: k for k, v in codes.items()}
        e = JournalEntry(company_id=CID, fiscal_period_id=P10, entry_number='000900', entry_date=s.emission_date, gloss=f'Por la provision de la Factura {s.document_number}', entry_type='sale', currency=s.currency, exchange_rate=s.exchange_rate, status='approved')
        e.lines.append(JournalEntryLine(company_id=CID, chart_account_id=acc['121201'], debit_amount=s.total, credit_amount=0))
        e.lines.append(JournalEntryLine(company_id=CID, chart_account_id=acc['701101'], debit_amount=0, credit_amount=s.total))
        db.session.add(e); db.session.commit()
def msg(r):
    j = r.get_json() or {}; return j.get('message') or (j.get('error') or {}).get('message')
def cobrar(pairs, ref, comm=0.0, bank=None, date='2026-10-05', rate=None):
    # Modal individual / varios: el monto aplicado incluye la comision (lo recibido + comision)
    body = dict(bank_account_id=bank or BPEN, payment_date=date, payment_method='transfer', reference_number=ref,
                notes=(f'Comision: {comm:.2f}' if comm else ''), items=[dict(sale_id=s, amount=a) for s, a in pairs])
    if MODO == 'rama':
        body['commission_amount'] = comm
        if rate: body['exchange_rate'] = rate
    r = cl.post(f'/api/payments/{CID}/collect', headers=H, json=body)
    if r.status_code == 201 and comm:   # el modal crea el movimiento de COMISIONES
        cl.post(f'/api/banks/{CID}/transactions', headers=H, json=dict(account_id=BCOM, transaction_date=date, transaction_type='deposit', amount=comm, reference_number=ref, description='Comision de cobro', related_document_type='sale', related_document_id=pairs[0][0]))
    return r.status_code, msg(r), (r.get_json().get('data') or {}).get('payment_id')
def editar(pid, sid, amount, ref, comm=0.0):
    body = dict(items=[dict(document_type='sale', document_id=sid, amount_applied=amount, currency='PEN')], reference_number=ref,
                notes=(f'Comision: {comm:.2f}' if comm else ''), payment_date='2026-10-05')
    if MODO == 'rama': body['commission_amount'] = comm
    r = cl.put(f'/api/payments/{CID}/{pid}', headers=H, json=body)
    if r.status_code < 300 and comm and MODO == 'main':   # main: el modal crea OTRO movimiento de COMISIONES al editar
        cl.post(f'/api/banks/{CID}/transactions', headers=H, json=dict(account_id=BCOM, transaction_date='2026-10-05', transaction_type='deposit', amount=comm, reference_number=ref, description='Comision de cobro', related_document_type='sale', related_document_id=sid))
    return r.status_code, msg(r)
def periodos():
    with app.app_context():
        return [f"{e.entry_number} periodo {db.session.get(FiscalPeriod, e.fiscal_period_id).period_month}/2026 fecha {e.entry_date}" for e in JournalEntry.query.filter_by(entry_type='payment').order_by(JournalEntry.created_at).all()]
def ventas(ids): return [doc(Sale, i) for i in ids]
def lineas(pid):
    with app.app_context(): return [(l.document_number, float(l.amount_applied)) for l in PaymentLine.query.filter_by(payment_id=pid).all()]
def todo(ids, pid=None):
    return dict(ventas=ventas(ids), lineas=lineas(pid) if pid else None, asientos=[(a['asiento'], a['cuadra'], a['lineas']) for a in asientos()], periodos=periodos(),
                banco=banco(BPEN) + banco(BUSD), comisiones=[t[1] for t in banco(BCOM)])

if CASO == 'comision':
    v = venta('1', 1000.0); s, m, pid = cobrar([(v, 1000.0)], 'OP1', comm=10.0)
    out(paso='recibido 990 + comision 10 (venta 1000)', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'cerrado':
    v = venta('1', 500.0); s, m, pid = cobrar([(v, 500.0)], 'OP2', date='2026-09-15')
    out(paso='cobro con fecha 15/09 (setiembre CERRADO)', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'fecha_imposible':
    v = venta('1', 429.0); s, m, pid = cobrar([(v, 429.0)], 'OP3', date='0009-10-09')
    out(paso='cobro con fecha 09/10/0009', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'usd_banco_usd':
    v = venta_usd('1', 118.0, 3.50); s, m, pid = cobrar([(v, 118.0)], 'OPU', bank=BUSD, rate=3.39)
    out(paso='venta US$118 TC 3.50, cobro a cuenta en US$ TC compra 3.39', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'usd_banco_pen':
    v = venta_usd('1', 118.0, 3.50); s, m, pid = cobrar([(v, 118.0)], 'OPU2', bank=BPEN, rate=3.39)
    out(paso='venta US$118 TC 3.50, cobro a cuenta en SOLES TC 3.39', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'usd_comision':
    v = venta_usd('1', 1000.0, 3.50); s, m, pid = cobrar([(v, 1000.0)], 'OPU3', comm=15.0, bank=BUSD, rate=3.39)
    out(paso='venta US$1000 TC 3.50, recibido US$985 + comision US$15 en cuenta US$, TC 3.39', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'usd_provision_produccion':
    v = venta_usd('1', 118.0, 3.50); provision(v); s, m, pid = cobrar([(v, 118.0)], 'OPU4', bank=BUSD, rate=3.39)
    out(paso='venta US$118 TC 3.50 con provision como produccion (12 Debe 118), cobro a cuenta US$ TC 3.39', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'mixto':
    v1 = venta('1', 100.0); v2 = venta_usd('2', 50.0, 3.5); s, m, pid = cobrar([(v1, 100.0), (v2, 50.0)], 'OPM')
    out(paso='una venta en soles y otra en dolares juntas', http=s, mensaje=m, **todo([v1, v2], pid))
elif CASO == 'comisiones_como_banco':
    v = venta('1', 2006.0); s, m, pid = cobrar([(v, 2006.0)], 'OPC', bank=BCOM)
    out(paso='cobro registrado en la cuenta COMISIONES', http=s, mensaje=m, **todo([v], pid))
elif CASO == 'editar_varios':
    v1 = venta('1', 500.0); v2 = venta('2', 300.0); v3 = venta('3', 200.0)
    s, m, pid = cobrar([(v1, 500.0), (v2, 300.0), (v3, 200.0)], 'OPX')
    out(paso='cobro de 3 ventas (500+300+200)', http=s, **todo([v1, v2, v3], pid))
    out(paso='Editar desde F001-1: 500 -> 400', r=editar(pid, v1, 400.0, 'OPX'), **todo([v1, v2, v3], pid))
elif CASO == 'editar_comision':
    v = venta('1', 1000.0); s, m, pid = cobrar([(v, 1000.0)], 'OPE', comm=10.0)
    out(paso='cobro 990 + comision 10', http=s, **todo([v], pid))
    out(paso='Editar sin cambiar nada (modal: monto 990 + comision 10)', r=editar(pid, v, 1000.0, 'OPE', comm=10.0), **todo([v], pid))
    out(paso='Editar otra vez: comision 12 (recibido 988)', r=editar(pid, v, 1000.0, 'OPE', comm=12.0), **todo([v], pid))
elif CASO == 'eliminar_cerrado':
    v = venta('1', 300.0); s, m, pid = cobrar([(v, 300.0)], 'OPD')
    with app.app_context():
        for p in FiscalPeriod.query.filter_by(company_id=CID).all(): p.status = 'closed'
        db.session.commit()
    r = cl.post(f'/api/payments/{CID}/{pid}/void', headers=H)
    out(paso='cobro de octubre; se cierran los periodos; Eliminar', http=r.status_code, mensaje=msg(r), **todo([v], pid))
elif CASO == 'eliminar_abierto':
    v = venta('1', 300.0); s, m, pid = cobrar([(v, 300.0)], 'OPD', comm=5.0)
    r = cl.post(f'/api/payments/{CID}/{pid}/void', headers=H)
    out(paso='cobro con comision en periodo abierto; Eliminar', http=r.status_code, mensaje=msg(r), **todo([v], pid))
elif CASO == 'borrar_mov_banco':
    v = venta('1', 300.0); s, m, pid = cobrar([(v, 300.0)], 'OPB')
    with app.app_context(): txid = BankTransaction.query.filter_by(account_id=BPEN, reference_number='OPB').first().id
    r = cl.delete(f'/api/banks/{CID}/transactions/{txid}', headers=H)
    with app.app_context(): p = db.session.get(PaymentRecord, pid); est = p.status if p else 'BORRADO'
    out(paso='Transacciones: borrar el deposito del cobro', http=r.status_code, mensaje=msg(r), cobro=est, **todo([v], pid))
def a_legado(pid, mes_fecha=None):
    # Deja el cobro como los registrados hoy en produccion: asiento en 1/2026, comision solo en la nota,
    # banco y asiento con la comision mal (104 D 1000 / 12 H 1010 / 639 D 10)
    from app.models.journal_entry import JournalEntryLine
    with app.app_context():
        p1 = FiscalPeriod.query.filter_by(company_id=CID, period_month=1).first()
        e = JournalEntry.query.filter_by(attachment_path=f'payment:{pid}').first(); e.fiscal_period_id = p1.id
        pay = db.session.get(PaymentRecord, pid); pay.commission_amount = None
        if mes_fecha: pay.payment_date = mes_fecha; e.entry_date = mes_fecha
        acc = {v: k for k, v in codes.items()}
        for l in e.lines:
            if codes[l.chart_account_id] == '104101': l.debit_amount = 1000
            if codes[l.chart_account_id] == '121201': l.credit_amount = 1010
        BankTransaction.query.filter_by(related_document_id=pid).first().amount = 1000
        db.session.commit()
if CASO == 'legado_editar':
    v = venta('1', 1000.0); s, m, pid = cobrar([(v, 1000.0)], 'OPL', comm=10.0); a_legado(pid)
    out(paso='cobro antiguo (asiento en 1/2026, comision mal)', **todo([v], pid))
    out(paso='Editar sin cambiar nada', r=editar(pid, v, 1000.0, 'OPL', comm=10.0), **todo([v], pid))
elif CASO == 'legado_fecha_cerrada':
    v = venta('1', 1000.0); s, m, pid = cobrar([(v, 1000.0)], 'OPL', comm=10.0); a_legado(pid, D(2026, 9, 15))
    r = cl.post(f'/api/payments/{CID}/{pid}/void', headers=H)
    out(paso='cobro antiguo de fecha 15/09 (setiembre cerrado) con asiento en 1/2026 (abierto): Eliminar', http=r.status_code, mensaje=msg(r), **todo([v], pid))
    out(paso='... y Editar', r=editar(pid, v, 1000.0, 'OPL', comm=10.0), **todo([v], pid))
