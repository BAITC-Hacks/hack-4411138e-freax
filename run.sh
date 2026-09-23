#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for candidate in "$ROOT/.venv/bin/python" "${AYQYN_PYTHON:-}" python3 python; do
    if [[ -n "$candidate" ]] && command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        exec "$candidate" "$ROOT/scripts/bootstrap.py" "$@"
    fi
done
printf '%s\n' 'Python 3.10+ is required. Install it from https://www.python.org/downloads/ (Linux: install python3 and python3-venv), then run this script again.' >&2
exit 1
