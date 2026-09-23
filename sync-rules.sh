#!/bin/bash
# Copia nel bundle dell'app un TAG del repo pubblico haipagato-rules.
#
# Un tag e non main: la versione spedita deve essere riproducibile, e main cambia
# sotto i piedi. Se domani un utente segnala un falso positivo, si deve poter dire
# esattamente quali regole aveva l'app che ha spedito quel binario.
#
# Uso:  tools/sync-rules.sh <tag>        es. tools/sync-rules.sh v2026.09.23
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE="${HAIPAGATO_RULES_REMOTE:-https://github.com/ivemberg/haipagato-rules.git}"
DEST="rules"
SUPPORTED_SCHEMA=(1)

fail() { printf '\033[31mFALLITO: %s\033[0m\n' "$*"; exit 1; }
ok() { printf '\033[32m%s\033[0m\n' "$*"; }

TAG="${1:-}"
[ -n "$TAG" ] || fail "manca il tag. Uso: tools/sync-rules.sh <tag>"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Scarico $REMOTE al tag $TAG"
git clone --quiet --depth 1 --branch "$TAG" "$REMOTE" "$TMP/rules" 2>/dev/null \
  || fail "tag '$TAG' non trovato su $REMOTE"

SRC="$TMP/rules"
[ -f "$SRC/rules.json" ] || fail "il repo pubblico non contiene rules.json alla radice"

# Il controllo dello schema va fatto QUI e non a runtime: altrimenti ci si accorge
# del disallineamento solo sul telefono, a binario gia' spedito.
schema=$(python3 -c "
import json,sys
try: print(json.load(open('$SRC/rules.json')).get('schemaVersion', 1))
except Exception as e: print('ERRORE', e); sys.exit(1)
") || fail "rules.json del repo pubblico non e' JSON valido"

found=0
for s in "${SUPPORTED_SCHEMA[@]}"; do [ "$s" = "$schema" ] && found=1; done
[ "$found" = 1 ] || fail "schemaVersion $schema non supportato (attesi: ${SUPPORTED_SCHEMA[*]})"

for f in "$SRC"/*.json "$SRC"/*.geojson; do
  [ -e "$f" ] || continue
  python3 -m json.tool "$f" > /dev/null || fail "$(basename "$f") non e' JSON valido"
  cp "$f" "$DEST/"
done
[ -f "$SRC/README.md" ] && cp "$SRC/README.md" "$DEST/"
[ -f "$SRC/SOURCES.md" ] && cp "$SRC/SOURCES.md" "$DEST/"

version=$(python3 -c "import json;d=json.load(open('$DEST/rules.json'));print(d['version'], d['updatedAt'])")
ok "Copiate le regole $TAG (schemaVersion $schema, dati $version)"
echo "Ora lancia ./tools/verify.sh: i test girano sul rules.json vero."
