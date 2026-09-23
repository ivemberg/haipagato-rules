#!/bin/sh
# Rigenera Shared.xcframework da Gradle. Va lanciato prima di `tuist generate`:
# l'xcframework non e' versionato, e senza il percorso la generazione fallisce.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# In macchina non c'e' java nel PATH: cerco un JDK noto senza toccare l'ambiente globale.
if [ -z "$JAVA_HOME" ]; then
  for candidate in \
    "$HOME/.sdkman/candidates/java/current" \
    "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  do
    if [ -x "$candidate/bin/java" ]; then JAVA_HOME="$candidate"; break; fi
  done
fi
[ -n "$JAVA_HOME" ] || { echo "JAVA_HOME non trovato: serve un JDK 17+" >&2; exit 1; }
export JAVA_HOME

CONFIG="${1:-debug}"
echo "Genero Shared.xcframework ($CONFIG) con JAVA_HOME=$JAVA_HOME"
./gradlew :shared:assembleSharedXCFramework
echo "Fatto: shared/build/XCFrameworks/$CONFIG/Shared.xcframework"
