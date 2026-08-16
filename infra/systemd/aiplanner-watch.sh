#!/bin/sh
set -eu

cd /opt/repos/aiplanner
docker compose up -d --no-build --remove-orphans

while sleep 30; do
  for service in postgres redis api web worker backup; do
    container_id=$(docker compose ps -q "$service")
    if [ -z "$container_id" ]; then
      docker compose up -d --no-build "$service"
      continue
    fi
    state=$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")
    case "$state" in
      "running healthy"|"running starting"|"running ") ;;
      *) docker compose up -d --no-build --force-recreate "$service" ;;
    esac
  done
done
