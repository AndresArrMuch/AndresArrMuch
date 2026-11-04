const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, CID] = process.argv.slice(2);
const W = (p, ms) => p.waitForTimeout(ms);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = []; let reqs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); }); p.on('dialog', d => d.accept());
  p.on('request', r => { if (['POST', 'PUT'].includes(r.method()) && /\/api\/(payments|banks)\//.test(r.url())) reqs.push(r.method() + ' ' + r.url().replace(/^.*\/api\//, '').replace(/[0-9a-f-]{36}/g, 'ID') + (r.postData() ? ' ' + r.postData().replace(/[0-9a-f-]{36}/g, 'ID').slice(0, 260) : '')); });
  const log = (o) => console.log(JSON.stringify(Object.assign({ srv: TAG }, o)));
  const aviso = () => p.evaluate(() => document.querySelector('.notice')?.textContent?.trim().slice(0, 160));
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await W(p, 1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin()); await W(p, 6000);
  const cobros = async () => { await p.click('button[data-view="banks"]'); await W(p, 2000); await p.click('button[data-bank-tab="transacciones"]'); await W(p, 2000); await p.click('#cxc-tab-cobros'); await W(p, 2000); };
  const abrir = async (doc) => { await cobros(); await p.locator('tr.cxc-row', { hasText: doc }).locator('button', { hasText: '+ Cobro' }).click(); await W(p, 1500); };
  const cuenta = async (c) => { const v = await p.evaluate((c) => [...document.querySelectorAll('#qp-account option')].find(o => o.textContent.includes(c))?.value, c); await p.selectOption('#qp-account', v); await W(p, 300); };
  // 1) Doble clic en el cobro individual
  reqs = []; await abrir('F001-31'); await cuenta('191-PEN'); await p.dblclick('#qp-save-btn'); await W(p, 4000);
  log({ paso: '1 doble clic en + Cobro de F001-31 (sin N. operacion)', envios_collect: reqs.filter(r => /collect/.test(r)).length });
  // 2) Cobro con comision: recibido 108 + comision 10
  reqs = []; await abrir('F001-32');
  const opciones = await p.evaluate(() => [...document.querySelectorAll('#qp-account option')].map(o => o.textContent.trim()).filter(Boolean));
  await cuenta('191-PEN'); await p.fill('#qp-amount', '108'); await p.fill('#qp-reference', 'OPC1');
  await p.check('#qp-commission-checkbox'); await p.fill('#qp-commission-amount', '10'); await p.click('#qp-save-btn'); await W(p, 4000);
  log({ paso: '2 cobro F001-32: recibido 108 + comision 10', cuentas_en_lista: opciones, envios: reqs, aviso: await aviso() });
  // 3) Editar ese cobro sin cambiar nada
  await cobros(); await W(p, 5000); const row = p.locator('tr.cxc-row', { hasText: 'F001-32' }).first(); const id = await row.getAttribute('data-doc-id');
  const det = p.locator(`.cxc-detail-row[data-detail-for="${id}"]`); if (!(await det.isVisible())) { await row.click(); await W(p, 5000); }
  log({ filas: await p.locator('tr.cxc-row', { hasText: 'F001-32' }).count(), detalles: await p.evaluate((id) => [...document.querySelectorAll('.cxc-detail-row[data-detail-for="' + id + '"]')].map(d => d.style.display + '|' + d.textContent.trim().slice(0, 80)), id), errs, dbg: (await det.textContent().catch(() => 'sin detalle')).slice(0, 300) });
  await det.locator('.btn-edit-payment').first().click({ timeout: 8000 }); await W(p, 1200);
  const monto = await p.inputValue('#qp-amount'); const comm = await p.inputValue('#qp-commission-edit-amount').catch(() => null);
  reqs = []; await p.click('#qp-save-btn'); await W(p, 4000);
  log({ paso: '3 Editar el cobro de F001-32 sin cambiar nada', monto_mostrado: monto, comision_mostrada: comm, envios: reqs, aviso: await aviso() });
  await p.evaluate(() => document.getElementById('qp-modal')?.remove());
  // 4) Cobro de venta en USD a la cuenta en dolares
  reqs = []; await abrir('F001-41'); await cuenta('191-USD');
  const tc = await p.evaluate(() => { const w = document.getElementById('qp-collect-rate-wrap'); return w ? { visible: w.style.display !== 'none', valor: document.getElementById('qp-collect-rate').value } : null; });
  const saldo = await p.evaluate(() => document.querySelector('#qp-modal')?.textContent.match(/Saldo pendiente:\s*(\S+\s?[0-9.,]+)/)?.[1]?.trim());
  await p.fill('#qp-reference', 'OPU1'); await p.click('#qp-save-btn'); await W(p, 4000);
  log({ paso: '4 cobro F001-41 (US$118, TC factura 3.50) a 191-USD', saldo_mostrado: saldo, campo_tc: tc, envios: reqs, aviso: await aviso() });
  await p.evaluate(() => document.getElementById('qp-modal')?.remove());
  // 5) Varios documentos con comision (F001-51 y F001-52)
  reqs = []; await cobros();
  for (const d of ['F001-51', 'F001-52']) await p.locator('tr.cxc-row', { hasText: d }).locator('.cxc-select-checkbox').check();
  await W(p, 500); await p.click('#cxc-multi-collect'); await W(p, 1200);
  const hayComision = await p.locator('#mp-commission').count();
  const v = await p.evaluate(() => [...document.querySelectorAll('#mp-account option')].find(o => o.textContent.includes('191-PEN'))?.value); await p.selectOption('#mp-account', v);
  await p.fill('#mp-reference', 'OPM1'); if (hayComision) await p.fill('#mp-commission', '6');
  await p.dblclick('#mp-save-btn'); await W(p, 4000);
  log({ paso: '5 cobrar F001-51 + F001-52 con comision 6 (doble clic)', campo_comision: hayComision > 0, envios: reqs, aviso: await aviso() });
  log({ erroresJS: errs });
  await b.close();
})();
