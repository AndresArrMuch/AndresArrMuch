#!/bin/bash
S=/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/af
P="psql -h localhost -p 5433 -U postgres"
U="--usuario sistema.fika@t.pe"
fresh() { $P -qc "DROP DATABASE IF EXISTS $1" -c "CREATE DATABASE $1 TEMPLATE af_base" 2>/dev/null; }
h() { $P $1 -Atf $S/hash.sql; }
nf() { wc -l < $S/nf.log; }
kardex() { $P $1 -Atc "select i.item_code, m.movement_date, m.movement_type, coalesce(m.reference_type,'') ref, m.quantity, m.balance_quantity, left(coalesce(m.notes,''),40) from inventory_movement m join inventory_item i on i.id=m.item_id where m.item_id like 'af-i%' order by i.item_code, m.movement_date, m.created_at" | sed 's/^/    /'; }
case_abort() {  # nombre, sql de preparacion, [args extra], [escenario nubefact]
  echo; echo "################ ABORTO: $1"; fresh af_c; [ -n "$2" ] && $P af_c -qc "$2"
  echo "${4:-{\}}" > $S/esc.json; H0=$(h af_c); N0=$(nf)
  $S/run.sh af_c ${3:-$U} --aplicar | grep -E "FALLA|ABORTADO|ERROR|\[--\]|codigo de salida"
  H1=$(h af_c); echo "  llamadas a NubeFact simulada: $(( $(nf) - N0 ))"; [ "$H0" == "$H1" ] && echo "  BASE SIN CAMBIOS (hash identico antes y despues)" || echo "  !!! LA BASE CAMBIO"
}
echo '{}' > $S/esc.json
echo "################ 1) MODO DE PRUEBA (no escribe)"; fresh af_t1; H0=$(h af_t1); $S/run.sh af_t1 $U | tail -8; H1=$(h af_t1); echo "  antes: $H0" | tr '\n' ' '; echo; echo "  despues: $H1" | tr '\n' ' '; echo; [ "$H0" == "$H1" ] && echo "  BASE SIN CAMBIOS"
echo; echo "  Reportes ANTES:"; /tmp/claude-0/venv/bin/python $S/reports.py af_t1 2>/dev/null | grep "^  "
echo; echo "################ 2) --aplicar"; $S/run.sh af_t1 $U --aplicar | sed -n '/== Lo que se hara/,$p'; H2=$(h af_t1)
echo "  hash F030-000120 + su asiento: antes $(echo "$H0" | grep F030) / despues $(echo "$H2" | grep F030)"
echo "  Kardex despues:"; kardex af_t1
echo "  Venta:"; $P af_t1 -Atc "select document_number, status, coalesce(sunat_status,'(vacio)'), coalesce(sunat_ticket,'(vacio)'), coalesce(pdf_path,'(vacio)'), accounting_status, replace(notes,E'\n',' / ') from sale where document_number like 'F030%' order by 1" | sed 's/^/    /'
echo "  Bitacora audit_log:"; $P af_t1 -Atc "select action, table_name, record_id, user_agent, new_values->>'accion', new_values->>'usuario', old_values->>'status', new_values->>'status' from audit_log where record_id='b20e1049-9875-4dce-aacc-a37cf275d4ce'" | sed 's/^/    /'
echo "  Asientos con F030-000119 en la glosa: $($P af_t1 -Atc "select count(*) from journal_entry where gloss ilike '%F030-000119%'")"
echo; echo "  Reportes DESPUES:"; /tmp/claude-0/venv/bin/python $S/reports.py af_t1 2>/dev/null | grep "^  "
echo; echo "################ 3) SEGUNDA EJECUCION (prueba y --aplicar)"; N0=$(nf)
$S/run.sh af_t1 $U | tail -2; $S/run.sh af_t1 $U --aplicar | tail -2; H3=$(h af_t1)
echo "  llamadas a NubeFact: $(( $(nf) - N0 ))"; [ "$H2" == "$H3" ] && echo "  BASE SIN CAMBIOS"
echo; echo "################ 4) DESHACER (prueba, --aplicar, segunda vez)"
$S/run.sh af_t1 $U --deshacer | sed -n '/== Lo que haria/,$p'; [ "$H3" == "$(h af_t1)" ] && echo "  (prueba) BASE SIN CAMBIOS"
$S/run.sh af_t1 $U --deshacer --aplicar | sed -n '/APLICADO/,$p'
echo "  Kardex despues de deshacer:"; kardex af_t1
$P af_t1 -Atc "select '    venta: '||status||' sunat_status='||coalesce(sunat_status,'(vacio)')||' notes='||coalesce(notes,'(vacio)') from sale where document_number='F030-000119'"
H4=$(h af_t1); $S/run.sh af_t1 $U --deshacer --aplicar | tail -2; [ "$H4" == "$(h af_t1)" ] && echo "  BASE SIN CAMBIOS en la segunda vez"
echo "  hash F030-000120 + su asiento al final: $(h af_t1 | grep F030)"
echo "  Archivo de registro:"; tail -2 /root/anular_f030_000119.log | cut -c1-220 | sed 's/^/    /'
SID=b20e1049-9875-4dce-aacc-a37cf275d4ce
case_abort "NubeFact responde que el documento EXISTE" "" "" '{"F030-000119":{"existe":true,"aceptada":true}}'
case_abort "NubeFact sin conexion (error de red)" "UPDATE company SET nubecont_api_url='http://127.0.0.1:8939/api' WHERE id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'"
case_abort "NubeFact sin token (autenticacion/configuracion)" "UPDATE company SET nubecont_api_token='' WHERE id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433'"
case_abort "Tiene guia (sales_workflow vinculado)" "CREATE TEMP TABLE w AS SELECT * FROM sales_workflow LIMIT 1; INSERT INTO sales_workflow SELECT (jsonb_populate_record(w, jsonb_build_object('id','af-w','sale_id','$SID','quotation_number','COT-AF','guide_series','T030','guide_correlative','000001'))).* FROM w"
case_abort "Tiene cobro (amount_paid)" "UPDATE sale SET amount_paid=100 WHERE id='$SID'"
case_abort "Tiene linea de cobro (amount_paid en cero)" "INSERT INTO payment_record (id,company_id,payment_date,payment_type,total_amount,status,created_at,updated_at,is_active) VALUES ('af-pr','976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433','2026-10-17','cobro',100,'applied',now(),now(),true); INSERT INTO payment_line (id,payment_id,document_type,document_id,document_number,amount_applied,created_at,updated_at,is_active) VALUES ('af-pl','af-pr','sale','$SID','F030-000119',100,now(),now(),true)"
case_abort "Tiene nota de credito" "CREATE TEMP TABLE n AS SELECT * FROM sale WHERE id='NC1'; INSERT INTO sale SELECT (jsonb_populate_record(n, jsonb_build_object('id','af-nc','document_number','FC30-000001','series','FC30','correlative','000001','referenced_document_number','F030-000119'))).* FROM n"
case_abort "Tiene asiento de venta" "CREATE TEMP TABLE j AS SELECT * FROM journal_entry WHERE id='af-j120'; INSERT INTO journal_entry SELECT (jsonb_populate_record(j, jsonb_build_object('id','af-j119','entry_number','000119','gloss','Venta F030-000119 - PONEDORAS S.A.C.'))).* FROM j"
case_abort "Periodo de hoy cerrado" "UPDATE fiscal_period SET status='closed' WHERE id='ed4a35e4-8128-4b35-839b-f4d5ff62d837'"
case_abort "Cantidad distinta en una salida (21 en vez de 20)" "UPDATE inventory_movement SET quantity=21 WHERE id='af-m3'"
case_abort "Ya existe una entrada de reversa" "CREATE TEMP TABLE m AS SELECT * FROM inventory_movement WHERE id='af-m3'; INSERT INTO inventory_movement SELECT (jsonb_populate_record(m, jsonb_build_object('id','af-rv','movement_type','in','reference_type','sale_void'))).* FROM m"
case_abort "Ya enviada (sunat_status lleno)" "UPDATE sale SET sunat_status='aceptada' WHERE id='$SID'"
case_abort "F030-000120 no aceptada" "UPDATE sale SET sunat_status=NULL WHERE id='af-s120'"
case_abort "Usuario sin permiso (Vendedor)" "" "--usuario $($P af_base -Atc "select u.email from \"user\" u join role r on r.id=u.role_id where u.company_id='976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433' and r.name='Vendedor-FIKA' limit 1")"
case_abort "Sin --usuario y dos usuarios de rol Sistema" "" " "
case_abort "Movimiento con fecha posterior en el kardex (todo o nada: falla DESPUES de escribir y revierte)" "CREATE TEMP TABLE m AS SELECT * FROM inventory_movement WHERE id='af-m5'; INSERT INTO inventory_movement SELECT (jsonb_populate_record(m, jsonb_build_object('id','af-fut','reference_id','af-otra','movement_date','2026-12-31','balance_quantity',60))).* FROM m"
