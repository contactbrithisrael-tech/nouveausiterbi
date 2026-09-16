#!/bin/sh
# Lance toute la suite. Aucune dépendance externe requise.
cd "$(dirname "$0")" || exit 1
code=0
for f in tests/test_*.py; do
    echo "── $f"
    python3 "$f" || code=1
done
exit $code
