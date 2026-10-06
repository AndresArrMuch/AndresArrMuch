const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, CID, OUT] = process.argv.slice(2);
const W = (p, ms) => p.waitForTimeout(ms);
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ acceptDownloads: true, viewport: { width: 1500, height: 1000 } }); const p = await ctx.newPage();
  await ctx.route(/cdnjs\.cloudflare\.com\/ajax\/libs\/xlsx\//, r => r.fulfill({ path: '/tmp/claude-0/xl/package/dist/xlsx.full.min.js', contentType: 'application/javascript' }));
  let n = 0; // la TERCERA tanda de guide-places falla (502)
  await ctx.route(/\/api\/guide-reports\/[^/]+\/guide-places$/, r => { n += 1; if (n === 3) return r.fulfill({ status: 502, contentType: 'text/html', body: '<html>502 Bad Gateway</html>' }); return r.continue(); });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  const dialogs = []; p.on('dialog', d => { dialogs.push(d.message().slice(0, 300)); d.accept(); });
  const log = (o) => console.log(JSON.stringify(Object.assign({ srv: TAG }, o)));
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await W(p, 1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin()); await W(p, 6000);
  await p.click('button[data-view="sales"]'); await W(p, 1500);
  await p.evaluate(() => { state.salesTab = 'guides'; }); const gt = p.locator('[data-tab="guides"]'); if (await gt.count()) { await gt.first().click(); await W(p, 3000); }
  await p.click('text=Guías para DIGEMID'); await W(p, 1000);
  await p.fill('#dgr-from', '2026-09-01'); await p.fill('#dgr-to', '2026-09-30'); await p.click('#dgr-search'); await W(p, 3000);
  log({ paso: '1 buscar setiembre', info: await p.textContent('#dgr-info') });
  const visible = async () => p.evaluate(() => {
    // que ve el usuario: texto de avance y mensajes; ¿el aviso global queda tapado por el modal?
    const g = [...document.querySelectorAll('.notice')].find(n => n.textContent.trim());
    let tapado = null;
    if (g) { const r = g.getBoundingClientRect(); const el = document.elementFromPoint(r.left + 5, r.top + 5); tapado = !g.contains(el); }
    const alerta = document.getElementById('dgr-alert');
    return { info: document.getElementById('dgr-info')?.textContent, aviso_global: g ? g.textContent.slice(0, 160) : null, aviso_global_tapado_por_el_modal: tapado,
             alerta_en_el_modal: alerta && alerta.offsetParent ? alerta.innerText.slice(0, 400) : null,
             exportar_habilitado: !document.getElementById('dgr-export').disabled };
  });
  const t0 = Date.now();
  await p.click('#dgr-places'); await W(p, 3000);
  log({ paso: '2 a los 3 s de presionar Traer', ...(await visible()) });
  await p.screenshot({ path: OUT + '_vol_3s.png' });
  // Como un usuario: exporta a los 3 s
  const exp = p.locator('#dgr-export');
  if (await exp.isEnabled()) {
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 15000 }).catch(() => null), exp.click()]);
    if (dl) { await dl.saveAs(OUT + '_vol_a_los_3s.xlsx'); log({ paso: '3 exportar a los 3 s', archivo: 'descargado' }); } else log({ paso: '3 exportar a los 3 s', archivo: 'no se descargo', dialogos: dialogs.splice(0) });
  } else log({ paso: '3 exportar a los 3 s', archivo: 'boton deshabilitado' });
  // Esperar a que termine
  for (let i = 0; i < 120; i++) { await W(p, 1000); if (!(await p.locator('#dgr-places').isDisabled())) break; }
  log({ paso: '4 al terminar', segundos: Math.round((Date.now() - t0) / 1000), ...(await visible()) });
  await p.screenshot({ path: OUT + '_vol_fin.png' });
  const [dl2] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.click('#dgr-export')]);
  await dl2.saveAs(OUT + '_vol_final.xlsx'); log({ paso: '5 exportar al terminar', dialogos: dialogs.splice(0) });
  await p.screenshot({ path: OUT + '_vol_alerta.png' });
  // Reintentar las que fallaron
  await p.click('#dgr-places'); for (let i = 0; i < 60; i++) { await W(p, 1000); if (!(await p.locator('#dgr-places').isDisabled())) break; }
  log({ paso: '6 segundo Traer (reintento)', ...(await visible()) });
  const [dl3] = await Promise.all([p.waitForEvent('download', { timeout: 20000 }), p.click('#dgr-export')]);
  await dl3.saveAs(OUT + '_vol_tras_reintento.xlsx'); log({ paso: '7 exportar tras el reintento', dialogos: dialogs.splice(0), ...(await visible()) });
  await p.screenshot({ path: OUT + '_vol_reintento.png' });
  log({ erroresJS: errs });
  await b.close();
})();
