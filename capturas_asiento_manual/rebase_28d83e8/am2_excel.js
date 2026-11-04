// Excel del Libro Diario (servidor) con los asientos manuales ya registrados
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, OUT, FA] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima', acceptDownloads: true });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    if (u.includes('xlsx/0.18.5/xlsx.full.min.js')) return r.fulfill({ path: '/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/xlsx0185/package/dist/xlsx.full.min.js', contentType: 'application/javascript' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433').catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading); await p.waitForTimeout(2500);
  await p.click('#menu [data-view="journal"]'); await p.waitForFunction(() => state._jd && !state._jd.loading && document.getElementById('jd-info')?.innerText); await p.waitForTimeout(500);
  await p.screenshot({ path: `${OUT}/am2_rama_libro_diario_octubre.png`, fullPage: false });
  const [dl] = await Promise.all([p.waitForEvent('download'), p.evaluate(() => exportJournalExcel())]);
  await dl.saveAs(`${OUT}/am2_rama_excel_octubre.xlsx`);
  console.log('ok', JSON.stringify(errs));
  await b.close();
})();
