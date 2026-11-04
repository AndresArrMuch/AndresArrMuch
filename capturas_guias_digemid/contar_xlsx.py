import sys, openpyxl
for f in sys.argv[1:]:
    ws = openpyxl.load_workbook(f).active
    h = [c.value for c in ws[1]]; ip, il, ipdf = h.index('Punto de partida'), h.index('Punto de llegada'), h.index('Enlace PDF')
    filas = list(ws.iter_rows(min_row=2, values_only=True))
    print(f.split('/')[-1], '| filas', len(filas), '| con partida', sum(1 for r in filas if r[ip]), '| con llegada', sum(1 for r in filas if r[il]), '| con PDF', sum(1 for r in filas if r[ipdf]))
