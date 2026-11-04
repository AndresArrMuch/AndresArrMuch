import os, sys, json
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
from flask_jwt_extended import create_access_token
ids = json.load(open('/tmp/claude-0/repro/dig/ids.json')); CID = ids['CID']
app = create_app()
with app.app_context(): tok = create_access_token(identity=ids['UID'])
cl = app.test_client(); H = {'Authorization': 'Bearer ' + tok}
print('== Reporte DIGEMID, periodo setiembre 2026 (por defecto: solo DIGEMID, sin traslados)')
rows = cl.get(f'/api/guide-reports/{CID}/digemid-guides?from=2026-09-01&to=2026-09-30', headers=H).get_json()['data']['rows']
for r in rows:
    print(f"  {r['guia']:12} {r['tipo_guia']:14} fact={r['factura'] or '-':12} sugerida={r['factura_sugerida'] or '-':12} {r['codigo']} | linea='{r['producto'][:60]}' | lote={r['lote'] or '-'} ff={r['fabricacion'] or '-'} fv={r['vencimiento'] or '-'} rs={r['registro_sanitario'] or '-'} | {r['estado']}")
print('  guias no DIGEMID en el reporte (TTT1-000002, TTT1-000003):', [r['guia'] for r in rows if r['guia'] in ('TTT1-000002', 'TTT1-000003')])
print('  traslados en el reporte:', [r['guia'] for r in rows if r['kind'] == 'transfer'])
print('== sale-guides setiembre: guia sugerida de las facturas sin guia')
d = cl.get(f'/api/guide-reports/{CID}/sale-guides?from=2026-09-01&to=2026-09-30', headers=H).get_json()['data']
n = {ids['S1']: 'F001-1', ids['S2']: 'F001-2', ids['S3']: 'F001-3 (nota: TTT4-000009, no existe)', ids['S7']: 'F001-7 (nota: TTT4-000010, mismo cliente)', ids['S8']: 'F001-8 (nota: TTT1-000001, de OTRO cliente)', ids['S9']: 'F001-9 (nota: TTT4-777, no existe)'}
for k, v in n.items(): print(f"  {v:45} vinculadas={[g['guide_number'] for g in d['guides'].get(k, [])]} sugerida={d['suggested'].get(k, [])}")
