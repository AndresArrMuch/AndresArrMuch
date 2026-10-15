// Diagnostico del Destinatario instalado (main 2f05eb0): que ve el usuario mientras escribe
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [PORT, DELAY] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 950 } });
  await p.route(/cdnjs\.cloudflare\.com/, r => r.abort());
  if (Number(DELAY)) await p.route(/\/customers\?q=/, async r => { await new Promise(x => setTimeout(x, Number(DELAY))); r.continue(); });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1000);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForTimeout(4500);
  await p.evaluate(() => { state.view = 'inventory'; state.invTab = 'gratuitas'; renderView(); }); await p.waitForTimeout(2500);
  const foto = () => p.evaluate(() => {
    const box = document.getElementById('ft-recipient-sug');
    return { aviso: document.getElementById('ft-recipient-hint')?.innerText.trim(), lista: box && box.style.display !== 'none' ? box.querySelectorAll('.ft-sug').length + ' clientes' : 'cerrada' };
  });
  await p.click('#ft-recipient'); await p.waitForTimeout(600);
  console.log(`[retraso red ${DELAY} ms] al hacer clic:`, JSON.stringify(await foto()));
  await p.type('#ft-recipient', '10', { delay: 180 }); await p.waitForTimeout(300);
  console.log(`[retraso red ${DELAY} ms] tras escribir "10":`, JSON.stringify(await foto()));
  const linea = [];
  const t0 = Date.now();
  const tecla = (async () => { for (const c of '45') { await p.keyboard.type(c); await p.waitForTimeout(180); } })();
  for (let i = 0; i < 25; i++) { const f = await foto(); linea.push(`${Date.now() - t0}ms ${f.aviso} / ${f.lista}`); await p.waitForTimeout(100); }
  await tecla;
  const unicos = linea.filter((x, i) => i === 0 || x.split(' ').slice(1).join(' ') !== linea[i - 1].split(' ').slice(1).join(' '));
  console.log(`[retraso red ${DELAY} ms] escribiendo "45" (cambios):\n  ` + unicos.join('\n  '));
  await b.close();
})();
