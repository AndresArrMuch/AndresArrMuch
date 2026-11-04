// Funcion 1: sin clics repetidos. Uso: node f1_test.js <puerto app> <TAG> <log fake> <salida>
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, TAG, LOG, OUT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
const llamadas = (op) => (fs.existsSync(LOG) ? fs.readFileSync(LOG, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : []).filter(x => x.op === op).length;
(async () => {
  const R = { errores_js: [] };
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' })).newPage();
  p.on('pageerror', e => R.errores_js.push(e.message)); p.on('dialog', d => d.accept());
  await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(900);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading); await p.waitForTimeout(2500);
  const saleId = await p.evaluate(() => (state.cache.sales || []).find(s => s.document_number === 'F001-000003')?.id);
  R.venta = saleId ? 'F001-000003' : 'no encontrada';
  // 1) Servidor: 10 solicitudes simultaneas al mismo documento
  for (const [op, metodo, ruta] of [['generar_anulacion', 'POST', 'electronic/void'], ['consultar_comprobante', 'GET', 'electronic/status']]) {
    const antes = llamadas(op);
    R['servidor_10_simultaneas_' + ruta] = await p.evaluate(async ([id, metodo, ruta]) => {
      const reqs = Array.from({ length: 10 }, () => fetch('/api/sales/' + state.companyId + '/' + id + '/' + ruta, { method: metodo, headers: { Authorization: 'Bearer ' + state.token, 'Content-Type': 'application/json' },
        body: metodo === 'POST' ? JSON.stringify({ void_reason: 'prueba' }) : undefined }).then(async r => r.status + ' ' + ((await r.json().catch(() => ({})))?.error?.code || 'OK')));
      const res = await Promise.all(reqs); const c = {}; res.forEach(x => c[x] = (c[x] || 0) + 1); return c;
    }, [saleId, metodo, ruta]);
    R['llamadas_a_nubefact_' + ruta] = llamadas(op) - antes;
  }
  // 2) Pantalla: 10 clics rapidos en "Anular factura" del modal
  await p.evaluate(() => { state.view = 'sales'; state.salesTab = 'invoices'; renderView(); }); await p.waitForTimeout(2500);
  const hay = await p.evaluate((id) => !!document.querySelector(`[data-action="sale-void"][data-id="${id}"]`), saleId);
  R.boton_anular_visible = hay;
  if (hay) {
    await p.evaluate((id) => document.querySelector(`[data-action="sale-void"][data-id="${id}"]`).click(), saleId);
    await p.waitForSelector('#void-sale-confirm');
    const antes = llamadas('generar_anulacion');
    const notices = [];
    await p.exposeFunction('_registrarAviso', (t) => notices.push(t));
    await p.evaluate(() => { const orig = window.setNotice; window.setNotice = function (m, t) { window._registrarAviso((t || '') + ': ' + m); return orig.apply(this, arguments); }; });
    for (let i = 0; i < 10; i++) await p.click('#void-sale-confirm', { force: true, timeout: 2000 }).catch(() => {});
    R.boton_tras_clics = await p.evaluate(() => { const b = document.getElementById('void-sale-confirm'); return b ? { texto: b.innerText, desactivado: b.disabled } : 'modal cerrado'; });
    await p.waitForTimeout(3500);
    R.llamadas_a_nubefact_10_clics = llamadas('generar_anulacion') - antes;
    R.mensajes_mostrados = notices;
    R.boton_despues = await p.evaluate(() => { const b = document.getElementById('void-sale-confirm'); return b ? { texto: b.innerText, desactivado: b.disabled } : 'modal cerrado'; });
  }
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); console.log(JSON.stringify(R, null, 1));
  await b.close();
})();
