#!/bin/bash
set -e

if [ -n "$DB_HOST" ]; then
    echo "Esperando a PostgreSQL en $DB_HOST:$DB_PORT..."
    python -c "
import socket, time, os
host = os.environ['DB_HOST']
port = int(os.environ.get('DB_PORT', 5432))
while True:
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print('PostgreSQL listo')
        break
    except (OSError, ConnectionRefusedError):
        time.sleep(0.5)
"
fi

python manage.py migrate --database=default
python manage.py migrate_all_tenants
python manage.py collectstatic --noinput

exec "$@"
