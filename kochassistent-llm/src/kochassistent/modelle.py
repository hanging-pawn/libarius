"""Modellbestand auf dem Mac Studio: was liegt wo, was ist doppelt, und kein Laden ohne vorhandene Kopie.

Zwei Ablagen auf dem Studio:
  App-Cache   /Users/Shared/huggingface/hub[/hub]/models--<org>--<name>  (Unsloth-App; lädt nur hierhin nach)
  LM Studio   /Users/Shared/lmstudio-models/<org>/<name>                (LM-Studio-Dienst als edal)

Regel: Vor jedem Training und jedem Laden prüft `sicherstellen`, ob das Modell vollständig im App-Cache liegt —
anhand der Dateien (alle Teile aus dem Index), nicht nur der App-Liste: Ein Ordner mit nur config.json gilt dort
als vorhanden.
Fehlt es, bricht der Aufruf ab und nennt vorhandene Kopien unter ähnlichem Namen; ein Download braucht
ausdrücklich `download_erlaubt=True` (CLI: --download-erlauben).

  liste                       alle Modelle mit Ort, Grösse, «doppelt»
  pruefen <repo_id>           vorhanden? sonst Kopien unter ähnlichem Namen
  laden <repo_id> [--parallel 4] [--max-seq 8192]   Modell zum Antworten laden (nur wenn vorhanden)
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
import time

from kochassistent.studio_api import SSH, ApiFehler, api

APP_CACHES = ("/Users/Shared/huggingface/hub/hub", "/Users/Shared/huggingface/hub")  # die App nutzt beide Wurzeln
LMSTUDIO = "/Users/Shared/lmstudio-models"

# Läuft auf dem Studio (python3 -): je Modellordner Grösse der Gewichte (Symlinks aufgelöst, jede Datei einmal),
# Format, vollständig (alle Teile aus dem Index da, keine .incomplete) und die Inodes der Gewichte.
_ERFASSEN = r"""
import glob, json, os
WURZELN = %r
LM = %r
GEW = (".safetensors", ".gguf", ".bin", ".npz")
def erfassen(ordner):
    dateien = [os.path.join(w, f) for w, _, fs in os.walk(ordner, followlinks=True) for f in fs]
    gewichte = [d for d in dateien if d.endswith(GEW) and os.path.exists(d)]
    inodes = {os.stat(d).st_ino: os.stat(d).st_size for d in gewichte}
    teile = {os.path.basename(d): [os.stat(d).st_size, os.stat(d).st_ino] for d in gewichte}
    ok = bool(gewichte) and not any(d.endswith(".incomplete") for d in dateien)
    for idx in [d for d in dateien if d.endswith(".safetensors.index.json")]:
        try:
            noetig = set(json.load(open(idx))["weight_map"].values())
            ok = ok and all(os.path.exists(os.path.join(os.path.dirname(idx), t)) for t in noetig)
        except Exception:
            ok = False
    fmt = "gguf" if any(d.endswith(".gguf") for d in gewichte) else "safetensors" if gewichte else "-"
    return {"gb": sum(inodes.values()) / 1e9, "vollstaendig": ok, "format": fmt, "inodes": sorted(inodes),
            "teile": teile}
aus = []
for w in WURZELN:
    for d in sorted(glob.glob(w + "/models--*")):
        org, _, name = os.path.basename(d)[8:].partition("--")
        aus.append({"id": org + "/" + name, "ort": "App-Cache", "pfad": d, **erfassen(os.path.join(d, "snapshots"))})
for d in sorted(glob.glob(LM + "/*/*")):
    if os.path.isdir(d):
        aus.append({"id": "/".join(d.split("/")[-2:]), "ort": "LM Studio", "pfad": d, **erfassen(d)})
print(json.dumps(aus))
"""


class ModellFehlt(RuntimeError):
    pass


def schluessel(name: str) -> str:
    """Vergleichsname für «ähnlich»: ohne Anbieter, Format- und Quantisierungs-Endungen."""
    n = name.rsplit("/", 1)[-1].lower()
    return re.sub(r"[-_.]?(mlx|gguf|\d+bit|bf16|fp8|fp16|q\d_k_m|q\d_0|instruct|it)\b", "", n)


def _ordner() -> list[dict]:
    r = subprocess.run(SSH + ["python3 -"], input=_ERFASSEN % (APP_CACHES, LMSTUDIO), capture_output=True,
                       text=True, timeout=600, check=True)
    return json.loads(r.stdout)


def app_cache() -> set[str]:
    """repo_ids, die die App selbst als lokal führt (Ergänzung zur Dateiprüfung)."""
    return {m["id"] for m in api("GET", "/api/models/local")["models"]
            if m.get("source") == "hf_cache" and not m["id"].startswith("ref:")}


def bestand() -> list[dict]:
    """Alle Modellordner. «doppelt_gb»: Gewichtsdateien, die gleich heissen und gleich gross sind wie in einem
    anderen Ordner, aber eigene Daten haben (echte zweite Kopie). «verlinkt»: zeigt auf dieselben Dateien."""
    eintraege = [e for e in _ordner() if e["gb"] > 0.01 or e["ort"] == "LM Studio"]
    for e in eintraege:
        doppelt, verlinkt = 0, False
        for x in eintraege:
            if x is e:
                continue
            for name, (groesse, inode) in e["teile"].items():
                y = x["teile"].get(name)
                if y and y[0] == groesse and groesse > 1e8:
                    doppelt += groesse * (y[1] != inode)
                    verlinkt |= y[1] == inode
        e["doppelt_gb"], e["verlinkt"] = doppelt / 1e9, verlinkt
    return sorted(eintraege, key=lambda e: (e["id"].rsplit("/", 1)[-1].lower(), e["ort"]))


def vorhanden(repo_id: str, ordner: list[dict] | None = None) -> bool:
    """Vollständig im App-Cache: Dateien geprüft und von der App geführt."""
    ordner = _ordner() if ordner is None else ordner
    return any(e["ort"] == "App-Cache" and e["id"] == repo_id and e["vollstaendig"] for e in ordner) \
        and repo_id in app_cache()


def sicherstellen(repo_id: str, download_erlaubt: bool = False) -> None:
    """Abbruch, wenn repo_id nicht vollständig im App-Cache liegt und kein Download erlaubt ist."""
    ordner = _ordner()
    if vorhanden(repo_id, ordner):
        return
    if download_erlaubt:
        print(f"Hinweis: {repo_id} fehlt im App-Cache, Download erlaubt.", file=sys.stderr)
        return
    aehnlich = [e for e in ordner if schluessel(e["id"]) == schluessel(repo_id) and e["gb"] > 0.01]
    zeilen = "\n".join(f"  {e['ort']:9} {e['id']}  {e['gb']:.0f} GB  {'vollständig' if e['vollstaendig'] else 'UNVOLLSTÄNDIG'}"
                       f"  {e['pfad']}" for e in aehnlich) or "  keine"
    raise ModellFehlt(f"{repo_id} liegt nicht vollständig im App-Cache; die App würde es herunterladen.\n"
                      f"Vorhandene Kopien unter ähnlichem Namen:\n{zeilen}\n"
                      "Vorhandene Kopie verwenden oder bewusst mit --download-erlauben starten.")


def laden(repo_id: str, parallel: int = 4, max_seq: int = 8192, download_erlaubt: bool = False) -> dict:
    """Modell zum Antworten laden; wartet, solange laufende Antworten das Umladen sperren (HTTP 409)."""
    sicherstellen(repo_id, download_erlaubt)
    body = {"model_path": repo_id, "max_seq_length": max_seq, "n_parallel": parallel, "load_in_4bit": False}
    while True:
        try:
            return api("POST", "/api/inference/load", body, timeout=1800)
        except ApiFehler as exc:
            if "409" not in str(exc):
                raise
            time.sleep(10)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    sub.add_parser("liste")
    p = sub.add_parser("pruefen"); p.add_argument("repo_id")
    l = sub.add_parser("laden"); l.add_argument("repo_id")
    l.add_argument("--parallel", type=int, default=4); l.add_argument("--max-seq", type=int, default=8192)
    l.add_argument("--download-erlauben", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.befehl == "liste":
            b = bestand()
            for e in b:
                marke = ((f" DOPPELT {e['doppelt_gb']:.0f} GB" if e["doppelt_gb"] else "") + " verlinkt" * e["verlinkt"]
                         + " UNVOLLSTÄNDIG" * (not e["vollstaendig"]))
                print(f"{e['ort']:9} {e['gb']:6.1f} GB  {e['format']:11} {e['id']}{marke}")
            belegt = {i: e["gb"] / max(len(e["inodes"]), 1) for e in b for i in e["inodes"]}
            print(f"\nbelegt {sum(belegt.values()):.0f} GB; davon doppelt (zweite Kopie mit eigenen Daten) "
                  f"{sum(e['doppelt_gb'] for e in b) / 2:.0f} GB")
        elif a.befehl == "pruefen":
            sicherstellen(a.repo_id)
            print(f"{a.repo_id}: vollständig im App-Cache")
        else:
            print(laden(a.repo_id, a.parallel, a.max_seq, a.download_erlauben))
    except ModellFehlt as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
