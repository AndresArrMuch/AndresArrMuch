const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, OUT, FA] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 1400, height: 1000 }, timezoneId: 'America/Lima' })).newPage();
  await p.route(/cdnjs\.cloudflare\.com/, r => { const u = r.request().url();
    if (u.includes('all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) }); return r.abort(); });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433').catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading); await p.waitForTimeout(2000);
  await p.evaluate(() => { state.view = 'journal'; renderView(); }); await p.waitForFunction(() => document.querySelector('#mj-card #mj-save'));
  for (const [d, n] of [['2026-07-15', 'cerrado'], ['2026-10-13', 'sin_tc'], ['2026-10-14', 'abierto']]) {
    await p.fill('#mj-date', d); await p.dispatchEvent('#mj-date', 'change'); await p.waitForTimeout(900);
    console.log(n, '|', await p.evaluate(() => { const t = document.getElementById('mj-card').innerText; return [t.match(/Periodo contable\s*([^\n]*\n[^\n]*)/)?.[1], t.match(/Tipo de cambio\s*([^\n]*\n?[^\n]*)/)?.[1]].map(x => (x || '').replace(/\s+/g, ' ')).join(' || '); }));
    await p.locator('#mj-card').screenshot({ path: `${OUT}/am_rama_card_${n}.png` });
  }
  await b.close();
})();
