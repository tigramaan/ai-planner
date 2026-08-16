#!/bin/sh
set -eu

install -d -o planner -g planner -m 0700 /worker-secrets
install -o planner -g planner -m 0400 /run/secrets/vapid_private_source /worker-secrets/vapid_private.pem

exec gosu planner python /worker/worker.py
