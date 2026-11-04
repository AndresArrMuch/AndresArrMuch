import os, sys, json, subprocess, warnings
warnings.filterwarnings("ignore")
F = "976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433"
ALM = "20e9a97f-c3c9-4302-b488-c27f74bdcc1f"
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

