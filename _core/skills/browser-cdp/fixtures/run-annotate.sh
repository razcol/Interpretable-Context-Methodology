#!/usr/bin/env bash
# Checks screenshot annotations (scripts/annotate.js) through screenshot.js, interact.js and diff.js.
# Prereq: node scripts/browser.js start. The fixture server is started here when nothing answers on port 8765.
# Usage: bash fixtures/run-annotate.sh [OUT_DIR]. Prints one line per check and exits 1 when any check fails.
set -u
cd "$(dirname "$0")/.."
OUT="${1:-$(mktemp -d)}"
mkdir -p "$OUT/shots"
PORT=8765
U="http://127.0.0.1:$PORT"
fail=0
SERVER_PID=""
cleanup() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT

if ! curl -fs -o /dev/null "$U/"; then
  node fixtures/serve.js "$PORT" > "$OUT/serve.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 25); do curl -fs -o /dev/null "$U/" && break; sleep 0.2; done
fi

pass() { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
# jget FILE EXPR: evaluates EXPR with `j` bound to the parsed JSON file and prints the result.
jget() { node -e 'const j=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));const v=eval(process.argv[2]);process.stdout.write(String(v))' "$1" "$2" 2>/dev/null; }
# expect NAME WANT_EXIT cmd...: runs cmd, stores stdout in OUT/NAME.json, checks the exit code.
expect() {
  local name="$1" want="$2"; shift 2
  "$@" > "$OUT/$name.json" 2>&1
  local got=$?
  if [ "$got" = "$want" ]; then pass "$name (exit $got)"; else bad "$name (exit $got, want $want)"; fi
}
# check NAME FILE EXPR: passes when EXPR (with j = parsed JSON) is true.
check() { if [ "$(jget "$2" "$3")" = "true" ]; then pass "$1"; else bad "$1 ($3)"; fi; }

ANN='[{"type":"box","selector":"#form","badge":1,"label":"sign-in form"},{"type":"arrow","to":"#submit","label":"submit here"},{"type":"badge","selector":"h1","text":"H","position":"top-right"},{"type":"box","rect":{"x":420,"y":40,"width":120,"height":60},"color":"#2563eb"}]'

# (1) annotated shot differs from the clean shot
expect shot-clean      0 node scripts/screenshot.js --url "$U/" --name clean --out-dir "$OUT/shots"
expect shot-annotated  0 node scripts/screenshot.js --url "$U/" --name annotated --out-dir "$OUT/shots" --annotations "$ANN"
check  annotations-all-applied "$OUT/shot-annotated.json" 'j.screenshots[0].annotations.length===4 && j.screenshots[0].annotations.every((a,i)=>a.applied===true&&a.index===i&&a.rect)'
check  clean-has-no-annotations-key "$OUT/shot-clean.json" '!("annotations" in j.screenshots[0])'
expect diff-annotated  0 node scripts/diff.js --baseline "$OUT/shots/clean__1280x800.png" --current "$OUT/shots/annotated__1280x800.png" --out "$OUT/diff-annotated.png"
check  annotated-differs "$OUT/diff-annotated.json" 'j.match===false && j.diffPixels>0'

# fullPage and element captures also annotate (and stay the same size as their clean twins)
expect full-clean      0 node scripts/screenshot.js --url "$U/" --full-page --name fc --out-dir "$OUT/shots"
expect full-annotated  0 node scripts/screenshot.js --url "$U/" --full-page --name fa --out-dir "$OUT/shots" --annotations '[{"type":"box","selector":"#result","badge":"R"}]'
expect diff-full       0 node scripts/diff.js --baseline "$OUT/shots/fc__1280x800__full.png" --current "$OUT/shots/fa__1280x800__full.png" --out "$OUT/diff-full.png"
check  full-differs "$OUT/diff-full.json" 'j.match===false && j.diffPixels>0'
expect sel-annotated   0 node scripts/screenshot.js --url "$U/" --selector "#form" --name sel --out-dir "$OUT/shots" --annotations '[{"type":"box","selector":"#submit"},{"type":"badge","x":2,"y":2,"text":7}]'
check  sel-applied "$OUT/sel-annotated.json" 'j.screenshots[0].annotations.every((a)=>a.applied===true)'

# (2) overlay cleans up in interact.js: a clean shot after an annotated one equals the clean shot before it
STEPS='[{"action":"screenshot","name":"ia-before"},{"action":"screenshot","name":"ia-marked","annotations":[{"type":"box","selector":"#form","badge":1},{"type":"arrow","to":"#submit"}]},{"action":"eval","expression":"document.getElementById(\"__bcdp-overlay\") === null"},{"action":"screenshot","name":"ia-after"}]'
expect interact-annotated 0 node scripts/interact.js --new-tab --url "$U/" --out-dir "$OUT/shots" --steps "$STEPS"
check  interact-annotations-result "$OUT/interact-annotated.json" 'j.results[2].annotations.length===2 && j.results[2].annotations.every((a)=>a.applied) && !("annotations" in j.results[1])'
check  interact-overlay-removed "$OUT/interact-annotated.json" 'j.results[3].value===true'
expect diff-interact-clean 0 node scripts/diff.js --baseline "$OUT/shots/ia-before.png" --current "$OUT/shots/ia-after.png" --out "$OUT/diff-interact.png"
check  interact-cleanup-ratio-0 "$OUT/diff-interact-clean.json" 'j.diffRatio===0 && j.match===true'
expect diff-interact-marked 0 node scripts/diff.js --baseline "$OUT/shots/ia-before.png" --current "$OUT/shots/ia-marked.png" --out "$OUT/diff-interact-marked.png"
check  interact-marked-differs "$OUT/diff-interact-marked.json" 'j.diffRatio>0'

# (3) a missing selector reports applied:false and the run still exits 0
expect missing-selector 0 node scripts/screenshot.js --url "$U/" --name missing --out-dir "$OUT/shots" --annotations '[{"type":"box","selector":"#nope"},{"type":"box","selector":"#form"}]'
check  missing-applied-false "$OUT/missing-selector.json" 'j.ok===true && j.screenshots[0].annotations[0].applied===false && /not found/.test(j.screenshots[0].annotations[0].reason) && j.screenshots[0].annotations[0].selector==="#nope" && j.screenshots[0].annotations[1].applied===true'
expect interact-missing 0 node scripts/interact.js --steps '[{"action":"screenshot","name":"ia-missing","annotations":[{"type":"badge","selector":"#nope","text":1}]}]' --out-dir "$OUT/shots"
check  interact-missing-applied-false "$OUT/interact-missing.json" 'j.results[0].annotations[0].applied===false'

# strict validation: USAGE, exit 1
expect bad-json        1 node scripts/screenshot.js --url "$U/" --annotations '{not json'
expect bad-type        1 node scripts/screenshot.js --url "$U/" --annotations '[{"type":"circle","selector":"#form"}]'
expect not-array       1 node scripts/screenshot.js --url "$U/" --annotations '{"type":"box","selector":"#form"}'
expect unknown-key     1 node scripts/screenshot.js --url "$U/" --annotations '[{"type":"box","selector":"#form","bogus":1}]'
expect arrow-no-to     1 node scripts/screenshot.js --url "$U/" --annotations '[{"type":"arrow","from":{"x":1,"y":1}}]'
echo '[{"type":"box","selector":"#form"}]' > "$OUT/ann.json"
expect both-flags      1 node scripts/screenshot.js --url "$U/" --annotations '[]' --annotations-file "$OUT/ann.json"
expect file-ok         0 node scripts/screenshot.js --url "$U/" --name fromfile --out-dir "$OUT/shots" --annotations-file "$OUT/ann.json"
expect file-missing    1 node scripts/screenshot.js --url "$U/" --annotations-file "$OUT/does-not-exist.json"
expect interact-bad-type 1 node scripts/interact.js --steps '[{"action":"screenshot","name":"x","annotations":[{"type":"star"}]}]'
check  usage-code "$OUT/bad-type.json" 'j.ok===false && j.error.code==="USAGE"'

exit $fail
