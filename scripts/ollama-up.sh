#!/usr/bin/env bash
# Start the compose Ollama service and pull the local Qwen model.
#
#   ./scripts/ollama-up.sh
#
# The service also starts with `docker compose up -d` next to Postgres and
# Temporal. This script waits until the API answers, then pulls OLLAMA_MODEL
# (default qwen3:8b) into the ollama volume.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${OLLAMA_MODEL:-qwen3:8b}"

info() { printf '[ollama] %s\n' "$*"; }

cd "${ROOT}"
docker compose up -d ollama

info "waiting for the Ollama API"
ready=0
for _ in $(seq 1 60); do
  if docker compose exec -T ollama ollama list >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "${ready}" -ne 1 ]]; then
  info "Ollama did not become ready"
  exit 1
fi

info "pulling ${MODEL}"
docker compose exec -T ollama ollama pull "${MODEL}"
