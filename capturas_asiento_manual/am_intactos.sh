# Compara filas que ya existian en am_base contra la BD despues de las pruebas (rama)
P="psql -h /var/run/postgresql -p 5433 -U postgres -At"
for T in journal_entry journal_entry_line bank_transaction fiscal_period payment_record conciliacion_pago_registrado bank_account exchange_rate chart_of_account; do
  B=$($P -d am_base -c "select md5(string_agg(t::text, '|' order by t.id)) from $T t" 2>&1)
  for D in am_api_rama am_ui_rama; do
    X=$($P -d $D -c "select md5(string_agg(t::text, '|' order by t.id)) from $T t where t.id in (select id from dblink('dbname=am_base port=5433 host=/var/run/postgresql user=postgres','select id from $T') as x(id text))" 2>&1)
    echo "$T $D $([ "$B" = "$X" ] && echo INTACTAS || echo "DIFERENTES $B $X")"
  done
done
