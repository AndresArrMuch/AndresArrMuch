// Asiento manual por diario: pantalla (rama) y comparacion de lo existente (main y rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] }; const log = (...a) => console.log(TAG, '|', ...a);
  const entrar = async (email, cid, nombre) => {
    const ctx = await b.newContext({ viewport: { width: 1500, height: 1200 }, timezoneId: 'America/Lima' });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(nombre + ': ' + e.message)); p.on('dialog', d => d.accept('Monto equivocado (prueba)'));
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
      const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(2500);
    return p;
  };
  const conciliacion = async (p, cuenta) => {
    await p.evaluate(async (c) => { state.view = 'banks'; state.bankTab = 'conciliacion'; state._concAccount = c; state._concMonth = '2026-10'; state._concYear = '2026'; renderView(); await cargarExcelPersistidoConciliacion(); }, cuenta);
    await p.waitForTimeout(2500);
    return p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(tr => tr.dataset.op + ' ' + tr.children[2].innerText.trim() + ' ' + tr.children[4].innerText.trim()));
  };
  const listo = async (p) => { await p.waitForFunction(() => state._jd && !state._jd.loading && !!document.getElementById('jd-info')?.innerText, null, { timeout: 60000 }); await p.waitForTimeout(300); };
  const diario = async (p) => {
    await p.evaluate(() => { state.view = 'journal'; renderView(); }); await listo(p);
    return p.evaluate(() => [...document.querySelectorAll('#jd-tbody tr')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()).filter(t => /^M\d\d-/.test(t)));
  };
  // Libro completo desde el servidor (todas las paginas): numero visible, fecha, glosa, debe, haber
  const libro = (p) => p.evaluate(async () => {
    const u = new URLSearchParams({ tz: String(new Date().getTimezoneOffset()), all: '1' });
    const d = (await api('/api/journal-entries/' + state.companyId + '/book?' + u)).data;
    return d.data.map(e => [e.display_number, e.entry_number, e.entry_date, e.gloss, (e.lines || []).reduce((a, l) => a + Number(l.debit_amount || 0), 0).toFixed(2)].join(' | '));
  });
  const tarjetaDashboard = (p) => p.evaluate(() => { renderKPIs(); const a = [...document.querySelectorAll('#kpis > *')].find(x => /ASIENTOS CONTABLES/.test(x.innerText)); return a ? a.innerText.replace(/\s+/g, ' ').trim() : ''; });
  const contador = (p) => p.evaluate(() => ({ resumen: state.cache.journal_summary?.count, info: document.getElementById('jd-info')?.innerText || '' }));
  const admin = await entrar('admin@t.pe', FIKA, 'admin FIKA');
  // Lo que ya existe, antes de registrar nada (debe ser igual en main y rama)
  R.existente = { diario: await diario(admin), libro_completo: await libro(admin), tarjeta_dashboard: await tarjetaDashboard(admin), conciliacion_fika: await conciliacion(admin, 'bk-fika-bcp-mn'),
    dashboard: await admin.evaluate(() => { state.view = 'dashboard'; renderView(); return document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | '); }) };
  if (TAG === 'rama') {
    await diario(admin);
    await admin.waitForFunction(() => document.querySelector('#mj-card #mj-save'), null, { timeout: 30000 });
    await admin.screenshot({ path: `${OUT}/am2_rama_1_formulario.png`, fullPage: true });
    const fillLine = async (i, acc, campo, monto) => {
      await admin.fill(`#mj-card .mj-acc[data-i="${i}"]`, acc); await admin.dispatchEvent(`#mj-card .mj-acc[data-i="${i}"]`, 'change'); await admin.waitForTimeout(200);
      await admin.fill(`#mj-card input.${campo}[data-i="${i}"]:not([disabled])`, String(monto)); await admin.dispatchEvent(`#mj-card input.${campo}[data-i="${i}"]:not([disabled])`, 'input');
    };
    const estado = () => admin.evaluate(() => ({ cuadra: document.getElementById('mj-cuadra')?.innerText, guardar_habilitado: !document.getElementById('mj-save')?.disabled,
      totales: ['mj-t-pd', 'mj-t-pc', 'mj-t-ud', 'mj-t-uc'].map(id => document.getElementById(id)?.innerText),
      periodo: document.querySelector('#mj-card')?.innerText.match(/Periodo contable\s*\n([^\n]+)/)?.[1], tc: document.querySelector('#mj-card')?.innerText.match(/Tipo de cambio\s*\n([^\n]+)/)?.[1] }));
    // Contador antes del caso de los S/ 3,000 (lista en "Todos los periodos")
    await admin.selectOption('#jd-period', ''); await listo(admin);
    R.contador_antes = { ...(await contador(admin)), tarjeta: await tarjetaDashboard(admin) };
    // (1) Asiento original (julio esta cerrado: en la prueba va en junio) Debe 104101 / Haber 103101
    await admin.fill('#mj-date', '2026-06-30'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    R.junio_estado = await estado();
    await admin.fill('#mj-gloss', 'Deposito de FLUMISA por error (original, prueba en junio)'); await admin.dispatchEvent('#mj-gloss', 'input');
    await admin.fill('#mj-op', 'ORIG-UI-1'); await admin.dispatchEvent('#mj-op', 'input');
    await fillLine(0, '104101 - BANCO DE CREDITO MN', 'mj-d', 3000);
    await admin.selectOption('#mj-card .mj-bank[data-i="0"]', 'bk-fika-bcp-mn');
    await fillLine(1, '103101 - EN TRANSITO', 'mj-c', 3000);
    await admin.click('#mj-save'); await admin.waitForTimeout(2500); await listo(admin);
    R.original_guardado = await admin.evaluate(() => document.getElementById('mj-msg')?.innerText);
    R.contador_tras_original = { ...(await contador(admin)), tarjeta: await tarjetaDashboard(admin) };
    // Devolucion de S/ 3,000 del 14/10 (op 01117932)
    await admin.fill('#mj-date', '2026-10-14'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    await admin.fill('#mj-gloss', 'Devolucion a FLUMISA de dinero depositado por error'); await admin.dispatchEvent('#mj-gloss', 'input');
    await admin.fill('#mj-op', '01117932'); await admin.dispatchEvent('#mj-op', 'input');
    await fillLine(0, '103101 - EN TRANSITO', 'mj-d', 3000);
    await fillLine(1, '104101 - BANCO DE CREDITO MN', 'mj-c', 3000);
    R.banco_opciones = await admin.evaluate(() => [...document.querySelectorAll('#mj-card .mj-bank[data-i="1"] option')].map(o => o.textContent));
    await admin.selectOption('#mj-card .mj-bank[data-i="1"]', 'bk-fika-bcp-mn');
    R.devolucion_antes_de_guardar = await estado();
    R.equivalentes_usd_linea = await admin.evaluate(() => [...document.querySelectorAll('#mj-card tr[data-mj-line] input[type=number]')].map(i => (i.disabled ? 'auto:' : '') + i.value));
    await admin.screenshot({ path: `${OUT}/am2_rama_2_devolucion.png`, fullPage: true });
    await admin.dblclick('#mj-save'); await admin.waitForTimeout(3000);
    R.devolucion_guardada = await admin.evaluate(() => document.getElementById('mj-msg')?.innerText);
    await listo(admin);
    R.contador_tras_devolucion = { ...(await contador(admin)), tarjeta: await tarjetaDashboard(admin) };
    R.lista_paginada_muestra_los_dos = await admin.evaluate(() => (state._jd.data?.data || []).filter(e => /FLUMISA/.test(e.gloss || '')).map(e => e.display_number + ' ' + e.entry_number + ' ' + e.entry_date + ' ' + e.gloss));
    R.filas_visibles_tbody = await admin.evaluate(() => [...document.querySelectorAll('#jd-tbody tr')].map(tr => tr.innerText.replace(/\s+/g, ' ').trim()).filter(t => /FLUMISA/.test(t)));
    R.recargas_de_pagina = await admin.evaluate(() => performance.getEntriesByType('navigation').length);
    await admin.screenshot({ path: `${OUT}/am2_rama_libro_paginado_tras_registrar.png`, fullPage: false });
    // Casillas excluyentes
    await admin.check('#mj-cur-usd'); await admin.waitForTimeout(300);
    R.casillas_tras_marcar_dolares = await admin.evaluate(() => ({ soles: document.getElementById('mj-cur-pen').checked, dolares: document.getElementById('mj-cur-usd').checked,
      soles_inhabilitados: [...document.querySelectorAll('#mj-card tr[data-mj-line="0"] input[type=number]')].map(i => i.disabled) }));
    await admin.check('#mj-cur-pen'); await admin.waitForTimeout(300);
    // Fecha sin TC y periodo cerrado
    await admin.fill('#mj-date', '2026-10-13'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    R.fecha_sin_tc = await estado();
    await admin.fill('#mj-date', '2026-07-15'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    R.periodo_cerrado = await estado();
    await admin.screenshot({ path: `${OUT}/am2_rama_3_periodo_cerrado.png`, fullPage: true });
    // Otro caso real (S/ 100, op 01108170) con doble clic
    await admin.fill('#mj-date', '2026-10-14'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    await admin.fill('#mj-gloss', 'Transferencia a FLUMISA S/ 100 (pendiente de definir por el contador)'); await admin.dispatchEvent('#mj-gloss', 'input');
    await admin.fill('#mj-op', '01108170'); await admin.dispatchEvent('#mj-op', 'input');
    await fillLine(0, '103101 - EN TRANSITO', 'mj-d', 100); await fillLine(1, '104101 - BANCO DE CREDITO MN', 'mj-c', 100);
    await admin.selectOption('#mj-card .mj-bank[data-i="1"]', 'bk-fika-bcp-mn');
    await admin.dblclick('#mj-save'); await admin.waitForTimeout(3000);
    R.caso_100 = await admin.evaluate(() => document.getElementById('mj-msg')?.innerText);
    R.lista = await admin.evaluate(() => state._mj.list.map(m => m.entry_number + ' ' + m.operation_number + ' ' + m.status));
    // Conciliacion: las filas de esos N. de operacion quedan Registradas
    R.conciliacion_tras_registrar = await conciliacion(admin, 'bk-fika-bcp-mn');
    await admin.screenshot({ path: `${OUT}/am2_rama_4_conciliacion.png`, fullPage: false });
    // Anular el de S/ 100 desde la lista: la fila vuelve a Error
    await diario(admin); await admin.waitForFunction(() => document.querySelector('#mj-card [data-mj-void]'), null, { timeout: 30000 });
    await admin.selectOption('#jd-period', ''); await listo(admin);
    R.contador_antes_de_anular = await contador(admin);
    await admin.evaluate(() => { const m = state._mj.list.find(x => x.operation_number === '01108170'); document.querySelector(`#mj-card [data-mj-void="${m.id}"]`).click(); });
    await admin.waitForTimeout(3000); await listo(admin);
    R.contador_tras_anular = { ...(await contador(admin)), tarjeta: await tarjetaDashboard(admin) };
    R.lista_paginada_reversa = await admin.evaluate(() => (state._jd.data?.data || []).filter(e => /Anulacion/i.test(e.gloss || '')).map(e => e.display_number + ' ' + e.entry_number + ' ' + e.gloss));
    R.anulado = await admin.evaluate(() => [document.getElementById('mj-msg')?.innerText, state._mj.list.map(m => m.entry_number + ' ' + m.operation_number + ' ' + m.status + (m.reversal_entry_number ? ' reversa ' + m.reversal_entry_number : ''))]);
    R.puente = await admin.evaluate(() => (state._mj.options?.bridge_balances || []).map(x => x.account_code + ' ' + x.balance));
    await admin.screenshot({ path: `${OUT}/am2_rama_5_anulado.png`, fullPage: true });
    R.conciliacion_tras_anular = await conciliacion(admin, 'bk-fika-bcp-mn');
    R.diario_nuevos = (await diario(admin)).filter(t => /FLUMISA|Anulacion/i.test(t));
    // Usuario sin permiso
    const v = await entrar('ventas@t.pe', FIKA, 'ventas'); await diario(v);
    await v.waitForFunction(() => /permiso/.test(document.getElementById('mj-card')?.innerText || ''), null, { timeout: 30000 });
    R.sin_permiso = await v.evaluate(() => document.getElementById('mj-card').innerText.match(/Tu usuario[^\n]+/)?.[0]);
    // FLUMISA: el flujo queda preparado (registro de prueba del ingreso 02117932)
    const f = await entrar('admin@t.pe', FLU, 'admin FLUMISA');
    R.conciliacion_flumisa_antes = await conciliacion(f, 'bk-flu-bcp-mn');
    await f.evaluate(async () => {
      const acc = (c) => state.cache.accounts.find(a => a.account_code === c).id;
      await api('/api/manual-journal/' + state.companyId, { method: 'POST', body: JSON.stringify({ entry_date: '2026-10-14', gloss: 'Ingreso de FIKA (prueba)', currency: 'PEN', operation_number: '02117932',
        lines: [{ chart_account_id: acc('104101'), debit: 3000, bank_account_id: 'bk-flu-bcp-mn' }, { chart_account_id: acc('103101'), credit: 3000 }] }) });
    });
    await f.evaluate(async () => { await syncChanges({ force: true }); });
    R.conciliacion_flumisa_despues = await conciliacion(f, 'bk-flu-bcp-mn');
  }
  fs.writeFileSync(`${OUT}/am2_ui_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(JSON.stringify(R, null, 1).slice(0, 6000));
  await b.close();
})();
