#!/usr/bin/env bash
# Set up the Ollama local-model fallback on the machine that serves it.
#
# Usage (on the serving machine — downloads GBs, do NOT run where you
# do not want the model stored):
#   ./scripts/setup_ollama.sh [model-tag]
#
# Then, to use it instead of Gemini:
#   export CLAIMLENS_PROVIDER=ollama
#   export OLLAMA_HOST=http://localhost:11434   # or the serving host
#   export CLAIMLENS_MODEL_PLANNER="$MODEL" CLAIMLENS_MODEL_AGENT="$MODEL" CLAIMLENS_MODEL_FAST="$MODEL"
#
# This is a MANUAL switch (no automatic failover). Small local models
# are weaker at function calling: expect more agent retries; the loop
# already nudges, caps iterations, and never invents values.
set -euo pipefail

MODEL="${1:-${OLLAMA_MODEL:-gemma3:4b}}"
HOST="${OLLAMA_HOST:-http://localhost:11434}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "error: 'ollama' is not installed. Install it from https://ollama.com/download" >&2
  exit 1
fi

if ! curl -fsS -m 5 "$HOST/api/tags" >/dev/null 2>&1; then
  echo "Ollama server is not reachable at $HOST; starting 'ollama serve' in the background."
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  for _ in $(seq 1 30); do
    sleep 2
    if curl -fsS -m 5 "$HOST/api/tags" >/dev/null 2>&1; then
      break
    fi
  done
fi
curl -fsS -m 10 "$HOST/api/tags" >/dev/null
echo "Ollama server is up at $HOST."

echo "Pulling model '$MODEL' (large download, cached under ~/.ollama)..."
ollama pull "$MODEL"

echo "Smoke-testing '$MODEL' through the ClaimLens gateway..."
export CLAIMLENS_PROVIDER=ollama
export OLLAMA_HOST="$HOST"
export CLAIMLENS_MODEL_PLANNER="$MODEL"
export CLAIMLENS_MODEL_AGENT="$MODEL"
export CLAIMLENS_MODEL_FAST="$MODEL"
python3 - <<'PYEOF'
import os
from claimlens.config import ClaimLensConfig
from claimlens.llm import LLMGateway

gateway = LLMGateway(config=ClaimLensConfig.from_env())
result = gateway.complete(
    task="smoke_test",
    messages=[{"role": "user", "content": "Reply with the word ok."}],
    role="fast",
)
print("gateway smoke test returned:", str(result)[:200])
PYEOF

echo "OK: '$MODEL' is ready. Set CLAIMLENS_PROVIDER=ollama (plus OLLAMA_HOST if remote) to use it."
