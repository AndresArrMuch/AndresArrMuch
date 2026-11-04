import sys
exec(open('/tmp/claude-0/repro/regla/regla_test.py').read().split("setmode('ok')\nRUTAS")[0])
setmode('ok')
w = cot([L(DIG, 'PAR'), L(N1, 'NIU')]); sid, fnum = factura([(DIG, 'PAR'), (N1, 'NIU')])
sql(f"update sales_workflow set status='invoiced', sale_id='{sid}' where id='{w}'")   # facturada antes de la guia
caso(f'TC | cotizacion mezclada ya facturada ({fnum}) sin guia', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(DIG, 'PAR'), L(N1, 'NIU')], src_wf=w)), w)
caso(f'GF | la misma factura {fnum} desde "-> Guia"', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(DIG, 'PAR'), L(N1, 'NIU')], src_sale=sid)), sid)
w2 = cot([L(DIG, 'PAR')]); sid2, f2 = factura([(DIG, 'PAR')]); sql(f"update sales_workflow set status='invoiced', sale_id='{sid2}' where id='{w2}'")
caso(f'TC | cotizacion 100% DIGEMID ya facturada ({f2}) sin guia', lambda: call('post', '/api/sales/{cid}/workflow/direct-guide', body_dg([L(DIG, 'PAR')], src_wf=w2)), w2)
