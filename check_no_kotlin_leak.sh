#!/bin/bash
# Verifica che nessun tipo Kotlin compaia nella superficie pubblica di HaiPagatoCore.
#
# Un test che usa l'API non basta: dimostra che quel percorso e' pulito, non che l'API
# lo sia. Qui si guarda cosa il compilatore dichiara davvero come pubblico.
#
# Due controlli indipendenti:
#   1. l'header ObjC generato da Kotlin non deve contenere tipi del dominio ne' kotlinx;
#   2. la superficie pubblica Swift di HaiPagatoCore non deve nominare tipi Kotlin.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() { printf '\033[31mLEAK: %s\033[0m\n' "$*"; exit 1; }
ok() { printf '\033[32m%s\033[0m\n' "$*"; }

# --------------------------------------------------------------- 1. header Kotlin
HEADER=$(find shared/build/XCFrameworks/debug -name "Shared.h" 2>/dev/null | head -1)
[ -n "$HEADER" ] || fail "Shared.h non trovato: lancia prima tools/build_xcframework.sh"

# Tipi del dominio che devono restare @HiddenFromObjC, piu' tutto kotlinx.
DOMAIN_TYPES="Kotlinx_datetime|Kotlinx_serialization|SharedRules|SharedZone|SharedGeometry|SharedDeadline|SharedSchedule|SharedHolidays|SharedOperator|SharedRing|SharedChain|SharedGeoPoint|SharedTrackPoint|SharedProjection|SharedLocated|SharedPaymentDue|SharedTransitDetection|SharedZoneActivity|SharedPolygonParams|SharedPolylineParams|SharedGeoJsonResult|SharedGate"
leaked=$(grep -oE "$DOMAIN_TYPES" "$HEADER" | sort -u || true)
if [ -n "$leaked" ]; then
  echo "$leaked" | sed 's/^/  - /'
  fail "l'header ObjC espone tipi del dominio: manca @HiddenFromObjC"
fi
ok "   header Kotlin: nessun tipo di dominio ne' kotlinx"

# --------------------------------------------------------------- 2. superficie Swift
SIM_UDID="${1:-}"
if [ -z "$SIM_UDID" ]; then
  SIM_UDID=$(xcrun simctl list devices available -j | python3 -c "
import json,sys
for rt, devs in json.load(sys.stdin)['devices'].items():
    if 'iOS' not in rt: continue
    for d in devs:
        if d.get('isAvailable') and 'iPhone' in d.get('name',''): print(d['udid']); sys.exit()
")
fi
[ -n "$SIM_UDID" ] || fail "nessun simulatore iPhone disponibile"

# Rigenerare il progetto non e' facoltativo: Tuist raccoglie i sorgenti alla generazione,
# e senza questo passo un file nuovo non verrebbe nemmeno compilato. La prima versione dello
# script passava proprio per questo, con la fuga gia' sul disco.
(cd ios && tuist generate --no-open) > /tmp/leak-generate.log 2>&1 \
  || { tail -20 /tmp/leak-generate.log; fail "tuist generate"; }

BUILD_DIR=$(mktemp -d)
(cd ios && xcodebuild -workspace HaiPagato.xcworkspace -scheme HaiPagatoCore \
  -destination "id=$SIM_UDID" -derivedDataPath "$BUILD_DIR" \
  BUILD_LIBRARY_FOR_DISTRIBUTION=YES -quiet build) > /tmp/leak-build.log 2>&1 \
  || { tail -20 /tmp/leak-build.log; fail "build con library evolution fallito"; }

# Con library evolution il compilatore emette la .swiftinterface: e' il contratto
# pubblico testuale del modulo, l'unica cosa che conta davvero.
IFACE=$(find "$BUILD_DIR" -name "*.swiftinterface" -path "*HaiPagatoCore*" | head -1)
[ -n "$IFACE" ] || fail ".swiftinterface non generata: impossibile verificare la superficie"

SWIFT_LEAKS="Shared\.|import Shared|Kotlin[A-Z]|Bridge[A-Z]|NSNumber"
found=$(grep -nE "$SWIFT_LEAKS" "$IFACE" | grep -v "^\s*//" || true)
if [ -n "$found" ]; then
  echo "$found" | head -12 | sed 's/^/  - /'
  fail "la superficie pubblica Swift nomina tipi Kotlin"
fi
ok "   superficie Swift: nessun tipo Kotlin in $(basename "$IFACE")"
echo "   ($(grep -c 'public' "$IFACE") dichiarazioni pubbliche verificate)"
