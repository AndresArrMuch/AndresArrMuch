# Rotar el token de NubeFact (FIKA y FLUMISA)

Este procedimiento nunca muestra ni copia el token. Cada comando indica solo si el valor existe y su largo.

## 0. Antes de rotar: instalar `claude/sin-token-al-navegador`
Si se rota antes de instalarla, el token nuevo vuelve a llegar al navegador en la siguiente consulta.

## 1. Dónde se guarda hoy (lo dice el código)
`nubecont_service._provider_config`, en cada llamada al proveedor:
1. **Primero, la empresa en la base de datos.** `company.nubecont_api_token` y `company.nubecont_api_url`. Si la empresa tiene valor, **ese manda**.
2. **Si la empresa no tiene valor, el entorno:**
   - `NUBECONT_TOKEN` y `NUBECONT_*_URL`;
   - se leen de `backend/.env` y **también** de `backend/(1).env`. Ese segundo archivo se carga después y **sobrescribe** al primero;
   - pueden venir también del `Environment` del servicio systemd.

El `.env` se vuelve a leer **en cada llamada**, así que cambiarlo no requiere reiniciar. La base de datos también se lee en cada llamada.

**Comprobar dónde está, sin mostrar valores** (en el servidor, todo de solo lectura):
```
sudo -u postgres psql cea_erp_prod -c "SELECT business_name, ruc, coalesce(nubecont_api_token,'') <> '' AS token_en_bd, length(nubecont_api_token) AS largo_token, coalesce(nubecont_api_url,'') <> '' AS ruta_en_bd FROM company ORDER BY business_name"
```
```
cd ~/cea-erp/backend; for f in .env "(1).env"; do echo "$f: $(grep -c '^NUBECONT_TOKEN=' "$f" 2>/dev/null || echo 'no existe')"; done; echo "systemd: $(sudo systemctl show cea-erp -p Environment | grep -o 'NUBECONT_TOKEN=' | wc -l)"; ls /etc/systemd/system/cea-erp.service.d/ 2>/dev/null; sudo grep -l NUBECONT /etc/systemd/system/cea-erp.service.d/* 2>/dev/null
```
- Si `token_en_bd` es verdadero para una empresa, se cambia **en la empresa** (paso 3A).
- Si es falso, esa empresa usa el entorno y se cambia donde indique el segundo comando (paso 3B).
- FIKA y FLUMISA tienen RUC distintos y, normalmente, cuentas de NubeFact distintas: **un token por empresa, una empresa a la vez.**

## 2. En NubeFact: generar el token nuevo
1. Entrar al panel de la cuenta de la empresa, en la sección de API o integración, y generar o crear un token nuevo. Anótalo solo en el gestor de contraseñas.
2. **Antes de desactivar el viejo, comprobar si NubeFact permite tener dos tokens activos:**
   - **Si los permite:** se deja el viejo activo hasta terminar el paso 4. No se corta la emisión.
   - **Si generar uno nuevo invalida el viejo al instante:** hacer los pasos 2 a 4 seguidos, fuera de horario, en un mismo minuto. Durante ese minuto un envío puede fallar con un error de token. Con la función 1 ya instalada no se duplica; se reintenta.
3. **La ruta (URL)** identifica la cuenta y también se expuso. Preguntar a NubeFact si se puede regenerar. Si se puede, se cambia igual que el token.

## 3. En el sistema: poner el token nuevo, con el sistema funcionando
**A) Token en la empresa (lo normal).** Desde Configuración › Empresas › Editar:
- con la rama instalada, el campo aparece vacío con el texto "configurado (no se muestra)";
- se pega el token nuevo **solo en ese campo** y se guarda;
- dejar el campo vacío **no** borra nada;
- surte efecto en la siguiente llamada, sin reiniciar.

**B) Token en el entorno.**
1. Editar con `sudo nano` el archivo que indicó el paso 1: `.env`, `(1).env` o el `.conf` de systemd. Cambiar solo el valor de `NUBECONT_TOKEN`.
2. Si estaba en systemd, ejecutar `sudo systemctl daemon-reload && sudo systemctl restart cea-erp`.
3. Si estaba en `.env`, no hace falta reiniciar.

## 4. Comprobar que el nuevo funciona (antes de desactivar el viejo)
Una consulta real **de solo lectura**, con el script de la rama `claude/diag-estado-aceptada`. Consulta el estado de un documento aceptado y no escribe nada:
```
cd ~/cea-erp && git fetch origin && git show origin/claude/diag-estado-aceptada:backend/scripts/diag_estado_aceptada.py > /tmp/diag_estado_aceptada.py && cd backend && export DATABASE_URL=$(sudo systemctl show cea-erp -p Environment | grep -o 'DATABASE_URL=[^ ]*' | cut -d= -f2-) && .venv/bin/python /tmp/diag_estado_aceptada.py --empresa <RUC de la empresa> --limite 3
```
- **`CONFIRMADOS: 3`:** el token nuevo funciona.
- **`ERROR_CONSULTA: HTTP 401` o `403`:** el sistema todavía usa otro valor. Revisar el paso 1; por ejemplo, `(1).env` puede estar sobrescribiendo.

Después, una emisión real de bajo riesgo en horario normal, la siguiente venta. Solo entonces se **desactiva el token viejo** en NubeFact y se repite la comprobación.

## 5. Repetir con la otra empresa
Pasos 2 a 4 con la otra cuenta.

## 6. Qué no hace este procedimiento
- No muestra, copia ni registra ningún token.
- No cambia nada de ventas, asientos, periodos, PLE ni TXT.
