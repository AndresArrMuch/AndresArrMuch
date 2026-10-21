"""Pruebas del envio a NubeFact (SIMULADO). Uso: api_test.py <backend> <db> <dir_estado> <salida.json> <modo main|rama>"""
import json, os, sys, time, warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')
B, DB, D, OUT, MODO = sys.argv[1:6]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
os.environ['NUBECONT_TIMEOUT'] = '2'
os.environ['CEA_REINTENTO_AUTOMATICO'] = '0'
sys.path.insert(0, B); os.chdir(B)
from app import create_app, db
from app.models import Sale, JournalEntry, Company
from app.models.user import User
from flask_jwt_extended import create_access_token
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
URL_OK, URL_CAIDA = 'http://127.0.0.1:8941/api/ruta-secreta-xyz', 'http://127.0.0.1:8949/api/ruta-secreta-xyz'
app = create_app('development'); cl = app.test_client()
R = {}
def H(email):
    with app.app_context():
        return {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email=email, company_id=F).first().id)}
VEN, GER = H('vendedor.fika@t.pe'), H('gerente.fika@t.pe')
def set_url(u):
    with app.app_context():
        c = Company.query.get(F); c.nubecont_api_url = u; c.nubecont_api_token = 'TKN-SIMULADO-123'; db.session.commit()
def esc(doc, mode):
    e = json.load(open(f'{D}/escenario.json')); e[doc] = mode; json.dump(e, open(f'{D}/escenario.json', 'w'))
def J(r):
    j = r.get_json(silent=True) or {}
    err = j.get('error') if isinstance(j.get('error'), dict) else {}
    txt = r.get_data(as_text=True)
    return {'http': r.status_code, 'codigo': err.get('code'), 'mensaje': (err.get('message') or j.get('message') or '')[:220],
            'tiene_token': 'TKN-SIMULADO-123' in txt, 'tiene_ruta': 'ruta-secreta-xyz' in txt}
def venta(total=118.0, confirm=False, h=VEN, series='F020'):
    body = dict(customer_id='cli-1', document_type='01', series=series, emission_date='2026-10-22', due_date='2026-10-22',
                currency='PEN', lines=[dict(description='SERVICIO PRUEBA', quantity=1, unit='ZZ', unit_price=total, igv_percentage=18)],
                price_includes_igv=True)
    if confirm: body['confirmar_repetida'] = True
    r = cl.post(f'/api/sales/{F}', json=body, headers=h)
    j = r.get_json() or {}
    return r, (j.get('data') or {})
def estado(sid):
    with app.app_context():
        s = Sale.query.get(sid)
        je = JournalEntry.query.filter(JournalEntry.company_id == F, JournalEntry.gloss.like(f'%{s.document_number}%')).count()
        out = {'doc': s.document_number, 'status': s.status, 'sunat_status': s.sunat_status or '', 'ticket': bool(s.sunat_ticket),
               'pdf': bool(s.pdf_path), 'xml': bool(s.xml_path), 'cdr': bool(s.cdr_path), 'contable': s.accounting_status, 'asientos': je}
        try:
            from app.models.electronic_send_attempt import ElectronicSendAttempt
            out['intentos'] = [[a.operation, a.origin, a.outcome, a.http_status, (a.provider_message or a.error_code or '')[:80]]
                               for a in ElectronicSendAttempt.query.filter_by(sale_id=sid).order_by(ElectronicSendAttempt.started_at).all()]
        except Exception:
            out['intentos'] = 'no existe la tabla (main)'
        return out
def nf(doc):
    return [l for l in (json.loads(x) for x in open(f'{D}/log.jsonl')) if l['doc'] == doc]
def send(sid, body=None, h=VEN):
    return J(cl.post(f'/api/sales/{F}/{sid}/electronic/send', json=body or {}, headers=h))
def post(sid):
    return J(cl.post(f'/api/sales/{F}/{sid}/post', headers=VEN))

set_url(URL_OK)
# 1) Venta normal: NubeFact acepta
r, s1 = venta(118.0); esc(s1['document_number'], 'ok')
R['1_normal'] = {'envio': send(s1['id']), 'post': post(s1['id'])}
R['1_normal'].update(estado=estado(s1['id']), nubefact=nf(s1['document_number']))

# 2) NubeFact caido (no hay red): queda registrada y no enviada; luego "Enviar a SUNAT"
set_url(URL_CAIDA)
r, s2 = venta(236.0)
R['2_caido'] = {'envio': send(s2['id'])}
R['2_caido']['estado_tras_fallo'] = estado(s2['id'])
set_url(URL_OK); esc(s2['document_number'], 'ok')
if MODO == 'rama':
    R['2_caido']['reintento_boton'] = J(cl.post(f'/api/sales/{F}/{s2["id"]}/electronic/retry', json={}, headers=VEN))
R['2_caido']['estado_final'] = estado(s2['id']); R['2_caido']['nubefact'] = nf(s2['document_number'])

# 3) Tiempo agotado pero NubeFact SI lo recibio: no debe reenviarse ni quedar "sin enviar"
r, s3 = venta(354.0); esc(s3['document_number'], 'timeout_recibido')
R['3_timeout_recibido'] = {'envio': send(s3['id']), 'estado': estado(s3['id']), 'nubefact': nf(s3['document_number'])}

# 4) Rechazo de NubeFact por datos: motivo guardado
r, s4 = venta(472.0); esc(s4['document_number'], 'rechazo')
R['4_rechazo'] = {'envio': send(s4['id']), 'estado': estado(s4['id'])}

# 5) Aceptacion pendiente (aceptada_por_sunat false): no debe quedar 'aceptada'
r, s5 = venta(590.0); esc(s5['document_number'], 'ok_pendiente')
R['5_pendiente_sunat'] = {'envio': send(s5['id']), 'estado': estado(s5['id'])}
if MODO == 'rama':
    json.dump([s5['document_number']], open(f'{D}/aceptar.json', 'w'))
    R['5_pendiente_sunat']['consultar'] = J(cl.get(f'/api/sales/{F}/{s5["id"]}/electronic/status', headers=VEN))
    R['5_pendiente_sunat']['estado_tras_consulta'] = estado(s5['id'])

# 6) Venta repetida: la primera no llego a NubeFact y se intenta crear otra igual
set_url(URL_CAIDA)
r, s6 = venta(4250.0)
R['6_repetida'] = {'envio_1': send(s6['id'])}
r2, s6b = venta(4250.0)
R['6_repetida']['crear_otra_igual'] = J(r2)
r3, s6c = venta(4250.0, confirm=True)
R['6_repetida']['crear_con_confirmacion'] = J(r3)
set_url(URL_OK)
if MODO == 'rama' and s6c.get('id'):
    esc(s6['document_number'], 'ok'); esc(s6c['document_number'], 'ok')
    R['6_repetida']['enviar_la_primera'] = J(cl.post(f'/api/sales/{F}/{s6["id"]}/electronic/retry', json={}, headers=VEN))
    R['6_repetida']['enviar_la_segunda_vendedor'] = J(cl.post(f'/api/sales/{F}/{s6c["id"]}/electronic/retry', json={}, headers=VEN))
    R['6_repetida']['enviar_la_segunda_gerente_confirma'] = J(cl.post(f'/api/sales/{F}/{s6c["id"]}/electronic/retry', json={'confirmar_gemelo': True}, headers=GER))
    R['6_repetida']['estado_1'] = estado(s6['id']); R['6_repetida']['estado_2'] = estado(s6c['id'])

# 7) Consultar un documento que nunca llego (como B030-000016): no cambia sunat_status
r, s7 = venta(14.0)
with app.app_context():
    x = Sale.query.get(s7['id']); x.sunat_status = None; db.session.commit()
R['7_consulta_no_existe'] = {'consultar': J(cl.get(f'/api/sales/{F}/{s7["id"]}/electronic/status', headers=VEN)), 'estado': estado(s7['id'])}

# 8) NC sobre una factura anulada
with app.app_context():
    an = Sale.query.filter_by(company_id=F, document_number='F001-000002').first(); an_id = an.id
R['8_nc_sobre_anulada'] = J(cl.post(f'/api/sales/{F}/{an_id}/credit-note', json={'notes': 'prueba'}, headers=GER))

# 9) Lista de pendientes y resumen de motivos
if MODO == 'rama':
    pv = cl.get(f'/api/sales/{F}/electronic/pending', headers=VEN); pg = cl.get(f'/api/sales/{F}/electronic/pending', headers=GER)
    R['9_lista'] = {'vendedor': J(pv), 'gerente_http': pg.status_code,
                    'gerente_docs': [[d['document_number'], d['estado_envio'], d['motivo'][:60], d['intentos'], d['posible_repetida_de']] for d in (pg.get_json() or {}).get('data', {}).get('documentos', [])][:20]}
    sm = cl.post(f'/api/sales/{F}/electronic/attempts-summary', json={'sale_ids': [s4['id'], s7['id']]}, headers=VEN)
    R['9_resumen_motivos'] = {k[:8]: v for k, v in ((sm.get_json() or {}).get('data') or {}).items()}
    with app.app_context():
        from app.models.electronic_send_attempt import ElectronicSendAttempt
        txt = json.dumps([a.to_dict() for a in ElectronicSendAttempt.query.all()])
        R['10_tabla_intentos'] = {'filas': ElectronicSendAttempt.query.count(), 'tiene_token': 'TKN-SIMULADO-123' in txt, 'tiene_ruta': 'ruta-secreta-xyz' in txt}

# 11) Reintento automatico (ultimas 24 h)
if MODO == 'rama':
    from sqlalchemy import text as _t
    from app.services.electronic_auto_retry import run_cycle
    set_url(URL_CAIDA)
    r, a1 = venta(101.0)                                   # no llega: lo retomara el reintento
    send(a1['id'])
    r, a2 = venta(102.0)                                   # no llega y es de hace 2 dias: no se toca
    send(a2['id'])
    r, a3 = venta(103.0)                                   # se pasa a serie E (portal SUNAT): no se toca
    r, a5 = venta(105.0)                                   # recien creada (< 3 min): no se toca
    nc = cl.post(f'/api/sales/{F}/{s1["id"]}/credit-note', json={'notes': 'devolucion'}, headers=GER).get_json()['data']
    R['11_auto'] = {'nc_envio_fallido': send(nc['id'], {'credit_note_reason_code': '01', 'credit_note_reason_text': 'Anulacion'}, h=GER)}
    set_url(URL_OK)
    r, a4 = venta(104.0); esc(a4['document_number'], 'ok_pendiente'); send(a4['id'])   # recibido, SUNAT pendiente
    json.dump([a4['document_number']], open(f'{D}/aceptar.json', 'w'))
    with app.app_context():
        db.session.execute(_t("UPDATE sale SET created_at = now() at time zone 'utc' - interval '10 minutes' WHERE id IN (:a,:b,:c,:d,:n,:r)"),
                           {'a': a1['id'], 'b': a3['id'], 'c': a4['id'], 'd': s4['id'], 'n': nc['id'], 'r': s1['id']})
        db.session.execute(_t("UPDATE sale SET created_at = now() at time zone 'utc' - interval '2 days' WHERE id = :x"), {'x': a2['id']})
        db.session.execute(_t("UPDATE sale SET series='E001', document_number='E001-' || correlative WHERE id = :x"), {'x': a3['id']})
        db.session.execute(_t("UPDATE sale SET pdf_path=NULL, cdr_path=NULL WHERE id = :x"), {'x': s1['id']})
        db.session.commit()
        R['11_auto']['simulado'] = run_cycle(dry_run=True, company_ids=[F])
        # candado: si otro proceso ya esta reintentando, este no hace nada
        hold = db.engine.connect(); hold.execute(_t('SELECT pg_advisory_lock(7302, 0)')); hold.commit()
        R['11_auto']['con_otro_proceso'] = run_cycle(company_ids=[F])
        hold.execute(_t('SELECT pg_advisory_unlock(7302, 0)')); hold.commit(); hold.close()
        R['11_auto']['real'] = run_cycle(company_ids=[F])
        R['11_auto']['segunda_pasada'] = run_cycle(company_ids=[F])
        R['11_auto']['tercera_y_cuarta'] = run_cycle(company_ids=[F]) + run_cycle(company_ids=[F])
    R['11_auto']['estados'] = {k: estado(v['id']) for k, v in (('a1_24h', a1), ('a2_2dias', a2), ('a3_serieE', a3), ('a4_pendiente', a4), ('a5_recien', a5), ('nc', nc), ('s1_sin_pdf', s1), ('s4_rechazo', s4))}
    R['11_auto']['nubefact_envios_a1'] = nf(a1['document_number'])
R['ids'] = {'s2': s2['id'], 's4': s4['id'], 's6': s6['id']}
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('ok')
