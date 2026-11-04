import json, sys
S = sys.argv[1]
M, R = json.load(open(f'{S}/res_main.json')), json.load(open(f'{S}/res_rama.json'))
def e(x): return {k: x[k] for k in ('doc', 'sunat_status', 'ticket', 'pdf', 'cdr', 'contable')} if isinstance(x, dict) and 'doc' in x else x
def r(x): return f"{x['http']} {x['codigo'] or ''} {x['mensaje'][:110]}".strip() + (' [TOKEN]' if x.get('tiene_token') else '') + (' [RUTA SECRETA]' if x.get('tiene_ruta') else '')
L = []
def caso(t, *pairs):
    L.append('\n=== ' + t)
    for label, fm, fr in pairs:
        L.append(f'  {label}\n    MAIN: {fm(M)}\n    RAMA: {fr(R)}')
caso('1) Venta normal, NubeFact acepta',
     ('envio', lambda X: r(X['1_normal']['envio']), lambda X: r(X['1_normal']['envio'])),
     ('estado', lambda X: e(X['1_normal']['estado']), lambda X: e(X['1_normal']['estado'])),
     ('llamadas a NubeFact', lambda X: [l['r'] for l in X['1_normal']['nubefact']], lambda X: [l['r'] for l in X['1_normal']['nubefact']]))
caso('2) NubeFact caido (sin red) al emitir',
     ('envio', lambda X: r(X['2_caido']['envio']), lambda X: r(X['2_caido']['envio'])),
     ('queda registrado', lambda X: e(X['2_caido']['estado_tras_fallo']), lambda X: e(X['2_caido']['estado_tras_fallo'])),
     ('motivo guardado', lambda X: X['2_caido']['estado_tras_fallo']['intentos'], lambda X: X['2_caido']['estado_tras_fallo']['intentos']),
     ('boton Enviar a SUNAT', lambda X: '(no existe el boton)', lambda X: r(X['2_caido']['reintento_boton'])),
     ('estado final', lambda X: e(X['2_caido']['estado_final']), lambda X: e(X['2_caido']['estado_final'])))
caso('3) Tiempo agotado, pero NubeFact SI lo recibio',
     ('envio', lambda X: r(X['3_timeout_recibido']['envio']), lambda X: r(X['3_timeout_recibido']['envio'])),
     ('estado', lambda X: e(X['3_timeout_recibido']['estado']), lambda X: e(X['3_timeout_recibido']['estado'])),
     ('llamadas a NubeFact', lambda X: [l['op'] + ':' + l['r'] for l in X['3_timeout_recibido']['nubefact']], lambda X: [l['op'] + ':' + l['r'] for l in X['3_timeout_recibido']['nubefact']]))
caso('4) NubeFact rechaza por datos',
     ('envio', lambda X: r(X['4_rechazo']['envio']), lambda X: r(X['4_rechazo']['envio'])),
     ('motivo guardado', lambda X: X['4_rechazo']['estado']['intentos'], lambda X: X['4_rechazo']['estado']['intentos']))
caso('5) NubeFact lo recibe, SUNAT aun no acepta (aceptada_por_sunat=false)',
     ('estado tras enviar', lambda X: e(X['5_pendiente_sunat']['estado']), lambda X: e(X['5_pendiente_sunat']['estado'])),
     ('tras Consultar (SUNAT ya acepto)', lambda X: '-', lambda X: e(X['5_pendiente_sunat']['estado_tras_consulta'])))
caso('6) Venta repetida (la primera no llego a NubeFact)',
     ('crear otra igual', lambda X: r(X['6_repetida']['crear_otra_igual']), lambda X: r(X['6_repetida']['crear_otra_igual'])),
     ('crear con confirmacion', lambda X: r(X['6_repetida']['crear_con_confirmacion']), lambda X: r(X['6_repetida']['crear_con_confirmacion'])),
     ('enviar la segunda (vendedor)', lambda X: '-', lambda X: r(X['6_repetida']['enviar_la_segunda_vendedor'])),
     ('enviar la segunda (gerente confirma)', lambda X: '-', lambda X: r(X['6_repetida']['enviar_la_segunda_gerente_confirma'])))
caso('7) Consultar un documento que nunca llego (como B030-000016)',
     ('consulta', lambda X: r(X['7_consulta_no_existe']['consultar']), lambda X: r(X['7_consulta_no_existe']['consultar'])),
     ('sunat_status despues', lambda X: repr(X['7_consulta_no_existe']['estado']['sunat_status']), lambda X: repr(X['7_consulta_no_existe']['estado']['sunat_status'])))
caso('8) Nota de credito sobre una factura anulada',
     ('crear NC', lambda X: r(X['8_nc_sobre_anulada']), lambda X: r(X['8_nc_sobre_anulada'])))
L.append('\n=== 9) Lista de pendientes (solo rama)')
L.append('  vendedor: ' + r(R['9_lista']['vendedor']) + ' | gerente: ' + str(R['9_lista']['gerente_http']))
for d in R['9_lista']['gerente_docs']: L.append('    ' + str(d))
L.append('\n=== 10) Tabla de intentos: ' + json.dumps(R['10_tabla_intentos']))
L.append('\n=== 11) Reintento automatico (solo rama)')
for k in ('simulado', 'con_otro_proceso', 'real', 'segunda_pasada', 'tercera_y_cuarta'):
    L.append('  -- ' + k)
    for x in R['11_auto'][k]: L.append(f"     {x.get('documento', '-'):<13} {x.get('paso', ''):<17} {x.get('resultado', '')}")
L.append('  -- estado final de cada documento')
for k, v in R['11_auto']['estados'].items():
    L.append(f'     {k:<13} {e(v)} intentos: ' + ', '.join(i[1] + ':' + i[2] for i in v['intentos']))
print('\n'.join(L))
