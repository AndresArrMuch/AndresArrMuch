# Servidor de prueba con NubeCont simulado para consultar guias (SOLO PRUEBA)
import os, sys, base64, io, zipfile
BACK, DBP, PORT = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.environ['DATABASE_URL'] = DBP
sys.path.insert(0, BACK); os.chdir(BACK)
import warnings; warnings.filterwarnings('ignore')
import app as _a; _a._restore_sqlite_database_from_respaldo = lambda app: None
from app import create_app
app = create_app()
try:
    import app.routes.guide_report_routes as gr
    def fake_doc(company, wf):
        g = f'{wf.guide_series}-{wf.guide_correlative}'
        xml = (f'<DespatchAdvice><cac:Delivery><cac:DeliveryAddress><cbc:ID>150131</cbc:ID><cac:AddressLine><cbc:Line>Llegada de {g}</cbc:Line></cac:AddressLine></cac:DeliveryAddress>'
               f'<cac:Despatch><cac:DespatchAddress><cbc:ID>150103</cbc:ID><cac:AddressLine><cbc:Line>Partida de {g}</cbc:Line></cac:AddressLine></cac:DespatchAddress></cac:Despatch></cac:Delivery></DespatchAdvice>')
        b = io.BytesIO(); z = zipfile.ZipFile(b, 'w'); z.writestr('g.xml', xml); z.close()
        return {'ok': True, 'data': {'aceptada_por_sunat': True, 'enlace_del_pdf': f'https://nube.test/pdf/{g}.pdf', 'xml_zip_base64': base64.b64encode(b.getvalue()).decode()}}
    gr.get_guide_document = fake_doc
except ImportError:
    pass   # main no tiene el modulo
app.run(port=PORT, debug=False, threaded=True)
