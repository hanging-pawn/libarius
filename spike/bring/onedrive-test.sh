#!/bin/sh
# LIBAR-57 Spike, Seite c: prueft, ob der Bring!-Parser eine Seite hinter einem anonymen
# OneDrive-Freigabelink lesen kann. Aufruf: sh onedrive-test.sh '<Freigabelink>'
# Testet den Link selbst, die Download-Variante und die Direkt-URL ueber die Shares-API.
# Sendet nur den Freigabelink an api.getbring.com (wie integration-check), sonst nichts.
set -u
LINK="${1:?Freigabelink als Argument angeben}"
B64=$(printf '%s' "$LINK" | base64 | tr -d '=\n' | tr '/+' '_-')
case "$LINK" in *\?*) DL="$LINK&download=1" ;; *) DL="$LINK?download=1" ;; esac
for U in "$LINK" "$DL" "https://api.onedrive.com/v1.0/shares/u!$B64/root/content"; do
  E=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$U")
  echo "=== $U"
  curl -sIL "$U" | grep -i -E '^HTTP|^content-type' | tail -2
  curl -s -w "\nHTTP %{http_code}\n" "https://api.getbring.com/rest/bringrecipes/parser?url=$E" | cut -c1-400
  echo
done
