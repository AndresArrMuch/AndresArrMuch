"""Reproduce guias con unidad de linea distinta de la del producto (NubeFact SIMULADA en 8933). Uso: gd_test.py <backend> <db_plantilla> <salida.json>"""
import os, sys, json, subprocess, warnings
warnings.filterwarnings('ignore')
B, TPL, OUT = sys.argv[1:4]
S = os.path.dirname(os.path.abspath(__file__))
CAP, MODE = f'{S}/cap.jsonl', f'{S}/mode.json'
FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
CUST = '80bb9db3-6e9f-426f-8ba6-a94f64e83655'
WH = 'ec674a11-2d4d-40e3-93b5-4ebf1c2085f6'
GUIDE = {'motivo_de_traslado': '01', 'tipo_de_transporte': '02', 'indicador_m1l': False, 'fecha_de_inicio_de_traslado': '2026-10-19',
         'fecha_de_entrega_al_transportista': '2026-10-19', 'peso_bruto_total': '100', 'peso_bruto_unidad_de_medida': 'KGM', 'numero_de_bultos': '10',
         'transportista_placa_numero': 'ABC123', 'conductor_documento_tipo': '1', 'conductor_documento_numero': '12345678', 'conductor_nombre': 'JUAN',
         'conductor_apellidos': 'PEREZ', 'conductor_numero_licencia': 'Q12345678', 'punto_de_partida_ubigeo': '150132', 'punto_de_partida_direccion': 'AV PARTIDA 1',
         'punto_de_partida_codigo_establecimiento_sunat': '0000', 'punto_de_llegada_ubigeo': '150101', 'punto_de_llegada_direccion': 'AV LLEGADA 2',
         'punto_de_llegada_codigo_establecimiento_sunat': '0000', 'observaciones': ''}

def fresh(name):
    subprocess.run(['psql', '-h', 'localhost', '-p', '5433', '-U', 'postgres', '-qc', f'DROP DATABASE IF EXISTS {name}', '-c', f'CREATE DATABASE {name} TEMPLATE {TPL}'],
                   check=True, capture_output=True)

def line(item, unit, qty):
    return {'inventory_item_id': item, 'description': 'x', 'quantity': qty, 'unit': unit, 'unit_price': 17, 'warehouse_id': WH}

CASES = [
    ('1 Traer cotizacion: linea BX sobre producto NIU (como COT-000202), serie TTT1', 'direct', {'source_workflow_id': 'gd-w1', 'series': 'TTT1', 'lines': [line('gd-niu', 'BX', 3800)]}, False),
    ('2 Traer cotizacion: linea NIU sobre producto NIU, serie TTT1', 'direct', {'source_workflow_id': 'gd-w2', 'series': 'TTT1', 'lines': [line('gd-niu', 'NIU', 3800)]}, False),
    ('3 Traer cotizacion: linea BX sobre producto BX, serie TTT1', 'direct', {'source_workflow_id': 'gd-w3', 'series': 'TTT1', 'lines': [line('gd-bx', 'BX', 3800)]}, False),
    ('4 Traer cotizacion: linea BX sobre producto BX, serie TTT4 (producto no DIGEMID)', 'direct', {'source_workflow_id': 'gd-w3', 'series': 'TTT4', 'lines': [line('gd-bx', 'BX', 3800)]}, False),
    ('5 DIGEMID: linea BX sobre producto DIGEMID BX (TTT4)', 'direct', {'source_workflow_id': 'gd-w5', 'series': 'TTT4', 'digemid_departure_address': 'AV DIGEMID 9', 'lines': [line('gd-dgbx', 'BX', 10)]}, False),
    ('6 DIGEMID: linea BX sobre producto DIGEMID NIU (como COT-000162-DIGEMID, TTT4)', 'direct', {'source_workflow_id': 'gd-w4', 'series': 'TTT4', 'digemid_departure_address': 'AV DIGEMID 9', 'lines': [line('gd-dgniu', 'BX', 10)]}, False),
    ('7 Traer cotizacion con linea NIU guardada, pero la pantalla manda BX y cantidad 1 (lo que se ve no es lo que se envia)', 'direct', {'source_workflow_id': 'gd-w2', 'series': 'TTT1', 'lines': [line('gd-niu', 'BX', 1)]}, False),
    ('8 Guia directa sin cotizacion: producto NIU con unidad BX en la linea', 'direct', {'series': 'TTT1', 'lines': [line('gd-niu', 'BX', 3800)]}, False),
    ('9 issue-guide (emitir guia desde la cotizacion aceptada): linea BX sobre producto NIU', 'issue', {'workflow': 'gd-w1', 'series': 'TTT1'}, False),
    ('10 Como el caso 1, con el PROVEEDOR rechazando: "Despatch advice lines catalog unidad de medida incorrecto"', 'direct', {'source_workflow_id': 'gd-w1', 'series': 'TTT1', 'lines': [line('gd-niu', 'BX', 3800)]}, True),
]
results = []
for i, (title, kind, body, reject) in enumerate(CASES, 1):
    db = f'gd_c{i}'; fresh(db)
    json.dump({'rechazar': reject, 'mensaje': 'Despatch advice lines catalog unidad de medida incorrecto', 'codigo': 20}, open(MODE, 'w'))
    n0 = sum(1 for _ in open(CAP)) if os.path.exists(CAP) else 0
    code = f'''
import os, sys, json, warnings; warnings.filterwarnings("ignore")
os.environ["DATABASE_URL"]="postgresql://postgres@/{db}?host=/var/run/postgresql&port=5433"; sys.path.insert(0, {B!r}); os.chdir({B!r})
from app import create_app; from app.models.user import User; from flask_jwt_extended import create_access_token
app=create_app("development"); cl=app.test_client()
with app.app_context(): h={{"Authorization":"Bearer "+create_access_token(identity=User.query.filter_by(email="sistema.fika@t.pe", company_id="{FIKA}").first().id)}}
kind={kind!r}; body={body!r}; guide={GUIDE!r}
if kind=="direct":
    req=dict(customer_id="{CUST}", dispatch_date="2026-10-19", currency="PEN", notes="", guide_data=guide, send_electronic=True, **body)
    r=cl.post("/api/sales/{FIKA}/workflow/direct-guide", json=req, headers=h)
else:
    r=cl.post("/api/sales/{FIKA}/workflow/"+body["workflow"]+"/issue-guide", json=dict(guide_series=body["series"], series=body["series"], guide_data=guide, send_electronic=True), headers=h)
j=r.get_json(silent=True) or {{}}
err=j.get("error") if isinstance(j.get("error"), dict) else {{}}
print(json.dumps({{"http": r.status_code, "codigo": err.get("code"), "mensaje": j.get("message") or err.get("message"),
  "guias": [w.get("guide_number") for w in ([(j.get("data") or {{}}).get("workflow")] if isinstance((j.get("data") or {{}}).get("workflow"), dict) else [])] }}))
'''
    p = subprocess.run([sys.executable, '-W', 'ignore', '-c', code], capture_output=True, text=True)
    out = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {'error': p.stderr[-800:]}
    caps = [json.loads(l) for l in open(CAP)][n0:] if os.path.exists(CAP) else []
    guias = [c for c in caps if c.get('operacion') == 'generar_guia']
    out['payload_enviado'] = [{'serie': g.get('serie'), 'numero': g.get('numero'),
                               'items': [{k: it.get(k) for k in ('codigo', 'descripcion', 'cantidad', 'unidad_de_medida', 'COD_UND_MEDIDA_ITEM', 'PESO_ITEM')} for it in g.get('items', [])]}
                              for g in guias]
    q = subprocess.run(['psql', '-h', 'localhost', '-p', '5433', '-U', 'postgres', db, '-Atc',
                        "select coalesce(guide_number,'-')||' '||status from sales_workflow where id like 'gd-w%' or quotation_number like 'GDIR-%' order by created_at"], capture_output=True, text=True)
    out['estado_cotizaciones'] = q.stdout.split()
    results.append({'caso': title, **out})
    print(f"\n### {title}\n  respuesta: HTTP {out.get('http')} {out.get('codigo') or ''} {str(out.get('mensaje') or out.get('error') or '')[:160]}")
    for g in out['payload_enviado']:
        print(f"  enviado a NubeFact: {g['serie']}-{g['numero']}  items={g['items']}")
    if not out['payload_enviado']:
        print('  enviado a NubeFact: NADA (no se llamo al proveedor)')
json.dump(results, open(OUT, 'w'), ensure_ascii=False, indent=1)
