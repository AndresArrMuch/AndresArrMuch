# SOLO PRUEBA: ejecuta diag_guia_nubefact.py con NubeCont simulado. ESCENARIO=406 | sinprefijo | ok
import os, sys, io, base64, zipfile, threading, runpy
from http.server import BaseHTTPRequestHandler, HTTPServer
ESC = os.environ['ESCENARIO']
XML_PREF = ('<?xml version="1.0" encoding="UTF-8"?><DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2" xmlns:cac="urn:x:cac" xmlns:cbc="urn:x:cbc">'
            '<cbc:UBLVersionID>2.1</cbc:UBLVersionID><cbc:ID>TTT4-000002</cbc:ID><cac:Shipment><cac:Delivery><cac:DeliveryAddress><cbc:ID schemeAgencyName="PE:INEI">150120</cbc:ID>'
            '<cac:AddressLine><cbc:Line>AV. CLIENTE 2 MAGDALENA</cbc:Line></cac:AddressLine></cac:DeliveryAddress><cac:Despatch><cac:DespatchAddress><cbc:ID schemeAgencyName="PE:INEI">150132</cbc:ID>'
            '<cac:AddressLine><cbc:Line>URB. CANTO GRANDE AV. SANTA ROSA 550</cbc:Line></cac:AddressLine></cac:DespatchAddress></cac:Despatch></cac:Delivery></cac:Shipment></DespatchAdvice>')
XML_SIN = XML_PREF.replace('cac:', '').replace('cbc:', '').replace('xmlns:cac="urn:x:cac" xmlns:cbc="urn:x:cbc"', '')
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        ua = self.headers.get('User-Agent', '')
        if ESC == '406' and 'Mozilla' not in ua:
            self.send_response(406); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(b'<html>Not Acceptable</html>'); return
        self.send_response(200); self.send_header('Content-Type', 'application/xml'); self.end_headers(); self.wfile.write(XML_PREF.encode())
    def log_message(self, *a): pass
srv = HTTPServer(('127.0.0.1', 5631), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ['NO_PROXY'] = '127.0.0.1'
sys.path.insert(0, os.environ['BACK'])
import warnings; warnings.filterwarnings('ignore')
import app.services.nubecont_service as ns, app.routes.guide_report_routes as gr
def fake(company, wf):
    data = {'aceptada_por_sunat': True, 'enlace_del_pdf': 'https://www.nubefact.com/guia/abc.pdf', 'token_interno': 'SECRETO123', 'sunat_description': 'ok', 'enlace': 'https://www.nubefact.com/guia/abc'}
    if ESC in ('406', 'ok'):
        data['enlace_del_xml'] = 'http://127.0.0.1:5631/guia/abc.xml?key=SECRETOQUERY'
    else:
        b = io.BytesIO(); z = zipfile.ZipFile(b, 'w'); z.writestr('20000000001-09-TTT4-2.xml', XML_SIN); z.close()
        data['xml_zip_base64'] = base64.b64encode(b.getvalue()).decode()
    return {'ok': True, 'status_code': 200, 'data': data, 'url': 'https://api.nubecont.test/x?token=SECRETOURL'}
ns.get_guide_document = fake; gr.get_guide_document = fake
sys.argv = ['diag', 'TTT4-000002', '--empresa', 'FIKA']
runpy.run_path(os.environ['BACK'] + '/scripts/diag_guia_nubefact.py', run_name='__main__')
