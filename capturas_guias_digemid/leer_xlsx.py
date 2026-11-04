import sys, openpyxl
for f in sys.argv[1:]:
    ws = openpyxl.load_workbook(f).active
    print('==', f.split('/')[-1], ws.max_row, 'filas x', ws.max_column, 'columnas')
    for row in ws.iter_rows(values_only=True):
        if any(v not in (None, '') for v in row): print('  ', [v for v in row])
