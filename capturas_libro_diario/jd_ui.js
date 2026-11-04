// Libro Diario paginado (rama): uso real en la pantalla
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const [PORT, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1100 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('dialog', d => d.accept());
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
    return r.abort();
  });
  const log = (...a) => console.log('rama |', ...a);
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading); await p.waitForTimeout(2500);
  const info = () => p.evaluate(() => document.getElementById('jd-info')?.innerText || '');
  const listo = async () => { await p.waitForFunction(() => !state._jd?.loading && !!document.getElementById('jd-info')?.innerText); await p.waitForTimeout(300); };
  await p.click('#menu [data-view="journal"]'); await listo();
  log('al entrar:', await info(), '| periodo:', await p.inputValue('#jd-period'));
  await p.screenshot({ path: `${OUT}/jd_rama_1_entrar.png`, fullPage: false });
  // Paginacion
  await p.click('[data-jd-page="2"]'); await listo(); log('Siguiente:', await info());
  const ult = await p.evaluate(() => state._jd.data.pagination.pages);
  await p.click(`#jd-pager [data-jd-page="${ult}"]`); await listo(); log('Ultima:', await info());
  // Filtro de glosa: "Cargando..." visible mientras responde y la pagina sigue respondiendo
  const vistos = new Set();
  const obs = setInterval(async () => { try { vistos.add(await p.evaluate(() => document.getElementById('jd-status')?.innerText || '')); } catch (e) {} }, 40);
  await p.type('#journal-glosa-filter', 'planilla', { delay: 60 });
  await p.waitForTimeout(150); await listo(); clearInterval(obs);
  log('glosa "planilla":', await info(), '| indicadores vistos:', JSON.stringify([...vistos].filter(Boolean)));
  await p.fill('#journal-glosa-filter', ''); await p.dispatchEvent('#journal-glosa-filter', 'input'); await p.waitForTimeout(500); await listo();
  // Todos los periodos
  await p.selectOption('#jd-period', ''); await listo(); log('Todos los periodos:', await info());
  // Monto real
  const monto = await p.evaluate(() => state._jd.data.data[0].lines.find(l => l.debit_amount > 0).debit_amount);
  await p.fill('#jd-amount', String(monto)); await p.dispatchEvent('#jd-amount', 'input'); await p.waitForTimeout(500); await listo();
  log('monto', monto, ':', await info());
  await p.fill('#jd-amount', ''); await p.dispatchEvent('#jd-amount', 'input'); await p.waitForTimeout(500);
  await p.selectOption('#jd-period', await p.evaluate(() => getTodayIso().slice(0, 7))); await listo();
  await p.screenshot({ path: `${OUT}/jd_rama_2_filtros.png`, fullPage: false });
  // Crear un asiento (borrador) por el formulario de siempre: Dashboard y lista se actualizan
  const antes = await p.evaluate(() => state.cache.journal_summary.count);
  await p.evaluate(async () => {
    const accs = state.cache.accounts.filter(a => a.accepts_movement !== false);
    const a1 = accs.find(a => a.account_code === '104101'), a2 = accs.find(a => a.account_code === '121201');
    await api('/api/journal-entries/' + state.companyId, { method: 'POST', body: JSON.stringify({ entry_date: getTodayIso(), gloss: 'PRUEBA LIBRO DIARIO PAGINADO', lines: [
      { chart_account_id: a1.id, debit_amount: 123.45, credit_amount: 0 }, { chart_account_id: a2.id, debit_amount: 0, credit_amount: 123.45 }] }) });
  });
  await p.waitForFunction((a) => state.cache.journal_summary.count === a + 1, antes, { timeout: 20000 });
  await p.waitForTimeout(3500); await listo();
  log('tras crear: resumen', antes, '->', await p.evaluate(() => state.cache.journal_summary.count), '| tarjeta:', await p.evaluate(() => [...document.querySelectorAll('#kpis > *')].find(x => /ASIENTOS/.test(x.innerText))?.innerText.replace(/\s+/g, ' ')),
      '| aparece en la lista:', await p.evaluate(() => (state._jd.data.data || []).some(e => e.gloss === 'PRUEBA LIBRO DIARIO PAGINADO')));
  // Eliminarlo desde la lista (borrador)
  await p.evaluate(() => { const e = state._jd.data.data.find(x => x.gloss === 'PRUEBA LIBRO DIARIO PAGINADO'); document.querySelector(`#jd-tbody [data-action="delete-journal"][data-id="${e.id}"]`).click(); });
  await p.waitForFunction((a) => state.cache.journal_summary.count === a, antes, { timeout: 20000 }); await p.waitForTimeout(1500); await listo();
  log('tras eliminar: resumen', await p.evaluate(() => state.cache.journal_summary.count), '| sigue en la lista:', await p.evaluate(() => (state._jd.data.data || []).some(e => e.gloss === 'PRUEBA LIBRO DIARIO PAGINADO')));
  await p.screenshot({ path: `${OUT}/jd_rama_3_lista.png`, fullPage: true });
  log('errores JS:', JSON.stringify(errs));
  await b.close();
})();
