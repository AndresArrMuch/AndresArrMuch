// Bancos > Movimiento entre cuentas (guia por pasos) y textos del asiento manual. main y rama.
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA, XLSX_JS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [], dialogos: [] };
  let politica = 'accept';
  const entrar = async (email, cid, nombre, viewport) => {
    const ctx = await b.newContext({ viewport: viewport || { width: 1500, height: 1100 }, timezoneId: 'America/Lima', acceptDownloads: true });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(nombre + ': ' + e.message));
    p.on('dialog', d => { R.dialogos.push(nombre + ' [' + d.type() + (politica === 'dismiss' && d.type() === 'confirm' ? ', cancelado' : '') + '] ' + d.message().replace(/\s+/g, ' ').slice(0, 220));
      if (politica === 'dismiss' && d.type() === 'confirm') d.dismiss(); else d.accept(d.type() === 'prompt' ? 'Cuenta equivocada (prueba)' : undefined); });
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
      const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
      if (u.includes('xlsx/0.18.5/xlsx.full.min.js')) return r.fulfill({ path: XLSX_JS, contentType: 'application/javascript' });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(900);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(2500);
    return p;
  };
  const conciliacion = async (p, cuenta) => {
    await p.evaluate(async (c) => { state.view = 'banks'; state.bankTab = 'conciliacion'; state._concAccount = c; state._concMonth = '2026-10'; state._concYear = '2026';
      state._concPagosRegistrados = null; state._concCobranzasPagos = null; renderView(); await cargarExcelPersistidoConciliacion(); }, cuenta);
    await p.waitForTimeout(2500);
    return p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(tr => tr.dataset.op + ' ' + tr.children[2].innerText.trim() + ' ' + tr.children[4].innerText.trim()));
  };
  const texto = (p) => p.evaluate(() => document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | '));
  const vista = async (p, v, extra) => { await p.evaluate(([v, e]) => { state.view = v; Object.assign(state, e || {}); renderView(); }, [v, extra]); await p.waitForTimeout(2000); return texto(p); };
  const libro = (p) => p.evaluate(async () => (await api('/api/journal-entries/' + state.companyId + '/book?all=1&tz=' + new Date().getTimezoneOffset())).data.data.map(e => [e.display_number, e.entry_number, e.entry_date, e.gloss].join(' | ')));
  const saldoBancario = (p) => p.evaluate(() => { state.view = 'dashboard'; renderView(); const t = document.getElementById('panelBody').innerText; return (t.match(/SALDO BANCARIO\s*\n?\s*([^\n]+)/i) || [])[1] || ''; });
  const admin = await entrar('admin@t.pe', FIKA, 'admin FIKA');
  // ---------- Lo existente (antes de registrar nada): igual en main y rama ----------
  R.existente = { libro: await libro(admin), conciliacion_bcp: await conciliacion(admin, 'bk-fika-bcp-mn'), conciliacion_ibk: await conciliacion(admin, 'bk-fika-ibk-mn'),
    cobranza: await vista(admin, 'banks', { bankTab: 'dashboard', _cxcMode: 'cobros' }), pagos: await vista(admin, 'banks', { bankTab: 'dashboard', _cxcMode: 'pagos' }),
    transacciones: await vista(admin, 'banks', { bankTab: 'transacciones' }), estado_cuenta: await vista(admin, 'banks', { bankTab: 'estado_cuenta' }),
    cuentas: await vista(admin, 'banks', { bankTab: 'cuentas' }), dashboard: await vista(admin, 'dashboard') };
  R.saldo_bancario_antes = await saldoBancario(admin);
  // Libro Diario: aviso, panel 103 y tipo de cambio (antes y despues)
  await vista(admin, 'journal'); await admin.waitForFunction(() => document.querySelector('#mj-card #mj-save'), null, { timeout: 30000 }); await admin.waitForTimeout(800);
  const diario = () => admin.evaluate(() => { const c = document.getElementById('mj-card'); const d = document.getElementById('mj-help');
    return { aviso: c.querySelector('div')?.innerText.split('\n')[0].trim(), alto_aviso_px: Math.round(c.querySelector('div')?.getBoundingClientRect().height || 0), desplegable: d ? (d.open ? 'abierto' : 'plegado') : 'no hay',
      panel_103: /Cuentas puente/.test(c.innerText), tipo_cambio: (c.innerText.match(/Tipo de cambio\s*\n([^\n]+)/i) || [])[1], ayuda_op: /genera su movimiento bancario/.test(c.querySelector('#mj-op')?.parentElement.innerText || '') }; });
  await admin.fill('#mj-date', '2026-10-16'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
  R.diario_soles_16_10 = await diario();
  await admin.screenshot({ path: `${OUT}/bg_${TAG}_diario_soles.png`, clip: { x: 290, y: 170, width: 1200, height: 560 } });
  if (TAG === 'rama') {
    await admin.click('#mj-help summary'); await admin.waitForTimeout(300); R.diario_desplegado = (await diario()).desplegable;
    await admin.screenshot({ path: `${OUT}/bg_rama_diario_aviso_desplegado.png`, clip: { x: 290, y: 170, width: 1200, height: 520 } });
    await admin.click('#mj-help summary'); await admin.waitForTimeout(300); R.diario_plegado_otra_vez = (await diario()).desplegable;
  }
  await admin.check('#mj-cur-usd').catch(() => {}); await admin.waitForTimeout(400);
  R.diario_dolares_16_10 = (await diario()).tipo_cambio;
  await admin.check('#mj-cur-pen').catch(() => {}); await admin.waitForTimeout(300);
  await admin.screenshot({ path: `${OUT}/bg_${TAG}_diario_completo.png`, fullPage: true });
  // Pestana de Bancos (antes / despues)
  await vista(admin, 'banks', { bankTab: 'movimiento' }); await admin.waitForTimeout(1500);
  await admin.screenshot({ path: `${OUT}/bg_${TAG}_bancos_pestana.png`, fullPage: true });
  R.bancos_texto_inicial = (await texto(admin)).slice(0, 900);
  if (TAG === 'rama') {
    const paso = () => admin.evaluate(() => _bmCurrentStep());
    const p4 = () => admin.evaluate(() => ({ frase: document.querySelector('.bm-frase')?.innerText, check: [...document.querySelectorAll('.bm-check li')].map(li => (li.dataset.ok === '1' ? 'OK ' : 'PEND ') + li.innerText.replace(/\s+/g, ' ')),
      tc: [...document.querySelectorAll('#bm-dyn > div')].map(d => d.innerText).find(t => /cambio de moneda|Tipo de cambio|tipo de cambio/.test(t)), boton: !document.getElementById('bm-save')?.disabled,
      tooltip: document.getElementById('bm-save')?.parentElement.getAttribute('title'), mism: document.querySelector('.bm-mism')?.innerText }));
    const elegir = async (kind) => { await admin.click(`.bm-kind[data-kind="${kind}"]`); await admin.waitForTimeout(400); };
    const fila = async (lado, op) => { await admin.waitForFunction(([l, o]) => [...document.querySelectorAll(`.bm-row[data-lado="${l}"]`)].some(x => x.innerText.includes(o)), [lado, op], { timeout: 20000 });
      await admin.evaluate(([l, o]) => [...document.querySelectorAll(`.bm-row[data-lado="${l}"]`)].find(x => x.innerText.includes(o)).click(), [lado, op]); await admin.waitForTimeout(500); };
    const listaFilas = (lado) => admin.evaluate((l) => [...document.querySelectorAll(`.bm-row[data-lado="${l}"]`)].map(x => x.innerText.replace(/\s+/g, ' ')), lado);
    const glosa = async (t) => { await admin.fill('#bm-gloss', t); await admin.dispatchEvent('#bm-gloss', 'input'); };
    const contra = async () => { await admin.fill('#bm-cp', '103101 EN TRANSITO'); await admin.dispatchEvent('#bm-cp', 'change'); await admin.waitForTimeout(300); };
    const resultado = () => admin.evaluate(() => document.getElementById('bm-result')?.innerText.replace(/\n+/g, ' | '));
    const nAsientos = () => admin.evaluate(async () => (await api('/api/manual-journal/' + state.companyId)).data.length);
    R.paso_inicial = await paso();
    await admin.screenshot({ path: `${OUT}/bg_rama_paso1.png`, fullPage: false });
    await elegir('counterpart'); R.paso_tras_elegir = await paso();
    await admin.selectOption('#bm-bank', 'bk-fika-bcp-mn'); await admin.waitForTimeout(1800);
    R.filas_error_bcp = await listaFilas('');
    // Paridad con la Conciliacion: las mismas filas en Error
    R.paridad = await admin.evaluate(() => { const e = state._bm.ext['bk-fika-bcp-mn|2026-10']; return (e.rows || []).map(r => r.operation_number + ':' + r._estado); });
    await admin.screenshot({ path: `${OUT}/bg_rama_paso2_lista_extracto.png`, fullPage: false });
    // Escrito a mano con errores: monto equivocado, fecha equivocada, numero inexistente
    await admin.click('.bm-manual[data-lado=""][data-on="1"]'); await admin.waitForTimeout(500);
    const mano = async (fecha, monto, dir, op) => {
      await admin.fill('#bm-date', fecha); await admin.dispatchEvent('#bm-date', 'change'); await admin.waitForTimeout(400);
      await admin.check(`input[name="bm-dir"][value="${dir}"]`); await admin.waitForTimeout(400);
      await admin.fill('#bm-amount', String(monto)); await admin.dispatchEvent('#bm-amount', 'input');
      await admin.fill('#bm-op', op); await admin.dispatchEvent('#bm-op', 'input'); await admin.waitForTimeout(300);
      return admin.evaluate(() => document.querySelector('#bm-chk-u .bm-chk')?.innerText.replace(/\s+/g, ' '));
    };
    R.mano_monto_equivocado = await mano('2026-10-14', 970, 'out', '01104038');
    await contra(); await glosa('Prueba con monto equivocado');
    R.mano_monto_paso4 = await p4();
    await admin.screenshot({ path: `${OUT}/bg_rama_mano_monto_equivocado.png`, fullPage: false });
    const antes = await nAsientos();
    politica = 'dismiss'; await admin.click('#bm-save'); await admin.waitForTimeout(1500); politica = 'accept';
    R.mano_monto_no_registrado = (await nAsientos()) === antes;
    R.mano_fecha_equivocada = await mano('2026-10-13', 975, 'out', '01104038');
    R.mano_sentido_equivocado = await mano('2026-10-14', 975, 'in', '01104038');
    R.mano_inexistente = await mano('2026-10-14', 975, 'out', '99999999');
    R.mano_correcto = await mano('2026-10-14', 975, 'out', '01104038');
    await admin.click('.bm-manual[data-lado=""][data-on="0"]'); await admin.waitForTimeout(500);
    // Los tres casos reales de FIKA elegidos de la lista
    for (const [op, g] of [['01117932', 'Devolucion a FLUMISA de dinero depositado por error'], ['01104038', 'Transferencia a FLUMISA S/ 975 (pendiente de definir)'], ['01108170', 'Transferencia a FLUMISA S/ 100 (pendiente de definir)']]) {
      await fila('', op); R['paso_tras_fila_' + op] = await paso();
      if (op === '01117932') { R.fila_elegida_solo_lectura = await admin.evaluate(() => ({ inputs_editables: document.querySelectorAll('#bm-date, #bm-amount, #bm-op').length, tarjeta: document.querySelector('.bm-unrow')?.parentElement.innerText.replace(/\s+/g, ' ') })); await admin.screenshot({ path: `${OUT}/bg_rama_paso3.png`, fullPage: false }); }
      await contra(); await glosa(g);
      R['paso4_' + op] = await p4();
      if (op === '01117932') { await admin.click('#bm-asiento summary'); await admin.waitForTimeout(300); R.asiento_desplegado = await admin.evaluate(() => document.querySelector('#bm-asiento table')?.innerText.replace(/\s+/g, ' ')); await admin.screenshot({ path: `${OUT}/bg_rama_paso4.png`, fullPage: false }); }
      const n0 = await nAsientos();
      if (op === '01117932') await admin.dblclick('#bm-save'); else await admin.click('#bm-save');
      await admin.waitForFunction(() => document.getElementById('bm-result') || /No se registró/.test(document.getElementById('bm-msg')?.innerText || ''), null, { timeout: 30000 }); await admin.waitForTimeout(800);
      R['resultado_' + op] = await resultado();
      if (op === '01117932') { R.doble_clic_un_solo_asiento = (await nAsientos()) === n0 + 1; await admin.screenshot({ path: `${OUT}/bg_rama_resultado.png`, fullPage: false }); }
      await admin.click('#bm-result-close'); await admin.waitForTimeout(400);
      if (await admin.evaluate(() => state._bm.form.kind !== 'counterpart')) await elegir('counterpart');
      await admin.evaluate(() => { if (!state._bm.form.bank) { state._bm.form.bank = 'bk-fika-bcp-mn'; renderBankMovementCard(); } }); await admin.waitForTimeout(1200);
    }
    // Entre mis cuentas: BCP MN -> Interbank MN, cada lado con su fila
    await elegir('own_transfer');
    await admin.selectOption('#bm-from', 'bk-fika-bcp-mn'); await admin.waitForTimeout(1200);
    await admin.selectOption('#bm-to', 'bk-fika-ibk-mn'); await admin.waitForTimeout(1500);
    R.propia_filas_salida = await listaFilas('out'); R.propia_filas_entrada = await listaFilas('in');
    await fila('out', '01200001'); await fila('in', '33300001'); await glosa('Traspaso del BCP al Interbank');
    R.propia_paso4 = await p4();
    await admin.screenshot({ path: `${OUT}/bg_rama_entre_mis_cuentas.png`, fullPage: false });
    await admin.click('#bm-save'); await admin.waitForFunction(() => document.getElementById('bm-result'), null, { timeout: 30000 }); await admin.waitForTimeout(800);
    R.propia_resultado = await resultado();
    await admin.click('#bm-result-close'); await admin.waitForTimeout(400);
    // Misma cuenta y monedas distintas
    await admin.selectOption('#bm-to', 'bk-fika-bcp-mn'); await admin.waitForTimeout(800);
    R.propia_misma_cuenta = await admin.evaluate(() => document.querySelector('.bm-err')?.innerText);
    await admin.selectOption('#bm-to', 'bk-fika-bcp-me'); await admin.waitForTimeout(800);
    R.propia_monedas_distintas = await admin.evaluate(() => document.querySelector('.bm-err')?.innerText);
    // N. de operacion ya registrado (el servidor lo bloquea)
    await elegir('counterpart'); await admin.selectOption('#bm-bank', 'bk-fika-bcp-mn'); await admin.waitForTimeout(1200);
    await admin.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await admin.waitForTimeout(400);
    R.op_repetido_aviso = await mano('2026-10-14', 3000, 'out', '01117932');
    await contra(); await glosa('Otra vez el mismo numero');
    await admin.click('#bm-save'); await admin.waitForTimeout(2500);
    R.op_repetido = await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    // Cuenta en dolares sin extracto: fin de semana (sabado 17/10) usa el ultimo TC publicado
    await admin.selectOption('#bm-bank', 'bk-fika-bcp-me'); await admin.waitForTimeout(1500);
    R.sin_extracto = await admin.evaluate(() => [...document.querySelectorAll('#bm-card section[data-paso="2"] div')].map(d => d.innerText).find(t => /Aún no hay extracto/.test(t))?.replace(/\s+/g, ' '));
    await admin.screenshot({ path: `${OUT}/bg_rama_sin_extracto.png`, fullPage: false });
    await admin.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await admin.waitForTimeout(400);
    await mano('2026-10-17', 100, 'in', 'USD-17'); await contra(); await glosa('Deposito en dolares de sabado (prueba)');
    R.dolares_sabado = await p4();
    await admin.screenshot({ path: `${OUT}/bg_rama_dolares_sabado.png`, fullPage: false });
    await admin.click('#bm-save'); await admin.waitForFunction(() => document.getElementById('bm-result') || /No se registró/.test(document.getElementById('bm-msg')?.innerText || ''), null, { timeout: 30000 }); await admin.waitForTimeout(800);
    R.dolares_sabado_resultado = await resultado() || await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    await admin.click('#bm-result-close').catch(() => {}); await admin.waitForTimeout(400);
    // Dolares sin ningun TC publicado hasta la fecha (20/06): bloqueado. Soles el mismo dia: no pide TC y se registra
    await elegir('counterpart'); await admin.evaluate(() => { state._bm.form.bank = 'bk-fika-bcp-me'; state._bm.form.month = '2026-06'; renderBankMovementCard(); }); await admin.waitForTimeout(1500);
    await admin.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await admin.waitForTimeout(400);
    await mano('2026-06-20', 50, 'in', 'USD-0620'); await contra(); await glosa('Dolares sin TC (prueba)');
    R.dolares_sin_tc = await p4();
    await admin.evaluate(() => { state._bm.form.bank = 'bk-fika-bcp-mn'; renderBankMovementCard(); }); await admin.waitForTimeout(1500);
    await admin.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await admin.waitForTimeout(400);
    await mano('2026-06-20', 50, 'out', 'PEN-0620'); await contra(); await glosa('Soles sin ningun TC publicado (prueba)');
    R.soles_sin_tc = await p4();
    await admin.screenshot({ path: `${OUT}/bg_rama_soles_sin_tc.png`, fullPage: false });
    await admin.click('#bm-save'); await admin.waitForFunction(() => document.getElementById('bm-result') || /No se registró/.test(document.getElementById('bm-msg')?.innerText || ''), null, { timeout: 30000 }); await admin.waitForTimeout(800);
    R.soles_sin_tc_resultado = await resultado() || await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    await admin.click('#bm-result-close').catch(() => {}); await admin.waitForTimeout(400);
    // Periodo cerrado (julio y agosto)
    for (const [mes, fecha] of [['2026-07', '2026-07-15'], ['2026-08', '2026-08-10']]) {
      await elegir('counterpart'); await admin.evaluate((m) => { state._bm.form.bank = 'bk-fika-bcp-mn'; state._bm.form.month = m; renderBankMovementCard(); }, mes); await admin.waitForTimeout(1500);
      await admin.click('.bm-manual[data-lado=""][data-on="1"]').catch(() => {}); await admin.waitForTimeout(400);
      await mano(fecha, 10, 'out', 'CER-' + mes); await contra(); await glosa('Periodo cerrado (prueba)');
      R['periodo_cerrado_' + mes] = await p4();
    }
    await admin.screenshot({ path: `${OUT}/bg_rama_periodo_cerrado.png`, fullPage: false });
    // Conciliacion despues
    R.conciliacion_bcp_despues = await conciliacion(admin, 'bk-fika-bcp-mn');
    R.conciliacion_ibk_despues = await conciliacion(admin, 'bk-fika-ibk-mn');
    await admin.screenshot({ path: `${OUT}/bg_rama_conciliacion_bcp_despues.png`, fullPage: false });
    // Transacciones, Estado de cuenta y Dashboard: cada movimiento una sola vez
    const cuenta = (t, op) => (t.match(new RegExp(op, 'g')) || []).length;
    await vista(admin, 'banks', { bankTab: 'transacciones' });
    const tx = await admin.evaluate(() => [...document.querySelectorAll('#btx-tbody tr')].map(tr => tr.textContent).join(' || '));   // la tabla esta en una seccion plegada
    const ec = await admin.evaluate(async () => { state.view = 'banks'; state.bankTab = 'estado_cuenta'; renderView(); await new Promise(r => setTimeout(r, 1500)); return document.getElementById('panelBody').innerText; });
    R.apariciones = Object.fromEntries(['01117932', '01104038', '01108170', '01200001', '33300001'].map(op => [op, { transacciones: cuenta(tx, op), estado_cuenta: cuenta(ec, op) }]));
    R.saldo_bancario_despues = await saldoBancario(admin);
    R.saldo_tx_sistema = await admin.evaluate(() => { const s = {}; (state.cache.bank_transactions || []).forEach(t => { s[t.account_id] = Math.round(((s[t.account_id] || 0) + (t.transaction_type === 'deposit' ? 1 : -1) * Number(t.amount)) * 100) / 100; }); return s; });
    // Anular la transferencia propia desde la lista: las filas vuelven a Error
    await vista(admin, 'banks', { bankTab: 'movimiento' }); await admin.waitForFunction(() => document.querySelector('#bm-card [data-bm-void]'), null, { timeout: 30000 });
    R.lista_movimientos = await admin.evaluate(() => [...document.querySelectorAll('.bm-mov')].map(x => x.innerText.replace(/\s+/g, ' ')));
    await admin.screenshot({ path: `${OUT}/bg_rama_lista_movimientos.png`, fullPage: true });
    await admin.evaluate(() => { const m = state._bm.list.find(x => x.operation_number === '01200001 / 33300001'); document.querySelector(`#bm-card [data-bm-void="${m.id}"]`).click(); });
    await admin.waitForTimeout(3500);
    R.anulado = await admin.evaluate(() => document.getElementById('bm-msg')?.innerText);
    R.conciliacion_bcp_tras_anular = await conciliacion(admin, 'bk-fika-bcp-mn');
    R.conciliacion_ibk_tras_anular = await conciliacion(admin, 'bk-fika-ibk-mn');
    R.libro_nuevos = (await libro(admin)).filter(t => /FLUMISA|Traspaso|Anulacion|prueba/i.test(t));
    // FLUMISA: "Registrar como..." desde la Conciliacion abre la guia en el paso 3; las otras dos desde la lista
    const f = await entrar('admin@t.pe', FLU, 'admin FLUMISA');
    R.flu_conciliacion_antes = await conciliacion(f, 'bk-flu-bcp-mn');
    await f.evaluate(() => document.querySelector('#conc-tabla-tbody tr[data-op="02117932"] .conc-registrar-mov-btn').click());
    await f.waitForFunction(() => document.querySelector('#bm-card .bm-paso'), null, { timeout: 30000 }); await f.waitForTimeout(1800);
    R.flu_registrar_como = await f.evaluate(() => ({ paso: _bmCurrentStep(), fila: document.querySelector('.bm-unrow')?.parentElement.innerText.replace(/\s+/g, ' ') }));
    await f.screenshot({ path: `${OUT}/bg_rama_registrar_como_paso3.png`, fullPage: false });
    const fGlosa = async (t) => { await f.fill('#bm-gloss', t); await f.dispatchEvent('#bm-gloss', 'input'); await f.fill('#bm-cp', '103101 EN TRANSITO'); await f.dispatchEvent('#bm-cp', 'change'); await f.waitForTimeout(300); };
    await fGlosa('Ingreso de FIKA S/ 3,000 (devolucion)');
    R.flu_aviso_factura = await f.evaluate(() => [...document.querySelectorAll('#bm-card section[data-paso="3"] div')].map(d => d.innerText).find(t => /Comprueba que no sea el pago de una factura/.test(t)));
    await f.click('#bm-save'); await f.waitForFunction(() => document.getElementById('bm-result'), null, { timeout: 30000 }); await f.waitForTimeout(800);
    R.flu_resultado_02117932 = await f.evaluate(() => document.getElementById('bm-result')?.innerText.replace(/\n+/g, ' | '));
    for (const op of ['02104038', '02108170']) {
      await f.click('#bm-result-close'); await f.waitForTimeout(400);
      await f.evaluate(() => { state._bm.form.kind = 'counterpart'; state._bm.form.bank = 'bk-flu-bcp-mn'; renderBankMovementCard(); }); await f.waitForTimeout(1500);
      await f.evaluate((o) => [...document.querySelectorAll('.bm-row[data-lado=""]')].find(x => x.innerText.includes(o)).click(), op); await f.waitForTimeout(500);
      await fGlosa('Ingreso de FIKA (pendiente de definir)');
      await f.click('#bm-save'); await f.waitForFunction(() => document.getElementById('bm-result'), null, { timeout: 30000 }); await f.waitForTimeout(800);
      R['flu_resultado_' + op] = await f.evaluate(() => document.getElementById('bm-result')?.innerText.replace(/\n+/g, ' | '));
    }
    R.flu_conciliacion_despues = await conciliacion(f, 'bk-flu-bcp-mn');
    // Celular
    const cel = await entrar('admin@t.pe', FIKA, 'celular', { width: 390, height: 844 });
    await cel.evaluate(() => { state.view = 'banks'; state.bankTab = 'movimiento'; renderView(); }); await cel.waitForTimeout(2000);
    await cel.screenshot({ path: `${OUT}/bg_rama_celular_paso1.png`, fullPage: false });
    await cel.click('.bm-kind[data-kind="counterpart"]'); await cel.waitForTimeout(400);
    await cel.selectOption('#bm-bank', 'bk-fika-bcp-mn'); await cel.waitForTimeout(1500);
    R.celular_scroll_horizontal = await cel.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
    await cel.evaluate(() => document.querySelector('#bm-card section[data-paso="2"]').scrollIntoView()); await cel.waitForTimeout(300);
    await cel.screenshot({ path: `${OUT}/bg_rama_celular_paso2.png`, fullPage: false });
    // Sin permiso
    const v = await entrar('vendedor.fika@t.pe', FIKA, 'Vendedor-FIKA');
    await v.evaluate(() => { state.view = 'banks'; state.bankTab = 'movimiento'; renderView(); });
    await v.waitForFunction(() => /permiso/.test(document.getElementById('bm-card')?.innerText || ''), null, { timeout: 30000 });
    R.sin_permiso = await v.evaluate(() => ({ aviso: document.getElementById('bm-card').innerText.match(/Tu usuario[^\n]+/)?.[0], pasos: document.querySelectorAll('.bm-paso').length, config: !!document.getElementById('bm-cfg') }));
  }
  fs.writeFileSync(`${OUT}/bg_ui_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(TAG, 'listo, errores', JSON.stringify(R.errores_js));
  await b.close();
})();
