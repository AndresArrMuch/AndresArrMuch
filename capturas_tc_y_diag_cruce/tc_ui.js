const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path'); const [PORT, OUT, FA] = process.argv.slice(2); const R = { errores: [] };
(async () => {
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 1500, height: 1100 }, timezoneId: 'America/Lima' })).newPage();
  p.on('pageerror', e => R.errores.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => { const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) }); return r.abort(); });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(900);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433').catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading); await p.waitForTimeout(2500);
  // Libro Diario
  await p.evaluate(() => { state.view = 'journal'; renderView(); }); await p.waitForFunction(() => document.querySelector('#mj-card #mj-save')); await p.waitForTimeout(800);
  const tcDiario = () => p.evaluate(() => (document.getElementById('mj-card').innerText.match(/Tipo de cambio\s*\n([^\n]+)/i) || [])[1]);
  for (const [fecha, cur] of [['2026-10-22', 'usd'], ['2026-10-23', 'usd'], ['2026-10-23', 'pen']]) {
    await p.fill('#mj-date', fecha); await p.dispatchEvent('#mj-date', 'change'); await p.waitForTimeout(700);
    await p.check('#mj-cur-' + cur); await p.waitForTimeout(500);
    R['diario ' + fecha + ' ' + cur] = await tcDiario();
    if (fecha === '2026-10-23' && cur === 'usd') await p.screenshot({ path: `${OUT}/tc_diario_23_10_dolares.png`, clip: { x: 290, y: 170, width: 1200, height: 360 } });
  }
  // Bancos
  await p.evaluate(() => { state.view = 'banks'; state.bankTab = 'movimiento'; renderView(); }); await p.waitForTimeout(1500);
  await p.click('.bm-kind[data-kind="counterpart"]'); await p.waitForTimeout(400);
  for (const [bank, fecha] of [['bk-fika-bcp-me', '2026-10-22'], ['bk-fika-bcp-me', '2026-10-23'], ['bk-fika-bcp-mn', '2026-10-23']]) {
    await p.selectOption('#bm-bank', bank); await p.waitForTimeout(1500);
    await p.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await p.waitForTimeout(400);
    await p.fill('#bm-date', fecha); await p.dispatchEvent('#bm-date', 'change'); await p.waitForTimeout(1200);
    await p.fill('#bm-amount', '100'); await p.dispatchEvent('#bm-amount', 'input'); await p.fill('#bm-op', 'X-' + fecha); await p.dispatchEvent('#bm-op', 'input');
    await p.fill('#bm-gloss', 'prueba'); await p.dispatchEvent('#bm-gloss', 'input'); await p.fill('#bm-cp', '103101 EN TRANSITO'); await p.dispatchEvent('#bm-cp', 'change'); await p.waitForTimeout(500);
    R['bancos ' + bank + ' ' + fecha] = await p.evaluate(() => ({ tc: [...document.querySelectorAll('#bm-dyn-info > div')].map(d => d.innerText).find(t => /cambio/.test(t)), tc_check: [...document.querySelectorAll('.bm-check li')].map(li => li.innerText).find(t => /Tipo de cambio/.test(t)), boton: !document.getElementById('bm-save').disabled }));
    if (fecha === '2026-10-23' && bank === 'bk-fika-bcp-me') await p.evaluate(() => document.querySelector('section[data-paso="4"]').scrollIntoView()), await p.screenshot({ path: `${OUT}/tc_bancos_23_10_dolares.png`, fullPage: false });
  }
  console.log(JSON.stringify(R, null, 1)); require('fs').writeFileSync(`${OUT}/tc_ui.json`, JSON.stringify(R, null, 1)); await b.close();
})();
