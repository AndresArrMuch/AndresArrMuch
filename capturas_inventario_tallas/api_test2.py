"""Pruebas API de la version con parametro, roles y documento. Uso: api_test2.py <backend_main> <backend_rama>"""
import sys, json, subprocess
sys.path.insert(0, '/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/itl')
from api_test_lib import fresh, run
BM, BR = sys.argv[1:3]
ON = "INSERT INTO system_parameter (id, company_id, parameter_key, parameter_value, data_type, is_editable, created_at, updated_at, is_active) VALUES ('p-lote','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','inventario_carga_lote','1','string',true,now(),now(),true)"
def psql(db, sql): subprocess.run(['psql', '-h', 'localhost', '-p', '5433', '-U', 'postgres', db, '-qc', sql], check=True, capture_output=True)
DOC = "document_type='factura_compra', document_number='F001-000123'"
MOV = "dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='{t}', {doc}notes={n!r}, lines={l})"
def mov(t='in', l="[dict(item_id='af-i1', quantity=10, unit_cost=2.5)]", doc=DOC + ', ', n='Ingreso de importacion'):
    return MOV.format(t=t, l=l, doc=doc, n=n)

# --- A) Parametro APAGADO (por defecto) ---
fresh('l2_off')
a = run(BR, 'l2_off', f"""
h=H('central@t.pe')
out['cfg']=cl.get('/api/inventory/'+F+'/batch-config', headers=h).get_json()['data']
out['items_batch']=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(description='X', category='Y', unit_of_measure='NIU', items=[dict(item_code='ZZ1')]), headers=h))
out['mov_batch']=J(cl.post('/api/inventory/'+F+'/movements/batch', json={mov()}, headers=h))
out['mov_simple']=J(cl.post('/api/inventory/'+F+'/movements', json=dict(item_id='af-i1', warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', quantity=5, unit_cost=0, notes='como antes'), headers=h))
out['item_simple']=J(cl.post('/api/inventory/'+F+'/items', json=dict(item_code='ZZ9', description='X', category='Y', unit_of_measure='NIU'), headers=h))
""")
print('### A) Parametro apagado (por defecto)')
print('  configuracion:', {k: a['cfg'][k] for k in ('habilitado', 'permitido')})
for k in ('items_batch', 'mov_batch', 'mov_simple', 'item_simple'):
    print(f'  {k}:', a[k]['http'], a[k]['codigo'] or '', '|', a[k]['mensaje'])

# --- B) Parametro ENCENDIDO: roles ---
fresh('l2_on'); psql('l2_on', ON)
users = ['central@t.pe', 'sistema.fika@t.pe', 'admin@t.pe', 'gerente@t.pe', 'tesoreria@t.pe', 'ventas@t.pe', 'vendedor.fika@t.pe', 'almacenguias.fika@t.pe', 'capon@t.pe']
code = "res={}\n" + "\n".join(f"""
hh=H({u!r})
res[{u!r}]=dict(cfg=cl.get('/api/inventory/'+F+'/batch-config', headers=hh).get_json()['data']['permitido'],
    mov=J(cl.post('/api/inventory/'+F+'/movements/batch', json={mov(l="[dict(item_id='af-i1', quantity=1, unit_cost=2.5)]")}, headers=hh))['http'],
    items=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(description='X', category='Y', unit_of_measure='NIU', items=[dict(item_code='RL-'+{u!r}[:8])]), headers=hh))['http'])""" for u in users) + "\nout['roles']=res"
b = run(BR, 'l2_on', code)
print('\n### B) Parametro encendido: quien puede (pantalla / movimiento por lote / items por lote)')
for u, v in b['roles'].items():
    print(f'  {u:28} pantalla {"SI" if v["cfg"] else "no"} | movimiento {v["mov"]} | items {v["items"]}')

# --- C) Documento y costo ---
fresh('l2_doc'); psql('l2_doc', ON)
c = run(BR, 'l2_doc', f"""
h=H('central@t.pe')
casos=[('sin tipo de documento', {mov(doc="document_number='F001-1', ")}),
       ('sin numero de documento', {mov(doc="document_type='factura_compra', ")}),
       ('numero = "para facturar"', {mov(doc="document_type='factura_compra', document_number='para facturar', ")}),
       ('numero sin digitos "SN"', {mov(doc="document_type='guia_remision', document_number='S/N', ")}),
       ('comentario "correccion de stock"', {mov(n='correccion de stock')}),
       ('costo 0.01', {mov(l="[dict(item_id='af-i1', quantity=10, unit_cost=2.5), dict(item_id='af-i2', quantity=5, unit_cost=0.01)]")}),
       ('costo 0', {mov(l="[dict(item_id='af-i1', quantity=10, unit_cost=0)]")})]
with app.app_context(): n0=InventoryMovement.query.count()
out['casos']=[[t, J(cl.post('/api/inventory/'+F+'/movements/batch', json=b, headers=h))] for t,b in casos]
with app.app_context(): out['nada']=InventoryMovement.query.count()==n0
out['ok']=J(cl.post('/api/inventory/'+F+'/movements/batch', json={mov(l="[dict(item_id='af-i1', quantity=10, unit_cost=2.5), dict(item_id='af-i2', quantity=4, unit_cost=1.2)]")}, headers=h))
with app.app_context(): out['notas']=[m.notes for m in InventoryMovement.query.filter(InventoryMovement.created_by.isnot(None)).all()]
""")
print('\n### C) Documento de origen y costo (central, parametro encendido)')
for t, r in c['casos']:
    print(f'  {t:34} {r["http"]} {r["codigo"] or ""} | {r["mensaje"]}')
print('  ninguno registro movimientos:', c['nada'])
print('  con documento y costos validos:', c['ok']['http'], c['ok']['mensaje'], '| comentario guardado:', c['notas'])

# --- D) Equivalencia con main (saldos) ---
SEQ = [('in', 'af-i1', 100, 2.5), ('in', 'af-i2', 40, 1.2), ('in', 'af-i1', 10, 3.0), ('out', 'af-i1', 5, 2.5), ('adjustment', 'af-i2', 3, 1.2)]
fresh('l2_main'); fresh('l2_rama'); psql('l2_rama', ON)
m = run(BM, 'l2_main', "h=H('central@t.pe')\n" + "\n".join(f"cl.post('/api/inventory/'+F+'/movements', json=dict(item_id='{it}', warehouse_id=ALM, movement_date='2026-10-21', movement_type='{t}', quantity={q}, unit_cost={cc}, notes='x'), headers=h)" for t, it, q, cc in SEQ) + "\nout['k']=kardex(['af-i1','af-i2']); out['c']=costos(['af-i1','af-i2'])")
r = run(BR, 'l2_rama', "h=H('central@t.pe')\n"
        + f"cl.post('/api/inventory/'+F+'/movements/batch', json={mov(l=str([dict(item_id=it, quantity=q, unit_cost=cc) for t,it,q,cc in SEQ if t=='in']))}, headers=h)\n"
        + f"cl.post('/api/inventory/'+F+'/movements/batch', json={mov(t='out', l=str([dict(item_id='af-i1', quantity=5, unit_cost=2.5)]))}, headers=h)\n"
        + f"cl.post('/api/inventory/'+F+'/movements/batch', json={mov(t='adjustment', l=str([dict(item_id='af-i2', quantity=3, unit_cost=1.2)]))}, headers=h)\n"
        + "out['k']=kardex(['af-i1','af-i2']); out['c']=costos(['af-i1','af-i2'])")
print('\n### D) Saldos: main (una linea por vez) vs rama (lote con documento)')
print('  kardex identico:', [x[:7] for x in m['k']] == [x[:7] for x in r['k']], '| costo identico:', m['c'] == r['c'])

# --- E) Doble clic con el parametro encendido ---
fresh('l2_dc'); psql('l2_dc', ON)
e = run(BR, 'l2_dc', f"""
h=H('central@t.pe'); import threading
res=[]
def go():
    c2=app.test_client(); res.append(J(c2.post('/api/inventory/'+F+'/movements/batch', json={mov(l="[dict(item_id='af-i1', quantity=1, unit_cost=2.5)]*20")}, headers=h))['http'])
ts=[threading.Thread(target=go) for _ in range(2)]; [t.start() for t in ts]; [t.join() for t in ts]
out['r']=sorted(res); out['n']=len([k for k in kardex(['af-i1']) if k[2]==1.0])
""")
print('\n### E) Doble clic (dos envios simultaneos de 20 lineas):', e['r'], '| lineas creadas:', e['n'])
