// Prueba en navegador de la pestana Alquiler (rama claude/alquiler-cxp)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const PORT = process.argv[2] || '5293';
const CID = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
const OUT = process.argv[3] || '.';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForTimeout(5000);
  const notice = () => p.evaluate(() => document.querySelector('[class*=notice]')?.textContent?.trim() || '');
  const rows = () => p.evaluate(() => [...document.querySelectorAll('#pur-tbody tr')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()));
  const pickSupplier = async (text) => {
    const inp = p.locator('#al-supplier-ac input'); await inp.click(); await inp.fill(text); await p.waitForTimeout(500);
    await p.locator('div[style*="999999"]:visible > div').first().dispatchEvent('mousedown'); await p.waitForTimeout(300);
  };
  await p.evaluate(async () => { state.view = 'purchases'; await loadModuleData(); renderView(); }); await p.waitForTimeout(1500);
  console.log('Pestanas:', JSON.stringify(await p.evaluate(() => [...document.querySelectorAll('[data-purchase-tab]')].map(b => b.textContent.trim()))));
  await p.click('[data-purchase-tab="rent"]'); await p.waitForTimeout(800);
  await p.click('#togglePurchaseRentFormBtn'); await p.waitForTimeout(1200);
  console.log('Cuenta de gasto:', await p.evaluate(() => { const s = document.getElementById('al-expense-account'); return s.options[s.selectedIndex]?.text + (s.disabled ? ' (fija)' : ''); }));
  // 1) Alquiler en soles
  await pickSupplier('JUAN');
  await p.fill('#al-corr', '000123');
  await p.fill('#al-date', '2026-10-05'); await p.dispatchEvent('#al-date', 'change'); await p.waitForTimeout(400);
  await p.fill('#al-due-date', '2026-10-15');
  await p.fill('#al-desc', 'Alquiler local Malvinas octubre 2026');
  await p.fill('#al-amount', '1500'); await p.dispatchEvent('#al-amount', 'input');
  console.log('Periodo elegido por la fecha:', await p.evaluate(() => { const s = document.getElementById('al-period-id'); return s.options[s.selectedIndex]?.text; }));
  console.log('Total en pantalla:', await p.textContent('#al-total-display'));
  await p.locator('#purchase-rent-form-wrap').screenshot({ path: `${OUT}/alq_1_formulario_soles.png` });
  await p.click('#createRentPurchaseBtn'); await p.waitForTimeout(3500);
  console.log('Aviso:', await notice()); console.log('Lista:', JSON.stringify(await rows()));
  // 2) Duplicado (mismo arrendador y correlativo)
  await p.click('#togglePurchaseRentFormBtn'); await p.waitForTimeout(1000);
  await pickSupplier('JUAN'); await p.fill('#al-corr', '000123'); await p.fill('#al-date', '2026-10-05'); await p.dispatchEvent('#al-date', 'change');
  await p.fill('#al-desc', 'Repetido'); await p.fill('#al-amount', '10'); await p.dispatchEvent('#al-amount', 'input');
  await p.click('#createRentPurchaseBtn'); await p.waitForTimeout(2000);
  console.log('Duplicado:', await p.textContent('#rent-toast'));
  // 3) Alquiler en dolares: el tipo de cambio sale de la tabla por la fecha
  await pickSupplier('MARIA'); await p.fill('#al-corr', 'OCT-2026');
  await p.selectOption('#al-currency', 'USD'); await p.fill('#al-date', '2026-10-05'); await p.dispatchEvent('#al-date', 'change'); await p.waitForTimeout(1500);
  await p.fill('#al-desc', 'Alquiler almacen octubre (USD)'); await p.fill('#al-amount', '400'); await p.dispatchEvent('#al-amount', 'input');
  console.log('USD: TC', await p.inputValue('#al-exchange-rate'), '|', await p.textContent('#al-total-display'), '|', await p.textContent('#al-total-pen-display'));
  await p.locator('#purchase-rent-form-wrap').screenshot({ path: `${OUT}/alq_2_formulario_usd.png` });
  await p.click('#createRentPurchaseBtn'); await p.waitForTimeout(3500);
  console.log('Aviso:', await notice()); console.log('Lista:', JSON.stringify(await rows()));
  await p.screenshot({ path: `${OUT}/alq_3_lista.png`, fullPage: false });
  // 4) Editar el alquiler en soles (sin pagos)
  const editId = await p.evaluate(() => (state.cache.purchases || []).find(x => x.document_number === 'AL10203040-000123')?.id);
  await p.click(`[data-action="edit-purchase"][data-id="${editId}"]`); await p.waitForTimeout(2500);
  console.log('Editar: titulo', await p.evaluate(() => document.querySelector('#purchase-rent-form-wrap h4')?.textContent), '| monto', await p.inputValue('#al-amount'), '| proveedor', await p.inputValue('#al-supplier-ac input'));
  await p.fill('#al-amount', '1600'); await p.dispatchEvent('#al-amount', 'input');
  await p.click('#createRentPurchaseBtn'); await p.waitForTimeout(3500);
  console.log('Aviso:', await notice()); console.log('Lista:', JSON.stringify(await rows()));
  // 5) Compra local y Reportes por periodo no muestran alquileres
  await p.click('[data-purchase-tab="local"]'); await p.waitForTimeout(800);
  console.log('Compra local muestra alquileres:', (await rows()).some(r => r.includes('AL1') || r.includes('Alquiler')));
  await p.click('[data-purchase-tab="reports"]'); await p.waitForTimeout(800);
  console.log('Reportes por periodo muestra alquileres:', await p.evaluate(() => _purchaseReportSelection().docs.some(d => d.document_type === 'AL') || [...document.querySelectorAll('#panelBody table')].some(t => /AL10203040|AL50607080/.test(t.innerText))));
  await p.screenshot({ path: `${OUT}/alq_5_reportes_periodo.png`, fullPage: false });
  // 6) Cobranza > Pagos: el alquiler aparece pendiente con su saldo y vencimiento
  await p.evaluate(async () => { state.view = 'banks'; state.bankTab = 'transacciones'; state._cxcMode = 'pagos'; await loadModuleData(); renderView(); }); await p.waitForTimeout(2500);
  const pend = await p.evaluate(() => [...document.querySelectorAll('tr')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()).filter(t => t.includes('AL10203040') || t.includes('AL50607080')));
  console.log('Pagos pendientes con alquileres:', JSON.stringify(pend));
  await p.screenshot({ path: `${OUT}/alq_4_pagos_pendientes.png`, fullPage: false });
  console.log('Errores JS:', JSON.stringify(errs));
  await b.close();
})();
