#!/usr/bin/env bash
# Trainingsversuch auf dem Mac Studio (SSH-Host «studio», Tailscale) fahren.
# Läuft auf dem MacBook, im Ordner kochassistent-llm/. Unterbefehle:
#   sync      Code, Konfig und Korpus (daten/korpus/<v>) nach $ZIEL auf dem Studio kopieren, für alle Benutzer schreibbar
#   pruefen   Unsloth-CLI ($UNSLOTH) auf dem Studio prüfen (Version, doctor)
#   start     Training im Hintergrund starten (nohup), Log: $ZIEL/modelle/<lauf>.log
#   status    letzte Logzeilen und Speicher des Studios
#   holen     Adapter und Log zurück nach modelle/ auf dem MacBook
#   probe     Prüffragen (konfig/probe-fragen.txt) an Basismodell und Adapter, Ausgabe modelle/<lauf>.probe.md
#   api-start / api-status / api-runs   Training über die API der Studio-App (Schlüssel in $SCHLUESSEL)
# Unsloth gehört zur Unsloth-Studio-App des Benutzers edal; der SSH-Benutzer admin darf sie nicht ausführen.
# start und probe geben dann den Befehl aus, den edal im Terminal des Studios einfügt.
# Variablen: HOST (studio), KORPUS (v01), KONFIG (konfig/versuch-01-raw.yaml), LAUF (versuch-01), EXTRA (CLI-Flags),
#            ZIEL (/Users/Shared/kochassistent-llm), UNSLOTH (CLI der Studio-App von edal)
set -euo pipefail
HOST=${HOST:-studio}
KORPUS=${KORPUS:-v01}
KONFIG=${KONFIG:-konfig/versuch-01-raw.yaml}
LAUF=${LAUF:-versuch-01}
EXTRA=${EXTRA:-}
ZIEL=${ZIEL:-/Users/Shared/kochassistent-llm}
UNSLOTH=${UNSLOTH:-/Users/edal/.unsloth/studio/unsloth_studio/bin/unsloth}
API_KONFIG=${API_KONFIG:-konfig/versuch-01-api.json}
SCHLUESSEL=${SCHLUESSEL:-$HOME/.config/kochassistent/studio-api-key}
cd "$(dirname "$0")/.."

# Befehl auf dem Studio ausführen, wenn der SSH-Benutzer Unsloth starten darf, sonst für edal ausgeben.
studio_oder_zeigen() {
  if ssh "$HOST" "test -x '$UNSLOTH'"; then
    ssh "$HOST" "$1"
  else
    echo "Der SSH-Benutzer darf $UNSLOTH nicht ausführen. Als edal im Terminal des Studios einfügen:"
    echo
    echo "$1"
  fi
}

case "${1:-}" in
  sync)
    ssh "$HOST" "mkdir -p $ZIEL/daten/korpus $ZIEL/modelle"
    rsync -a --delete --exclude .venv --exclude daten --exclude modelle --exclude .env \
      --exclude '__pycache__' --exclude .pytest_cache ./ "$HOST:$ZIEL/"
    rsync -a --stats "daten/korpus/$KORPUS" "$HOST:$ZIEL/daten/korpus/"
    # edal muss lesen und nach modelle/ schreiben können; Skripte und Konfig bleiben nur für admin schreibbar
    ssh "$HOST" "chmod -R go-w,a+rX $ZIEL && chmod -R a+rwX $ZIEL/daten $ZIEL/modelle && chmod 1777 $ZIEL"
    ;;
  pruefen)
    studio_oder_zeigen "'$UNSLOTH' --version && '$UNSLOTH' doctor 2>&1 | tail -12"
    ;;
  start)
    studio_oder_zeigen "cd $ZIEL && mkdir -p modelle && nohup '$UNSLOTH' train -c $KONFIG --output-dir modelle/$LAUF $EXTRA > modelle/$LAUF.log 2>&1 & echo gestartet: \$!"
    ;;
  status)
    ssh "$HOST" "tail -n 15 $ZIEL/modelle/$LAUF.log; echo; pgrep -fl 'unsloth train' || echo 'kein Training aktiv'; memory_pressure | tail -1"
    ;;
  holen)
    mkdir -p modelle
    rsync -a --stats --exclude 'checkpoint-*' "$HOST:$ZIEL/modelle/$LAUF" modelle/
    rsync -a "$HOST:$ZIEL/modelle/$LAUF.log" modelle/
    ;;
  probe)
    BASIS=${BASIS:-$(awk '/^model:/{print $2}' "$KONFIG")}
    studio_oder_zeigen "cd $ZIEL && out=modelle/$LAUF.probe.md && : > \$out && grep -v '^#' konfig/probe-fragen.txt | while IFS= read -r f; do
  [ -z \"\$f\" ] && continue
  printf '## %s\\n\\n### Basis\\n\\n' \"\$f\" >> \$out
  '$UNSLOTH' inference $BASIS \"\$f\" --no-server --no-think --max-new-tokens 400 < /dev/null 2>/dev/null | sed -n '/^Assistant:/,\$p' >> \$out
  printf '\\n### Adapter\\n\\n' >> \$out
  '$UNSLOTH' inference $ZIEL/modelle/$LAUF \"\$f\" --no-server --no-think --max-new-tokens 400 < /dev/null 2>/dev/null | sed -n '/^Assistant:/,\$p' >> \$out
done; echo \$out"
    ;;
  api-schluessel)
    # Schlüssel, den skripte/schluessel-ablegen.command auf dem Studio abgelegt hat, holen und dort löschen.
    mkdir -p "$(dirname "$SCHLUESSEL")" && chmod 700 "$(dirname "$SCHLUESSEL")"
    ( umask 077; ssh "$HOST" "cat $ZIEL/.studio-api-key" > "$SCHLUESSEL.neu" ) &&
      [ "$(tr -d '[:space:]' < "$SCHLUESSEL.neu" | wc -c)" -ge 20 ] &&
      mv "$SCHLUESSEL.neu" "$SCHLUESSEL" && ssh "$HOST" "rm -f $ZIEL/.studio-api-key" &&
      echo "Schlüssel nach $SCHLUESSEL geholt, auf dem Studio gelöscht." ||
      { rm -f "$SCHLUESSEL.neu"; echo "Kein Schlüssel auf dem Studio. Zuerst schluessel-ablegen.command doppelklicken."; exit 1; }
    ;;
  api-start|api-status|api-runs)
    # Studio-API (Port 8888 auf dem Studio, nur lokal). Der Schlüssel (Zugriff «full») liegt in $SCHLUESSEL
    # und geht über stdin an curl, damit er weder im Chat noch in einer Prozessliste steht.
    [ -s "$SCHLUESSEL" ] || { echo "Kein Schlüssel in $SCHLUESSEL"; exit 1; }
    api() {  # api METHODE PFAD [JSON-Datei auf dem Studio]
      local daten=""; [ -n "${3:-}" ] && daten="-H 'Content-Type: application/json' --data-binary @$3"
      printf 'Authorization: Bearer %s\n' "$(tr -d '[:space:]' < "$SCHLUESSEL")" |
        ssh "$HOST" "curl -sS -m 60 -X $1 -H @- $daten -w '\nHTTP %{http_code}\n' http://127.0.0.1:8888$2"
    }
    case "$1" in
      api-start)  api POST /api/train/start "$ZIEL/$API_KONFIG" ;;
      api-status) api GET /api/train/status; echo; api GET /api/train/metrics | tail -c 1500 ;;
      api-runs)   api GET /api/train/runs | head -c 3000 ;;
    esac
    ;;
  *)
    sed -n '2,15p' "$0"; exit 1
    ;;
esac
