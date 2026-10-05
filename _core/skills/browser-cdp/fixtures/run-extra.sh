#!/usr/bin/env bash
# Second test batch: edge cases, external pages, determinism, persistence, timing.
# Usage: run-extra.sh OUT_DIR   (needs fixture server on 8765 and a running default browser)
set -u
OUT="${1:?usage: run-extra.sh OUT_DIR}"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
U=http://127.0.0.1:8765

t() { # t NAME cmd...   records json, exit code and wall ms
  local name="$1"; shift
  local s=$(date +%s%N)
  "$@" > "$OUT/$name.json" 2>&1
  echo $? > "$OUT/$name.exit"
  echo $(( ($(date +%s%N) - s) / 1000000 )) > "$OUT/$name.ms"
}

# edge cases
t shot-375            node scripts/screenshot.js --url "$U/" --viewports 375x812 --name small --out-dir "$OUT/shots"
t diff-sizemismatch   node scripts/diff.js --baseline "$OUT/shots/small__375x812.png" --current "$OUT/../all/shots/page__1280x800.png"
t navigate-refused    node scripts/navigate.js --url http://127.0.0.1:65000/ --timeout 8000
t no-browser          node scripts/navigate.js --url "$U/" --profile not-running
t snapshot-a11y-clean node scripts/snapshot.js --url "$U/" --mode a11y --out "$OUT/a11y-clean.json"

# external pages (real-world usage)
t ext-navigate        node scripts/navigate.js --url https://example.com/
t ext-shots-a         node scripts/screenshot.js --url https://example.com/ --viewports 375x812,768x1024,1280x800 --out-dir "$OUT/ext-a"
t ext-shots-b         node scripts/screenshot.js --url https://example.com/ --viewports 375x812,768x1024,1280x800 --out-dir "$OUT/ext-b"
t ext-capture         node scripts/capture.js --url https://example.com/
t ext-a11y            node scripts/snapshot.js --url https://example.com/ --mode a11y --out "$OUT/ext-a11y.json"
t ext-text            node scripts/snapshot.js --url https://example.com/ --mode text --out "$OUT/ext-text.txt"
t hn-full             node scripts/screenshot.js --url https://news.ycombinator.com/ --full-page --name hn --out-dir "$OUT/ext-a"
t hn-capture          node scripts/capture.js --url https://news.ycombinator.com/ --out "$OUT/hn-details.json"
t hn-interact         node scripts/interact.js --new-tab --url https://news.ycombinator.com/ --steps '[{"action":"get_text","selector":".titleline a"},{"action":"click","selector":"a.morelink"},{"action":"assert_url","contains":"p=2"}]'

# persistence across browser restart (persistent cookie)
cat > "$OUT/persist-cookie.json" <<'JSON'
[{"name":"persist_me","value":"keepme123","domain":"127.0.0.1","path":"/","expires":2000000000,"httpOnly":false,"secure":false}]
JSON
t persist-set         node scripts/state.js cookies-set --file "$OUT/persist-cookie.json"
t browser-stop        node scripts/browser.js stop
t browser-status-off  node scripts/browser.js status
t browser-start       node scripts/browser.js start
t persist-get         node scripts/state.js cookies-get --domain 127.0.0.1

# headed attempt (needs WSLg)
echo "DISPLAY=${DISPLAY:-} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}" > "$OUT/display.txt"
t headed-start        node scripts/browser.js start --headed --profile headed-test --port 9444
t headed-shot         node scripts/screenshot.js --url "$U/" --profile headed-test --name headed --out-dir "$OUT/headed"
t headed-stop         node scripts/browser.js stop --profile headed-test

echo done > "$OUT/DONE"
