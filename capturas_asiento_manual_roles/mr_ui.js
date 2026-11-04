// Roles, aviso corto y cuenta sin 104 propia en pantalla (main y rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
const ROLES = ['Administrador-FIKA', 'Administrador-FLUMISA', 'AlmacenGuias-FIKA', 'AlmacenGuias-FLUMISA', 'Almacenero-FLUMISA', 'Gerente-FIKA',
  'Gerente-FLUMISA', 'Sistema-FIKA', 'Sistema-FLUMISA', 'TiendaCapon-FIKA', 'TiendaCapon-FLUMISA', 'TiendaMalvinas-FIKA',
  'TiendaMalvinas-FLUMISA', 'Vendedor-FIKA', 'Vendedor-FLUMISA', 'Tesoreria', 'Encargado-FIKA', 'Encargado-FLUMISA', 'Sistemas', 'Gerente', 'Administrador'];
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [], roles: {} };
  const entrar = async (email, cid, nombre) => {
    const ctx = await b.newContext({ viewport: { width: 1500, height: 1100 }, timezoneId: 'America/Lima' });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(nombre + ': ' + e.message)); p.on('dialog', d => d.accept());
    await p.route(/cdnjs\.cloudflare\.com/, r => {
      const u = r.request().url();
      if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
      const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
      return r.abort();
    });
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(2000);
    return p;
  };
  const conciliacion = async (p, cuenta) => {
    await p.evaluate(async (c) => { state.view = 'banks'; state.bankTab = 'conciliacion'; state._concAccount = c; state._concMonth = '2026-10'; state._concYear = '2026'; renderView(); await cargarExcelPersistidoConciliacion(); }, cuenta);
    await p.waitForTimeout(2500);
    return p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(tr => tr.dataset.op + ' ' + tr.children[2].innerText.trim() + ' ' + tr.children[4].innerText.trim() + ' [' + (tr.children[8].innerText.trim() || '-') + ']'));
  };
  const tarjeta = async (p, view, tab, host, save) => {
    await p.evaluate(([v, t]) => { state.view = v; if (t) state.bankTab = t; renderView(); }, [view, tab]);
    await p.waitForFunction(([h, s]) => document.querySelector(h + ' ' + s) || /permiso/.test(document.querySelector(h)?.innerText || ''), [host, save], { timeout: 30000 });
    return p.evaluate(([h, s]) => document.querySelector(h + ' ' + s) ? 'formulario' : (document.querySelector(h).innerText.match(/Tu usuario[^\n]+/)?.[0] || '?'), [host, save]);
  };
  for (const name of ROLES) {
    const cid = name.endsWith('-FLUMISA') ? FLU : FIKA;
    const p = await entrar(name.toLowerCase().replace(/-/g, '.') + '@t.pe', cid, name);
    const row = { empresa: cid === FIKA ? 'FIKA' : 'FLUMISA' };
    row.libro_diario = await tarjeta(p, 'journal', null, '#mj-card', '#mj-save');
    row.bancos_movimiento = await tarjeta(p, 'banks', 'movimiento', '#bm-card', '#bm-save').catch(() => 'sin pestana');
    const filas = await conciliacion(p, cid === FIKA ? 'bk-fika-bcp-mn' : 'bk-flu-bcp-mn');
    row.conciliacion_boton = filas.filter(f => /Registrar como/.test(f)).length + ' de ' + filas.length + ' filas';
    R.roles[name] = row;
    if (name === 'Sistema-FIKA') await p.screenshot({ path: `${OUT}/mr_${TAG}_sistema_fika_libro_diario.png`, fullPage: false }).catch(() => {});
    await p.context().close();
  }
  // Administrador de prueba: aviso, desplegable, ayuda del N. de operacion, cuenta sin 104 propia; lo existente
  const admin = await entrar('admin@t.pe', FIKA, 'admin');
  R.existente = {
    libro: await admin.evaluate(async () => (await api('/api/journal-entries/' + state.companyId + '/book?all=1&tz=' + new Date().getTimezoneOffset())).data.data.map(e => [e.display_number, e.entry_number, e.entry_date, e.gloss].join(' | '))),
    conciliacion_bcp: (await conciliacion(admin, 'bk-fika-bcp-mn')).map(f => f.replace(/ \[.*\]$/, '')),
    dashboard: await admin.evaluate(() => { state.view = 'dashboard'; renderView(); return document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | '); }),
  };
  await admin.evaluate(() => { state.view = 'journal'; renderView(); }); await admin.waitForFunction(() => document.querySelector('#mj-card #mj-save'), null, { timeout: 30000 });
  await admin.waitForTimeout(800);
  const card = () => admin.evaluate(() => { const c = document.getElementById('mj-card'); const d = document.getElementById('mj-help');
    return { aviso: c.querySelector('div')?.innerText.split('\n')[0], alto_aviso_px: Math.round(c.querySelector('div')?.getBoundingClientRect().height || 0),
      desplegable: d ? (d.open ? 'abierto' : 'plegado') : 'no hay', lista_visible: d ? d.querySelector('ul').getBoundingClientRect().height > 0 : null,
      ayuda_op: c.querySelector('#mj-op')?.parentElement.innerText.replace(/\s+/g, ' ') }; });
  R.aviso_al_entrar = await card();
  await admin.screenshot({ path: `${OUT}/mr_${TAG}_1_aviso.png`, clip: { x: 290, y: 170, width: 1200, height: 520 } });
  if (TAG === 'rama') {
    await admin.click('#mj-help summary'); await admin.waitForTimeout(300);
    R.aviso_tras_clic = await card();
    R.lista_desplegada = await admin.evaluate(() => document.querySelector('#mj-help ul').innerText.split('\n'));
    await admin.screenshot({ path: `${OUT}/mr_rama_2_aviso_desplegado.png`, clip: { x: 290, y: 170, width: 1200, height: 620 } });
    // Al redibujar la tarjeta (p. ej. al escribir la glosa y cambiar la fecha) se queda abierto
    await admin.fill('#mj-date', '2026-10-14'); await admin.dispatchEvent('#mj-date', 'change'); await admin.waitForTimeout(800);
    R.aviso_tras_redibujar = (await card()).desplegable;
    await admin.click('#mj-help summary'); await admin.waitForTimeout(300);
    R.aviso_tras_segundo_clic = await card();
  }
  // Linea 104101: que cuentas bancarias ofrece la pantalla
  await admin.fill('#mj-card .mj-acc[data-i="1"]', '104101 - BANCO DE CREDITO MN'); await admin.dispatchEvent('#mj-card .mj-acc[data-i="1"]', 'change'); await admin.waitForTimeout(400);
  R.bancos_para_104101 = await admin.evaluate(() => [...document.querySelectorAll('#mj-card .mj-bank[data-i="1"] option')].map(o => o.textContent.trim()));
  await admin.screenshot({ path: `${OUT}/mr_${TAG}_3_banco_104101.png`, clip: { x: 290, y: 170, width: 1200, height: 620 } });
  fs.writeFileSync(`${OUT}/mr_ui_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(TAG, 'listo, errores', JSON.stringify(R.errores_js));
  await b.close();
})();
