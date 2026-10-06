import os, sys, json
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from flask_jwt_extended import create_access_token
ids = json.load(open('/tmp/claude-0/repro/dig/ids.json'))
app = create_app()
import app.routes.guide_report_routes as gr
# NubeCont simulado: devuelve un XML UBL 2.1 con partida y llegada (SOLO PRUEBA)
llamadas = []
def fake_doc(company, wf):
    llamadas.append(f'{wf.guide_series}-{wf.guide_correlative}')
    xml = ('<DespatchAdvice><cac:Shipment><cac:Delivery><cac:DeliveryAddress><cbc:ID schemeAgencyName="PE:INEI">150131</cbc:ID>'
           '<cac:AddressLine><cbc:Line><![CDATA[Jr. Llegada Real 77, San Isidro]]></cbc:Line></cac:AddressLine></cac:DeliveryAddress>'
           '<cac:Despatch><cac:DespatchAddress><cbc:ID schemeAgencyName="PE:INEI">150103</cbc:ID><cac:AddressLine><cbc:Line>Calle Sanitaria 20, Lima</cbc:Line>'
           '</cac:AddressLine></cac:DespatchAddress></cac:Despatch></cac:Delivery></cac:Shipment></DespatchAdvice>')
    import base64, io, zipfile
    b = io.BytesIO(); z = zipfile.ZipFile(b, 'w'); z.writestr('g.xml', xml); z.close()
    return {'ok': True, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': f'https://nube/pdf/{wf.guide_series}-{wf.guide_correlative}.pdf', 'xml_zip_base64': base64.b64encode(b.getvalue()).decode()}}
gr.get_guide_document = fake_doc
with app.app_context():
    tok = create_access_token(identity=ids['UID'], additional_claims={'company_id': ids['CID']})
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}; CID = ids['CID']
def show(t, r):
    j = r.get_json(); print('==', t, r.status_code); return j
j = show('sale-guides setiembre', cl.get(f'/api/guide-reports/{CID}/sale-guides?from=2026-09-01&to=2026-09-30', headers=H))
names = {ids['S1']: 'F001-1', ids['S2']: 'F001-2', ids['S3']: 'F001-3'}
for k, v in j['data'].items(): print(' ', names.get(k, k), [(g['guide_number'], g['dispatch_date'], g['state']) for g in v])
print('  F001-3 (sin guia) en la respuesta:', ids['S3'] in j['data'])
def rep(t, q):
    j = show(t, cl.get(f'/api/guide-reports/{CID}/digemid-guides?{q}', headers=H))
    for r in j['data']['rows']:
        print('  ', r['fecha'], r['guia'], r['tipo_guia'], '|', r['factura'] or '-', '|', r['cliente'] or '-', '|', r['codigo'], r['cantidad'], r['unidad'], '| salida:', r['almacen_salida'], '| destino:', r['almacen_destino'] or '-', '| RS:', r['registro_sanitario'] or '-', 'lote:', r['lote'] or '-', 'venc:', r['vencimiento'] or '-', '|', r['estado'])
    return j
rep('DIGEMID por defecto (solo productos DIGEMID, con anuladas, sin traslados)', 'from=2026-09-01&to=2026-09-30')
rep('sin anuladas', 'from=2026-09-01&to=2026-09-30&include_voided=0')
rep('serie TTT4', 'series=TTT4')
rep('con traslados', 'include_transfers=1&include_voided=0')
rep('producto D002 (texto)', 'product=d002')
rep('cliente BOTICA', 'customer=botica')
rep('estado facturada', 'status=facturada')
rep('todos los productos (no solo DIGEMID)', 'only_digemid=0&include_voided=0')
j = show('guide-places (G1, G4, T1, uno ajeno)', cl.post(f'/api/guide-reports/{CID}/guide-places', headers=H, json={'guides': [{'workflow_id': ids['G1']}, {'workflow_id': ids['G4']}, {'transfer_id': ids['T1']}, {'workflow_id': 'no-existe'}]}))
for k, v in j['data'].items(): print('  ', v)
show('guide-places otra vez (cache, sin llamar a NubeCont)', cl.post(f'/api/guide-reports/{CID}/guide-places', headers=H, json={'guides': [{'workflow_id': ids['G1']}]}))
print('   llamadas a NubeCont:', llamadas)
show('guide-places 11 guias (tope)', cl.post(f'/api/guide-reports/{CID}/guide-places', headers=H, json={'guides': [{'workflow_id': ids['G1']}] * 11}))
show('otra empresa (sin acceso)', cl.get(f'/api/guide-reports/{ids["C2"]}/digemid-guides', headers=H))
show('sin sesion', cl.get(f'/api/guide-reports/{CID}/digemid-guides'))
