"""Reemplaza los emojis de index.html por iconos de Font Awesome (ya cargado en el sistema).
Uso: python emoji_a_iconos.py <index.html>
Icono: <i data-ico class=fa-xxx></i>  (sin comillas: sirve dentro de cualquier cadena de JS/HTML).
"""
import re, sys
P = sys.argv[1]
s = open(P, encoding='utf-8').read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:90])
    s = s.replace(old, new)

# ---- 1) Contextos de texto plano: el icono no se puede dibujar, se quita el emoji ----
for e in ('💰 Cobro a Cliente', '💳 Pago a Proveedor', '🔄 Transferencia entre cuentas propias', '📋 Gasto / Ingreso directo'):
    rep('>' + e, '>' + e.split(' ', 1)[1])                                   # <option> de Movimiento bancario
rep('setNotice("📝 Llegó un requerimiento', 'setNotice("Llegó un requerimiento')  # aviso = textContent
rep('"Estado": Math.abs(diff) > 0.01 ? "⚠️ REVISAR" : "✅ OK"', '"Estado": Math.abs(diff) > 0.01 ? "REVISAR" : "OK"')  # Excel
# Avisos de transferencias gratuitas: el texto va escapado; el icono lo pone la caja segun el tipo
rep('texto: "✅ Transferencia gratuita "', 'texto: "Transferencia gratuita "')
rep('texto: "⛔ No se registró: "', 'texto: "No se registró: "')
rep('texto: "✅ " + d.document_number', 'texto: d.document_number')
rep('texto: "⛔ No se anuló: "', 'texto: "No se anuló: "')
rep('"background:#fee2e2;color:#991b1b;border:1px solid #fecaca;"}">${escapeHtml(ft.msg.texto)}</div>',
    '"background:#fee2e2;color:#991b1b;border:1px solid #fecaca;"}">${ft.msg.tipo === "ok" ? "✅" : "⛔"} ${escapeHtml(ft.msg.texto)}</div>')
# textContent con emoji fijo -> innerHTML (texto fijo, sin datos del usuario)
rep("qOcFileExisting.textContent = workflow.purchase_order_file_path ? '📎", "qOcFileExisting.innerHTML = workflow.purchase_order_file_path ? '📎")
rep('if (msg) msg.textContent = mix.norm\n        ? "⚠️', 'if (msg) msg.innerHTML = mix.norm\n        ? "⚠️')

# ---- 2) El decorador de botones no debe agregar un segundo icono ----
rep('        if (btn.querySelector(".btn-icon")) return;\n        if (btn.children.length > 0',
    '        if (btn.querySelector(".btn-icon, [data-ico]")) return;  // ya tiene icono propio (14/10/2026)\n        if (btn.children.length > 0')

# ---- 3) Estilo del icono ----
rep('    .btn-icon { margin-right: 6px; font-size: 0.9em; }\n',
    '    .btn-icon { margin-right: 6px; font-size: 0.9em; }\n'
    '    /* Iconos en lugar de emojis (14/10/2026): <i data-ico class=fa-...></i> con Font Awesome */\n'
    '    [data-ico] { font-family: "Font Awesome 6 Free"; font-weight: 900; font-style: normal; font-variant: normal; display: inline-block; line-height: 1; text-rendering: auto; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }\n'
    '    [data-ico].fa-circle { font-size: 0.7em; vertical-align: 0.1em; }\n'
    '    [data-ico=green] { color: #16a34a; } [data-ico=red] { color: #dc2626; } [data-ico=orange] { color: #ea580c; } [data-ico=amber] { color: #d97706; }\n')

# ---- 4) Reemplazo general ----
VS = '(?:️|&#65039;)?'
BASE = {  # emoji -> icono por defecto
    '📊': 'fa-chart-column', '&#128202;': 'fa-chart-column', '📈': 'fa-chart-line', '&#128200;': 'fa-chart-line',
    '💾': 'fa-floppy-disk', '&#128190;': 'fa-floppy-disk', '📄': 'fa-file-lines', '&#128196;': 'fa-file-lines',
    '📋': 'fa-clipboard-list', '&#128203;': 'fa-clipboard-list', '📝': 'fa-note-sticky', '&#128221;': 'fa-note-sticky',
    '🔄': 'fa-right-left', '🎁': 'fa-gift', '🏢': 'fa-building', '&#127970;': 'fa-building', '🚫': 'fa-ban',
    '🗂': 'fa-book-open', '🛒': 'fa-cart-shopping', '&#128722;': 'fa-cart-shopping', '📤': 'fa-paper-plane', '🚚': 'fa-truck',
    '✕': 'fa-xmark', '&#10005;': 'fa-xmark', '&#10007;': 'fa-xmark', '✓': 'fa-check', '&#10003;': 'fa-check',
    '⚠': 'fa-triangle-exclamation', '&#9888;': 'fa-triangle-exclamation', '👁': 'fa-eye', '&#128065;': 'fa-eye',
    '📥': 'fa-download', '🗑': 'fa-trash-can', '&#128465;': 'fa-trash-can', '✏': 'fa-pen', '&#9999;': 'fa-pen',
    '☁': 'fa-cloud-arrow-up', '✅': 'fa-circle-check', '&#9989;': 'fa-circle-check', '⛔': 'fa-circle-xmark', '&#10060;': 'fa-circle-xmark',
    '🏦': 'fa-building-columns', '&#127974;': 'fa-building-columns', '💰': 'fa-sack-dollar', '&#128176;': 'fa-sack-dollar',
    '💵': 'fa-money-bill-wave', '💳': 'fa-credit-card', '&#128179;': 'fa-credit-card', '🧾': 'fa-receipt', '👥': 'fa-users',
    '🏖': 'fa-umbrella-beach', '💼': 'fa-briefcase', '&#128188;': 'fa-briefcase', '⚙': 'fa-gear', '⚡': 'fa-bolt', '&#9889;': 'fa-bolt',
    '📎': 'fa-paperclip', '👆': 'fa-hand-pointer', '🖨': 'fa-print', '&#128269;': 'fa-magnifying-glass', '&#128270;': 'fa-magnifying-glass',
    '&#9203;': 'fa-hourglass-half', '&#8987;': 'fa-hourglass-half', '&#9993;': 'fa-envelope', '&#128274;': 'fa-lock',
    '&#128230;': 'fa-box', '&#128100;': 'fa-user', '&#128209;': 'fa-file-invoice', '&#128177;': 'fa-money-bill-transfer',
    '&#11014;': 'fa-upload', '&#9432;': 'fa-circle-info', '&#8942;': 'fa-ellipsis-vertical', '&#8618;': 'fa-share',
    '&#9776;': 'fa-bars', '➜': 'fa-arrow-right',
    '🟢': 'fa-circle', '🔴': 'fa-circle', '🟠': 'fa-circle', '🟡': 'fa-circle',
}
COLOR = {'🟢': 'green', '🔴': 'red', '🟠': 'orange', '🟡': 'amber'}

def icon_for(tok, after):
    a = after[:60].lower()
    cls = BASE[tok]
    if tok in ('📊', '&#128202;') and ('excel' in a or 'kardex completo' in a):
        cls = 'fa-file-excel'
    elif tok in ('💾', '&#128190;') and 'txt' in a:
        cls = 'fa-file-lines'
    elif tok in ('📄', '&#128196;') and (a.startswith(' pdf') or a.startswith(' boleta')):
        cls = 'fa-file-pdf'
    elif tok in ('📄', '&#128196;') and a.startswith(' exportar'):
        cls = 'fa-file-export'
    elif tok == '🔄' and 'recalcular' in a:
        cls = 'fa-rotate'
    elif tok in ('📝', '&#128221;') and ('requerimiento' in a or 'atendiendo' in a):
        cls = 'fa-clipboard-list'
    elif tok == '📥' and 'jalar' in a:
        cls = 'fa-inbox'
    return cls

toks = sorted(BASE, key=len, reverse=True)
rx = re.compile('(' + '|'.join(re.escape(t) for t in toks) + ')' + VS)
SKIP_LINE_SNIPPETS = ('/* Menu lateral como cajon',)  # comentario CSS
out, changed = [], 0
for line in s.split('\n'):
    if any(x in line for x in SKIP_LINE_SNIPPETS):
        out.append(line); continue
    def sub(m):
        global changed
        tok = m.group(1)
        cls = icon_for(tok, line[m.end():])
        changed += 1
        return f'<i data-ico{"=" + COLOR[tok] if tok in COLOR else ""} class={cls}></i>'
    out.append(rx.sub(sub, line))
s = '\n'.join(out)
open(P, 'w', encoding='utf-8').write(s)
print('emojis reemplazados:', changed)
