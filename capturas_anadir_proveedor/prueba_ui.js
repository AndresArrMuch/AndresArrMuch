const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.click('button[data-view="purchases"]'); await p.waitForTimeout(2000);
  const toast = () => p.evaluate(() => [...document.querySelectorAll('[id*="toast"], .notice')].map(x => x.innerText).filter(t => t && !t.includes('Sesion iniciada')).join(' | ').slice(0, 300));
  const opcionesLista = () => p.evaluate(() => { const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display === 'block'); const d = dd[dd.length - 1]; return d ? [...d.children].map(c => c.innerText.replace(/\s+/g, ' ')) : []; });
  // 1) Compra extranjero: escribir y "+ Anadir proveedor"
  await p.evaluate(() => { state.purchaseTab = 'foreign'; renderView(); }); await p.waitForTimeout(1500);
  const inp = p.locator('#pf-supplier-ac input');
  await inp.click(); await inp.type('BLUE SAIL (HONG KONG) TRADING LIMITED', { delay: 5 }); await p.waitForTimeout(500);
  R.lista_extranjero = await opcionesLista();
  await p.screenshot({ path: `${SHOTS}/1_lista_con_anadir.png` });
  await p.evaluate(() => { const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display === 'block'); const d = dd[dd.length - 1]; d.lastChild.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); });
  await p.waitForTimeout(500);
  R.ventana = await p.evaluate(() => ({ abierta: !!document.getElementById('qs-modal'), tipo: document.getElementById('qs-tipo')?.value, nombre: document.getElementById('qs-name')?.value, ruc: document.getElementById('qs-ruc')?.value }));
  await p.fill('#qs-ruc', 'HK-91440300'); await p.fill('#qs-address', 'HONG KONG');
  await p.screenshot({ path: `${SHOTS}/2_ventana_anadir.png` });
  await p.click('#qs-save'); await p.waitForTimeout(2000);
  R.tras_guardar = { aviso: await toast(), campo: await inp.inputValue(), oculto: await p.evaluate(() => !!document.getElementById('pf-supplier').value) };
  // completar y crear la compra
  await p.fill('#pf-series', 'INV'); await p.fill('#pf-corr', 'A260708958H'); await p.fill('#pf-date', '2026-10-09');
  await p.evaluate(() => document.getElementById('pf-date').dispatchEvent(new Event('change')));
  await p.fill('#pf-due-date', '2026-10-09'); await p.selectOption('#pf-country', { index: 1 }).catch(() => {});
  await p.selectOption('#pf-currency', 'USD').catch(() => {}); await p.waitForTimeout(300); await p.fill('#pf-exchange-rate', '3.36');
  await p.fill('#pf-taxed-amount', '0').catch(() => {});
  await p.fill('#pf-desc', 'DAM 118-2026-10-515757'); await p.fill('#pf-qty', '1');
  const cb = p.locator('#pf-has-untaxed-costs'); if (!(await cb.isChecked())) await cb.check();
  await p.fill('#pf-untaxed-amount', '70840');
  await p.evaluate(() => createForeignPurchase()); await p.waitForTimeout(3500);
  R.compra_extranjero = await toast();
  // 2) Alquiler: escribir un RUC nuevo
  await p.evaluate(() => { state.purchaseTab = 'rent'; state.purchaseRentFormVisible = true; renderView(); }); await p.waitForTimeout(1500);
  const ia = p.locator('#al-supplier-ac input');
  if (await ia.count()) {
    await ia.click(); await ia.type('20557450565', { delay: 5 }); await p.waitForTimeout(500);
    R.lista_alquiler = await opcionesLista();
    await p.evaluate(() => { const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display === 'block'); const d = dd[dd.length - 1]; d.lastChild.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); });
    await p.waitForTimeout(400);
    R.ventana_alquiler = await p.evaluate(() => ({ tipo: document.getElementById('qs-tipo')?.value, ruc: document.getElementById('qs-ruc')?.value, nombre: document.getElementById('qs-name')?.value }));
    await p.fill('#qs-name', 'FLUMISA E.I.R.L.'); await p.fill('#qs-address', 'LIMA');
    await p.click('#qs-save'); await p.waitForTimeout(2000);
    R.alquiler_tras_guardar = { aviso: await toast(), campo: await ia.inputValue() };
    // 3) Duplicado: escribir otro nombre y anadir con el MISMO RUC -> elige el existente
    await p.evaluate(() => { const h = document.getElementById('al-supplier'); if (h) h.value = ''; });
    await ia.fill(''); await ia.type('FLUMISA EIRL OTRO', { delay: 5 }); await p.waitForTimeout(400);
    await p.evaluate(() => { const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display === 'block'); const d = dd[dd.length - 1]; d.lastChild.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); });
    await p.waitForTimeout(400);
    await p.fill('#qs-ruc', '20557450565'); await p.fill('#qs-address', 'LIMA');
    await p.click('#qs-save'); await p.waitForTimeout(2000);
    R.duplicado = { aviso: await toast(), campo: await ia.inputValue() };
  } else R.alquiler = 'sin formulario';
  // 4) Compra local: guardar con proveedor no registrado -> abre la ventana sola
  await p.evaluate(() => { state.purchaseTab = 'local'; state.purchaseLocalFormVisible = true; renderView(); }); await p.waitForTimeout(1500);
  const il = p.locator('#p-supplier-ac input'); await il.fill('PROVEEDOR NUEVO SAC'); await p.keyboard.press('Escape');
  await p.fill('#p-series', 'F001').catch(() => {}); await p.fill('#p-corr', '123').catch(() => {});
  await p.evaluate(() => createQuickPurchase()); await p.waitForTimeout(1200);
  R.local_guardar = { aviso: await toast(), ventana_abierta: await p.evaluate(() => !!document.getElementById('qs-modal')), nombre: await p.evaluate(() => document.getElementById('qs-name')?.value) };
  await p.screenshot({ path: `${SHOTS}/3_local_abre_ventana.png` });
  R.proveedores = await p.evaluate(async () => ((await api('/api/suppliers/' + state.companyId + '?page=1&per_page=500')).data?.data || []).map(x => [x.ruc_or_dni, x.business_name, x.supplier_type]));
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
