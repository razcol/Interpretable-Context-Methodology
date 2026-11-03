#!/usr/bin/env bash
# Checks measure.js on the two local fixtures and its URL guard. Prereq: node scripts/browser.js start.
# Prints one line per case and exits 1 when any expectation fails.
set -u
cd "$(dirname "$0")/.."
F="file://$(pwd)/fixtures"
OUT="${1:-$(mktemp -d)}"
mkdir -p "$OUT"
fail=0
expect() { # expect NAME WANT_EXIT cmd...
  local name="$1" want="$2"; shift 2
  "$@" > "$OUT/$name.json" 2>&1
  local got=$?
  if [ "$got" = "$want" ]; then echo "ok   $name (exit $got)"; else echo "FAIL $name (exit $got, want $want)"; fail=1; fi
}
expect overflow     11 node scripts/measure.js --url "$F/overflow.html" --viewports 1100x800 --selector "#section" --out-dir "$OUT"
expect no-overflow  0  node scripts/measure.js --url "$F/no-overflow.html" --viewports 1920x1080,1440x900,1100x800 --selector "#section" --out-dir "$OUT"
expect remote-url   1  node scripts/measure.js --url https://example.com/ --out-dir "$OUT"
expect lan-url      1  node scripts/measure.js --url http://192.168.1.10:3000/ --out-dir "$OUT"
grep -q '"overflowPx": 200' "$OUT/overflow.json" && echo "ok   overflow is 200px" || { echo "FAIL overflow amount"; fail=1; }
exit $fail
