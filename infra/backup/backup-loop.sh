#!/bin/sh
set -eu

interval=${BACKUP_INTERVAL_SECONDS:-86400}
while true; do
  /opt/backup/backup-once.sh
  sleep "$interval"
done
