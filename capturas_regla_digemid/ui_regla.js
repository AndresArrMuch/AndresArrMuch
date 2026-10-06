// Pantalla de la regla DIGEMID (SOLO PRUEBA, NubeCont simulado)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, TAG, LOG, COT_DIG, COT_MIX] = process.argv.slice(2);
const W = (p, ms) => p.waitForTimeout(ms);
const P3 = 'ccfabd3b-6328-433a-84fc-7d617dee1c66', P1 = '2a9e4da0-d0eb-4d65-9823-4554349027b2', ALM = '93490ee2-011e-4664-b8cc-bc868bb21940';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1500, height: 1200 } });
  const errs = []; let posts = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('dialog', d => d.accept());
  await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
  p.on('response', async r => { if (r.request().method() === 'POST' && /workflow\/(direct-guide|[^/]+\/issue-guide)$/.test(r.url())) { let j = {}; try { j = await r.json(); } catch (e) {} posts.push({ body: JSON.parse(r.request().postData() || '{}'), status: r.status(), resp: j }); } });
  const log = (o) => console.log(JSON.stringify(Object.assign({ srv: TAG }, o)));
  const modo = (m) => fs.writeFileSync(LOG + '.mode', m);
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await W(p, 1500);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433').catch(() => {});
  await p.evaluate(() => doLogin()); await W(p, 6000);
  const abrirGD = async (items) => {
    await p.evaluate(() => { state.view = 'sales'; state.salesTab = 'guides'; state.showDirectGuideForm = true; state.guideFromSaleId = null; state.activeGuideWorkflowId = null; renderView(); }); await W(p, 2500);
    await p.evaluate(([items, ALM]) => {
      const c = (state.cache.customers || [])[0]; document.getElementById('dg-customer').value = c.id;
      const ac = document.querySelector('#dg-customer-ac input'); if (ac) ac.value = c.ruc_or_dni + ' - ' + c.business_name;
      document.getElementById('direct-guide-lines').innerHTML = '';
      items.forEach(id => addDirectGuideLine({ inventory_item_id: id, quantity: 1, warehouse_id: ALM }));
      document.querySelectorAll('#direct-guide-lines .dg-warehouse').forEach(sel => { if (![...sel.options].some(o => o.value === ALM)) sel.add(new Option('ALMFIKA (prueba)', ALM)); sel.value = ALM; });
      document.getElementById('dg-llegada-dir').value = 'Jr. Cusco 456'; document.getElementById('dg-llegada-ubigeo').value = '150101';
      const sp = document.getElementById('dg-partida-dir'); if (sp && sp.options.length) sp.selectedIndex = 0;
    }, [items, ALM]);
    await p.fill('#dg-fecha-inicio', '2026-10-07'); await p.fill('#dg-peso', '2'); await p.fill('#dg-bultos', '1');
    await p.fill('#dg-placa', 'ABC123'); await p.fill('#dg-cond-doc', '74096091'); await p.fill('#dg-cond-nombre', 'JUAN'); await p.fill('#dg-cond-apellidos', 'PEREZ'); await p.fill('#dg-cond-lic', 'Q74096091');
    await W(p, 500);
  };
  const panel = () => p.evaluate(() => {
    const pn = document.getElementById('dg-digemid-panel'), s = document.getElementById('dg-partida-dir-digemid'), e = document.getElementById('dg-digemid-err');
    return { panel_visible: !!pn && pn.style.display !== 'none', texto: document.getElementById('dg-digemid-msg')?.textContent, partida_elegida: s?.value || '(vacia)',
             opciones: s ? [...s.options].map(o => o.textContent).slice(0, 6) : [], error_rojo: !!e && e.style.display !== 'none',
             lineas_en_formulario: [...document.querySelectorAll('#direct-guide-lines .dg-line')].map(r => (state.cache.inventory_items.find(i => i.id === r.dataset.inventoryItemId) || {}).item_code) };
  });
  const emitir = async (espera = 6000) => {
    posts = []; await p.click('#createDirectGuideBtn'); await W(p, espera);
    return { envios: posts.map(x => ({ http: x.status, serie: x.body.series, partida_digemid: x.body.digemid_departure_address, lineas: (x.body.lines || []).length,
                                       guias: ((x.resp.data && (x.resp.data.workflows || [x.resp.data])) || []).map(w => (w.workflow || w).guide_number).filter(Boolean), codigo: x.resp.error && x.resp.error.code })),
             aviso: await p.evaluate(() => (document.getElementById('guide-inline-notice')?.textContent || '').trim().slice(0, 330)) };
  };
  modo('ok');
  // A) Guia directa: solo DIGEMID
  await abrirGD([P3]);
  log({ caso: 'A1 guia directa con P0003 (DIGEMID): panel', ...(await panel()) });
  log({ caso: 'A2 emitir sin elegir la partida DIGEMID', ...(await emitir(1500)), ...(await panel()) });
  await p.screenshot({ path: `/tmp/claude-0/repro/regla/${TAG}_A2_sin_partida.png` });
  await p.selectOption('#dg-partida-dir-digemid', { index: 1 }); await W(p, 300);
  log({ caso: 'A3 eligo la partida y emito', ...(await emitir()), error_rojo_despues_de_elegir: (await panel()).error_rojo });
  // B) Mezclada, falla la segunda guia (la no DIGEMID) y reintento
  await abrirGD([P3, P1]);
  log({ caso: 'B1 guia directa con P0003 + P0001: panel', ...(await panel()) });
  await p.screenshot({ path: `/tmp/claude-0/repro/regla/${TAG}_B1_mezclada.png` });
  await p.selectOption('#dg-partida-dir-digemid', { index: 2 }); modo('failnot4');
  log({ caso: 'B2 emitir: falla la segunda guia', ...(await emitir()), ...(await panel()) });
  await p.screenshot({ path: `/tmp/claude-0/repro/regla/${TAG}_B2_falla_segunda.png` });
  modo('ok');
  log({ caso: 'B3 reintento con lo que quedo en el formulario', ...(await emitir()) });
  // C) Sin DIGEMID
  await abrirGD([P1]);
  log({ caso: 'C1 guia directa solo P0001: panel', ...(await panel()) });
  log({ caso: 'C2 emitir', ...(await emitir()) });
  // D) Traer cotizacion 100% DIGEMID
  await abrirGD([]);
  await p.evaluate((id) => { const w = (state.cache.sale_workflows || []).find(x => x.id === id); applyQuotationToDirectGuide(w); }, COT_DIG); await W(p, 1500);
  log({ caso: 'D1 Traer cotizacion 100% DIGEMID: panel', ...(await panel()) });
  // E) Modal 'Emitir guia' de una cotizacion mezclada
  await p.evaluate((id) => { window.__modalRes = 'pendiente'; openGuideDataModal(id, { title: 'Prueba' }).then(r => { window.__modalRes = r ? { digemid_departure_address: r.digemid_departure_address, serie: r.serie } : null; }); }, COT_MIX); await W(p, 1500);
  const modalInfo = () => p.evaluate(() => { const s = document.getElementById('g-partida-dir-digemid'); const e = document.getElementById('g-digemid-err');
    return { panel: !!s, texto: s ? s.parentElement.querySelector('label').textContent : null, partida: s ? (s.value || '(vacia)') : null, error_rojo: !!e && e.style.display !== 'none', modal_abierto: !!document.getElementById('guide-modal-save'), resultado: window.__modalRes }; });
  log({ caso: 'E1 modal Emitir guia (cotizacion mezclada)', ...(await modalInfo()) });
  await p.evaluate(() => { const set = (id, v) => { const e = document.getElementById(id); if (e) e.value = v; }; set('g-fecha-traslado', '2026-10-07'); set('g-cond-doc', '74096091'); set('g-cond-lic', 'Q1'); set('g-partida-ubigeo', '150101'); set('g-llegada-ubigeo', '150101'); });
  await p.click('#guide-modal-save'); await W(p, 800);
  log({ caso: 'E2 Guardar sin elegir la partida DIGEMID', ...(await modalInfo()) });
  await p.screenshot({ path: `/tmp/claude-0/repro/regla/${TAG}_E2_modal_sin_partida.png` });
  await p.selectOption('#g-partida-dir-digemid', { index: 1 }); await p.click('#guide-modal-save'); await W(p, 800);
  log({ caso: 'E3 eligo la partida y Guardar', ...(await modalInfo()) });
  log({ erroresJS: errs });
  await b.close();
})();
