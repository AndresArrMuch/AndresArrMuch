"""NubeFact SIMULADA que guarda el payload recibido (sin el TOKEN). Nunca la real.
Uso: python fake_capture.py <puerto> <capturas.jsonl> <modo.json>   modo: {"rechazar": bool, "mensaje": "..."}"""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT, LOG, MODE = int(sys.argv[1]), sys.argv[2], sys.argv[3]
lock = threading.Lock()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = b'%PDF-1.4\n%%EOF\n'; self.send_response(200); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        body.pop('TOKEN', None)
        mode = json.load(open(MODE))
        with lock:
            open(LOG, 'a').write(json.dumps(body, ensure_ascii=False) + '\n')
        op = body.get('operacion'); doc = f"{body.get('serie')}-{str(body.get('numero')).zfill(6)}"
        if op == 'generar_guia' and mode.get('rechazar'):
            code, out = 400, {'errors': mode.get('mensaje'), 'codigo': mode.get('codigo', 20)}
        elif op == 'consultar_guia' and mode.get('rechazar'):
            code, out = 400, {'errors': 'Documento no existe', 'codigo': 24}
        elif op in ('generar_guia', 'consultar_guia'):
            base = f'http://127.0.0.1:{PORT}/doc/{doc}'
            code, out = 200, {'serie': body.get('serie'), 'numero': body.get('numero'), 'aceptada_por_sunat': True, 'sunat_description': 'aceptada',
                              'enlace': base, 'enlace_del_pdf': base + '.pdf', 'enlace_del_xml': base + '.xml', 'enlace_del_cdr': base + '.cdr', 'key': 'K-' + doc}
        else:
            code, out = 400, {'errors': 'Documento no existe', 'codigo': 24}
        b = json.dumps(out).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
