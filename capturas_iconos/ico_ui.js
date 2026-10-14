// Iconos en lugar de emojis: recorre las pantallas (main o rama), cuenta emojis visibles y captura
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
const EMOJI = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{2300}-\u{23FF}]/gu;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1500, height: 1100 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  // Font Awesome 6.5.1 desde la copia local (cdnjs no es accesible en la prueba); el resto de cdnjs se corta
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/);
    if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1500);
  await p.screenshot({ path: `${OUT}/ico_${TAG}_00_login.png` });
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForTimeout(5000);
  const pantallas = [
    ['01_vista_general', { view: 'overview' }],
    ['02_dashboard', { view: 'dashboard' }],
    ['03_ventas_facturas', { view: 'sales', salesTab: 'invoices' }],
    ['04_ventas_cotizaciones', { view: 'sales', salesTab: 'quotations' }],
    ['05_ventas_reportes', { view: 'sales', salesTab: 'reports' }],
    ['06_compras_local', { view: 'purchases', purchaseTab: 'local' }],
    ['07_compras_reportes', { view: 'purchases', purchaseTab: 'reports' }],
    ['08_inventario_items', { view: 'inventory', invTab: 'items' }],
    ['09_inventario_transferencias', { view: 'inventory', invTab: 'transfers' }],
    ['10_inventario_gratuitas', { view: 'inventory', invTab: 'gratuitas' }],
    ['11_inventario_requerimientos', { view: 'inventory', invTab: 'requerimientos' }],
    ['12_cobranza_cobros', { view: 'banks', bankTab: 'transacciones', _cxcMode: 'cobros' }],
    ['13_cobranza_pagos', { view: 'banks', bankTab: 'transacciones', _cxcMode: 'pagos' }],
    ['14_bancos_conciliacion', { view: 'banks', bankTab: 'conciliacion' }],
    ['15_bancos_cuentas', { view: 'banks', bankTab: 'cuentas' }],
    ['16_planilla', { view: 'payroll' }],
    ['17_libro_diario', { view: 'journal' }],
    ['18_tributario', { view: 'tax' }],
    ['19_vendedores', { view: 'vendedores' }],
    ['20_rendicion', { view: 'rendicion' }],
  ];
  const resumen = {};
  for (const [nombre, st] of pantallas) {
    await p.evaluate(async (st) => { Object.assign(state, st); try { renderView(); } catch (e) { console.error(e); } }, st);
    await p.waitForTimeout(1800);
    const info = await p.evaluate(() => {
      const txt = document.body.innerText;
      return {
        texto: txt,
        iconos_nuevos: document.querySelectorAll('[data-ico]').length,
        iconos_sin_fuente: [...document.querySelectorAll('[data-ico]')].filter(i => getComputedStyle(i, '::before').content === 'none').length,
        codigo_visible: txt.includes('<i data-ico') || txt.includes('data-ico class='),
        botones: [...document.querySelectorAll('#panelBody button')].slice(0, 400).map(x => x.innerText.trim()).filter(Boolean),
      };
    });
    const emojis = [...new Set(info.texto.match(EMOJI) || [])];
    resumen[nombre] = { emojis_visibles: emojis.join(' '), iconos: info.iconos_nuevos, iconos_sin_fuente: info.iconos_sin_fuente,
                        codigo_visible: info.codigo_visible, botones_con_iconos_dobles: 0 };
    resumen[nombre].iconos_dobles = await p.evaluate(() => [...document.querySelectorAll('button, .btn')].filter(x => x.querySelectorAll('.btn-icon, [data-ico]').length > 1).map(x => x.innerText.trim()));
    await p.screenshot({ path: `${OUT}/ico_${TAG}_${nombre}.png` });
  }
  console.log(JSON.stringify({ tag: TAG, resumen, errores_js: errs }, null, 1));
  await b.close();
})();
