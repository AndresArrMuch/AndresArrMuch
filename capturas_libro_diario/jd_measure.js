// Libro Diario: mediciones en el navegador (main o rama)
// Uso: node jd_measure.js <puerto> <etiqueta> <carpeta_salida> <fa_dir> [email] [empresa]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA, EMAIL = 'admin@t.pe', CID = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch({ args: ['--enable-precise-memory-info'] });
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' });
  await ctx.addInitScript(() => {
    window.__lt = [];
    try { new PerformanceObserver(l => l.getEntries().forEach(e => window.__lt.push(e.duration))).observe({ type: 'longtask', buffered: true }); } catch (e) {}
    // Pausa maxima del hilo principal: un reloj cada 50 ms mide cuanto se atrasa
    window.__gap = 0; let last = performance.now();
    setInterval(() => { const now = performance.now(); window.__gap = Math.max(window.__gap, now - last - 50); last = now; }, 50);
  });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
    return r.abort();
  });
  const resp = [];
  p.on('requestfinished', async (req) => {
    if (!req.url().includes('/api/')) return;
    try {
      const r = await req.response(); const body = await r.body(); const t = req.timing();
      resp.push({ url: req.url().replace(/^https?:\/\/[^/]+/, '').replace(/[0-9a-f-]{36}/g, ':id'), bytes: body.length, ms: Math.round(t.responseEnd), at: Date.now() });
    } catch (e) {}
  });
  const cdp = await ctx.newCDPSession(p); await cdp.send('Performance.enable');
  const heapMB = async () => p.evaluate(() => Math.round((performance.memory ? performance.memory.usedJSHeapSize : 0) / 1048576));
  const reset = () => p.evaluate(() => { window.__lt = []; window.__gap = 0; });
  const bloqueo = () => p.evaluate(() => ({ tareas_largas: window.__lt.length, ms_bloqueado: Math.round(window.__lt.reduce((a, b) => a + b, 0)), tarea_mas_larga_ms: Math.round(Math.max(0, ...window.__lt)), pausa_maxima_ms: Math.round(window.__gap) }));
  const quieto = async (ms = 1500, max = 90000) => {  // espera hasta que no haya respuestas nuevas en "ms"
    const t0 = Date.now(); let n = -1, since = Date.now();
    while (Date.now() - t0 < max) { if (resp.length !== n) { n = resp.length; since = Date.now(); } if (Date.now() - since > ms) break; await p.waitForTimeout(200); }
  };
  const R = { tag: TAG, usuario: EMAIL };
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1500);
  await p.fill('#email', EMAIL); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await reset(); resp.length = 0;
  const t0 = Date.now();
  await p.evaluate(() => doLogin());
  await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 });
  const tPantalla = Date.now() - t0;
  await quieto();
  R.inicio_sesion = { ms_hasta_pantalla: tPantalla, ms_hasta_terminar_descargas: Date.now() - t0 - 1500, ...(await bloqueo()), memoria_mb: await heapMB(),
    descargas_total_kb: Math.round(resp.reduce((a, r) => a + r.bytes, 0) / 1024),
    mas_pesadas: resp.slice().sort((a, b) => b.bytes - a.bytes).slice(0, 8).map(r => `${r.url} ${Math.round(r.bytes / 1024)} KB en ${r.ms} ms`) };
  R.dashboard_asientos = await p.evaluate(() => {
    state.view = 'overview'; renderView();
    const art = [...document.querySelectorAll('#kpis article, #kpis > *')].find(a => /ASIENTOS CONTABLES/.test(a.innerText));
    return art ? art.innerText.replace(/\s+/g, ' ').trim() : '(no encontrada)';
  });
  // Abrir el Libro Diario
  await reset(); const n0 = resp.length;
  const t1 = Date.now();
  await p.evaluate(() => setTimeout(() => document.querySelector('#menu [data-view="journal"]').click(), 0));
  await p.waitForFunction(() => document.getElementById('jd-tbody') ? !!(document.getElementById('jd-info')?.innerText) : document.querySelectorAll('#panelBody tbody tr').length > 0, null, { timeout: 900000 });
  const tTabla = Date.now() - t1;
  await quieto(1000);
  R.libro_diario = { ms_hasta_ver_la_tabla: tTabla, ...(await bloqueo()), memoria_mb: await heapMB(),
    filas_dibujadas: await p.evaluate(() => document.querySelectorAll('#panelBody tbody tr').length), contador: await p.evaluate(() => document.getElementById('jd-info')?.innerText || ''),
    elementos_en_pagina: await p.evaluate(() => document.querySelectorAll('*').length),
    descargas: resp.slice(n0).map(r => `${r.url} ${Math.round(r.bytes / 1024)} KB en ${r.ms} ms`) };
  // Escribir en un filtro (glosa): cuanto se bloquea por tecla
  if (process.env.SIN_FILTRO) { R.filtro_glosa = 'omitido'; } else {
  await reset();
  const t2 = Date.now();
  const sel = await p.$('#journal-glosa-filter') ? '#journal-glosa-filter' : '#jd-f-text';
  await p.type(sel, 'planilla', { delay: 80 });
  await p.waitForTimeout(1500);
  R.filtro_glosa = { ms: Date.now() - t2, ...(await bloqueo()), filas: await p.evaluate(() => document.querySelectorAll('#panelBody tbody tr').length), contador: await p.evaluate(() => document.getElementById('jd-info')?.innerText || '') };
  }
  await p.screenshot({ path: `${OUT}/jd_${TAG}_libro_diario.png` });
  R.errores_js = errs;
  fs.writeFileSync(`${OUT}/jd_${TAG}.json`, JSON.stringify(R, null, 1));
  console.log(JSON.stringify(R, null, 1));
  await b.close();
})();
