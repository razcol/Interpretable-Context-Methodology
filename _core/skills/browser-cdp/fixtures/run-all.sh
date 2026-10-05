#!/usr/bin/env bash
# Exercises every browser-cdp script against the fixture server and writes
# <name>.json + <name>.exit into the directory given as $1.
# Prereqs: node fixtures/serve.js (port 8765) and node scripts/browser.js start.
set -u
OUT="${1:?usage: run-all.sh OUT_DIR}"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
U=http://127.0.0.1:8765

t() { # t NAME cmd...
  local name="$1"; shift
  "$@" > "$OUT/$name.json" 2>&1
  echo $? > "$OUT/$name.exit"
}

t navigate            node scripts/navigate.js --url "$U/"
t navigate-404        node scripts/navigate.js --url "$U/nope"
t navigate-refused    node scripts/navigate.js --url http://127.0.0.1:1/
t navigate-bad-url    node scripts/navigate.js --url not-a-url
t capture             node scripts/capture.js --url "$U/" --out "$OUT/capture-details.json"
t snapshot-a11y       node scripts/snapshot.js --url "$U/" --mode a11y --out "$OUT/snap-a11y.json"
t snapshot-dom        node scripts/snapshot.js --url "$U/" --mode dom --max-depth 3 --out "$OUT/snap-dom.json"
t snapshot-html-sel   node scripts/snapshot.js --url "$U/" --mode html --selector form --out "$OUT/snap-form.html"
t snapshot-text       node scripts/snapshot.js --url "$U/" --mode text --out "$OUT/snap-text.txt"
t shot-base           node scripts/screenshot.js --url "$U/" --name page --out-dir "$OUT/shots"
t shot-variant        node scripts/screenshot.js --url "$U/variant" --name page-variant --out-dir "$OUT/shots"
t shot-full           node scripts/screenshot.js --url "$U/" --full-page --name page --out-dir "$OUT/shots"
t shot-selector       node scripts/screenshot.js --url "$U/" --selector "#form" --name page --out-dir "$OUT/shots"
t shot-missing-sel    node scripts/screenshot.js --url "$U/" --selector "#nope" --name page --timeout 2000 --out-dir "$OUT/shots"
t diff-init           node scripts/diff.js --baseline "$OUT/baseline/page.png" --current "$OUT/shots/page__1280x800.png" --init
t diff-same           node scripts/diff.js --baseline "$OUT/baseline/page.png" --current "$OUT/shots/page__1280x800.png"
t diff-changed        node scripts/diff.js --baseline "$OUT/baseline/page.png" --current "$OUT/shots/page-variant__1280x800.png" --out "$OUT/diff.png"
t diff-failondiff     node scripts/diff.js --baseline "$OUT/baseline/page.png" --current "$OUT/shots/page-variant__1280x800.png" --out "$OUT/diff2.png" --fail-on-diff
t diff-sizemismatch   node scripts/diff.js --baseline "$OUT/baseline/page.png" --current "$OUT/shots/page__375x812.png"
t interact-form       node scripts/interact.js --new-tab --url "$U/" --out-dir "$OUT/shots" --steps '[{"action":"type","selector":"#name","text":"Ada"},{"action":"select","selector":"#plan","value":"pro"},{"action":"click","selector":"#submit"},{"action":"wait_for","text":"Hello Ada"},{"action":"assert_text","selector":"#result","contains":"(pro)"},{"action":"get_text","selector":"#result"},{"action":"screenshot","name":"after-submit"}]'
t interact-continue   node scripts/interact.js --steps '[{"action":"assert_url","contains":"127.0.0.1:8765"},{"action":"get_text","selector":"#result"}]'
t interact-badselector node scripts/interact.js --timeout 1500 --steps '[{"action":"click","selector":"#does-not-exist"}]'
t interact-assertfail node scripts/interact.js --steps '[{"action":"assert_text","contains":"this text is not here"}]'
t interact-badaction  node scripts/interact.js --steps '[{"action":"explode"}]'
t state-cookies       node scripts/state.js cookies-get --url "$U/" --out "$OUT/cookies.json"
t state-cookies-shown node scripts/state.js cookies-get --url "$U/" --show-values
t state-storage       node scripts/state.js storage-get --url "$U/"
t state-storage-set   node scripts/state.js storage-set --url "$U/" --key k1 --value v1
t state-cookies-clear node scripts/state.js cookies-clear --domain 127.0.0.1
t state-cookies-after node scripts/state.js cookies-get --domain 127.0.0.1
t state-cookies-set   node scripts/state.js cookies-set --file "$OUT/cookies.json"
t state-cookies-restored node scripts/state.js cookies-get --domain 127.0.0.1
t unknown-option      node scripts/screenshot.js --url "$U/" --bogus 1
t missing-required    node scripts/screenshot.js
echo done > "$OUT/DONE"
