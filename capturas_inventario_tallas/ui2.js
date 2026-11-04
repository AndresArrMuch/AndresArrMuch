// Pantalla con parametro apagado y encendido; roles; documento obligatorio; tallas y Excel
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT_OFF, PORT_ON, OUT, XLS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', ALM = '20e9a97f-c3c9-4302-b488-c27f74bdcc1f';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const entrar = async (port, email) => {
    const ctx = await b.newContext({ viewport: { width: 1600, height: 1300 }, timezoneId: 'America/Lima' });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(email + ': ' + e.message));
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('xlsx.full.min.js')) return r.fulfill({ path: '/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/imp/xlsx.full.min.js', contentType: 'application/javascript' });
      if (u.endsWith('.css')) return r.fulfill({ body: '', contentType: 'text/css' });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${port}/erp`); await p.waitForTimeout(800);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1500);
    await p.evaluate(() => { state.view = 'inventory'; state.invTab = 'items'; renderView(); }); await p.waitForTimeout(2000);
    return p;
  };
  const visible = (p) => p.evaluate(() => Object.fromEntries(['i-tallas-box', 'inv-import-details', 'm-add-line', 'm-doc-row'].map(id => [id, !!document.getElementById(id) && document.getElementById(id).style.display !== 'none'])));
  const notice = (p) => p.evaluate(() => (document.querySelector('.notice') || {}).innerText || '');
  // 1) Parametro apagado: todo como antes (una linea, ruta de siempre)
  const off = await entrar(PORT_OFF, 'central@t.pe');
  R.apagado_visible = await visible(off);
  await off.evaluate(() => { document.getElementById('inv-mov-details').open = true; });
  await off.selectOption('#m-warehouse', ALM);
  const inp = off.locator('#m-lines .m-line').nth(0).locator('.ml-item input');
  await inp.click(); await inp.type('TERMOMETRO', { delay: 20 }); await off.waitForTimeout(500);
  await off.evaluate(() => { const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display !== 'none' && e.children.length); dd[dd.length - 1].children[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); });
  await off.locator('#m-lines .ml-qty').nth(0).fill('2'); await off.locator('#m-lines .ml-cost').nth(0).fill('0'); await off.fill('#m-notes', 'como antes');
  await off.evaluate(() => document.getElementById('inv-mov-details').scrollIntoView());
  await off.screenshot({ path: `${OUT}/v2_1_apagado_como_antes.png` });
  await off.click('#createInventoryMovementBtn'); await off.waitForTimeout(2500);
  R.apagado_movimiento_simple = await notice(off);
  // 2) Encendido pero rol no autorizado (Tesoreria)
  const tes = await entrar(PORT_ON, 'tesoreria@t.pe');
  R.encendido_tesoreria_visible = await visible(tes);
  // 3) Encendido con AlmacenGeneral: tallas -> movimiento con documento
  const p = await entrar(PORT_ON, 'central@t.pe');
  R.encendido_almacen_visible = await visible(p);
  await p.evaluate(() => { const d = [...document.querySelectorAll('details')].find(x => x.innerText.includes('Nuevo item de inventario')); d.open = true; });
  await p.fill('#i-code', 'BSTL260708NG65'); await p.fill('#i-cat', 'DESCARTABLES'); await p.fill('#i-desc', 'NITRILO VERDE X100 GUANTES DE 6.5 GRAMOS');
  await p.fill('#i-secondary-desc', 'VERDE'); await p.fill('#i-cost', '8.5'); await p.fill('#i-sale-price', '12');
  await p.click('#i-tallas-sml'); await p.click('#createInventoryItemBtn'); await p.waitForTimeout(3500);
  R.tallas = await notice(p);
  await p.waitForTimeout(800);
  await p.selectOption('#m-warehouse', ALM);
  for (let i = 0; i < 3; i++) await p.locator('#m-lines .m-line .ml-qty').nth(i).fill(String((i + 1) * 100));
  // sin documento -> error en pantalla
  await p.click('#createInventoryMovementBtn'); await p.waitForTimeout(800);
  R.sin_documento = await notice(p);
  await p.selectOption('#m-doc-type', 'factura_compra'); await p.fill('#m-doc-number', 'F001-000123');
  // costo 0.01 -> error en pantalla
  await p.locator('#m-lines .ml-cost').nth(1).fill('0.01');
  await p.click('#createInventoryMovementBtn'); await p.waitForTimeout(800);
  R.costo_relleno = await notice(p);
  await p.locator('#m-lines .ml-cost').nth(1).fill('8.5');
  // "para facturar" en el numero -> error del servidor
  await p.fill('#m-doc-number', 'para facturar 01');
  await p.click('#createInventoryMovementBtn'); await p.waitForTimeout(1500);
  R.para_facturar = await notice(p);
  await p.fill('#m-doc-number', 'F001-000123'); await p.fill('#m-notes', 'Llegada del proveedor');
  await p.evaluate(() => document.getElementById('inv-mov-details').scrollIntoView());
  await p.screenshot({ path: `${OUT}/v2_2_movimiento_con_documento.png` });
  await p.click('#createInventoryMovementBtn'); await p.waitForTimeout(3000);
  R.movimiento_ok = await notice(p);
  // 4) Excel con el parametro encendido
  await p.evaluate(() => { const d = document.getElementById('inv-import-details'); d.open = true; });
  await p.setInputFiles('#imp-file', XLS); await p.click('#imp-leer'); await p.waitForTimeout(1500);
  await p.fill('#imp-all-cat', 'DESCARTABLES'); await p.fill('#imp-all-cost', '7.2'); await p.click('#imp-aplicar'); await p.waitForTimeout(300);
  R.excel_resumen = await p.innerText('#imp-resumen');
  await p.click('#imp-crear'); await p.waitForTimeout(3500);
  R.excel_crear = await notice(p);
  R.excel_movimiento_lineas = await p.evaluate(() => document.querySelectorAll('#m-lines .m-line').length);
  console.log(JSON.stringify(R, null, 1)); await b.close();
})();
