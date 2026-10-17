"""NubeFact SIMULADO para pruebas (nunca se llama al real). Uso: python fake_nubefact.py <puerto> <log.jsonl> <escenario.json>
Escenario: {"<serie>-<numero>": {"existe": bool, "aceptada": bool}, "_demora": segundos, "_send_falla": bool}
Responde a las operaciones de NubeFact: generar_comprobante, consultar_comprobante, generar_anulacion."""
import json, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT, LOG, ESC = int(sys.argv[1]), sys.argv[2], sys.argv[3]
lock = threading.Lock()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        esc = json.load(open(ESC))
        op = body.get('operacion'); doc = f"{body.get('serie')}-{str(body.get('numero')).zfill(6)}"
        with lock:
            open(LOG, 'a').write(json.dumps({'t': time.time(), 'op': op, 'doc': doc}) + '\n')
        time.sleep(float(esc.get('_demora', 0)))
        d = esc.get(doc, {})
        if op == 'consultar_comprobante':
            if d.get('existe'):
                code, out = 200, {'tipo_de_comprobante': 1, 'serie': body.get('serie'), 'numero': body.get('numero'), 'aceptada_por_sunat': bool(d.get('aceptada')),
                                  'sunat_description': 'La Factura numero %s, ha sido aceptada' % doc if d.get('aceptada') else 'en proceso', 'key': 'KEY-' + doc,
                                  'enlace': 'http://127.0.0.1:%d/doc/%s' % (PORT, doc)}
            else:
                code, out = 400, {'errors': 'Documento no existe', 'codigo': 24}
        elif op == 'generar_anulacion':
            code, out = (200, {'numero': 1, 'key': 'BAJA-' + doc, 'aceptada_por_sunat': True}) if d.get('existe') else (400, {'errors': 'El documento no existe o no fue enviado a NubeFacT', 'codigo': 24})
        else:   # generar_comprobante
            if esc.get('_send_falla'):
                code, out = 400, {'errors': 'Error simulado del proveedor', 'codigo': 99}
            else:
                code, out = 200, {'aceptada_por_sunat': True, 'sunat_description': 'aceptada', 'key': 'KEY-' + doc}
        b = json.dumps(out).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
