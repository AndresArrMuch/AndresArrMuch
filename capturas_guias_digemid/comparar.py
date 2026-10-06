# Compara la extraccion del reporte (Python) con la del SQL (PostgreSQL) sobre los mismos textos
import os, sys, subprocess, json
sys.path.insert(0, '/tmp/claude-0/wt_dig/backend'); os.environ['DATABASE_URL'] = 'sqlite://'
import warnings; warnings.filterwarnings('ignore')
from app.routes.guide_report_routes import _from_text
textos = [r[0] for r in json.loads(subprocess.run(['su', 'postgres', '-c', "psql -p 5433 -d digemid -Atc \"select json_agg(json_build_array(trim(coalesce(description,'')||' '||coalesce(secondary_description,'')))) from inventory_item where requires_digemid\""], capture_output=True, text=True, cwd='/tmp').stdout)]
textos += ['PARACETAMOL VENC. 2027-05-30 RS: EE-01234', 'BOLSA LTE. SIN NUMERO', 'X LTE.IN25 FV:03/2028 FF:01/2026', 'Y Lote: ab-12 vto 2029-01', 'COLTE.99 SALVE F.V.12-2030', 'R.S. N° DM-000-E']
sql = "select json_agg(json_build_array(t, " + ", ".join(
    "substring(t from '" + rx + "')" for rx in [
 r"(?i)(?:^|[^A-Z0-9])(?:R\.?\s?S\.?|REG(?:ISTRO)?\.?\s*SAN(?:ITARIO)?\.?)\s*(?:N[°ºO]\.?\s*)?[:#\-]?\s*([A-Z]{1,4}[\-\s]?[0-9]{2,}[A-Z0-9\-/]*)",
 r"(?i)(?:^|[^A-Z0-9])(?:LOTE|LTE)\.?\s*(?:N[°ºO]\.?\s*)?[:#\-]?\s*([A-Z0-9\-/]*[0-9][A-Z0-9\-/]*)",
 r"(?i)(?:^|[^A-Z0-9])(?:F\.?\s?V(?:ENC)?\.?|VENC(?:IMIENTO)?\.?|VTO\.?)\s*[:\-]?\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{1,2}[/\-.][0-9]{4}|[0-9]{4}[/\-.][0-9]{1,2}(?:[/\-.][0-9]{1,2})?)",
 r"(?i)(?:^|[^A-Z0-9])F\.?\s?F\.?\s*[:\-]?\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{1,2}[/\-.][0-9]{4}|[0-9]{4}[/\-.][0-9]{1,2}(?:[/\-.][0-9]{1,2})?)"]) + ")) from unnest(%s::text[]) t"
arr = "ARRAY[" + ",".join("'" + t.replace("'", "''") + "'" for t in textos) + "]"
open('/tmp/cmp.sql', 'w').write(sql % arr)
out = json.loads(subprocess.run(['su', 'postgres', '-c', 'psql -p 5433 -d digemid -Atf /tmp/cmp.sql'], capture_output=True, text=True, cwd='/tmp').stdout)
dif = 0
for t, rs, lote, venc, fab in out:
    py = _from_text((t,))
    sq = {'registro_sanitario': rs or '', 'lote': lote or '', 'vencimiento': venc or '', 'fabricacion': fab or ''}
    igual = py == sq; dif += not igual
    print('IGUAL' if igual else 'DISTINTO', '|', t[:70], '->', {k: v for k, v in py.items() if v}, '' if igual else sq)
print('textos:', len(out), 'diferencias:', dif)
