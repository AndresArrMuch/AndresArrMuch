const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, EMAIL, CID, OUT] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ acceptDownloads: true }); const p = await ctx.newPage();
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().includes('xlsx') ? r.fulfill({ path: '/tmp/claude-0/xl/package/dist/xlsx.full.min.js' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', EMAIL); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
  await p.evaluate(async () => { state.view = 'inventory'; state.invTab = 'items'; await loadModuleData(); renderView(); }); await p.waitForTimeout(2500);
  if (!(await p.locator('#kardex-export-btn').count())) { console.log(TAG, 'sin boton de exportar kardex (kardex oculto)'); await b.close(); return; }
  await p.evaluate(() => { document.getElementById('kardex-toggle-body').style.display = 'block'; });
  const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 60000 }), p.locator('#kardex-export-btn').click()]);
  await dl.saveAs(`${OUT}/kdx_export_${TAG}.xlsx`); console.log(TAG, 'descargado');
  await b.close();
})();
