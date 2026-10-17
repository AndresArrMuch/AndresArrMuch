import os,sys,warnings; warnings.filterwarnings('ignore')
B, DB = sys.argv[1:3]
os.environ['DATABASE_URL']=f'postgresql://postgres@/{DB}?host=/var/run/postgresql&port=5433'; sys.path.insert(0,B); os.chdir(B)
from app import create_app; from app.models.user import User; from app.models import Company; from flask_jwt_extended import create_access_token
F='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'; app=create_app('development'); cl=app.test_client()
with app.app_context(): h={'Authorization':'Bearer '+create_access_token(identity=User.query.filter_by(email='sistema.fika@t.pe',company_id=F).first().id)}
def tok():
    with app.app_context(): c=Company.query.get(F); return c.nubecont_api_token, c.nubecont_api_url
g=cl.get(f'/api/companies/{F}',headers=h).get_json()['data']
print('  GET empresa, claves nubecont:', {k:(v if 'configurad' in k else '<valor>') for k,v in g.items() if 'nubecont' in k})
base={'ruc':g['ruc'],'business_name':g['business_name'],'address':g['address'],'email':'fika@prueba.pe','phone':'999999999','tax_regime':'RG','economic_activity_ciiu':'4690','district_ubigeo':'150101'}
# Lo que enviaba/envia la pantalla: main manda los valores que recibio en el formulario; la rama no los manda si no se escribio nada
screen = dict(base, nubecont_api_url=g.get('nubecont_api_url'), nubecont_api_token=g.get('nubecont_api_token')) if 'nubecont_api_token' in g else dict(base)
r=cl.put(f'/api/companies/{F}',json=screen,headers=h); print('  1) Editar la empresa sin tocar el token:', r.status_code, '| token y URL conservados:', tok()==('TKN-PRUEBA-7f3a9c1e5b2d','http://127.0.0.1:8931/api/ruta-secreta-0b9e4c'))
r=cl.put(f'/api/companies/{F}',json=dict(base, nubecont_api_token='', nubecont_api_url=None),headers=h); print('  2) Enviar token vacio y URL null:', r.status_code, '| token conservado:', tok()[0]=='TKN-PRUEBA-7f3a9c1e5b2d', '| URL conservada:', tok()[1] is not None)
r=cl.put(f'/api/companies/{F}',json=dict(base, nubecont_api_token='TKN-NUEVO-PRUEBA-0000aaaa'),headers=h); t=r.get_data(as_text=True)
print('  3) Escribir un token nuevo:', r.status_code, '| guardado:', tok()[0]=='TKN-NUEVO-PRUEBA-0000aaaa', '| la respuesta muestra el nuevo:', 'TKN-NUEVO' in t)
r=cl.get(f'/api/sales/{F}/af-s120/electronic/status',headers=h); print('  4) Consultar estado con el nuevo:', r.status_code, '| respuesta con el token nuevo:', 'TKN-NUEVO' in r.get_data(as_text=True))
