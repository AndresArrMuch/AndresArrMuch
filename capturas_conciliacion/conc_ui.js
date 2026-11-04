// Conciliacion bancaria: lo que muestra la pantalla en cada caso (main o rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, OUT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1500, height: 1300 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
  const ver = async (nombre) => {
    await p.waitForTimeout(1800);
    const info = await p.evaluate(() => {
      const card = (t) => { const el = [...document.querySelectorAll('div')].find(d => d.textContent.trim() === t && d.style.textTransform === 'uppercase'); return el ? el.nextElementSibling.innerText.trim().split('\n')[0] : null; };
      const rows = [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')];
      return {
        cuenta: state._concAccount || '(ninguna)', mes: state._concMonth,
        ingresos: card('Total Ingresos'), egresos: card('Total Egresos'), neto: card('Movimiento Neto'),
        filas: rows.length, filas_texto: rows.slice(0, 8).map(r => [r.children[0].innerText.trim(), r.children[1].innerText.trim(), r.children[2].innerText.trim(), r.children[4].innerText.trim(), [...r.querySelectorAll('button')].map(x => x.className.replace('btn small ', '')).join(',')].join(' | ')),
        vacio: document.querySelector('#conc-tabla-tbody td[colspan]')?.innerText.trim() || '',
        aviso_sin_cuenta: document.getElementById('conc-aviso-sin-cuenta')?.innerText.trim() || '',
        aviso_sin_excel: document.getElementById('conc-aviso-sin-excel')?.innerText.trim() || '',
        estado_extracto: document.getElementById('conc-estado-extracto')?.innerText.trim() || '',
        resumen_cuentas: [...document.querySelectorAll('#conc-resumen-cuentas tbody tr')].map(r => r.innerText.replace(/\s+/g, ' ').trim()),
        aviso_carga: document.getElementById('conc-upload-msg')?.innerText.trim() || '',
        sistema_sin_extracto: document.getElementById('conc-sistema-sin-extracto') ? (document.getElementById('conc-sistema-sin-extracto').open ? 'abierta' : 'cerrada') + ': ' + document.querySelector('#conc-sistema-sin-extracto summary').innerText.trim() : '',
        pastillas: [...document.querySelectorAll('.conc-account-pill')].map(x => x.innerText.trim() + (x.style.background.includes('37, 99, 235') ? ' [elegida]' : '')),
      };
    });
    console.log(TAG, '|', nombre, '|', JSON.stringify(info));
    await p.screenshot({ path: `${OUT}/conc_${TAG}_${nombre}.png`, fullPage: false });
    return info;
  };
  const ir = async (mes) => { await p.evaluate(async (m) => { state.view = 'banks'; state.bankTab = 'conciliacion'; state._concMonth = m; state._concYear = m.slice(0, 4); renderView(); await cargarExcelPersistidoConciliacion(); }, mes); };
  const elegir = async (cuenta) => { await p.click(`.conc-account-pill[data-account="${cuenta}"]`); };
  const subir = async (nombre) => {
    await p.setInputFiles('#conc-statement-file', { name: nombre, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('x') });
    await p.waitForTimeout(3000);
  };

  // 1) Sin cuenta elegida, octubre
  await ir('2026-10'); await ver('1_sin_cuenta_octubre');
  // 2) FIKA BCP PEN agosto: sin Excel (caso de produccion)
  await elegir('bank-pen'); await ir('2026-08'); await ver('2_bcp_pen_agosto_sin_excel');
  // 3) BCP PEN octubre: con Excel
  await ir('2026-10'); await ver('3_bcp_pen_octubre_con_excel');
  // 4) BCP USD octubre
  await elegir('bank-usd'); await ver('4_bcp_usd_octubre');
  // 5) Subir un Excel de septiembre para BCP PEN (lectura del archivo simulada; el guardado es real)
  await elegir('bank-pen'); await ir('2026-09');
  await p.route('**/statement-upload', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, message: '2 movimientos extraidos correctamente', data: { filename: 'BCP_MN_setiembre.xlsx', rows: [
    { date: '2026-09-10', description: 'ABONO SEPTIEMBRE', operation_number: 'SEP-1', amount: 900, type: 'in' },
    { date: '2026-09-11', description: 'IMPUESTO ITF', operation_number: 'SEP-2', amount: -0.05, type: 'out' }] } }) }));
  await subir('BCP_MN_setiembre.xlsx'); await ver('5_subida_ok_septiembre');
  // 6) Error al guardar (el servidor responde 500)
  await ir('2026-07');
  await p.unroute('**/statement-upload');
  await p.route('**/statement-upload', r => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, message: '1 movimiento extraido', data: { filename: 'BCP_MN_julio.xlsx', rows: [
    { date: '2026-07-15', description: 'ABONO JULIO', operation_number: 'JUL-1', amount: 4321, type: 'in' }] } }) }));
  await p.route('**/conciliacion-import/bank-pen', r => r.request().method() === 'POST'
    ? r.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ success: false, error: { code: 'X', message: 'Fallo de prueba al guardar' }, message: 'Fallo de prueba al guardar' }) })
    : r.continue());
  await subir('BCP_MN_julio.xlsx'); await ver('6_subida_con_error');
  await p.unroute('**/conciliacion-import/bank-pen');
  // 7) Cambiar de empresa a FLUMISA sin recargar y volver a Conciliacion
  await p.evaluate(async (flu) => { await setActiveCompany(flu, 'FLUMISA PRUEBA SAC'); }, FLU); await ir('2026-10'); await ver('7_cambio_a_flumisa');
  console.log(TAG, '| errores JS:', JSON.stringify(errs));
  await b.close();
})();
