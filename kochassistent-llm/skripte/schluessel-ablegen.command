#!/bin/bash
# Auf dem Mac Studio als edal doppelklicken, nachdem der API-Schlüssel der Unsloth-App in der Zwischenablage liegt.
# Legt ihn für den SSH-Benutzer admin lesbar ab (Gruppe staff, nicht für alle) und leert die Zwischenablage.
# studio.sh api-schluessel holt ihn danach aufs MacBook und löscht die Datei auf dem Studio.
ziel=/Users/Shared/kochassistent-llm/.studio-api-key
k=$(pbpaste | tr -d '[:space:]')
if [ ${#k} -lt 20 ] || [ "${k:0:1}" = "/" ]; then
  echo "In der Zwischenablage steht kein API-Schlüssel (${#k} Zeichen). Schlüssel in der Unsloth-App kopieren und nochmals doppelklicken."
else
  umask 027
  printf '%s\n' "$k" > "$ziel" && chgrp staff "$ziel" && chmod 640 "$ziel"
  printf '' | pbcopy
  echo "Schlüssel abgelegt (${#k} Zeichen), Zwischenablage geleert. Das Fenster kann zu."
fi
read -n 1 -s -r -p "Taste drücken zum Schliessen"
