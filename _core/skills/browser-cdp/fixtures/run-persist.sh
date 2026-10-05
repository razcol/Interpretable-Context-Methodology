#!/usr/bin/env bash
# Verifies a persistent cookie survives stop/start of the browser (profile persistence).
set -u
OUT="${1:?usage: run-persist.sh OUT_DIR}"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
cat > "$OUT/persist-cookie.json" <<'JSON'
[{"name":"persist_me","value":"keepme123","domain":"127.0.0.1","path":"/","expires":2000000000,"httpOnly":false,"secure":false}]
JSON
node scripts/browser.js start      > "$OUT/1-start.json" 2>&1
node scripts/state.js cookies-set --file "$OUT/persist-cookie.json" > "$OUT/2-set.json" 2>&1
node scripts/browser.js stop       > "$OUT/3-stop.json" 2>&1
node scripts/browser.js start      > "$OUT/4-start.json" 2>&1
node scripts/state.js cookies-get --domain 127.0.0.1 > "$OUT/5-get.json" 2>&1
echo done > "$OUT/DONE"
