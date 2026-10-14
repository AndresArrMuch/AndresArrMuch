"""Transferencias gratuitas: pruebas de servidor (main y rama).
Uso: python tg_api_test.py <backend_dir> <db> <salida.json>
"""
import os, sys, json, io, hashlib, threading
BACKEND, DB, OUT = sys.argv[1:4]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None

# --- Espia de NubeFact/NubeCont: cualquier llamada HTTP o funcion del servicio queda registrada ---
LLAMADAS_EXTERNAS = []
import requests
_orig_request = requests.Session.request
def _espia_request(self, method, url, *a, **k):
    LLAMADAS_EXTERNAS.append(f'{method} {url}')
    raise RuntimeError('red bloqueada en la prueba')
requests.Session.request = _espia_request
import app.services.nubecont_service as nc
for _name in [n for n in dir(nc) if not n.startswith('_') and callable(getattr(nc, n)) and getattr(getattr(nc, n), '__module__', '') == nc.__name__]:
    def _mk(n):
        def _f(*a, **k):
            LLAMADAS_EXTERNAS.append('nubecont_service.' + n)
            raise RuntimeError('NubeCont bloqueado en la prueba')
        return _f
    setattr(nc, _name, _mk(_name))

from app import create_app, db
from app.models import InventoryItem, InventoryWarehouse, InventoryMovement, Sale
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text
from openpyxl import load_workbook

FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app(); cl = app.test_client()
R = {}
with app.app_context():
    WH = {w.code: w.id for w in InventoryWarehouse.query.filter_by(company_id=FIKA).all()}
    IT = {i.item_code: i.id for i in InventoryItem.query.filter_by(company_id=FIKA).all()}
    TOK = {}
    for key, email in [('admin', 'admin@t.pe'), ('nilton', 'ventas2@fikaperu.com'), ('saul', 'ventas.tda.filomena@gmail.com'),
                       ('almacenero', 'central@t.pe')]:
        u = User.query.filter_by(email=email, company_id=FIKA).first()
        TOK[key] = create_access_token(identity=u.id)
    TIENE_TG = 'free_transfers' in app.blueprints

def H(user): return {'Authorization': 'Bearer ' + TOK[user]}
def get(user, url): r = cl.get(url, headers=H(user)); return r.status_code, r
def jget(user, url): st, r = get(user, url); return st, (r.get_json(silent=True) or {})
def jpost(user, url, body): r = cl.post(url, headers=H(user), json=body); return r.status_code, (r.get_json(silent=True) or {})

def saldo(code_item, code_wh):
    with app.app_context():
        m = (InventoryMovement.query.filter_by(company_id=FIKA, item_id=IT[code_item], warehouse_id=WH[code_wh])
             .order_by(InventoryMovement.movement_date.desc(), InventoryMovement.created_at.desc()).first())
        return float(m.balance_quantity) if m else 0.0

def snapshot():
    """Reportes que NO deben cambiar: ventas, tarjetas, Por Cobrar, PLE/TXT, conciliacion, transferencias."""
    out = {}
    def h(b): return hashlib.sha256(b).hexdigest()[:16]
    gets = {
        'dashboard': f'/api/dashboard/{FIKA}',
        'ventas_lista': f'/api/sales/{FIKA}?per_page=20000',
        'cotizaciones_guias': f'/api/sales/{FIKA}/workflow?per_page=20000',
        'periodos_reporte': f'/api/sales/{FIKA}/reports/periods',
        'pagos_historial': f'/api/payments/{FIKA}/history',
        'anticipos': f'/api/payments/{FIKA}/anticipos',
        'transferencias_almacenes': f'/api/inventory/{FIKA}/transfers',
        'conciliacion_estado_oct': f'/api/banks/{FIKA}/conciliacion-import-status?periodo=2026-10',
        'asientos': f'/api/journal-entries/{FIKA}?per_page=20000',
    }
    for k, url in gets.items():
        st, r = get('admin', url)
        out[k] = [st, h(r.data)]
    posts = {
        'reporte_ventas_periodo_oct': (f'/api/sales/{FIKA}/reports/periodic', {'period_year': 2026, 'period_month': 10}),
        'tendencia_ventas': (f'/api/sales/{FIKA}/reports/periodic/trend', {'period_year': 2026, 'period_month': 10}),
        'txt_sunat_ventas_oct': (f'/api/sales/{FIKA}/reports/periodic/export-sunat', {'period_year': 2026, 'period_month': 10}),
        'ple_ventas_oct': (f'/api/tax/{FIKA}/ple/export', {'register_type': 'sales_register', 'period_year': 2026, 'period_month': 10}),
    }
    for k, (url, body) in posts.items():
        r = cl.post(url, headers=H('admin'), json=body)
        out[k] = [r.status_code, h(r.data)]
    with app.app_context():
        out['ventas_bd'] = [x for x in db.session.execute(text(
            "select count(*), coalesce(sum(total),0)::text, max(document_number) from sale where company_id=:c"), {'c': FIKA}).first()]
        out['series_ventas'] = sorted({x[0] for x in db.session.execute(text("select distinct series from sale"))})
        out['series_guias'] = sorted({x[0] for x in db.session.execute(text(
            "select distinct guide_series from sales_workflow where guide_series is not null"))})
        out['cxc_asientos'] = db.session.execute(text("select count(*) from journal_entry")).scalar()
    return out

R['tiene_transferencias_gratuitas'] = TIENE_TG
R['reportes_antes'] = snapshot()
R['saldos_antes'] = {f'{i}@{w}': saldo(i, w) for i, w in [('P0001', 'ALMFIKA'), ('P0002', 'ALMFIKA'), ('P0003', 'ALMFIKA'),
                                                          ('P0001', 'TDAFIKAMALVINAS'), ('P0002', 'TDAFIKACAPON')]}

if TIENE_TG:
    B = f'/api/free-transfers/{FIKA}'
    hoy = None
    st, o = jget('admin', B + '/options'); hoy = o['data']['today']
    R['opciones_admin'] = {'status': st, 'serie': o['data']['series'], 'siguiente': o['data']['next_number'],
                           'almacenes': [w['code'] for w in o['data']['warehouses']], 'motivos': [m['label'] for m in o['data']['reasons']],
                           'puede_anular': o['data']['can_void']}
    st, o = jget('nilton', B + '/options')
    R['opciones_nilton'] = {'status': st, 'almacenes': [w['code'] for w in o['data']['warehouses']], 'restringido': o['data']['restricted'],
                            'almacen_por_defecto': [k for k, v in WH.items() if v == o['data']['default_warehouse_id']], 'puede_anular': o['data']['can_void']}

    base = {'transfer_date': hoy, 'reason': 'muestra', 'recipient_name': 'cliente generico', 'responsible_name': 'Vendedor de prueba',
            'notes': 'Muestras para visita'}
    # 1) Crear: baja el stock del almacen elegido
    st, d = jpost('admin', B, dict(base, warehouse_id=WH['ALMFIKA'], client_request_id='req-1',
                                   lines=[{'item_id': IT['P0001'], 'quantity': 3}, {'item_id': IT['P0002'], 'quantity': 2}]))
    TG1 = d.get('data', {})
    R['1_crear'] = {'status': st, 'numero': TG1.get('document_number'), 'estado': TG1.get('status'), 'mensaje': d.get('message'),
                    'lineas': [(l['item_code'], l['quantity']) for l in TG1.get('lines', [])],
                    'tiene_precio': any(k in json.dumps(TG1) for k in ('unit_price', 'unit_cost', '"total"', 'igv'))}
    R['1_saldos_despues'] = {'P0001@ALMFIKA': saldo('P0001', 'ALMFIKA'), 'P0002@ALMFIKA': saldo('P0002', 'ALMFIKA'),
                             'P0001@TDAFIKAMALVINAS (otro almacen, no cambia)': saldo('P0001', 'TDAFIKAMALVINAS')}
    st, k = jget('admin', f'/api/inventory/{FIKA}/movements?per_page=20000')
    movs = [m for m in k['data']['data'] if m['reference_id'] == TG1.get('id')]
    R['1_kardex'] = [(m['warehouse_code'], m['item_code'], m['movement_type'], m['reference_type'], m['quantity'], m['balance_quantity']) for m in movs]
    with app.app_context():
        R['1_kardex_nota_bd'] = sorted({x[0] for x in db.session.execute(text("select notes from inventory_movement where reference_id=:i"), {'i': TG1['id']})})

    # 2) Mas de lo que hay: bloqueado, sin documento ni movimiento, sin consumir numero
    antes_docs = len(jget('admin', B)[1]['data'])
    st, d = jpost('admin', B, dict(base, warehouse_id=WH['ALMFIKA'], client_request_id='req-2',
                                   lines=[{'item_id': IT['P0003'], 'quantity': 9}, {'item_id': IT['P0001'], 'quantity': 1}]))
    R['2_sobre_stock'] = {'status': st, 'codigo': (d.get('error') or {}).get('code'), 'mensaje': (d.get('error') or {}).get('message'),
                          'documentos_creados': len(jget('admin', B)[1]['data']) - antes_docs,
                          'saldo_P0003@ALMFIKA': saldo('P0003', 'ALMFIKA'), 'saldo_P0001@ALMFIKA': saldo('P0001', 'ALMFIKA')}
    st, d = jpost('admin', B, dict(base, warehouse_id=WH['TDAFIKAMALVINAS'], client_request_id='req-2b',
                                   lines=[{'item_id': IT['P0004'], 'quantity': 1}]))
    R['2_producto_sin_stock_en_ese_almacen'] = [st, (d.get('error') or {}).get('message')]

    # 3) Doble clic: mismo envio dos veces (seguido y en paralelo) -> un solo documento
    body = dict(base, warehouse_id=WH['ALMFIKA'], client_request_id='req-3', lines=[{'item_id': IT['P0002'], 'quantity': 1}])
    s1, d1 = jpost('admin', B, body); s2, d2 = jpost('admin', B, body)
    R['3_doble_envio_seguido'] = {'estados': [s1, s2], 'numeros': [d1['data']['document_number'], d2['data']['document_number']],
                                  'segundo_idempotente': d2['data'].get('idempotent')}
    with app.app_context():
        R['3_documentos_con_ese_envio'] = db.session.execute(text("select count(*) from free_transfer where client_request_id='req-3'")).scalar()
        R['3_movimientos_de_ese_doc'] = db.session.execute(text("select count(*) from inventory_movement where reference_id=:i"), {'i': d1['data']['id']}).scalar()

    # 4) Encargado de tienda (Nilton, Malvinas): solo su tienda y el central
    st, d = jpost('nilton', B, dict(base, warehouse_id=WH['TDAFIKACAPON'], client_request_id='req-4a', lines=[{'item_id': IT['P0002'], 'quantity': 1}]))
    R['4_nilton_desde_capon'] = [st, (d.get('error') or {}).get('code')]
    st, d = jpost('nilton', B, dict(base, warehouse_id=WH['TDAFIKAMALVINAS'], client_request_id='req-4b', reason='obsequio',
                                    lines=[{'item_id': IT['P0001'], 'quantity': 2}]))
    TG_N = d.get('data', {})
    R['4_nilton_desde_su_tienda'] = [st, TG_N.get('document_number'), saldo('P0001', 'TDAFIKAMALVINAS')]
    R['4_nilton_stock_capon'] = get('nilton', B + '/stock?warehouse_id=' + WH['TDAFIKACAPON'])[0]
    R['4_nilton_stock_central'] = get('nilton', B + '/stock?warehouse_id=' + WH['ALMFIKA'])[0]
    st, d = jpost('admin', B, dict(base, warehouse_id=WH['TDAFIKACAPON'], client_request_id='req-4c', reason='uso_interno',
                                   lines=[{'item_id': IT['P0002'], 'quantity': 1}]))
    TG_CAPON = d.get('data', {})
    R['4_admin_desde_capon'] = [st, TG_CAPON.get('document_number')]
    R['4_lista_nilton'] = sorted(x['document_number'] + ' ' + x['warehouse_code'] for x in jget('nilton', B)[1]['data'])
    R['4_lista_saul_capon'] = sorted(x['document_number'] + ' ' + x['warehouse_code'] for x in jget('saul', B)[1]['data'])
    R['4_nilton_ver_doc_capon'] = get('nilton', B + '/' + TG_CAPON['id'])[0]

    # 5) Validaciones de fecha y datos
    R['5_fecha_futura'] = jpost('admin', B, dict(base, transfer_date='2026-12-31', warehouse_id=WH['ALMFIKA'], lines=[{'item_id': IT['P0001'], 'quantity': 1}]))[1].get('error', {}).get('code')
    R['5_fecha_antes_ultimo_mov'] = jpost('admin', B, dict(base, transfer_date='2026-10-02', warehouse_id=WH['ALMFIKA'], lines=[{'item_id': IT['P0001'], 'quantity': 1}]))[1].get('error', {}).get('message')
    R['5_sin_destinatario'] = jpost('admin', B, dict(base, recipient_name='', warehouse_id=WH['ALMFIKA'], lines=[{'item_id': IT['P0001'], 'quantity': 1}]))[1].get('error', {}).get('code')
    R['5_motivo_otro_sin_detalle'] = jpost('admin', B, dict(base, reason='otro', notes='', warehouse_id=WH['ALMFIKA'], lines=[{'item_id': IT['P0001'], 'quantity': 1}]))[1].get('error', {}).get('code')
    R['5_cantidad_cero'] = jpost('admin', B, dict(base, warehouse_id=WH['ALMFIKA'], lines=[{'item_id': IT['P0001'], 'quantity': 0}]))[1].get('error', {}).get('code')

    # 6) Anular: rol autorizado, motivo obligatorio, devuelve stock con movimiento de entrada
    R['6_anular_nilton'] = jpost('nilton', B + f'/{TG1["id"]}/void', {'reason': 'x'})[0]
    R['6_anular_almacenero'] = jpost('almacenero', B + f'/{TG1["id"]}/void', {'reason': 'x'})[0]
    R['6_anular_sin_motivo'] = jpost('admin', B + f'/{TG1["id"]}/void', {'reason': ''})[1].get('error', {}).get('code')
    st, d = jpost('admin', B + f'/{TG1["id"]}/void', {'reason': 'Muestras devueltas por el vendedor'})
    R['6_anular'] = {'status': st, 'estado': d['data']['status'], 'motivo': d['data']['void_reason'], 'anulado_por': d['data']['voided_by_name'],
                     'P0001@ALMFIKA': saldo('P0001', 'ALMFIKA'), 'P0002@ALMFIKA': saldo('P0002', 'ALMFIKA')}
    st, k = jget('admin', f'/api/inventory/{FIKA}/movements?per_page=20000')
    R['6_kardex_del_documento'] = sorted((m['item_code'], m['movement_type'], m['reference_type'], m['quantity']) for m in k['data']['data'] if m['reference_id'] == TG1['id'])
    R['6_anular_otra_vez'] = jpost('admin', B + f'/{TG1["id"]}/void', {'reason': 'otra'})[1].get('error', {}).get('code')
    R['6_sigue_visible_anulada'] = [(x['document_number'], x['status']) for x in jget('admin', B)[1]['data'] if x['id'] == TG1['id']]

    # 7) Lista con filtros y Excel
    R['7_filtro_producto_P0001'] = sorted(x['document_number'] for x in jget('admin', B + '?item_id=' + IT['P0001'])[1]['data'])
    R['7_filtro_motivo_obsequio'] = sorted(x['document_number'] for x in jget('admin', B + '?reason=obsequio')[1]['data'])
    R['7_filtro_almacen_capon'] = sorted(x['document_number'] for x in jget('admin', B + '?warehouse_id=' + WH['TDAFIKACAPON'])[1]['data'])
    R['7_filtro_destinatario'] = len(jget('admin', B + '?recipient=GENERICO')[1]['data'])
    R['7_filtro_fechas_sin_resultado'] = len(jget('admin', B + '?date_from=2026-09-01&date_to=2026-09-30')[1]['data'])
    st, r = get('admin', B + '/export')
    ws = load_workbook(io.BytesIO(r.data)).active
    R['7_excel'] = {'status': st, 'titulo': ws['A1'].value, 'cabecera': [c.value for c in ws[2]], 'filas': ws.max_row - 2,
                    'primera_fila': [str(c.value) for c in ws[3]]}
    st, r = get('nilton', B + '/export')
    R['7_excel_nilton_almacenes'] = sorted({row[3] for row in load_workbook(io.BytesIO(r.data)).active.iter_rows(min_row=3, values_only=True)})

    # 8) Serie interna vs series de ventas y guias
    with app.app_context():
        R['8_numeros_internos'] = [x[0] for x in db.session.execute(text("select document_number from free_transfer order by correlative"))]
        R['8_choque_con_ventas'] = db.session.execute(text("select count(*) from sale s join free_transfer f on f.document_number = s.document_number or f.series = s.series")).scalar()

R['llamadas_nubefact_o_red'] = LLAMADAS_EXTERNAS
R['reportes_despues'] = snapshot()
R['reportes_identicos'] = R['reportes_antes'] == R['reportes_despues']
R['reportes_diferencias'] = {k: [R['reportes_antes'][k], R['reportes_despues'][k]] for k in R['reportes_antes'] if R['reportes_antes'][k] != R['reportes_despues'][k]}
json.dump(R, open(OUT, 'w'), indent=1, ensure_ascii=False, default=str)
print('listo', OUT)
