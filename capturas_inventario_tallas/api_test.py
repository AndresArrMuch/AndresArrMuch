"""Pruebas API: tallas en un paso y movimiento con varias lineas. Uso: api_test.py <backend_main> <backend_rama>"""
import os, sys, json, subprocess, warnings
warnings.filterwarnings('ignore')
BM, BR = sys.argv[1:3]
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
ALM = '20e9a97f-c3c9-4302-b488-c27f74bdcc1f'
def fresh(db):
    subprocess.run(['psql', '-h', 'localhost', '-p', '5433', '-U', 'postgres', '-qc', f'DROP DATABASE IF EXISTS {db}', '-c', f'CREATE DATABASE {db} TEMPLATE af_base'], check=True, capture_output=True)
def run(backend, db, code):
    prog = f'''
import os, sys, json, warnings; warnings.filterwarnings("ignore")
os.environ["DATABASE_URL"]="postgresql://postgres@/{db}?host=/var/run/postgresql&port=5433"; sys.path.insert(0,{backend!r}); os.chdir({backend!r})
from app import create_app, db; from app.models.user import User; from app.models import InventoryItem, InventoryMovement
from flask_jwt_extended import create_access_token
app=create_app("development"); cl=app.test_client(); F="{F}"; ALM="{ALM}"
def H(email):
    with app.app_context(): return {{"Authorization":"Bearer "+create_access_token(identity=User.query.filter_by(email=email, company_id=F).first().id)}}
def J(r):
    j=r.get_json(silent=True) or {{}}; e=j.get("error") if isinstance(j.get("error"),dict) else {{}}
    return {{"http": r.status_code, "codigo": e.get("code"), "mensaje": j.get("message") or e.get("message")}}
def kardex(item_ids):
    with app.app_context():
        rows=InventoryMovement.query.filter(InventoryMovement.item_id.in_(item_ids), InventoryMovement.warehouse_id==ALM).order_by(InventoryMovement.created_at).all()
        return [[r.item_id, r.movement_type, float(r.quantity), float(r.unit_cost), float(r.total_cost), float(r.balance_quantity), float(r.balance_cost), r.created_by is not None] for r in rows]
def costos(item_ids):
    with app.app_context(): return {{i.item_code: float(i.current_cost) for i in InventoryItem.query.filter(InventoryItem.id.in_(item_ids)).all()}}
out={{}}
{code}
print(json.dumps(out, ensure_ascii=False))
'''
    p = subprocess.run([sys.executable, '-W', 'ignore', '-c', prog], capture_output=True, text=True)
    lines = p.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else {'error': p.stderr[-1500:]}

ITEMS = "['af-i1','af-i2']"
SEQ = [('in', 'af-i1', 100, 2.5), ('in', 'af-i2', 40, 1.2), ('in', 'af-i1', 10, 3.0), ('out', 'af-i1', 5, 2.5), ('adjustment', 'af-i2', 3, 1.2)]
# --- 1) Equivalencia: lineas sueltas en main == movimiento con varias lineas en la rama ---
fresh('itl_main'); fresh('itl_rama')
single = "h=H('central@t.pe')\n" + "\n".join(
    f"out.setdefault('resp',[]).append(J(cl.post('/api/inventory/'+F+'/movements', json=dict(item_id='{it}', warehouse_id=ALM, movement_date='2026-10-21', movement_type='{t}', quantity={q}, unit_cost={c}, notes='prueba'), headers=h)))"
    for t, it, q, c in SEQ) + f"\nout['kardex']=kardex({ITEMS}); out['costos']=costos({ITEMS})"
m = run(BM, 'itl_main', single)
batch_in = [l for l in SEQ if l[0] == 'in']
code_b = "h=H('central@t.pe')\n" + (
    f"out['resp_in']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', notes='prueba', lines={[dict(item_id=it, quantity=q, unit_cost=c) for t,it,q,c in batch_in]}), headers=h))\n"
    f"out['resp_out']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='out', notes='prueba', lines=[dict(item_id='af-i1', quantity=5, unit_cost=2.5)]), headers=h))\n"
    f"out['resp_adj']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='adjustment', notes='prueba', lines=[dict(item_id='af-i2', quantity=3, unit_cost=1.2)]), headers=h))\n"
    f"out['kardex']=kardex({ITEMS}); out['costos']=costos({ITEMS})")
r = run(BR, 'itl_rama', code_b)
print('### 1) Mismas entradas, salida y ajuste: main (una linea por vez) vs rama (varias lineas en un movimiento)')
print('  main respuestas:', [x['http'] for x in m.get('resp', [])], '| rama respuestas:', r.get('resp_in', {}).get('http'), r.get('resp_out', {}).get('http'), r.get('resp_adj', {}).get('http'))
km = [k[:7] for k in m['kardex']]; kr = [k[:7] for k in r['kardex']]
print('  kardex identico (tipo, cantidad, costo, total, saldo, saldo valorizado):', km == kr)
for a in kr: print('   ', a)
print('  costo del item identico:', m['costos'] == r['costos'], r['costos'])
print('  usuario guardado: main', [k[7] for k in m['kardex']], '| rama', [k[7] for k in r['kardex']])

# --- 2..9) casos de la rama ---
fresh('itl_c')
cases = r'''
h=H('central@t.pe'); hc=H('capon@t.pe')
base=dict(description='NITRILO VERDE X100 GUANTES DE 6.5 GRAMOS', category='DESCARTABLES', unit_of_measure='NIU', brand='BSTL', model='GENERAL', current_cost=8.5, sale_price=12, requires_digemid=False)
r=cl.post('/api/inventory/'+F+'/items/batch', json=dict(base, items=[dict(item_code='BSTL260708NG65TS', secondary_description='S, VERDE'), dict(item_code='BSTL260708NG65TM', secondary_description='M, VERDE'), dict(item_code='BSTL260708NG65TL', secondary_description='L, VERDE', barcode='1211')]), headers=h)
out['2_tres_tallas']=J(r); ids=[x['id'] for x in (r.get_json() or {}).get('data') or []]
with app.app_context():
    out['2_creados']=[[i.item_code, i.secondary_description, i.unit_of_measure, float(i.current_cost), i.model, i.created_by is not None] for i in InventoryItem.query.filter(InventoryItem.id.in_(ids)).order_by(InventoryItem.item_code).all()]
n0=None
with app.app_context(): n0=InventoryItem.query.count()
out['3_codigo_ya_existe']=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(base, items=[dict(item_code='BSTL260708NG65TXL'), dict(item_code='BSTL260708NG65TL')]), headers=h))
out['4_sufijo_repetido']=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(base, items=[dict(item_code='ZZ1TS'), dict(item_code='zz1ts')]), headers=h))
out['5_barra_repetida']=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(base, items=[dict(item_code='ZZ2TS', barcode='1211')]), headers=h))
with app.app_context(): out['3a5_no_se_creo_nada']= InventoryItem.query.count()==n0
lines=[dict(item_id=i, quantity=q, unit_cost=8.5) for i,q in zip(ids,[100,200,300])]
r=cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', notes='Factura proveedor F001-123', lines=lines), headers=h)
out['6_ingreso_3_tallas']=J(r); out['6_kardex']=kardex(ids)
r=cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', lines=[dict(item_id=ids[0], quantity=10, unit_cost=9), dict(item_id=ids[0], quantity=5, unit_cost=10)]), headers=h)
out['7_mismo_item_dos_veces']=J(r); out['7_kardex']=kardex([ids[0]])[-2:]
with app.app_context(): k0=InventoryMovement.query.count()
out['8_salida_sin_stock']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='out', lines=[dict(item_id=ids[1], quantity=50, unit_cost=8.5), dict(item_id=ids[2], quantity=9999, unit_cost=8.5)]), headers=h))
out['9_cantidad_cero']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', lines=[dict(item_id=ids[1], quantity=5, unit_cost=1), dict(item_id=ids[2], quantity=0, unit_cost=1)]), headers=h))
out['10_31_lineas']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', lines=[dict(item_id=ids[1], quantity=1, unit_cost=1)]*31), headers=h))
out['11_tienda_movimiento']=J(cl.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', lines=[dict(item_id=ids[1], quantity=1, unit_cost=1)]), headers=hc))
out['11_tienda_items']=J(cl.post('/api/inventory/'+F+'/items/batch', json=dict(base, items=[dict(item_code='ZZ3TS')]), headers=hc))
with app.app_context(): out['8a11_no_se_registro_nada']= InventoryMovement.query.count()==k0
# 12) doble clic: dos envios a la vez del mismo movimiento
import threading
res=[]
def go():
    c2=app.test_client(); res.append(J(c2.post('/api/inventory/'+F+'/movements/batch', json=dict(warehouse_id=ALM, movement_date='2026-10-21', movement_type='in', lines=[dict(item_id=ids[2], quantity=1, unit_cost=8.5)]*20), headers=h)))
ts=[threading.Thread(target=go) for _ in range(2)]; [t.start() for t in ts]; [t.join() for t in ts]
out['12_doble_clic']=sorted([x['http'] for x in res]); out['12_lineas_creadas']=len([k for k in kardex([ids[2]]) if k[2]==1.0])
'''
c = run(BR, 'itl_c', cases)
if 'error' in c: print(c['error'])
print('\n### 2) Tres tallas en un paso:', c['2_tres_tallas']['http'], c['2_tres_tallas']['mensaje'])
for x in c['2_creados']: print('   ', x)
for k in ('3_codigo_ya_existe', '4_sufijo_repetido', '5_barra_repetida'):
    print(f'### {k}:', c[k]['http'], c[k]['codigo'], '|', c[k]['mensaje'])
print('### 3 a 5) no se creo ningun item:', c['3a5_no_se_creo_nada'])
print('\n### 6) Ingreso de las 3 tallas en un movimiento:', c['6_ingreso_3_tallas']['http'], c['6_ingreso_3_tallas']['mensaje'])
for x in c['6_kardex']: print('   ', x[1:])
print('### 7) Mismo item dos veces en el movimiento:', c['7_mismo_item_dos_veces']['http'], '| ultimas dos lineas (saldo acumulado):', [x[1:7] for x in c['7_kardex']])
for k in ('8_salida_sin_stock', '9_cantidad_cero', '10_31_lineas', '11_tienda_movimiento', '11_tienda_items'):
    print(f'### {k}:', c[k]['http'], c[k]['codigo'], '|', c[k]['mensaje'])
print('### 8 a 11) no se registro ningun movimiento:', c['8a11_no_se_registro_nada'])
print('### 12) Doble clic (dos envios simultaneos de 20 lineas):', c['12_doble_clic'], '| lineas creadas:', c['12_lineas_creadas'])
