#!/bin/bash
# XLRTE Mastery installieren (macOS). Kopiert Mastery mit eigener Python-Laufzeit in einen Ordner deiner Wahl und startet die Einrichtung.
# Es wird nichts systemweit installiert, nichts gesendet. Deinstallieren: den Ordner löschen.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ask() { osascript -e "text returned of (display dialog \"$1\" default answer \"$2\" buttons {\"OK\"} default button 1 with title \"XLRTE Mastery\")"; }
TARGET="${MASTERY_TARGET:-}"
[ -z "$TARGET" ] && TARGET="$(ask 'In welchen Ordner soll XLRTE Mastery? Dort liegt später dein Lernstand. · Where should XLRTE Mastery live?' "$HOME/Documents/XLRTE Mastery")"
if [ -e "$TARGET/config/settings.json" ]; then
  echo "XLRTE Mastery ist dort schon eingerichtet: aktualisiere Programmdateien, dein Lernstand bleibt unverändert."
  rsync -a --exclude 'config/' --exclude '_xlrte/config.json' --exclude '_xlrte/data/' --exclude '_xlrte/state/' --exclude '_xlrte/journal/' --exclude '_xlrte/inbox/' --exclude '_xlrte/bridge/' --exclude '_xlrte/lab/' --exclude '_xlrte/_backup/' "$HERE/payload/" "$TARGET/"
else
  mkdir -p "$TARGET"
  cp -R "$HERE/payload/." "$TARGET/"
fi
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null || true
chmod +x "$TARGET/mastery" "$TARGET/runtime/bin/"* 2>/dev/null || true
echo "XLRTE Mastery liegt in: $TARGET"
echo "Die Einrichtung öffnet sich im Browser. Dieses Fenster offen lassen, bis sie fertig ist."
cd "$TARGET" && ./mastery
open "$TARGET" 2>/dev/null || true
