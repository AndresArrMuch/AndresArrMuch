// Destinatario con el selector de Ventas (rama) + comparacion del selector de Ventas (main vs rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const log = (...a) => console.log(TAG, '|', ...a); const errs = [];
  const entrar = async (email, cid, nombre, irDirecto = true) => {
    const ctx = await b.newContext({ viewport: { width: 1450, height: 1000 } });
    const p = await ctx.newPage(); p.on('pageerror', e => errs.push(nombre + ': ' + e.message));
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
      const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForTimeout(5000);
    if (irDirecto) { await p.evaluate(() => { state.view = 'inventory'; state.invTab = 'gratuitas'; renderView(); }); await p.waitForTimeout(2500); }
    return p;
  };
  const lista = (p) => p.evaluate(() => {
    const dd = [...document.querySelectorAll('body > div')].filter(d => d.style.position === 'fixed' && d.style.display === 'block' && d.style.zIndex === '999999');
    const d = dd[dd.length - 1]; if (!d) return 'cerrada';
    return [...d.children].map(r => r.innerText.replace(/\n/g, ' · ').trim());
  });
  const hint = (p) => p.evaluate(() => document.getElementById('ft-recipient-hint')?.innerText.trim());
  const escribir = async (p, t) => { await p.fill('#ft-recipient', ''); await p.type('#ft-recipient', t, { delay: 60 }); await p.waitForTimeout(250); };
  const guardar = async (p, itemCode) => {
    await p.fill('#ft-responsible', 'Prueba');
    const lbl = await p.evaluate((c) => { const i = state.cache.inventory_items.find(x => x.item_code === c); return i.item_code + ' - ' + i.description; }, itemCode);
    await p.fill('#ft-lines tr:nth-child(1) .ft-line-item', lbl); await p.fill('#ft-lines tr:nth-child(1) .ft-line-qty', '1');
    await p.click('#ft-save'); await p.waitForTimeout(3000);
    return p.evaluate(() => { const f = document.querySelector('#ft-tbody tr.ft-row'); return [document.getElementById('ft-msg')?.innerText.trim() || '', f ? f.children[0].innerText + ' | ' + f.children[4].innerText : '']; });
  };

  if (TAG === 'rama') {
    const g = await entrar('admin@t.pe', FIKA, 'gerencia FIKA');
    log('clientes en memoria (Ventas no abierta):', await g.evaluate(() => (state.cache.customers || []).length));
    await g.click('#ft-recipient'); await g.waitForTimeout(300);
    const ini = await lista(g); log('clic en el campo, sin escribir:', ini.length, 'clientes:', JSON.stringify(ini.slice(0, 4)));
    await g.screenshot({ path: `${OUT}/sel_rama_1_clic.png` });
    const t0 = Date.now(); await g.keyboard.type('1'); const l1 = await lista(g); const ms = Date.now() - t0;
    log(`1 caracter "1" -> ${l1.length} resultados en ${ms} ms (incluye ida y vuelta del navegador de prueba)`);
    await escribir(g, '1045'); log('escribe 1045:', JSON.stringify(await lista(g)));
    await g.screenshot({ path: `${OUT}/sel_rama_2_1045.png` });
    await escribir(g, 'flumisa'); log('escribe flumisa:', JSON.stringify(await lista(g)));
    await escribir(g, 'zzzz'); log('escribe zzzz:', JSON.stringify(await lista(g)), '| aviso:', await hint(g));
    await g.fill('#ft-recipient', ''); await g.dispatchEvent('#ft-recipient', 'input'); await g.waitForTimeout(200);
    const vuelta = await lista(g); log('borrar el texto vuelve a la lista inicial:', JSON.stringify(vuelta) === JSON.stringify(ini));
    // Teclado: SANDOVAL, flecha abajo x2, Enter
    await escribir(g, 'SANDOVAL'); await g.keyboard.press('ArrowDown'); await g.keyboard.press('ArrowDown'); await g.keyboard.press('Enter'); await g.waitForTimeout(200);
    log('teclado (SANDOVAL, abajo, abajo, Enter):', await g.inputValue('#ft-recipient'), '| aviso:', await hint(g), '| lista:', JSON.stringify(await lista(g)));
    log('guarda:', JSON.stringify(await guardar(g, 'P0001')));
    // Clic: FLUMISA EIRL
    await escribir(g, 'flumisa');
    await g.evaluate(() => { const dd = [...document.querySelectorAll('body > div')].filter(d => d.style.zIndex === '999999' && d.style.display === 'block').pop(); dd.children[0].dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); });
    await g.waitForTimeout(200);
    log('clic en FLUMISA EIRL:', await g.inputValue('#ft-recipient'), '| aviso:', await hint(g));
    log('guarda:', JSON.stringify(await guardar(g, 'P0001')));
    await escribir(g, 'cliente generico'); await g.click('#ft-responsible');
    log('texto libre: aviso:', await hint(g), '| guarda:', JSON.stringify(await guardar(g, 'P0001')));
    // Tienda FIKA y FLUMISA
    const n = await entrar('ventas2@fikaperu.com', FIKA, 'tienda FIKA');
    await n.click('#ft-recipient'); log('tienda FIKA clic:', (await lista(n)).length, 'clientes');
    await escribir(n, '1045'); log('tienda FIKA 1045:', JSON.stringify((await lista(n)).slice(0, 2)));
    const f = await entrar('admin@t.pe', FLU, 'gerencia FLUMISA');
    await f.click('#ft-recipient'); log('FLUMISA clic:', (await lista(f)).length, 'clientes, primeros:', JSON.stringify((await lista(f)).slice(0, 2)));
    await escribir(f, '1045'); log('FLUMISA 1045:', JSON.stringify((await lista(f)).slice(0, 2)));
    await escribir(f, 'flumisa eirl'); log('FLUMISA "flumisa eirl" (registro propio de FIKA, no debe salir):', JSON.stringify(await lista(f)));
    await f.keyboard.press('Escape');
    await escribir(f, 'SANDOVAL'); await f.keyboard.press('ArrowDown'); await f.keyboard.press('Enter');
    log('FLUMISA guarda SANDOVAL:', JSON.stringify(await guardar(f, 'P0001')));
    await f.screenshot({ path: `${OUT}/sel_rama_3_flumisa.png` });
    const t = await entrar('ventas1@fikaperu.com', FLU, 'tienda FLUMISA');
    await escribir(t, 'sandoval'); log('tienda FLUMISA sandoval:', JSON.stringify(await lista(t)));
  }
  // Selector de cliente de Ventas (cotizacion): debe ser igual en main y rama
  const v = await entrar('admin@t.pe', FIKA, 'ventas', false);
  await v.evaluate(() => { state.view = 'sales'; state.salesTab = 'quotations'; state.showQuotationForm = true; renderView(); }); await v.waitForTimeout(2500);
  const inp = '#q-customer-ac input';
  const hay = await v.$(inp);
  if (hay) {
    await v.click(inp); await v.waitForTimeout(300); const a = await lista(v);
    await v.type(inp, '1045', { delay: 50 }); await v.waitForTimeout(300); const c = await lista(v);
    await v.keyboard.press('ArrowDown'); await v.keyboard.press('Enter'); await v.waitForTimeout(200);
    log('VENTAS cotizacion: clic ->', a.length, 'clientes', JSON.stringify(a.slice(0, 2)), '| 1045 ->', JSON.stringify(c.slice(0, 3)), '| tras flecha+Enter valor:', JSON.stringify(await v.inputValue(inp)));
  } else log('VENTAS cotizacion: no se encontro el selector');
  log('errores JS:', JSON.stringify(errs));
  await b.close();
})();
