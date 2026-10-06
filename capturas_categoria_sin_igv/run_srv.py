import os, sys
os.environ['DATABASE_URL'] = 'postgresql://postgres@/ventas_test?host=/var/run/postgresql&port=5433'
B = sys.argv[1]; PORT = int(sys.argv[2]); sys.path.insert(0, B); os.chdir(B)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
create_app().run(host='127.0.0.1', port=PORT, threaded=True, use_reloader=False, debug=False)
