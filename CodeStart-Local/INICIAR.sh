#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if ! command -v ollama >/dev/null 2>&1; then
  echo "Instale o Ollama seguindo LEIA-ME.md antes de iniciar."
  exit 1
fi
python -m pip install -r requirements.txt
started_ollama=""
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama serve > ollama.log 2>&1 &
  started_ollama=$!
  trap 'if [ -n "$started_ollama" ]; then kill "$started_ollama" 2>/dev/null || true; fi' EXIT
  ready=0
  for attempt in {1..30}; do
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" != "1" ]; then echo "Ollama não iniciou. Confira ollama.log."; exit 1; fi
fi
ollama pull qwen2.5:1.5b
export AI_PROVIDER=ollama
python app.py
