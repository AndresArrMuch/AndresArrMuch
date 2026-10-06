# Base de prueba para los reportes de guias / DIGEMID. Uso: BACK=... DBP=postgresql://... python datos.py
import os, sys, json, datetime
BACK = os.environ['BACK']; os.environ['DATABASE_URL'] = os.environ['DBP']
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models.company import Company, FiscalPeriod
from app.models.sale import Customer, Sale, SaleLine, SalesWorkflow, SalesWorkflowLine
from app.models.inventory import InventoryItem, InventoryWarehouse, StockTransfer, StockTransferLine
from app.models.user import User, Role
from werkzeug.security import generate_password_hash
D = datetime.date
app = create_app()
with app.app_context():
    db.create_all()
    c = Company(ruc='20000000001', business_name='FIKA PRUEBA', address='Av. Empresa 100', district_ubigeo='150101', tax_regime='RG', economic_activity_ciiu='0000')
    c2 = Company(ruc='20000000002', business_name='OTRA EMPRESA', address='x', district_ubigeo='150101', tax_regime='RG', economic_activity_ciiu='0000')
    db.session.add_all([c, c2]); db.session.flush()
    fp = FiscalPeriod(company_id=c.id, period_year=2026, period_month=9, start_date=D(2026,9,1), end_date=D(2026,9,30), status='open'); db.session.add(fp)
    cu = Customer(company_id=c.id, ruc_or_dni='20111111111', business_name='CLINICA UNO SAC', address='Jr. Cliente 1', district_ubigeo='150131')
    cu2 = Customer(company_id=c.id, ruc_or_dni='20222222222', business_name='BOTICA DOS EIRL', address='Av. Cliente 2', district_ubigeo='150120')
    alm = InventoryWarehouse(company_id=c.id, code='ALM1', name='ALMACEN PRINCIPAL', address='Av. Almacen 500, Ate')
    alm2 = InventoryWarehouse(company_id=c.id, code='ALM2', name='ALMACEN DIGEMID', address='Calle Sanitaria 20, Lima')
    db.session.add_all([cu, cu2, alm, alm2]); db.session.flush()
    def item(code, desc, dig, sec=None):
        i = InventoryItem(company_id=c.id, item_code=code, description=desc, category='MED', unit_of_measure='NIU', requires_digemid=dig, secondary_description=sec)
        db.session.add(i); db.session.flush(); return i
    i1 = item('D001', 'GUANTE NITRILO M R.S. DM-12345-E LOTE A123 F.V. 12/2027', True)
    i2 = item('D002', 'MASCARILLA KN95', True, 'REG. SAN. DM7788E')
    i3 = item('N001', 'CAJA CARTON', False)
    def sale(corr, cust, lines, notes=None, dt='01', status='emitted'):
        s = Sale(company_id=c.id, customer_id=cust.id, fiscal_period_id=fp.id, document_type=dt, series='F001', correlative=corr, document_number='F001-' + corr,
                 emission_date=D(2026, 9, 10), due_date=D(2026, 9, 30), registration_date=D(2026, 9, 10), currency='PEN', exchange_rate=1,
                 subtotal=100, igv=18, total=118, status=status, amount_paid=0, payment_status='pending', notes=notes)
        db.session.add(s); db.session.flush()
        for it, q in lines:
            db.session.add(SaleLine(sale_id=s.id, company_id=c.id, inventory_item_id=it.id if it else None, description=it.description if it else 'SERVICIO', quantity=q, unit='NIU', unit_price=10, subtotal=10*q, igv=1.8*q, total=11.8*q))
        return s
    n = [0]
    def guia(cust, ser, corr, lines, sale_=None, status='delivered', notes=None, voided=False, parent=None, dia=8, wh=alm, qn=None):
        n[0] += 1
        w = SalesWorkflow(company_id=c.id, customer_id=cust.id, sale_id=sale_.id if sale_ else None, quotation_number=qn or f'COT-{n[0]:06d}', quotation_date=D(2026,9,1),
                          status=status, guide_series=ser, guide_correlative=corr, guide_number=f'{ser}-{corr}', dispatch_date=D(2026, 9, dia),
                          notes=notes, is_voided_locally=voided, parent_workflow_id=parent.id if parent else None)
        db.session.add(w); db.session.flush()
        for it, q in lines:
            db.session.add(SalesWorkflowLine(workflow_id=w.id, company_id=c.id, inventory_item_id=it.id, warehouse_id=wh.id, description=it.description, quantity=q, unit='NIU', unit_price=10))
        return w
    # Productos con nombre largo como los de FLUMISA (la linea de la guia viene recortada a 60 caracteres)
    largos = [
        ('D003', 'GUANTE DE NITRILO AZUL X 100 UNID 3.5 GRAMOS F.F 01-2026 F.V 01-2029 LTE. IN25029097 R.S. DM-10293-E'),
        ('D004', 'MASCARILLA QUIRURGICA 3 PLIEGUES X 50 UNID LTE. MQ2408 F.F. 08-2024 F.V. 08-2027'),
        ('D005', 'JERINGA DESCARTABLE 5ML C/AGUJA 21G X 100 UNID LTE. 2405117 F.V. 05/2029'),
        ('D006', 'ALCOHOL ETILICO 70 GRADOS 1 LT'),                      # sin rotulos: celdas vacias
        ('D007', 'GASA ESTERIL 10X10 CM X 100 SOBRES LOTE SIN NUMERO F.V. VER EMPAQUE'),  # rotulos sin dato: vacias
    ]
    largos = [item(c, d, True) for c, d in largos]
    s1 = sale('000001', cu, [(i1, 5)])                                   # una guia
    s2 = sale('000002', cu, [(i1, 2), (i3, 1)])                          # dos guias (venta + parte DIGEMID)
    s3 = sale('000003', cu2, [(i2, 4)], notes='Guia de remision: TTT4-000009')   # DIGEMID sin guia
    s4 = sale('000004', cu2, [(i3, 1)])                                  # sin DIGEMID, sin guia
    s5 = sale('000005', cu2, [(None, 1)])                                # linea sin producto
    s6 = sale('000006', cu, [(i1, 1)], status='cancelled')               # anulada
    g1 = guia(cu, 'TTT1', '000001', [(i1, 5)], s1, status='invoiced')
    g2 = guia(cu, 'TTT1', '000002', [(i3, 1)], s2, status='invoiced')
    g3 = guia(cu, 'TTT4', '000001', [(i1, 2)], s2, status='invoiced', notes='[DIGEMID] parte', parent=g2, wh=alm2)
    g4 = guia(cu2, 'TTT4', '000002', [(i2, 4)], None, notes='[DIGEMID] parte', dia=9, wh=alm2)   # candidata de F001-3
    g5 = guia(cu2, 'TTT4', '000003', [(i2, 1)], None, status='guide_voided', notes='[DIGEMID]', wh=alm2)  # anulada SUNAT
    g6 = guia(cu, 'TTT1', '000003', [(i3, 3)], None)                     # guia de venta sin DIGEMID
    g7 = guia(cu2, 'TTT1', '000004', [(i2, 1)], None, voided=True, qn='GDIR-000001')  # directa de baja interna
    g8 = guia(cu2, 'TTT4', '000010', [(x, 2) for x in largos], None, notes='[DIGEMID] parte', dia=12, wh=alm2)
    for l in g8.lines: l.description = l.description[:60]    # como en produccion: la linea recortada
    s7 = sale('000007', cu2, [(largos[0], 2)], notes='Venta mostrador | Guia de remision: TTT4-000010')   # sugerida: misma guia y cliente
    s8 = sale('000008', cu2, [(largos[1], 1)], notes='Guia de remision: TTT1-000001')   # guia de OTRO cliente: no se sugiere
    s9 = sale('000009', cu2, [(largos[2], 1)], notes='Ver guia TTT4-777')               # guia que no existe: no se sugiere
    t1 = StockTransfer(company_id=c.id, transfer_number='TR-0001', from_warehouse_id=alm.id, to_warehouse_id=alm2.id, transfer_date=D(2026,9,7), status='received', notes='Reposicion\n[TRF_GUIDE:TTT5-000001]', guide_sent=True)
    db.session.add(t1); db.session.flush()
    db.session.add(StockTransferLine(transfer_id=t1.id, company_id=c.id, item_id=i2.id, quantity_requested=10, quantity_sent=10))
    db.session.add(StockTransferLine(transfer_id=t1.id, company_id=c.id, item_id=i3.id, quantity_requested=2, quantity_sent=2))
    # otra empresa (no debe verse)
    o_cu = Customer(company_id=c2.id, ruc_or_dni='20333333333', business_name='AJENO', address='x'); db.session.add(o_cu); db.session.flush()
    db.session.add(SalesWorkflow(company_id=c2.id, customer_id=o_cu.id, quotation_number='COT-9', quotation_date=D(2026,9,1), status='delivered', guide_series='TTT4', guide_correlative='000099', guide_number='TTT4-000099', dispatch_date=D(2026,9,8)))
    rol = Role(name='Administrador', company_id=c.id); db.session.add(rol); db.session.flush()
    u = User(email='admin@t.pe', username='admin', password_hash=generate_password_hash('p'), first_name='A', last_name='B', role_id=rol.id, company_id=c.id, is_active=True)
    db.session.add(u); db.session.commit()
    json.dump(dict(CID=c.id, C2=c2.id, UID=u.id, I1=i1.id, I2=i2.id, S1=s1.id, S2=s2.id, S3=s3.id, S7=s7.id, S8=s8.id, S9=s9.id, G8=g8.id, G1=g1.id, G4=g4.id, T1=t1.id), open('/tmp/claude-0/repro/dig/ids.json', 'w'))
    print(c.id)
