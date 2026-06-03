#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/dist/agent/windows/amd64"
OUTPUT_EXE="$OUTPUT_DIR/cyclope-agent.exe"

mkdir -p "$OUTPUT_DIR"
cd "$ROOT_DIR/agent"

GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o "$OUTPUT_EXE" ./cmd/cyclope-agent

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && sha256sum cyclope-agent.exe > cyclope-agent.exe.sha256)
elif command -v shasum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && shasum -a 256 cyclope-agent.exe > cyclope-agent.exe.sha256)
else
  echo "sha256sum or shasum is required to generate checksums" >&2
  exit 1
fi

echo "Built $OUTPUT_EXE"
echo "Wrote $OUTPUT_EXE.sha256"
