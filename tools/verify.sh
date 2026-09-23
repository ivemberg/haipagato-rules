#!/bin/bash
# Unico criterio di "verde" del progetto. Un task e' finito solo se questo script esce con 0.
#
# Controlla quattro cose, e ognuna ha un modo noto di dare un verde falso:
#   1. test Kotlin      -> "BUILD SUCCESSFUL" con zero test eseguiti
#   2. XCFramework      -> assente o vecchio
#   3. test iOS         -> xcodebuild esce 0 e stampa "Executed 0 tests", perche' il
#                          reporter XCTest non conta i test Swift Testing
#   4. superficie       -> un test che usa l'API non prova che l'API sia pulita, e senza
#                          rigenerare il progetto un file nuovo non viene nemmeno compilato
#
# Per questo non ci si fida dei codici di uscita: si contano i test e si confrontano
# con tools/test-baseline.json, che e' versionato. Se il numero cala, e' un fallimento:
# un test cancellato o silenziato non deve poter passare per "verde".
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASELINE="tools/test-baseline.json"
SIMULATOR_NAME="${VERIFY_SIMULATOR:-iPhone 17 Pro}"
RESULT_BUNDLE="$(mktemp -d)/verify.xcresult"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }

fail() { red "FALLITO: $*"; exit 1; }

# Il JDK non e' nel PATH su questa macchina: lo cerco fra quelli noti.
if [ -z "${JAVA_HOME:-}" ]; then
  for candidate in \
    "$HOME/.sdkman/candidates/java/current" \
    "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  do
    if [ -x "$candidate/bin/java" ]; then JAVA_HOME="$candidate"; break; fi
  done
fi
[ -n "${JAVA_HOME:-}" ] || fail "JAVA_HOME non trovato: serve un JDK 17+"
export JAVA_HOME
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"

baseline_value() {
  python3 - "$1" <<'PY'
import json, sys
try:
    print(json.load(open("tools/test-baseline.json")).get(sys.argv[1], 0))
except Exception:
    print(0)
PY
}

echo "== 1/4  test Kotlin =="
# Si cancellano i risultati vecchi: senza, un target che smette di girare lascerebbe
# in giro il suo XML dell'esecuzione precedente e il conteggio sembrerebbe a posto.
rm -rf shared/build/test-results
./gradlew --no-daemon :shared:allTests > /tmp/verify-kotlin.log 2>&1
gradle_status=$?
[ "$gradle_status" -eq 0 ] || { tail -30 /tmp/verify-kotlin.log; fail "gradle allTests uscito con $gradle_status"; }

# Il confronto e' PER TARGET, non sul totale: se i test del simulatore iOS smettessero
# di girare e quelli Android ne guadagnassero altrettanti, un controllo sul solo totale
# non se ne accorgerebbe.
kotlin_report=$(python3 - <<'PY'
import glob, json, os, sys, xml.etree.ElementTree as ET
from collections import defaultdict

tests = defaultdict(int)
failed = defaultdict(int)
for f in glob.glob("shared/build/test-results/*/TEST-*.xml"):
    target = os.path.basename(os.path.dirname(f))
    r = ET.parse(f).getroot()
    tests[target] += int(r.get("tests", 0))
    failed[target] += int(r.get("failures", 0)) + int(r.get("errors", 0))

try:
    baseline = json.load(open("tools/test-baseline.json")).get("kotlin", {})
except Exception:
    baseline = {}
if not isinstance(baseline, dict):
    print("ERRORE baseline kotlin non e' un oggetto per target: aggiorna tools/test-baseline.json")
    sys.exit(0)

problems = []
for target, expected in sorted(baseline.items()):
    got = tests.get(target)
    if got is None:
        problems.append(f"il target {target} non ha eseguito alcun test (atteso {expected})")
    elif got < expected:
        problems.append(f"{target}: test scesi da {expected} a {got}")
for target in sorted(tests):
    if target not in baseline:
        problems.append(f"NUOVO target {target} con {tests[target]} test: aggiungilo alla baseline")
    if failed[target]:
        problems.append(f"{target}: {failed[target]} test falliti")
if not tests:
    problems.append("zero test Kotlin eseguiti: un BUILD SUCCESSFUL senza test non e' verde")

for p in problems:
    print("ERRORE " + p)
for target in sorted(tests):
    print(f"OK {target} {tests[target]} {baseline.get(target, 0)}")
PY
)
if grep -q '^ERRORE ' <<<"$kotlin_report"; then
  grep '^ERRORE ' <<<"$kotlin_report" | sed 's/^ERRORE /  - /'
  fail "baseline dei test Kotlin non rispettata"
fi
while read -r _ target got expected; do
  [ -n "${target:-}" ] && green "   $target: $got test (baseline $expected)"
done <<<"$(grep '^OK ' <<<"$kotlin_report")"
kotlin_total=$(awk '/^OK /{s+=$3} END{print s+0}' <<<"$kotlin_report")

echo "== 2/4  Shared.xcframework =="
./gradlew --no-daemon :shared:assembleSharedXCFramework > /tmp/verify-xcf.log 2>&1 \
  || { tail -30 /tmp/verify-xcf.log; fail "assembleSharedXCFramework"; }
for cfg in debug release; do
  [ -d "shared/build/XCFrameworks/$cfg/Shared.xcframework" ] \
    || fail "manca Shared.xcframework ($cfg)"
done
green "   xcframework debug e release presenti"

echo "== 3/4  test iOS su simulatore arm64 =="
# Serve un simulatore arm64 concreto: con una destinazione generica il linker scarta
# Shared senza errori, perche' l'xcframework ha solo slice arm64, e il build passa
# senza aver linkato nulla.
udid=$(xcrun simctl list devices available -j 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)['devices']
want = sys.argv[1]
for runtime, devices in data.items():
    if 'iOS' not in runtime: continue
    for d in devices:
        if d.get('name') == want and d.get('isAvailable'): print(d['udid']); sys.exit()
for runtime, devices in data.items():
    if 'iOS' not in runtime: continue
    for d in devices:
        if d.get('isAvailable') and 'iPhone' in d.get('name',''): print(d['udid']); sys.exit()
" "$SIMULATOR_NAME")
[ -n "$udid" ] || fail "nessun simulatore iPhone disponibile"

./tools/build_xcframework.sh > /dev/null 2>&1 || fail "rigenerazione xcframework"
(cd ios && tuist generate --no-open > /tmp/verify-tuist.log 2>&1) \
  || { tail -20 /tmp/verify-tuist.log; fail "tuist generate"; }

(cd ios && xcodebuild -workspace HaiPagato.xcworkspace -scheme HaiPagatoCore \
  -destination "id=$udid" -resultBundlePath "$RESULT_BUNDLE" test) \
  > /tmp/verify-ios.log 2>&1
xcode_status=$?

# Non ci si fida ne' del codice di uscita ne' dell'output: si legge il result bundle,
# l'unica fonte che conta davvero i test Swift Testing.
ios_counts=$(xcrun xcresulttool get test-results summary --path "$RESULT_BUNDLE" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('0 0'); sys.exit()
print(d.get('passedTests', 0), d.get('failedTests', 0))
")
ios_passed=${ios_counts% *}
ios_failed=${ios_counts#* }
ios_base=$(baseline_value ios)

[ "$xcode_status" -eq 0 ] || { tail -30 /tmp/verify-ios.log; fail "xcodebuild test uscito con $xcode_status"; }
[ "$ios_passed" -gt 0 ] || \
  fail "zero test iOS passati: attenzione, il reporter XCTest stampa 'Executed 0 tests' anche quando i test Swift Testing girano"
[ "$ios_failed" -eq 0 ] || fail "$ios_failed test iOS falliti"
[ "$ios_passed" -ge "$ios_base" ] || \
  fail "test iOS scesi da $ios_base a $ios_passed: test cancellati o silenziati"
green "   $ios_passed test iOS, 0 falliti (baseline $ios_base)"

echo "== 4/4  nessun tipo Kotlin nella superficie pubblica =="
# Un test che usa l'API non basta: dimostra che quel percorso e' pulito, non che l'API
# lo sia. Qui si guarda cosa il compilatore dichiara pubblico.
./tools/check_no_kotlin_leak.sh "$udid" || fail "tipi Kotlin nella superficie pubblica di HaiPagatoCore"

echo
green "VERDE. Kotlin $kotlin_total su $(grep -c '^OK ' <<<"$kotlin_report") target, iOS $ios_passed."

# Se qualcosa e' cresciuto lo si dice, con il JSON gia' pronto da incollare.
grown=$(python3 - "$ios_passed" <<'PY'
import json, sys, glob, os, xml.etree.ElementTree as ET
from collections import defaultdict
tests = defaultdict(int)
for f in glob.glob("shared/build/test-results/*/TEST-*.xml"):
    tests[os.path.basename(os.path.dirname(f))] += int(ET.parse(f).getroot().get("tests", 0))
b = json.load(open("tools/test-baseline.json"))
ios = int(sys.argv[1])
if any(tests[t] > b["kotlin"].get(t, 0) for t in tests) or ios > b.get("ios", 0):
    b["kotlin"] = dict(sorted(tests.items()))
    b["ios"] = ios
    print(json.dumps(b, ensure_ascii=False, indent=2))
PY
)
if [ -n "$grown" ]; then
  echo
  echo "Test cresciuti: aggiorna $BASELINE con"
  echo "$grown"
fi
