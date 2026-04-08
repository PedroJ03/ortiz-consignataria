# Skill: Sincronización de Base de Datos Railway → Local

## Trigger
Cuando el usuario necesita:
- "Traer base de producción"
- "Sync base de datos"
- "Actualizar db local"
- "Descargar datos de Railway"

## Contexto

Este proyecto (Ortiz Consignataria) usa **Railway** para producción y SQLite local para desarrollo.
Las bases de datos deben sincronizarse cuando se necesitan datos reales para pruebas.

## Ubicación de Bases

| Entorno | Ruta | Tamaño típico |
|---------|------|---------------|
| Producción (Railway) | `/app/data/precios_historicos.db` | ~2.3MB |
| Producción (Railway) | `/app/data/marketplace.db` | ~30KB |
| Local | `./precios_historicos.db` | Variable |
| Local | `./marketplace.db` | Variable |

**IMPORTANTE**: En Railway las bases están en `/app/data/`, NO en `/app/`.

## Método de Transferencia (OBLIGATORIO)

⚠️ **NUNCA uses `cat` directo** - se corrompe la base binaria.

✅ **SIEMPRE usa Python + Base64**:

```bash
# 1. Crear backup dentro de Railway usando Python
railway ssh -- "python3 -c '
import sqlite3
src = \"/app/data/precios_historicos.db\"
dst = \"/tmp/precios_backup.db\"
conn = sqlite3.connect(src)
backup_conn = sqlite3.connect(dst)
conn.backup(backup_conn)
backup_conn.close()
conn.close()
print(\"Backup creado\")
' && exit"

# 2. Transferir codificando en base64
railway ssh -- "python3 -c '
import base64
with open(\"/tmp/precios_backup.db\", \"rb\") as f:
    data = f.read()
encoded = base64.b64encode(data).decode(\"utf-8\")
for i in range(0, len(encoded), 4096):
    print(encoded[i:i+4096])
' && exit" > /tmp/db_base64.txt

# 3. Decodificar localmente
source entorno_consignataria/bin/activate
python3 -c "
import base64
with open('/tmp/db_base64.txt', 'r') as f:
    encoded = f.read()
encoded = ''.join(c for c in encoded if c.isalnum() or c in '+/=')
decoded = base64.b64decode(encoded)
with open('precios_historicos.db', 'wb') as f:
    f.write(decoded)
print(f'✅ Base actualizada: {len(decoded)} bytes')
"
```

## One-Liner Completo

```bash
cp precios_historicos.db precios_historicos_backup_$(date +%Y%m%d_%H%M).db 2>/dev/null || true && \
railway ssh -- "python3 -c 'import sqlite3; conn=sqlite3.connect(\"/app/data/precios_historicos.db\"); backup=sqlite3.connect(\"/tmp/precios_backup.db\"); conn.backup(backup); backup.close(); conn.close()'" && \
railway ssh -- "python3 -c 'import base64; f=open(\"/tmp/precios_backup.db\",\"rb\").read(); e=base64.b64encode(f).decode(); [print(e[i:i+4096]) for i in range(0,len(e),4096)]' && exit" > /tmp/db_base64.txt && \
source entorno_consignataria/bin/activate && \
python3 -c "import base64; d=base64.b64decode(''.join(c for c in open('/tmp/db_base64.txt').read() if c.isalnum() or c in '+/=')); open('precios_historicos.db','wb').write(d); print(f'✅ Base actualizada: {len(d)} bytes')"
```

## Verificación Post-Transferencia

```python
import sqlite3
conn = sqlite3.connect('precios_historicos.db')
cursor = conn.cursor()

# Verificar integridad
cursor.execute("PRAGMA integrity_check")
result = cursor.fetchone()
assert result[0] == 'ok', "Base corrompida"
print(f"✅ Integridad: {result[0]}")

# Verificar datos
cursor.execute("SELECT COUNT(*) FROM faena")
count = cursor.fetchone()
print(f"✅ Registros faena: {count[0]}")

cursor.execute("SELECT DISTINCT fecha_consulta FROM faena ORDER BY fecha_consulta DESC LIMIT 5")
print("✅ Últimas fechas:")
for row in cursor.fetchall():
    print(f"   - {row[0]}")

conn.close()
```

## Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| `database disk image is malformed` | Transferencia binaria corrupta | Usar Python + base64, nunca cat directo |
| `No such file: /app/*.db` | Wrong path | Las bases están en `/app/data/` |
| `sqlite3: not found` | No hay CLI en Railway | Usar Python sqlite3 module |
| Timeout en transferencia | Base muy grande | Usar chunks de 4096 chars en base64 |

## Notas

- Siempre hacer backup local antes de sobreescribir
- El comando `railway ssh` termina con `exit`
- SQLite en Railway no tiene CLI, usar Python obligatoriamente
