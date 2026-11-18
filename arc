#!/usr/bin/env bash
# ai-readiness command. Run ./arc help
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf 'python3 was not found.\n'
  printf 'This tool needs Python 3.9 or newer, standard library only.\n'
  printf 'macOS: install the Xcode command line tools with "xcode-select --install", or get Python from python.org.\n'
  exit 1
fi
exec python3 -B "$HERE/scripts/arc.py" "$@"
