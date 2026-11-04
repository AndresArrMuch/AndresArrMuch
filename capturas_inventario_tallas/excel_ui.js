// Pantalla: Traer items de Excel (panel editable) en la rama
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, OUT, XLS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1300 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('xlsx.full.min.js')) return r.fulfill({ path: '/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/imp/xlsx.full.min.js', contentType: 'application/javascript' });
    if (u.endsWith('.css')) return r.fulfill({ body: '', contentType: 'text/css' });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'central@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(2000);
  await p.evaluate(() => { state.view = 'inventory'; state.invTab = 'items'; renderView(); }); await p.waitForTimeout(1500);
  const notice = () => p.evaluate(() => (document.querySelector('.notice') || {}).innerText || '');
  const filas = () => p.evaluate(() => (state._invImport ? state._invImport.rows : []).map(r => (r.incluir ? '[x] ' : '[ ] ') + r.fila + ' ' + r.item_code + ' | ' + r.secondary_description + ' | ' + (r.category || '-') + ' | ' + r._estado));
  await p.evaluate(() => { const d = document.getElementById('inv-import-details'); d.open = true; d.scrollIntoView(); });
  await p.screenshot({ path: `${OUT}/1_apartado_traer_excel.png` });
  await p.setInputFiles('#imp-file', XLS); await p.click('#imp-leer'); await p.waitForTimeout(1500);
  R.resumen_al_leer = await p.innerText('#imp-resumen');
  R.filas_al_leer = await filas();
  await p.evaluate(() => document.getElementById('inv-import-details').scrollIntoView());
  await p.screenshot({ path: `${OUT}/2_panel_al_leer.png` });
  // Editar: detalle de una fila, quitar una fila, aplicar categoria/unidad/precio a las marcadas
  await p.fill('#inv-import-body .imp-f[data-k="0"][data-f="secondary_description"]', 'AZUL OSCURO');
  await p.dispatchEvent('#inv-import-body .imp-f[data-k="0"][data-f="secondary_description"]', 'change');
  const kManopla = await p.evaluate(() => state._invImport.rows.findIndex(r => r.item_code === 'NMIC25C01768PM2024CG'));
  await p.click(`#inv-import-body .imp-quitar[data-k="${kManopla}"]`); await p.waitForTimeout(300);
  await p.fill('#imp-all-cat', 'descartables'); await p.selectOption('#imp-all-unit', 'NIU'); await p.fill('#imp-all-price', '12.5'); await p.fill('#imp-all-cost', '7.2');
  await p.click('#imp-aplicar'); await p.waitForTimeout(400);
  await p.click('#imp-validar'); await p.waitForTimeout(1500);
  R.aviso_validar = await notice();
  R.resumen_antes_de_crear = await p.innerText('#imp-resumen');
  R.filas_antes_de_crear = await filas();
  await p.evaluate(() => document.getElementById('inv-import-details').scrollIntoView());
  await p.screenshot({ path: `${OUT}/3_panel_editado_validado.png` });
  await p.click('#imp-crear'); await p.waitForTimeout(3500);
  R.aviso_crear = await notice();
  R.movimiento = await p.evaluate(() => ({ abierto: document.getElementById('inv-mov-details')?.open,
    lineas: [...document.querySelectorAll('#m-lines .m-line')].map(r => r.querySelector('.ml-item input').value + ' | costo ' + r.querySelector('.ml-cost').value) }));
  await p.evaluate(() => document.getElementById('inv-mov-details').scrollIntoView());
  await p.screenshot({ path: `${OUT}/4_movimiento_con_items_creados.png` });
  console.log(JSON.stringify(R, null, 1)); await b.close();
})();
