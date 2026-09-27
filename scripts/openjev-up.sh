#!/usr/bin/env bash
# Start the compose openJev service and wait until its API answers.
#
#   ./scripts/openjev-up.sh
#
# The service also starts with `docker compose up -d` next to Postgres,
# Temporal, and Ollama. The first start downloads Laya weights into the
# openjev volume. This script waits for GET /health on the host port.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${JEV_BASE_URL:-http://127.0.0.1:8081}"

info() { printf '[openjev] %s\n' "$*"; }

cd "${ROOT}"
docker compose up -d openjev

info "waiting for ${BASE}/health"
ready=0
for _ in $(seq 1 180); do
  if curl -sf "${BASE}/health" >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "${ready}" -ne 1 ]]; then
  info "openJev did not become ready (weights may still be downloading)"
  docker compose ps openjev || true
  exit 1
fi

info "models"
curl -sf "${BASE}/v1/models"
printf '\n'
