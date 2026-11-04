"""NubeFact SIMULADO (nunca el real). Uso: python fake_nubefact2.py <puerto> <dir_estado>
dir_estado/escenario.json: {"_default": "ok", "<SERIE-NUMERO>": "ok|ok_pendiente|rechazo|caida|timeout|timeout_recibido"}
dir_estado/registro.json : comprobantes recibidos {doc: {"aceptada": bool, "total": x}} (lo escribe el simulador)
dir_estado/log.jsonl     : una linea por llamada (op, doc, resultado)
'aceptar.json' (lista de docs): al consultarlos pasan a aceptados (SUNAT respondio despues)."""
import json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT, D = int(sys.argv[1]), sys.argv[2]
lock = threading.Lock()
def rj(name, default):
    try: return json.load(open(os.path.join(D, name)))
    except Exception: return default
def wj(name, data): json.dump(data, open(os.path.join(D, name), 'w'))
def log(**kw):
    with lock: open(os.path.join(D, 'log.jsonl'), 'a').write(json.dumps(kw) + '\n')
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _out(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        body = b'%PDF-1.4 simulado' if self.path.endswith('.pdf') else (b'<xml/>' if self.path.endswith('.xml') else b'PK cdr')
        self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def doc_data(self, doc, reg):
        base = 'http://127.0.0.1:%d/f/%s' % (PORT, doc)
        return {'aceptada_por_sunat': bool(reg.get('aceptada')), 'sunat_description': 'La Factura %s ha sido aceptada' % doc if reg.get('aceptada') else '',
                'sunat_responsecode': '0' if reg.get('aceptada') else '', 'key': 'KEY-' + doc, 'total': reg.get('total'),
                'enlace': base, 'enlace_del_pdf': base + '.pdf', 'enlace_del_xml': base + '.xml', 'enlace_del_cdr': base + '.cdr' if reg.get('aceptada') else ''}
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        tok_ok = self.headers.get('Authorization') == 'TKN-SIMULADO-123'
        op = body.get('operacion'); doc = '%s-%s' % (body.get('serie'), str(body.get('numero')).zfill(6))
        esc = rj('escenario.json', {}); mode = esc.get(doc, esc.get('_default', 'ok'))
        with lock:
            reg = rj('registro.json', {})
            if op == 'consultar_comprobante' and doc in rj('aceptar.json', []) and doc in reg:
                reg[doc]['aceptada'] = True; wj('registro.json', reg)
        if not tok_ok:
            log(op=op, doc=doc, r='token'); return self._out(401, {'errors': 'Token invalido', 'codigo': 10})
        if op == 'consultar_comprobante':
            if doc in reg:
                log(op=op, doc=doc, r='existe'); return self._out(200, self.doc_data(doc, reg[doc]))
            log(op=op, doc=doc, r='no_existe'); return self._out(400, {'errors': 'Documento no existe', 'codigo': 24})
        if op == 'generar_comprobante':
            if doc in reg:
                log(op=op, doc=doc, r='duplicado'); return self._out(400, {'errors': 'Este documento ya existe en NubeFacT', 'codigo': 23})
            if mode == 'caida':
                log(op=op, doc=doc, r='503'); return self._out(503, {'errors': 'Servicio no disponible'})
            if mode == 'rechazo':
                log(op=op, doc=doc, r='rechazo'); return self._out(400, {'errors': 'El RUC del cliente no es valido', 'codigo': 20})
            if mode == 'timeout':
                log(op=op, doc=doc, r='timeout_sin_registrar'); time.sleep(6); return self._out(504, {'errors': 'tarde'})
            with lock:
                reg = rj('registro.json', {}); reg[doc] = {'aceptada': mode != 'ok_pendiente', 'total': body.get('total')}; wj('registro.json', reg)
            if mode == 'timeout_recibido':
                # lo registra y luego tarda mas que el tiempo de espera del sistema
                esc[doc] = 'ok'; wj('escenario.json', esc)
                log(op=op, doc=doc, r='registrado_y_timeout'); time.sleep(6); return self._out(200, self.doc_data(doc, reg[doc]))
            log(op=op, doc=doc, r='registrado_' + mode); return self._out(200, self.doc_data(doc, reg[doc]))
        log(op=op, doc=doc, r='op_desconocida'); return self._out(400, {'errors': 'operacion desconocida'})
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
