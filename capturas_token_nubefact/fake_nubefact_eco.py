"""NubeFact SIMULADA que ECO-devuelve el token recibido (para probar que nunca llega al navegador). Nunca la real.
Uso: python fake_nubefact_eco.py <puerto> <log.jsonl> <escenario.json>
Escenario: {"<serie>-<numero>": {"existe": bool, "aceptada": bool, "send_falla": bool}}"""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT, LOG, ESC = int(sys.argv[1]), sys.argv[2], sys.argv[3]
lock = threading.Lock()
PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = PDF if self.path.endswith('pdf') else (b'<?xml version="1.0"?><Invoice/>' if 'xml' in self.path else b'PK\x03\x04cdr')
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        esc = json.load(open(ESC))
        tok = body.get('TOKEN') or ''
        auth = self.headers.get('Authorization') or ''
        op = body.get('operacion'); doc = f"{body.get('serie')}-{str(body.get('numero')).zfill(6)}"
        with lock:
            open(LOG, 'a').write(json.dumps({'op': op, 'doc': doc, 'path': self.path}) + '\n')
        d = esc.get(doc, {})
        base = f'http://127.0.0.1:{PORT}/doc/{doc}'
        eco = {'token': tok, 'TOKEN': tok, 'Authorization': auth, 'api_key': tok, 'nota_proveedor': f'eco del token recibido {tok} via {auth}'}
        ok_doc = {'tipo_de_comprobante': body.get('tipo_de_comprobante'), 'serie': body.get('serie'), 'numero': body.get('numero'),
                  'enlace': base, 'enlace_del_pdf': base + '.pdf', 'enlace_del_xml': base + '.xml', 'enlace_del_cdr': base + '.cdr',
                  'key': 'KEY-' + doc, 'cadena_para_codigo_qr': 'QR|' + doc, 'codigo_hash': 'HASH' + doc}
        if op == 'consultar_comprobante' or op == 'consultar_guia':
            if d.get('existe'):
                code, out = 200, dict(ok_doc, aceptada_por_sunat=bool(d.get('aceptada', True)), sunat_description=d.get('desc', 'aceptada'), sunat_responsecode='0', anulado=bool(d.get('anulado')), **eco)
                if d.get('sin_campo'):
                    out.pop('aceptada_por_sunat')
                if d.get('http500'):
                    code, out = 500, {'errors': 'Error interno del proveedor'}
            else:
                code, out = 400, dict(errors=f'Documento no existe (token usado: {tok})', codigo=24, **eco)
        elif op == 'generar_anulacion':
            code, out = (200, dict(numero=1, key='BAJA-' + doc, aceptada_por_sunat=True, sunat_ticket_numero='TK1', **eco)) if d.get('existe') \
                else (400, dict(errors=f'El documento no existe o no fue enviado a NubeFacT (token {tok})', codigo=24, **eco))
        elif op in ('generar_comprobante', 'generar_guia'):
            if d.get('send_falla'):
                code, out = 400, dict(errors=f'Error simulado del proveedor; token recibido {tok}', codigo=99, **eco)
            else:
                code, out = 200, dict(ok_doc, aceptada_por_sunat=True, sunat_description='aceptada', **eco)
        else:
            code, out = 400, dict(errors='operacion desconocida', codigo=10, **eco)
        b = json.dumps(out).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
