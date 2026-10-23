"""Siembra la factura E001-2258 de FLUMISA en la base de prueba. Uso: python seed.py <backend> <db>"""
import os, sys
from datetime import date
from decimal import Decimal
BACKEND, DB = sys.argv[1:3]
os.environ['DATABASE_URL'] = f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'
sys.path.insert(0, BACKEND); os.chdir(BACKEND)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app, db
from app.models import Customer, Sale, SaleLine, FiscalPeriod, InventoryMovement
FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78'
app = create_app()
with app.app_context():
    jun = FiscalPeriod.query.filter_by(company_id=FLU, period_year=2026, period_month=6).first()
    c = Customer(company_id=FLU, ruc_or_dni='20603526962', business_name='PINTURAS DEL PERU S.A.', address='LIMA', document_type='6') if hasattr(Customer, 'document_type') else Customer(company_id=FLU, ruc_or_dni='20603526962', business_name='PINTURAS DEL PERU S.A.', address='LIMA')
    db.session.add(c); db.session.flush()
    def factura(corr, total, base, igv, cust):
        s = Sale(company_id=FLU, customer_id=cust, fiscal_period_id=jun.id, document_type='01', series='E001', correlative=corr,
                 document_number=f'E001-{corr}', emission_date=date(2026, 6, 8), due_date=date(2026, 6, 8), registration_date=date(2026, 6, 8),
                 is_electronic=False, sunat_status='aceptada', currency='PEN', exchange_rate=1, subtotal=base, igv=igv, total=total,
                 status='emitted', accounting_status='pending', amount_paid=0, payment_status='unpaid')
        s.lines.append(SaleLine(company_id=FLU, inventory_item_id='af-i1', description='GUANTE DE NITRILO AZUL TALLA M', quantity=10, unit='BX',
                                unit_price=Decimal('10.5930'), subtotal=base, igv_percentage=18, igv=igv, total=total))
        db.session.add(s); return s
    inv = factura('2258', Decimal('125.00'), Decimal('105.93'), Decimal('19.07'), c.id)
    factura('2259', Decimal('236.00'), Decimal('200.00'), Decimal('36.00'), 'cli-1')
    db.session.commit()
    print('factura', inv.id, 'junio', jun.id)
