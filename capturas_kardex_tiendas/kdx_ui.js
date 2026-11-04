// Kardex en pantalla para cada usuario (main o rama)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, TAG, OUT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', FLU = 'ff8936f6-245c-4ff4-bffa-78b8fc3f8c78';
const CASES = [['nilton', 'ventas2@fikaperu.com', FIKA], ['saul_yorko', 'ventas.tda.filomena@gmail.com', FIKA],
               ['francisco_fika', 'ventas1@fikaperu.com', FIKA], ['francisco_flumisa', 'ventas1@fikaperu.com', FLU],
               ['almacenero', 'central@t.pe', FIKA], ['admin', 'admin@t.pe', FIKA]];
(async () => {
  const b = await chromium.launch();
  for (const [key, email, cid] of CASES) {
    const p = await b.newPage({ viewport: { width: 1400, height: 1100 } }); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', cid).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
    await p.evaluate(async () => { state.view = 'inventory'; state.invTab = 'items'; await loadModuleData(); renderView(); }); await p.waitForTimeout(2500);
    const info = await p.evaluate(() => {
      const kardex = document.getElementById('kardex-toggle-header');
      if (kardex) document.getElementById('kardex-toggle-body').style.display = 'block';
      const sel = document.getElementById('inv-warehouse-filter');
      const ksel = document.getElementById('kardex-warehouse-filter');
      const rows = [...document.querySelectorAll('#kardex-tbody tr[data-warehouse-id]')];
      const whCodes = [...new Set(rows.map(r => r.children[2]?.innerText.trim().split(' ')[0]))].sort();
      const cabecera = [...document.querySelectorAll('#kardex-tbody')].length ? [...document.querySelector('#kardex-tbody').closest('table').querySelectorAll('thead th')].map(t => t.innerText.trim()) : [];
      return { usuario: state.user?.email, empresa: state.companyId, rol: state.user?.role?.name, kardex_visible: !!kardex,
               selector: sel ? [...sel.options].map(o => o.text) : [], selector_kardex: ksel ? [...ksel.options].map(o => o.text) : [], filas_kardex: rows.length, almacenes_en_kardex: whCodes,
               columnas_kardex: cabecera, costos_en_cache: (state.cache.inventory_movements || []).some(m => 'unit_cost' in m) };
    });
    console.log(TAG, key, JSON.stringify(info), 'errores JS:', JSON.stringify(errs));
    if (info.kardex_visible) { await p.locator('#kardex-toggle-header').scrollIntoViewIfNeeded(); await p.screenshot({ path: `${OUT}/kdx_${TAG}_${key}.png` }); }
    await p.close();
  }
  await b.close();
})();
