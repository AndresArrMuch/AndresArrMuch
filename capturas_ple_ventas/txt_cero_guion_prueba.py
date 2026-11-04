# Compara los dos TXT antes (c0bd93a) y despues (rama): campos, totales y como se ve el cero
import json
from decimal import Decimal as D
BK = {'txt_antes': '/tmp/claude-0/wt_guion/backend', 'txt_despues': '/tmp/claude-0/wt_txtg/backend'}
num = lambda x: D('0') if x == '-' else D(x)
def load(n):
    R = json.load(open(n + '.json')); assert not R['errores_js']
    s = [l.split('|') for l in R['txt_sunat']['texto'].strip().split('\n')]
    t = [l.split('|') for l in open(BK[n] + '/' + R['txt_tributario']['file_path']).read().strip().split('\n')]
    return s, t
A, B = load('txt_antes'), load('txt_despues')
AMT_S, AMT_T = range(13, 26), range(8, 11)
for nombre, a, b, amt, tot in (('TXT export-sunat', A[0], B[0], AMT_S, 25), ('TXT Tributario', A[1], B[1], AMT_T, 10)):
    print(f'== {nombre}: {len(a)} lineas antes, {len(b)} despues; campos por linea {sorted({len(x) for x in a})} -> {sorted({len(x) for x in b})}')
    print('  campos que no son importe, identicos:', all([x for i, x in enumerate(la) if i not in amt] == [x for i, x in enumerate(lb) if i not in amt] for la, lb in zip(a, b)))
    print('  importes iguales tomando "-" como 0:', all(num(la[i]) == num(lb[i]) for la, lb in zip(a, b) for i in amt))
    print('  ningun "0.00" queda en importes:', not any(lb[i] in ('0.00', '-0.00') for lb in b for i in amt))
    print('  total antes', sum(num(x[tot]) for x in a), '| despues', sum(num(x[tot]) for x in b))
    for lb in b:
        doc = (lb[7] + '-' + lb[8]) if nombre.endswith('sunat') else (lb[4] + '-' + lb[5])
        if doc in ('F001-000002', 'FC01-000001', 'F001-000001'):
            print('   ', doc, '|'.join(lb[i] for i in amt))
