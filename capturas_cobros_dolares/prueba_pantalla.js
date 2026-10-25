// Ventana de cobro de una factura en dolares (F001-000004, US$ 100, TC 3.75) al BCP ME
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1400, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1500);
  await p.evaluate(() => { state.view = 'banks'; renderView(); openQuickPaymentModal('sale', 'FU'); }); await p.waitForTimeout(1200);
  R.ventana = await p.evaluate(() => document.getElementById('qp-modal')?.innerText.replace(/\s+/g, ' ').slice(0, 600));
  R.tc_campo = await p.evaluate(() => document.getElementById('qp-rate')?.value || null);
  await p.fill('#qp-date', '2026-10-15'); await p.locator('#qp-date').dispatchEvent('change'); await p.waitForTimeout(300);
  R.tc_tras_fecha = await p.evaluate(() => document.getElementById('qp-rate')?.value || null);
  await p.fill('#qp-amount', '100'); await p.selectOption('#qp-account', 'bk-fika-bcp-me').catch(() => {});
  await p.fill('#qp-reference', 'UI-USD-1');
  await p.screenshot({ path: `${SHOTS}/1_cobro_factura_dolares.png` });
  await p.click('#qp-save-btn'); await p.waitForTimeout(3500);
  R.aviso = await p.evaluate(() => [...document.querySelectorAll('.notice, [id*="notice"]')].map(x => x.innerText).join(' | ').slice(0, 200));
  R.asiento = await p.evaluate(async (cid) => {
    const r = await api('/api/journal-entries/' + cid + '?per_page=50'); const e = (r.data?.data || r.data || []).find(x => String(x.gloss || '').includes('UI-USD-1'));
    return e ? { glosa: e.gloss, lineas: (e.lines || []).map(l => [l.account_code || l.chart_account_id, l.debit_amount, l.credit_amount, l.debit_amount_me, l.credit_amount_me]) } : null;
  }, FIKA);
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
