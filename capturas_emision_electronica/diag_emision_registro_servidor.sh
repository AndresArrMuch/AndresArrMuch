#!/bin/bash
# Diagnostico SOLO LECTURA del servidor para envios electronicos que no llegaron a NubeFact.
# No cambia nada; solo lee configuracion y registros. Uso:
#   bash /tmp/diag_registro.sh <sale_id_F020-000214> [<sale_id_B030-000016>]
# Los sale_id salen de la seccion e) de diag_emision_electronica.sql.
# Solo imprime lineas filtradas (rutas de la venta, reinicios, timeouts): no imprime tokens.
set -u
echo "== 1) Tiempos de espera configurados"
echo "-- gunicorn (servicio cea-erp):"
sudo systemctl cat cea-erp 2>/dev/null | grep -E '^(ExecStart|TimeoutStopSec|Restart)' | sed -E 's/(TOKEN|SECRET|KEY|PASSWORD)=[^ ]*/\1=***/g'
echo "-- variables de tiempo (sin valores secretos):"
sudo systemctl show cea-erp -p Environment | tr ' ' '\n' | grep -E '^(NUBECONT_TIMEOUT|GUNICORN|WEB_CONCURRENCY)' || echo "(NUBECONT_TIMEOUT no definido: se usa 20 s)"
grep -hE '^NUBECONT_TIMEOUT' ~/cea-erp/backend/.env ~/cea-erp/backend/'(1).env' 2>/dev/null || true
echo "-- nginx (proxy_*_timeout, client_body_timeout, keepalive):"
sudo grep -rhnE 'proxy_(read|send|connect)_timeout|send_timeout|client_body_timeout|keepalive_timeout|proxy_pass' /etc/nginx/sites-enabled/ /etc/nginx/nginx.conf /etc/nginx/conf.d/ 2>/dev/null || echo "(no se encontro configuracion de nginx)"

for ID in "$@"; do
  echo
  echo "== 2) Peticiones de la venta $ID en el registro de nginx (create no lleva el id; precheck, send, status, post si)"
  sudo zgrep -h "$ID" /var/log/nginx/access.log* 2>/dev/null | grep -oE '\[[^]]+\] "[A-Z]+ [^ ]+ [^"]+" [0-9]{3} [0-9]+( [0-9.]+)?' | sort || echo "(sin coincidencias)"
done

echo
echo "== 3) Respuestas 499/502/504 de nginx a rutas de envio electronico (cliente cerro, backend caido o tiempo agotado)"
sudo zgrep -hE '"POST /api/sales/[^ ]+/(electronic/send|electronic/precheck)[^"]*" (499|502|504) ' /var/log/nginx/access.log* 2>/dev/null | grep -oE '\[[^]]+\] "[A-Z]+ [^ ]+ [^"]+" [0-9]{3}' | sort | tail -50 || echo "(ninguna)"
echo "-- y a la creacion de ventas:"
sudo zgrep -hE '"POST /api/sales/[0-9a-f-]{36} [^"]*" (499|502|504) ' /var/log/nginx/access.log* 2>/dev/null | grep -oE '\[[^]]+\] "[A-Z]+ [^ ]+ [^"]+" [0-9]{3}' | sort | tail -50 || echo "(ninguna)"
echo "-- error.log de nginx (upstream timed out / connection refused / prematurely closed):"
sudo zgrep -hE 'upstream timed out|Connection refused|prematurely closed|no live upstreams' /var/log/nginx/error.log* 2>/dev/null | grep -oE '^[0-9/]+ [0-9:]+ \[[a-z]+\] [^,]+, client: [^,]+, server: [^,]+, request: "[A-Z]+ [^ ]+' | sort | tail -40 || echo "(ninguno)"

echo
echo "== 4) Reinicios del servicio y workers de gunicorn (17/09 y 21/10; horas del servidor)"
for D in 2026-09-17 2026-10-21; do
  echo "-- $D"
  sudo journalctl -u cea-erp --since "$D 00:00" --until "$D 23:59" --no-pager -o short-iso 2>/dev/null \
    | grep -E 'Started|Stopping|Stopped|WORKER TIMEOUT|Booting worker|Worker exiting|Shutting down|Handling signal|Traceback|Error|Exception' \
    | sed -E 's/(TOKEN|Authorization|token)[^ ]*/\1=***/Ig' | cut -c1-220 | tail -60
done
echo
echo "== 5) Rotacion de registros (cuantos dias guarda nginx)"
ls -la /var/log/nginx/ 2>/dev/null | grep access | head -20
