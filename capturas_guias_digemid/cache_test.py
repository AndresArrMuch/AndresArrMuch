import os, sys, json
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
from flask_jwt_extended import create_access_token
import app.routes.guide_report_routes as gr
ids = json.load(open('/tmp/claude-0/repro/dig/ids.json')); CID = ids['CID']
app = create_app()
with app.app_context(): tok = create_access_token(identity=ids['UID'])
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}
llamadas = []
modo = {'xml': 'falla'}
class R:
    def __init__(s, code, text): s.status_code, s.text = code, text
XML = '<?xml version="1.0"?><DespatchAdvice><cac:DeliveryAddress><cbc:ID>090612</cbc:ID><cbc:Line>LLEGADA</cbc:Line></cac:DeliveryAddress><cac:DespatchAddress><cbc:ID>150132</cbc:ID><cbc:Line>PARTIDA</cbc:Line></cac:DespatchAddress></DespatchAdvice>'
gr.requests.get = lambda url, timeout=15: R(500, '<html>error</html>') if modo['xml'] == 'falla' else (R(406, 'Not Acceptable') if modo['xml'] == '406' else R(200, XML))
def fake(company, wf):
    llamadas.append(wf.guide_correlative)
    return {'ok': True, 'data': {'enlace_del_pdf': 'https://x/p.pdf', 'enlace_del_xml': 'https://x/g.xml'}}
gr.get_guide_document = fake
def pedir():
    d = cl.post(f'/api/guide-reports/{CID}/guide-places', headers=H, json={'guides': [{'workflow_id': ids['G4']}]}).get_json()['data'][ids['G4']]
    return {k: d.get(k) for k in ('ok', 'complete', 'partida', 'llegada', 'motivo')}
print('1 XML responde 500  ->', pedir(), '| consultas a NubeCont:', len(llamadas))
print('2 se repite (no debe venir de memoria) ->', pedir(), '| consultas:', len(llamadas))
modo['xml'] = '406'
print('3 XML responde 406  ->', pedir(), '| consultas:', len(llamadas))
modo['xml'] = 'ok'
print('4 XML ya responde   ->', pedir(), '| consultas:', len(llamadas))
print('5 se repite (ahora SI de memoria) ->', pedir(), '| consultas:', len(llamadas))
