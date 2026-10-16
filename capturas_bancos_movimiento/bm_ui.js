// Bancos > Movimiento entre cuentas: pantalla (rama) y lo existente (main y rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [], dialogos: [] };
  const entrar = async (email, cid, nombre) => {
    const ctx = await b.newContext({ viewport: { width: 1500, height: 1200 }, timezoneId: 'America/Lima' });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(nombre + ': ' + e.message));
    p.on('dialog', d => { R.dialogos.push(nombre + ' [' + d.type() + '] ' + d.message().replace(/\s+/g, ' ')); d.accept(d.type() === 'prompt' ? 'Cuenta equivocada (prueba)' : undefined); });
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
  const botonesConc = (p) => p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(tr => tr.dataset.op + ' ' + (tr.children[8].innerText.trim() || '-')));
  const vista = async (p, v, extra) => { await p.evaluate(([v, e]) => { state.view = v; Object.assign(state, e || {}); renderView(); }, [v, extra]); await p.waitForTimeout(2000);
    return p.evaluate(() => document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | ')); };
  const libro = (p) => p.evaluate(async () => {
    const u = new URLSearchParams({ tz: String(new Date().getTimezoneOffset()), all: '1' });
    return (await api('/api/journal-entries/' + state.companyId + '/book?' + u)).data.data.map(e => [e.display_number, e.entry_number, e.entry_date, e.gloss].join(' | '));
  });
  const tabsBancos = (p) => p.evaluate(() => { state.view = 'banks'; state.bankTab = 'cuentas'; renderView(); return [...document.querySelectorAll('[data-bank-tab]')].map(x => x.innerText.trim()); });
  const admin = await entrar('admin@t.pe', FIKA, 'admin FIKA');
  // Lo que ya existe (debe ser igual en main y rama)
  R.existente = { pestanas_bancos: await tabsBancos(admin), libro: await libro(admin), conciliacion_bcp: await conciliacion(admin, 'bk-fika-bcp-mn'),
    conciliacion_interbank: await conciliacion(admin, 'bk-fika-ibk-mn'),
    cobranza: await vista(admin, 'banks', { bankTab: 'dashboard', _cxcMode: 'cobros' }), pagos: await vista(admin, 'banks', { bankTab: 'dashboard', _cxcMode: 'pagos' }), transacciones: await vista(admin, 'banks', { bankTab: 'transacciones' }),
    dashboard: await vista(admin, 'dashboard') };
  await conciliacion(admin, 'bk-fika-bcp-mn');
  R.botones_conciliacion_antes = await botonesConc(admin);
  await admin.screenshot({ path: `${OUT}/bm_${TAG}_antes_conciliacion.png`, fullPage: false });
  if (TAG === 'rama') {
    const hoyLima = await admin.evaluate(() => limaTodayIso());
    // (a) Fecha por defecto del asiento manual: hoy (Lima), tambien despues de registrar uno con otra fecha
    await vista(admin, 'journal'); await admin.waitForFunction(() => document.querySelector('#mj-card #mj-date'), null, { timeout: 30000 });
    R.fecha_asiento_manual = { hoy_lima: hoyLima, al_entrar: await admin.inputValue('#mj-date') };
    await admin.fill('#mj-date', '2026-10-14'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    await admin.fill('#mj-gloss', 'Asiento del diario con fecha 14/10 (prueba de fecha por defecto)'); await admin.dispatchEvent('#mj-gloss', 'input');
    for (const [i, acc, cls] of [[0, '103103 - EN TRANSITO', 'mj-d'], [1, '103105 - EN TRANSITO', 'mj-c']]) {
      await admin.fill(`#mj-card .mj-acc[data-i="${i}"]`, acc); await admin.dispatchEvent(`#mj-card .mj-acc[data-i="${i}"]`, 'change'); await admin.waitForTimeout(200);
      await admin.fill(`#mj-card input.${cls}[data-i="${i}"]:not([disabled])`, '1'); await admin.dispatchEvent(`#mj-card input.${cls}[data-i="${i}"]:not([disabled])`, 'input');
    }
    await admin.click('#mj-save'); await admin.waitForTimeout(2500);
    R.fecha_asiento_manual.registro = await admin.evaluate(() => document.getElementById('mj-msg')?.innerText);
    R.fecha_asiento_manual.tras_registrar = await admin.inputValue('#mj-date');
    await vista(admin, 'dashboard'); await vista(admin, 'journal'); await admin.waitForTimeout(800);
    R.fecha_asiento_manual.al_volver = await admin.inputValue('#mj-date');

    // Pestana nueva: sin lista de contrapartidas, el contador la define (aqui la usuaria admin de prueba)
    await vista(admin, 'banks', { bankTab: 'movimiento' }); await admin.waitForFunction(() => document.querySelector('#bm-card #bm-save'), null, { timeout: 30000 });
    R.pestanas_bancos_rama = await admin.evaluate(() => [...document.querySelectorAll('[data-bank-tab]')].map(x => x.innerText.trim()));
    R.bancos_ofrecidos = await admin.evaluate(() => [...document.querySelectorAll('#bm-bank option')].map(o => o.textContent.trim()));
    R.pestana_inicial = await admin.evaluate(() => ({ fecha: document.getElementById('bm-date').value, falta: document.querySelector('#bm-dyn span')?.innerText, aviso: document.querySelector('#bm-card > div')?.innerText }));
    await admin.screenshot({ path: `${OUT}/bm_rama_1_pestana_vacia.png`, fullPage: true });
    await admin.evaluate(() => { document.getElementById('bm-cfg').open = true; });
    await admin.fill('#bm-cfg-acc', '103101 - EN TRANSITO'); await admin.click('#bm-cfg-add'); await admin.waitForTimeout(300);
    await admin.click('#bm-cfg-save'); await admin.waitForTimeout(1500);
    R.lista_guardada = await admin.evaluate(() => [document.getElementById('bm-msg')?.innerText, state._bm.options.counterparts.map(c => c.account_code)]);

    // Casos reales: desde la Conciliacion (filas en Error) con "Registrar como..."
    const desdeConc = async (op, glosa) => {
      await conciliacion(admin, 'bk-fika-bcp-mn');
      await admin.evaluate((op) => document.querySelector(`#conc-tabla-tbody tr[data-op="${op}"] .conc-registrar-mov-btn`).click(), op);
      await admin.waitForFunction(() => document.querySelector('#bm-card #bm-save'), null, { timeout: 30000 }); await admin.waitForTimeout(800);
      const pre = await admin.evaluate(() => ({ tipo: document.querySelector('input[name="bm-kind"]:checked')?.value, fecha: document.getElementById('bm-date').value,
        monto: document.getElementById('bm-amount').value, sentido: document.querySelector('input[name="bm-dir"]:checked')?.value,
        banco: document.getElementById('bm-bank').selectedOptions[0]?.textContent, op: document.getElementById('bm-op').value }));
      await admin.fill('#bm-cp', '103101 - EN TRANSITO'); await admin.dispatchEvent('#bm-cp', 'change'); await admin.waitForTimeout(300);
      await admin.fill('#bm-gloss', glosa); await admin.dispatchEvent('#bm-gloss', 'input');
      return pre;
    };
    R.precargado_01117932 = await desdeConc('01117932', 'Devolucion a FLUMISA de dinero depositado por error');
    R.vista_previa_01117932 = await admin.evaluate(() => document.getElementById('bm-dyn').innerText.replace(/\s+/g, ' '));
    await admin.screenshot({ path: `${OUT}/bm_rama_2_desde_conciliacion.png`, fullPage: true });
    await admin.dblclick('#bm-save'); await admin.waitForTimeout(3000);
    R.registrado_01117932 = await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    for (const [op, g] of [['01104038', 'Transferencia a FLUMISA S/ 975 (pendiente de definir)'], ['01108170', 'Transferencia a FLUMISA S/ 100 (pendiente de definir)']]) {
      await desdeConc(op, g); await admin.click('#bm-save'); await admin.waitForTimeout(3000);
      R['registrado_' + op] = await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    }
    // Entre mis cuentas: BCP MN -> Interbank MN con dos N. de operacion
    await admin.check('input[name="bm-kind"][value="own_transfer"]'); await admin.waitForTimeout(300);
    await admin.fill('#bm-date', '2026-10-14'); await admin.dispatchEvent('#bm-date', 'change'); await admin.waitForTimeout(800);
    await admin.selectOption('#bm-from', 'bk-fika-bcp-mn'); await admin.waitForTimeout(200);
    await admin.selectOption('#bm-to', 'bk-fika-ibk-mn'); await admin.waitForTimeout(200);
    for (const [id, v] of [['bm-amount', '500'], ['bm-op-out', '01200001'], ['bm-op-in', '33300001'], ['bm-gloss', 'Traspaso de BCP a Interbank']]) { await admin.fill('#' + id, v); await admin.dispatchEvent('#' + id, 'input'); }
    R.vista_previa_propia = await admin.evaluate(() => document.getElementById('bm-dyn').innerText.replace(/\s+/g, ' '));
    await admin.screenshot({ path: `${OUT}/bm_rama_3_entre_mis_cuentas.png`, fullPage: true });
    await admin.click('#bm-save'); await admin.waitForTimeout(3000);
    R.registrado_propia = await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    // Bloqueos en pantalla
    const estado = () => admin.evaluate(() => ({ guardar: !document.getElementById('bm-save')?.disabled, periodo: document.querySelector('#bm-card')?.innerText.match(/Periodo contable\s*\n([^\n]+)/i)?.[1],
      tc: document.querySelector('#bm-card')?.innerText.match(/Tipo de cambio\s*\n([^\n]+)/i)?.[1], falta: document.querySelector('#bm-dyn span')?.innerText, error: document.querySelector('#bm-dyn > div[style*="fee2e2"]')?.innerText, msg: document.getElementById('bm-msg')?.innerText }));
    await admin.selectOption('#bm-from', 'bk-fika-bcp-mn'); await admin.waitForTimeout(300);
    await admin.selectOption('#bm-to', 'bk-fika-bcp-me'); await admin.waitForTimeout(300);
    for (const [id, v] of [['bm-amount', '100'], ['bm-op-out', 'M-1'], ['bm-op-in', 'M-2'], ['bm-gloss', 'Soles a dolares']]) { await admin.fill('#' + id, v); await admin.dispatchEvent('#' + id, 'input'); }
    R.monedas_distintas = await estado();
    await admin.check('input[name="bm-kind"][value="counterpart"]'); await admin.waitForTimeout(300);
    await admin.fill('#bm-date', '2026-07-15'); await admin.dispatchEvent('#bm-date', 'change'); await admin.waitForTimeout(800);
    R.julio_cerrado = await estado();
    await admin.screenshot({ path: `${OUT}/bm_rama_4_periodo_cerrado.png`, fullPage: false });
    await admin.fill('#bm-date', '2026-10-13'); await admin.dispatchEvent('#bm-date', 'change'); await admin.waitForTimeout(800);
    await admin.selectOption('#bm-bank', 'bk-fika-bcp-me'); await admin.waitForTimeout(300);
    R.dolares_sin_tc = await estado();
    // N. de operacion repetido (el servidor lo bloquea)
    await admin.fill('#bm-date', '2026-10-14'); await admin.dispatchEvent('#bm-date', 'change'); await admin.waitForTimeout(800);
    await admin.selectOption('#bm-bank', 'bk-fika-bcp-mn'); await admin.waitForTimeout(300);
    await admin.check('input[name="bm-dir"][value="out"]'); await admin.waitForTimeout(300);
    await admin.fill('#bm-cp', '103101 - EN TRANSITO'); await admin.dispatchEvent('#bm-cp', 'change'); await admin.waitForTimeout(300);
    for (const [id, v] of [['bm-amount', '3000'], ['bm-op', '01117932'], ['bm-gloss', 'Otra vez el mismo numero']]) { await admin.fill('#' + id, v); await admin.dispatchEvent('#' + id, 'input'); }
    await admin.click('#bm-save'); await admin.waitForTimeout(2500);
    R.op_repetido = (await estado()).msg;
    // Conciliacion despues: las filas quedan Registradas
    R.conciliacion_bcp_despues = await conciliacion(admin, 'bk-fika-bcp-mn');
    await admin.screenshot({ path: `${OUT}/bm_rama_5_conciliacion_registrada.png`, fullPage: false });
    R.conciliacion_interbank_despues = await conciliacion(admin, 'bk-fika-ibk-mn');
    // Anular la transferencia propia desde la lista de la pestana
    await vista(admin, 'banks', { bankTab: 'movimiento' }); await admin.waitForFunction(() => document.querySelector('#bm-card [data-bm-void]'), null, { timeout: 30000 });
    R.lista_antes_de_anular = await admin.evaluate(() => state._bm.list.filter(m => m.origin === 'bancos').map(m => m.entry_number + ' ' + m.operation_number + ' ' + m.status));
    await admin.evaluate(() => { const m = state._bm.list.find(x => x.operation_number === '01200001 / 33300001'); document.querySelector(`#bm-card [data-bm-void="${m.id}"]`).click(); });
    await admin.waitForTimeout(3000);
    R.anulado = await admin.evaluate(() => [document.getElementById('bm-msg')?.innerText, state._bm.list.filter(m => m.origin === 'bancos').map(m => m.entry_number + ' ' + m.operation_number + ' ' + m.status + (m.reversal_entry_number ? ' reversa ' + m.reversal_entry_number : ''))]);
    await admin.screenshot({ path: `${OUT}/bm_rama_6_lista_anulado.png`, fullPage: true });
    R.conciliacion_bcp_tras_anular = await conciliacion(admin, 'bk-fika-bcp-mn');
    R.conciliacion_interbank_tras_anular = await conciliacion(admin, 'bk-fika-ibk-mn');
    R.libro_nuevos = (await libro(admin)).filter(t => /FLUMISA|Traspaso|Anulacion|prueba de fecha/i.test(t));
    // Usuario sin permiso
    const v = await entrar('ventas@t.pe', FIKA, 'ventas');
    await vista(v, 'banks', { bankTab: 'movimiento' }); await v.waitForFunction(() => /permiso/.test(document.getElementById('bm-card')?.innerText || ''), null, { timeout: 30000 });
    R.sin_permiso = await v.evaluate(() => document.getElementById('bm-card').innerText.match(/Tu usuario[^\n]+/)?.[0]);
    // FLUMISA: entrada desde la Conciliacion con el aviso de factura (lista definida por su contador en la prueba)
    const f = await entrar('admin@t.pe', FLU, 'admin FLUMISA');
    await f.evaluate(async () => { await api('/api/manual-journal/' + state.companyId + '/bank-movement/counterparts', { method: 'PUT', body: JSON.stringify({ codes: ['103101'] }) }); });
    R.conciliacion_flumisa_antes = await conciliacion(f, 'bk-flu-bcp-mn');
    await f.evaluate(() => document.querySelector('#conc-tabla-tbody tr[data-op="02117932"] .conc-registrar-mov-btn').click());
    await f.waitForFunction(() => document.querySelector('#bm-card #bm-save'), null, { timeout: 30000 }); await f.waitForTimeout(800);
    await f.fill('#bm-cp', '103101 - EN TRANSITO'); await f.dispatchEvent('#bm-cp', 'change'); await f.waitForTimeout(300);
    await f.fill('#bm-gloss', 'Ingreso de FIKA S/ 3,000 (devolucion)'); await f.dispatchEvent('#bm-gloss', 'input');
    R.flumisa_aviso_entrada = await f.evaluate(() => [...document.querySelectorAll('#bm-card div')].map(d => d.innerText).find(t => /Comprueba que no sea el pago de una factura/.test(t)));
    await f.screenshot({ path: `${OUT}/bm_rama_7_flumisa_entrada_aviso.png`, fullPage: true });
    await f.click('#bm-save'); await f.waitForTimeout(3000);
    R.flumisa_registrado = await f.evaluate(() => document.getElementById('bm-msg')?.innerText);
    R.conciliacion_flumisa_despues = await conciliacion(f, 'bk-flu-bcp-mn');
    R.cuenta_ret_comis_caja_ofrecidas = (R.bancos_ofrecidos || []).filter(t => /Comisiones|Retenciones|Caja/i.test(t));
  }
  fs.writeFileSync(`${OUT}/bm_ui_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(TAG, 'listo, errores', JSON.stringify(R.errores_js));
  await b.close();
})();
