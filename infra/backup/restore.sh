#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: restore.sh /backups/planner-TIMESTAMP.dump" >&2
  exit 2
fi

source_file=$1
test -f "$source_file"
test -f "$source_file.sha256"
sha256sum -c "$source_file.sha256"
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$PGDATABASE" "$source_file"
