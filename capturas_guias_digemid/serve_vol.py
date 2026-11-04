# SOLO PRUEBA: servidor con NubeFact simulado (0.4 s por guia). Las guias TTT4-...x5 tienen PDF pero su XML falla (500).
import os, sys, time, threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
BACK, DBP, PORT = sys.argv[1], sys.argv[2], int(sys.argv[3])
XML = ('<?xml version="1.0"?><DespatchAdvice><cac:Shipment><cac:Delivery><cac:DeliveryAddress><cbc:ID>090612</cbc:ID><cac:AddressLine><cbc:Line>LLEGADA {g}</cbc:Line></cac:AddressLine></cac:DeliveryAddress>'
       '<cac:Despatch><cac:DespatchAddress><cbc:ID>150132</cbc:ID><cac:AddressLine><cbc:Line>JR. HUALLAGA 767 Int 111</cbc:Line></cac:AddressLine></cac:DespatchAddress></cac:Despatch></cac:Delivery></cac:Shipment></DespatchAdvice>')
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        g = self.path.rsplit('/', 1)[-1].replace('.xml', '')
        if g.endswith('5'):
            self.send_response(500); self.end_headers(); self.wfile.write(b'<html>error</html>'); return
        self.send_response(200); self.send_header('Content-Type', 'application/xml'); self.end_headers(); self.wfile.write(XML.format(g=g).encode())
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', PORT + 100), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ['NO_PROXY'] = '127.0.0.1'; os.environ['no_proxy'] = '127.0.0.1'
os.environ['DATABASE_URL'] = DBP
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
app = create_app()
import app.routes.guide_report_routes as gr
def fake_doc(company, wf):
    time.sleep(0.4)
    g = f'{wf.guide_series}-{wf.guide_correlative}'
    return {'ok': True, 'status_code': 200, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': f'https://nube.test/pdf/{g}.pdf', 'enlace_del_xml': f'http://127.0.0.1:{PORT + 100}/xml/{g}.xml'}}
gr.get_guide_document = fake_doc
app.run(port=PORT, debug=False, threaded=True)
