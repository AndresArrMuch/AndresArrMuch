from base import *
from werkzeug.security import generate_password_hash
from app.models.user import User
for c in ['31', '32', '51', '52']: venta(c, 118.0)
sid = venta('41', 118.0, 'USD')
with app.app_context():
    s = db.session.get(Sale, sid); s.exchange_rate = 3.50
    u = db.session.get(User, UID); u.password_hash = generate_password_hash('p'); db.session.commit()
print(CID)
