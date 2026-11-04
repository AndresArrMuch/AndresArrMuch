const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, CID, OUT] = process.argv.slice(2);
const W = (p, ms) => p.waitForTimeout(ms);
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ acceptDownloads: true, viewport: { width: 1500, height: 1000 } }); const p = await ctx.newPage();
  await ctx.route(/cdnjs\.cloudflare\.com\/ajax\/libs\/xlsx\//, r => r.fulfill({ path: '/tmp/claude-0/xl/package/dist/xlsx.full.min.js', contentType: 'application/javascript' }));
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('dialog', d => { console.log(JSON.stringify({ srv: TAG, dialogo: d.message().slice(0, 160) })); d.accept(); });
  const log = (o) => console.log(JSON.stringify(Object.assign({ srv: TAG }, o)));
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await W(p, 1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin()); await W(p, 6000);
  // 1) Excel de facturas de setiembre 2026
  await p.click('button[data-view="sales"]'); await W(p, 2500);
  await p.evaluate(() => { state.salesTab = 'reports'; }); await p.click('button[data-view="sales"]'); await W(p, 2500);
  const tab = p.locator('[data-tab="reports"]'); if (await tab.count()) { await tab.first().click(); await W(p, 3000); }
  await p.fill('#sr-year', '2026'); await p.fill('#sr-month', '9');
  const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 60000 }), p.click('#exportSalesExcelBtn')]);
  await dl.saveAs(OUT + '_ventas.xlsx'); log({ paso: '1 Excel de facturas', archivo: dl.suggestedFilename() });
  if (TAG === 'main') { log({ erroresJS: errs }); await b.close(); return; }
  // 2) Reporte DIGEMID
  await p.click('button[data-view="sales"]'); await W(p, 1500);
  await p.evaluate(() => { state.salesTab = 'guides'; }); const gt = p.locator('[data-tab="guides"]'); if (await gt.count()) { await gt.first().click(); await W(p, 3000); }
  await p.click('text=Guías para DIGEMID'); await W(p, 1000);
  log({ paso: '2a valores por defecto', solo_digemid: await p.isChecked('#dgr-only-digemid'), traslados: await p.isChecked('#dgr-include-transfers'), periodo: await p.inputValue('#dgr-period') });
  await p.fill('#dgr-period', '2026-09'); await p.dispatchEvent('#dgr-period', 'change'); await W(p, 3000);
  log({ paso: '2b periodo 2026-09 elegido', desde: await p.inputValue('#dgr-from'), hasta: await p.inputValue('#dgr-to') });
  const [dl0] = await Promise.all([p.waitForEvent('download'), p.click('#dgr-export')]);
  await dl0.saveAs(OUT + '_digemid_periodo.xlsx'); log({ paso: '2c Excel directo del periodo', archivo: dl0.suggestedFilename() });
  log({ paso: '2 reporte DIGEMID por defecto', info: await p.textContent('#dgr-info'), productos_digemid_en_filtro: await p.locator('#dgr-item option').count() - 1 });
  await p.screenshot({ path: OUT + '_digemid_1.png', fullPage: false });
  await p.click('#dgr-places'); await W(p, 4000);
  log({ paso: '3 traer partida/llegada y PDF', primera_fila: await p.evaluate(() => [...document.querySelectorAll('#dgr-table tbody tr')][0]?.innerText.replace(/\s+/g, ' ').slice(0, 300)) });
  await p.screenshot({ path: OUT + '_digemid_2.png', fullPage: false });
  const [dl2] = await Promise.all([p.waitForEvent('download'), p.click('#dgr-export')]);
  await dl2.saveAs(OUT + '_digemid.xlsx'); log({ paso: '4 exportar Excel DIGEMID', archivo: dl2.suggestedFilename() });
  await p.fill('#dgr-series', 'TTT4'); await p.uncheck('#dgr-include-voided'); await p.click('#dgr-search'); await W(p, 2000);
  log({ paso: '5 serie TTT4 sin anuladas', info: await p.textContent('#dgr-info') });
  await p.fill('#dgr-series', ''); await p.check('#dgr-include-transfers'); await p.click('#dgr-search'); await W(p, 2000);
  log({ paso: '6 con traslados', info: await p.textContent('#dgr-info'), tipos: await p.evaluate(() => [...new Set([...document.querySelectorAll('#dgr-table tbody tr')].map(r => r.children[2].innerText))]) });
  await p.click('#dgr-places'); await W(p, 3000);
  const popup = p.waitForEvent('popup', { timeout: 8000 }).catch(() => null);
  await p.locator('.dgr-pdf').first().click(); const pop = await popup;
  log({ paso: '7 boton PDF (fila 1)', abre: pop ? pop.url() : null });
  log({ erroresJS: errs });
  await b.close();
})();
