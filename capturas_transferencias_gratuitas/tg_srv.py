"""Servidor de prueba que registra cualquier llamada a NubeFact/NubeCont o a la red (y la bloquea)."""
import os, sys
B, PORT, DB, LOG = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, B); os.chdir(B)
import warnings; warnings.filterwarnings('ignore')
open(LOG, 'w').close()
def _log(t):
    with open(LOG, 'a') as fh: fh.write(t + '\n')
import requests
def _espia(self, method, url, *a, **k):
    _log(f'HTTP {method} {url}'); raise RuntimeError('red bloqueada en la prueba')
requests.Session.request = _espia
import app.services.nubecont_service as nc
for n in [n for n in dir(nc) if not n.startswith('_') and callable(getattr(nc, n)) and getattr(getattr(nc, n), '__module__', '') == nc.__name__]:
    def _mk(n):
        def _f(*a, **k):
            _log('nubecont_service.' + n); raise RuntimeError('NubeCont bloqueado en la prueba')
        return _f
    setattr(nc, n, _mk(n))
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
create_app().run(host='127.0.0.1', port=PORT, threaded=True, use_reloader=False, debug=False)
