#!/bin/sh
set -eu

backup_dir=${BACKUP_DIR:-/backups}
retention_days=${BACKUP_RETENTION_DAYS:-14}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
partial="$backup_dir/planner-$timestamp.dump.partial"
target="$backup_dir/planner-$timestamp.dump"

mkdir -p "$backup_dir"
pg_dump --format=custom --no-owner --no-acl --file="$partial"
pg_restore --list "$partial" >/dev/null
mv "$partial" "$target"
sha256sum "$target" > "$target.sha256"
date -u +%FT%TZ > "$backup_dir/latest.ok"
find "$backup_dir" -type f -name 'planner-*.dump' -mtime "+$retention_days" -delete
find "$backup_dir" -type f -name 'planner-*.dump.sha256' -mtime "+$retention_days" -delete
printf '%s\n' "$target"
