// Productos plegados en la lista de Transferencias gratuitas (main o rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const entrar = async (email, cid, nombre) => {
    const ctx = await b.newContext({ viewport: { width: 1500, height: 1100 }, acceptDownloads: true });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(nombre + ': ' + e.message));
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
      const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForTimeout(5000);
    return p;
  };
  const ir = async (p, view, extra) => { await p.evaluate(([v, e]) => { state.view = v; Object.assign(state, e || {}); renderView(); }, [view, extra]); await p.waitForTimeout(2500); };
  const filas = (p) => p.evaluate(() => [...document.querySelectorAll('#ft-tbody tr.ft-row')].map(tr => {
    const c = [...tr.children];
    const prod = c[6];
    const det = prod.querySelector('details');
    return {
      numero: c[0].innerText.trim(),
      otras_columnas: c.filter((_, i) => i !== 6).map(x => x.innerText.replace(/\s+/g, ' ').trim()).join(' | '),
      resumen: det ? det.querySelector('summary').innerText.trim() : null,
      abierto: det ? det.open : null,
      productos: [...prod.querySelectorAll('div')].map(x => x.textContent.replace(/\s+/g, ' ').trim()),
      alto_fila: Math.round(tr.getBoundingClientRect().height),
    };
  }));
  const usuarios = [['gerencia_fika', 'admin@t.pe', FIKA], ['gerencia_flumisa', 'admin@t.pe', FLU], ['tienda_fika', 'ventas2@fikaperu.com', FIKA]];
  for (const [nombre, email, cid] of usuarios) {
    const p = await entrar(email, cid, nombre);
    await ir(p, 'inventory', { invTab: 'gratuitas' });
    R[nombre] = { inicial: await filas(p) };
    await p.screenshot({ path: `${OUT}/fold_${TAG}_${nombre}_1_lista.png`, fullPage: true });
    if (nombre === 'gerencia_fika' && TAG === 'rama') {
      const sum = '#ft-tbody tr.ft-row[data-ft="TGR01-000001"] summary';
      const est = async () => p.evaluate(() => document.querySelector('#ft-tbody tr.ft-row[data-ft="TGR01-000001"] details').open);
      const seq = [];
      for (let i = 0; i < 5; i++) { await p.click(sum); await p.waitForTimeout(150); seq.push(await est()); }
      R[nombre].clics_en_TGR01_000001 = seq;
      await p.click('#ft-tbody tr.ft-row[data-ft="TGR01-000004"] summary'); await p.waitForTimeout(150);  // el anulado
      R[nombre].desplegado = await filas(p);
      await p.screenshot({ path: `${OUT}/fold_${TAG}_${nombre}_2_desplegado.png`, fullPage: true });
    }
    if (nombre === 'gerencia_fika') {
      // Imprimir TGR01-000001
      const btn = await p.evaluateHandle(() => document.querySelector('#ft-tbody tr.ft-row[data-ft="TGR01-000001"] [data-ft-print]'));
      const [pop] = await Promise.all([p.waitForEvent('popup'), btn.click()]);
      await pop.waitForTimeout(800);
      R.impresion_TGR01_000001 = await pop.evaluate(() => ({ filas_productos: document.querySelectorAll('tbody tr').length, texto: document.body.innerText.replace(/\s+/g, ' ') }));
      await pop.screenshot({ path: `${OUT}/fold_${TAG}_impresion.png`, fullPage: true }); await pop.close();
      // Excel (misma ruta que el boton)
      const xl = await p.evaluate(async () => { const r = await fetch('/api/free-transfers/' + state.companyId + '/export', { headers: { Authorization: 'Bearer ' + state.token } }); const buf = new Uint8Array(await r.arrayBuffer()); return [r.status, Array.from(buf)]; });
      fs.writeFileSync(`${OUT}/fold_${TAG}_excel.xlsx`, Buffer.from(xl[1])); R.excel_status = xl[0];
      // Resto del sistema
      R.otras = {};
      for (const [k, v, e] of [['inventario_items', 'inventory', { invTab: 'items' }], ['inventario_transferencias', 'inventory', { invTab: 'transfers' }], ['ventas_facturas', 'sales', { salesTab: 'invoices' }], ['ventas_cotizaciones', 'sales', { salesTab: 'quotations' }], ['dashboard', 'dashboard', {}]]) {
        await ir(p, v, e);
        R.otras[k] = await p.evaluate(() => document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | '));
      }
    }
  }
  fs.writeFileSync(`${OUT}/fold_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(TAG, 'listo; errores JS:', JSON.stringify(R.errores_js));
  await b.close();
})();
