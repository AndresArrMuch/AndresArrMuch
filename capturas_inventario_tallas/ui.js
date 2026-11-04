// Pantalla: Nuevo item con tallas S/M/L y Registrar movimiento con varias lineas (rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', ALM = '20e9a97f-c3c9-4302-b488-c27f74bdcc1f';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1300 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.endsWith('.css')) return r.fulfill({ body: '', contentType: 'text/css' });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'central@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(2000);
  await p.evaluate(() => { state.view = 'inventory'; state.invTab = 'items'; renderView(); }); await p.waitForTimeout(1500);
  const notice = () => p.evaluate(() => (document.querySelector('.notice') || {}).innerText || '');
  // 1) Nuevo item con tallas
  await p.evaluate(() => { const d = [...document.querySelectorAll('details')].find(x => x.innerText.includes('Nuevo item de inventario')); d.open = true; d.scrollIntoView(); });
  await p.fill('#i-code', 'BSTL260708NG65'); await p.fill('#i-cat', 'DESCARTABLES'); await p.fill('#i-desc', 'NITRILO VERDE X100 GUANTES DE 6.5 GRAMOS');
  await p.fill('#i-secondary-desc', 'VERDE'); await p.fill('#i-brand', 'BSTL'); await p.fill('#i-cost', '8.5'); await p.fill('#i-sale-price', '12');
  await p.click('#i-tallas-sml'); await p.waitForTimeout(300);
  R.vista_previa_tallas = await p.innerText('#i-tallas-preview');
  await p.locator('#i-tallas-box').screenshot({ path: `${OUT}/1_tallas_vista_previa.png` });
  await p.evaluate(() => { const d = [...document.querySelectorAll('details')].find(x => x.innerText.includes('Nuevo item de inventario')); d.scrollIntoView(); });
  await p.screenshot({ path: `${OUT}/1b_nuevo_item_con_tallas.png` });
  await p.click('#createInventoryItemBtn'); await p.waitForTimeout(3500);
  R.aviso_creacion = await notice();
  // 2) Registrar movimiento: abierto con las 3 tallas
  R.lineas_precargadas = await p.evaluate(() => [...document.querySelectorAll('#m-lines .m-line')].map(r => r.querySelector('.ml-item input').value + ' | costo ' + r.querySelector('.ml-cost').value));
  R.movimiento_abierto = await p.evaluate(() => document.getElementById('inv-mov-details')?.open);
  await p.selectOption('#m-warehouse', ALM);
  const qtys = ['100', '200', '300'];
  for (let i = 0; i < 3; i++) await p.locator('#m-lines .m-line .ml-qty').nth(i).fill(qtys[i]);
  // una cuarta linea con otro producto elegido a mano
  await p.click('#m-add-line'); await p.waitForTimeout(200);
  const inp = p.locator('#m-lines .m-line').nth(3).locator('.ml-item input');
  await inp.click(); await inp.type('TERMOMETRO', { delay: 20 }); await p.waitForTimeout(600);
  R.opcion_elegida = await p.evaluate(() => {
    const dd = [...document.body.children].filter(e => e.tagName === 'DIV' && e.style.position === 'fixed' && e.style.display !== 'none' && e.children.length);
    const opt = dd.length ? dd[dd.length - 1].children[0] : null; if (!opt) return 'sin opciones';
    opt.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); return opt.innerText.split('\n')[0];
  });
  await p.locator('#m-lines .m-line').nth(3).locator('.ml-qty').fill('5');
  await p.dispatchEvent('#m-lines .m-line:nth-child(4) .ml-qty', 'input');
  await p.fill('#m-notes', 'Factura proveedor F001-000123');
  R.total_lineas = await p.innerText('#m-lines-total');
  await p.evaluate(() => document.getElementById('inv-mov-details').scrollIntoView());
  await p.screenshot({ path: `${OUT}/2_movimiento_varias_lineas.png` });
  await p.click('#createInventoryMovementBtn'); await p.waitForTimeout(3500);
  R.aviso_movimiento = await notice();
  R.kardex = await p.evaluate(async (alm) => {
    const r = await api('/api/inventory/' + state.companyId + '/movements?page=1&per_page=200');
    const list = (r.data && (r.data.data || r.data.items)) || r.data || [];
    const items = state.cache.inventory_items || [];
    return list.filter(m => m.warehouse_id === alm && m.notes === 'Factura proveedor F001-000123')
      .map(m => (items.find(i => i.id === m.item_id) || {}).item_code + ' ' + m.movement_type + ' ' + m.quantity + ' @ ' + m.unit_cost + ' saldo ' + m.balance_quantity);
  }, ALM);
  // 3) Volver a crear las mismas tallas: debe rechazar sin crear nada
  await p.evaluate(() => { const d = [...document.querySelectorAll('details')].find(x => x.innerText.includes('Nuevo item de inventario')); d.open = true; });
  await p.fill('#i-code', 'BSTL260708NG65'); await p.fill('#i-cat', 'DESCARTABLES'); await p.fill('#i-desc', 'NITRILO VERDE X100 GUANTES DE 6.5 GRAMOS');
  await p.click('#i-tallas-sml'); await p.waitForTimeout(300);
  R.vista_previa_repetidos = await p.innerText('#i-tallas-preview');
  await p.click('#createInventoryItemBtn'); await p.waitForTimeout(2000);
  R.aviso_repetidos = await notice();
  await p.screenshot({ path: `${OUT}/3_tallas_ya_existen.png` });
  // 4) Item suelto sin tallas (como antes)
  await p.evaluate(() => { state.view = 'inventory'; renderView(); }); await p.waitForTimeout(1000);
  await p.evaluate(() => { const d = [...document.querySelectorAll('details')].find(x => x.innerText.includes('Nuevo item de inventario')); d.open = true; });
  await p.fill('#i-code', 'ITEMSUELTO01'); await p.fill('#i-cat', 'GENERAL'); await p.fill('#i-desc', 'ITEM SIN TALLAS');
  await p.click('#createInventoryItemBtn'); await p.waitForTimeout(2500);
  R.aviso_item_suelto = await notice();
  console.log(JSON.stringify(R, null, 1)); await b.close();
})();
