// Destinatario: busqueda de clientes compartidos en el navegador (main o rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch();
  const log = (...a) => console.log(TAG, '|', ...a);
  const errs = [];
  const entrar = async (email, cid, nombre) => {
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
    await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
    // Directo a la pestana, sin pasar por Ventas y sin clientes en memoria
    await p.evaluate(() => { state.cache.customers = []; state.view = 'inventory'; state.invTab = 'gratuitas'; renderView(); });
    await p.waitForTimeout(2500);
    return p;
  };
  const sugerencias = async (p, texto) => {
    await p.fill('#ft-recipient', ''); await p.type('#ft-recipient', texto, { delay: 40 }); await p.waitForTimeout(1200);
    return p.evaluate(() => {
      const box = document.getElementById('ft-recipient-sug');
      if (box) return box.style.display === 'none' ? [] : [...box.querySelectorAll('.ft-sug')].map(x => x.innerText.trim());
      const dl = document.getElementById('ft-customers-dl'); const v = document.getElementById('ft-recipient').value.toLowerCase();
      return dl ? [...dl.options].map(o => o.value).filter(x => x.toLowerCase().includes(v)) : [];  // main: lo que ofreceria el datalist
    });
  };
  const elegir = async (p, texto, contiene) => {
    await sugerencias(p, texto);
    const ok = await p.evaluate((c) => { const el = [...document.querySelectorAll('#ft-recipient-sug .ft-sug')].find(x => x.innerText.includes(c)); if (!el) return false; el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); return true; }, contiene);
    if (!ok) await p.fill('#ft-recipient', (await p.evaluate(() => document.querySelector('#ft-customers-dl option')?.value)) || texto);  // main: valor del datalist
    await p.dispatchEvent('#ft-recipient', 'input'); await p.waitForTimeout(300);
    return p.evaluate(() => [document.getElementById('ft-recipient').value, document.getElementById('ft-recipient-hint')?.innerText || '']);
  };
  const guardar = async (p, itemCode) => {
    await p.fill('#ft-responsible', 'Prueba');
    const lbl = await p.evaluate((c) => { const i = state.cache.inventory_items.find(x => x.item_code === c); return i.item_code + ' - ' + i.description; }, itemCode);
    await p.fill('#ft-lines tr:nth-child(1) .ft-line-item', lbl); await p.fill('#ft-lines tr:nth-child(1) .ft-line-qty', '1');
    await p.click('#ft-save'); await p.waitForTimeout(3000);
    return p.evaluate(() => {
      const fila = document.querySelector('#ft-tbody tr.ft-row');
      return [document.getElementById('ft-msg')?.innerText.trim() || '', fila ? fila.children[0].innerText + ' | destinatario: ' + fila.children[4].innerText : ''];
    });
  };

  // 1) Gerencia FIKA
  const g = await entrar('admin@t.pe', FIKA, 'gerencia FIKA');
  log('FIKA clientes en memoria (Ventas no abierta):', await g.evaluate(() => (state.cache.customers || []).length));
  log('FIKA escribe "1045":', JSON.stringify(await sugerencias(g, '1045')));
  await g.screenshot({ path: `${OUT}/dest_${TAG}_1_fika_1045.png` });
  log('FIKA escribe "SANDOVAL":', JSON.stringify(await sugerencias(g, 'SANDOVAL')));
  log('FIKA escribe "fl" (2 letras):', JSON.stringify(await sugerencias(g, 'fl')));
  log('FIKA escribe "flumisa":', JSON.stringify(await sugerencias(g, 'flumisa')));
  log('FIKA elige SANDOVAL:', JSON.stringify(await elegir(g, 'SANDOVAL', 'SANTISTEBAN')));
  log('FIKA guarda:', JSON.stringify(await guardar(g, 'P0001')));
  await g.screenshot({ path: `${OUT}/dest_${TAG}_2_fika_guardada.png` });
  log('FIKA elige FLUMISA EIRL:', JSON.stringify(await elegir(g, 'flumisa eirl', 'FLUMISA EIRL')));
  log('FIKA guarda:', JSON.stringify(await guardar(g, 'P0001')));
  await g.fill('#ft-recipient', 'cliente generico'); await g.dispatchEvent('#ft-recipient', 'input');
  log('FIKA texto libre guarda:', JSON.stringify(await guardar(g, 'P0001')));
  // 2) Encargado de tienda FIKA
  const n = await entrar('ventas2@fikaperu.com', FIKA, 'tienda FIKA');
  log('Tienda FIKA escribe "1045":', JSON.stringify(await sugerencias(n, '1045')));
  log('Tienda FIKA elige SANDOVAL:', JSON.stringify(await elegir(n, 'sandoval s', 'SANTISTEBAN')));
  log('Tienda FIKA guarda:', JSON.stringify(await guardar(n, 'P0001')));
  // 3) Gerencia y tienda FLUMISA
  const f = await entrar('admin@t.pe', FLU, 'gerencia FLUMISA');
  log('FLUMISA escribe "1045":', JSON.stringify(await sugerencias(f, '1045')));
  log('FLUMISA escribe "SANDOVAL":', JSON.stringify(await sugerencias(f, 'SANDOVAL')));
  log('FLUMISA elige SANDOVAL y guarda:', JSON.stringify(await elegir(f, 'SANDOVAL', 'SANTISTEBAN')), JSON.stringify(await guardar(f, 'P0001')));
  await f.screenshot({ path: `${OUT}/dest_${TAG}_3_flumisa.png` });
  const t = await entrar('ventas1@fikaperu.com', FLU, 'tienda FLUMISA');
  log('Tienda FLUMISA escribe "SANDOVAL":', JSON.stringify(await sugerencias(t, 'SANDOVAL')));
  log('errores JS:', JSON.stringify(errs));
  await b.close();
})();
