const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1500);
  await p.click('button[data-view="customers"]'); await p.waitForTimeout(3000);
  R.clientes = await p.evaluate(() => [...document.querySelectorAll('tr.cust-row')].map(tr => [tr.querySelector('.cli-name')?.innerText, tr.querySelector('.c-fact')?.innerText, tr.querySelector('.c-pend')?.innerText]).filter(r => r[0] && /PRUEBA|PONEDORAS/.test(r[0])));
  await p.screenshot({ path: SHOT });
  R.dashboard_ventas_total_js = await p.evaluate(() => (state.cache.sales || []).reduce((a, s) => a + pleAmountFactor(s) * Number(s.total || 0), 0));
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
