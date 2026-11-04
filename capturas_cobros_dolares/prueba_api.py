"""Registra la venta USD y 3 cobros por la API y muestra sus asientos. Uso: python ops.py <backend> <db> <etiqueta> [solo_ver]"""
import os, sys
BACKEND, DB, TAG = sys.argv[1:4]; SOLO_VER = len(sys.argv) > 4
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import text
F = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'
app = create_app(); cl = app.test_client()
with app.app_context():
    H = {'Authorization': 'Bearer ' + create_access_token(identity=User.query.filter_by(email='admin@t.pe', company_id=F).first().id)}
    db.session.execute(text("update sale set accounting_status='pending' where id='FU' and accounting_status is null")); db.session.commit()
def sql(q, **p):
    with app.app_context():
        return db.session.execute(text(q), p).fetchall()
if not SOLO_VER:
    r = cl.post(f'/api/sales/{F}/FU/post', headers=H); print(f'[{TAG}] asiento venta F001-000004 (US$ 100, TC 3.75): HTTP {r.status_code}')
    for banco, sale, monto, op, fecha, notas in [('bk-fika-bcp-me', 'FU', 100, 'USD-1', '2026-10-15', ''),
                                                 ('bk-fika-bcp-mn', 'b20e1049-9875-4dce-aacc-a37cf275d4ce', 540, 'COM-1', '2026-10-15', 'Comision: 21.10'),
                                                 ('bk-fika-bcp-mn', 'af-s120', 100, 'SEP-1', '2026-09-05', '')]:
        r = cl.post(f'/api/payments/{F}/collect', headers=H, json={'bank_account_id': banco, 'payment_date': fecha, 'reference_number': op,
                                                                 'notes': notas, 'items': [{'sale_id': sale, 'amount': monto}]})
        print(f'[{TAG}] cobro {op} ({banco}, {monto}, {fecha} {notas}): HTTP {r.status_code} {(r.get_json() or {}).get("error", {}).get("message", "") if r.status_code >= 300 else ""}')
print(f'[{TAG}] --- asientos ---')
for eid, num, gl, mes in sql("""select e.id, e.entry_number, e.gloss, p.period_month from journal_entry e join fiscal_period p on p.id=e.fiscal_period_id
        where e.company_id=:c and (e.gloss like '%%F001-000004%%' or e.gloss like '%%Ref: USD-1%%' or e.gloss like '%%Ref: COM-1%%' or e.gloss like '%%Ref: SEP-1%%') order by e.created_at""", c=F):
    print(f'[{TAG}]  {num} periodo {mes:02d}  {gl[:60]}')
    for code, d, c, dm, cm in sql("""select a.account_code, l.debit_amount, l.credit_amount, coalesce(l.debit_amount_me,0), coalesce(l.credit_amount_me,0)
            from journal_entry_line l join chart_of_account a on a.id=l.chart_account_id where l.entry_id=:e order by l.debit_amount desc, a.account_code""", e=eid):
        print(f'[{TAG}]     {code:8} D {d:>9} H {c:>9}' + (f'  US$ D {dm} H {cm}' if (dm or cm) else ''))
for ref, amt, acc in sql("select reference_number, amount, account_id from bank_transaction where reference_number in ('USD-1','COM-1','SEP-1') order by 1"):
    print(f'[{TAG}]  movimiento banco {ref}: {amt} en {acc}')
for code, saldo in sql("""select a.account_code, sum(l.debit_amount-l.credit_amount) from journal_entry_line l join journal_entry e on e.id=l.entry_id
        join chart_of_account a on a.id=l.chart_account_id where e.company_id=:c and (e.gloss like '%%F001-000004%%' or e.gloss like '%%Ref: USD-1%%')
        and a.account_code like '12%%' group by 1""", c=F):
    print(f'[{TAG}]  saldo CxC de F001-000004 en {code}: {saldo}')
