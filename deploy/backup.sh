#!/bin/sh
set -e
cd "$(dirname "$0")/.."
. ./.env
mkdir -p backups
out="backups/smhs-$(date +%Y%m%d-%H%M).sql.gz"
docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$out"
chmod 600 "$out"
find backups -name 'smhs-*.sql.gz' -mtime +30 -delete
