# SOLO PRUEBA: servidor del ERP con NubeCont SIMULADO (nunca toca produccion ni NubeCont real).
import os, sys, json, threading
BACK, DBF, PORT, LOG = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.environ['DATABASE_URL'] = DBF
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
import app.services.nubecont_service as ns
CREATED = set(); LOCK = threading.Lock()
def mode():
    try: return open(LOG + '.mode').read().strip() or 'ok'
    except Exception: return 'ok'
def occupy():
    try: return [x.strip() for x in open(LOG + '.occupy') if x.strip()]
    except Exception: return []
def fake(url, payload, url_name, company=None):
    op = payload.get('operacion') if isinstance(payload, dict) else None
    key = f"{payload.get('serie')}-{str(payload.get('numero')).zfill(6)}" if isinstance(payload, dict) else ''
    with LOCK:
        for o in occupy(): CREATED.add(o)
        if op == 'generar_guia':
            m = mode()
            with open(LOG, 'a') as f: f.write(json.dumps({'op': op, 'key': key, 'mode': m, 'payload': payload}, default=str) + '\n')
            if m == 'fail' or (m == 'failttt4' and payload.get('serie') == 'TTT4') or (m == 'failnot4' and payload.get('serie') != 'TTT4'):
                return {'ok': False, 'status_code': 400, 'data': {'errors': 'Simulado: NubeCont rechazo la guia'}}
            if key in CREATED:
                return {'ok': False, 'status_code': 400, 'data': {'errors': 'Este documento ya existe en NubeFact'}}
            CREATED.add(key)
            if m == 'timeout':
                return {'ok': False, 'status_code': 0, 'data': {'errors': 'Simulado: Read timed out'}}
            return {'ok': True, 'status_code': 200, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': 'http://simulado/' + key + '.pdf', 'sunat_ticket': 'X'}}
        if op == 'consultar_guia':
            if key in CREATED:
                return {'ok': True, 'status_code': 200, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': 'http://simulado/' + key + '.pdf'}}
            return {'ok': False, 'status_code': 400, 'data': {'errors': 'Simulado: documento no existe'}}
    return {'ok': True, 'status_code': 200, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': '', 'sunat_ticket': 'X'}}
ns._post_json = fake
app = create_app()
app.run(port=PORT, debug=False, threaded=True)
