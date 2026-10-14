// Transferencias gratuitas en el navegador (main o rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, OUT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1250 } });
  const log = (...a) => console.log(TAG, '|', ...a);
  const errs = [];
  const nuevaPagina = async (email) => {
    const p = await ctx.newPage();
    p.on('pageerror', e => errs.push(email + ': ' + e.message));
    await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
    return p;
  };
  const tablero = async (p) => p.evaluate(async () => {
    state.view = 'dashboard'; renderView(); await new Promise(r => setTimeout(r, 800));
    return document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !t.startsWith('Actualizado')).slice(0, 40).join(' | ');
  });
  const irInventario = async (p, tab) => { await p.evaluate((t) => { state.view = 'inventory'; state.invTab = t; renderView(); }, tab); await p.waitForTimeout(2500); };
  const kardex = async (p) => p.evaluate(() => [...document.querySelectorAll('tr[data-item-id]')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()).filter(t => /gratuita|TGR01/i.test(t)));
  const saldo = async (p, code, wh) => p.evaluate(async ([code, wh]) => {
    const r = await api('/api/inventory/' + state.companyId + '/movements?per_page=20000');
    const it = state.cache.inventory_items.find(i => i.item_code === code), w = state.cache.warehouses.find(x => x.code === wh);
    const m = (r.data.data || []).filter(m => m.item_id === it.id && m.warehouse_id === w.id)
      .sort((a, b) => (b.movement_date + b.created_at).localeCompare(a.movement_date + a.created_at))[0];
    return m ? m.balance_quantity : 0;
  }, [code, wh]);

  const admin = await nuevaPagina('admin@t.pe');
  const tableroAntes = await tablero(admin);
  log('tablero antes:', tableroAntes);
  await irInventario(admin, 'items');
  log('pestanas inventario:', JSON.stringify(await admin.evaluate(() => [...document.querySelectorAll('[data-inv-tab]')].map(x => x.textContent.trim()))));
  const tieneTG = await admin.evaluate(() => typeof renderFreeTransfersTab === 'function');
  log('tiene transferencias gratuitas:', tieneTG);

  if (tieneTG) {
    // 1) Crear desde ALMFIKA con doble clic
    await irInventario(admin, 'gratuitas');
    await admin.screenshot({ path: `${OUT}/tg_${TAG}_1_formulario.png` });
    log('almacenes (admin):', JSON.stringify(await admin.evaluate(() => [...document.querySelectorAll('#ft-warehouse option')].map(o => o.textContent))));
    await admin.selectOption('#ft-warehouse', { label: 'ALM FIKA' }).catch(async () => {
      const v = await admin.evaluate(() => state.cache.warehouses.find(w => w.code === 'ALMFIKA').id); await admin.selectOption('#ft-warehouse', v); });
    await admin.waitForTimeout(1200);
    await admin.selectOption('#ft-reason', 'muestra');
    await admin.fill('#ft-recipient', 'cliente generico');
    await admin.fill('#ft-responsible', 'Vendedor Prueba');
    const lbl = async (code) => admin.evaluate((c) => { const i = state.cache.inventory_items.find(x => x.item_code === c); return i.item_code + ' - ' + i.description; }, code);
    await admin.fill('#ft-lines tr:nth-child(1) .ft-line-item', await lbl('P0001'));
    await admin.fill('#ft-lines tr:nth-child(1) .ft-line-qty', '4');
    await admin.click('#ft-add-line'); await admin.waitForTimeout(400);
    await admin.fill('#ft-lines tr:nth-child(2) .ft-line-item', await lbl('P0002'));
    await admin.fill('#ft-lines tr:nth-child(2) .ft-line-qty', '1');
    log('stock mostrado por linea:', JSON.stringify(await admin.evaluate(() => [...document.querySelectorAll('.ft-line-stock')].map(x => x.textContent))));
    log('saldo P0001@ALMFIKA antes:', await saldo(admin, 'P0001', 'ALMFIKA'));
    await admin.dblclick('#ft-save');
    await admin.waitForTimeout(3500);
    log('aviso:', await admin.evaluate(() => document.getElementById('ft-msg')?.innerText || ''));
    log('lista:', JSON.stringify(await admin.evaluate(() => [...document.querySelectorAll('#ft-tbody tr.ft-row')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()))));
    log('saldo P0001@ALMFIKA despues:', await saldo(admin, 'P0001', 'ALMFIKA'));
    await admin.screenshot({ path: `${OUT}/tg_${TAG}_2_creada.png` });

    // 2) Mas de lo que hay
    await admin.fill('#ft-recipient', 'cliente generico');
    await admin.fill('#ft-responsible', 'Vendedor Prueba');
    await admin.fill('#ft-lines tr:nth-child(1) .ft-line-item', await lbl('P0003'));
    await admin.fill('#ft-lines tr:nth-child(1) .ft-line-qty', '50');
    await admin.click('#ft-save'); await admin.waitForTimeout(2500);
    log('sobre stock:', await admin.evaluate(() => document.getElementById('ft-msg')?.innerText || ''));
    log('documentos en lista:', await admin.evaluate(() => document.querySelectorAll('#ft-tbody tr.ft-row').length));
    await admin.screenshot({ path: `${OUT}/tg_${TAG}_3_sobre_stock.png` });

    // 3) Kardex de movimientos
    await irInventario(admin, 'items'); await admin.waitForTimeout(1500);
    log('kardex:', JSON.stringify(await kardex(admin)));
    await admin.evaluate(() => { document.getElementById('kardex-toggle-header')?.click(); });
    await admin.waitForTimeout(600);
    await admin.screenshot({ path: `${OUT}/tg_${TAG}_4_kardex.png`, fullPage: true });

    // 4) Imprimir
    await irInventario(admin, 'gratuitas');
    const [pop] = await Promise.all([admin.waitForEvent('popup'), admin.click('[data-ft-print]')]);
    await pop.waitForTimeout(800);
    log('impresion:', (await pop.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').slice(0, 600));
    await pop.screenshot({ path: `${OUT}/tg_${TAG}_5_impresion.png`, fullPage: true });
    await pop.close();

    // 5) Encargado de tienda: solo su tienda y el central; no puede anular
    const nilton = await nuevaPagina('ventas2@fikaperu.com');
    await irInventario(nilton, 'gratuitas');
    log('almacenes (Nilton, Malvinas):', JSON.stringify(await nilton.evaluate(() => [...document.querySelectorAll('#ft-warehouse option')].map(o => o.textContent + (o.selected ? ' [elegido]' : '')))));
    log('Nilton ve boton Anular:', await nilton.evaluate(() => document.querySelectorAll('[data-ft-void]').length));
    await nilton.screenshot({ path: `${OUT}/tg_${TAG}_6_encargado.png` });
    await nilton.close();

    // 6) Anular (admin): stock vuelve
    admin.once('dialog', d => d.accept('Muestras devueltas'));
    await admin.click('[data-ft-void]'); await admin.waitForTimeout(3000);
    log('anular aviso:', await admin.evaluate(() => document.getElementById('ft-msg')?.innerText || ''));
    log('lista despues de anular:', JSON.stringify(await admin.evaluate(() => [...document.querySelectorAll('#ft-tbody tr.ft-row')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()))));
    log('saldo P0001@ALMFIKA tras anular:', await saldo(admin, 'P0001', 'ALMFIKA'));
    await admin.screenshot({ path: `${OUT}/tg_${TAG}_7_anulada.png` });
    await irInventario(admin, 'items'); await admin.waitForTimeout(1500);
    log('kardex tras anular:', JSON.stringify(await kardex(admin)));
  }
  // 7) Tablero (Ventas del mes, Por Cobrar...) despues: igual al de antes
  const tableroDespues = await tablero(admin);
  log('tablero identico antes/despues:', tableroAntes === tableroDespues);
  log('errores JS:', JSON.stringify(errs));
  await b.close();
})();
