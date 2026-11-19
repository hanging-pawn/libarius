"""Trainingslauf in der Unsloth-Studio-App starten und verfolgen (REQ-021, LIBAR-117).

  starten  Datensätze hochladen, Pfade in die Konfiguration einsetzen, Lauf starten.
           Die eingesetzte Konfiguration landet neben der Vorlage als <name>.gestartet.json (Datenstand je Lauf).
  status   Phase, Schritt, Verlust und Eval-Verlust des aktuellen Laufs.
  warten   Bis der gestartete Lauf endet; trägt den neuen Adapter in <name>.gestartet.json ein und gibt ihn aus.
  adapter  Trainierte Adapter auflisten (Pfad für evaluation.probe).

Aufruf: python -m kochassistent.training.studio starten --konfig konfig/versuch-02-api.json \\
          --train daten/destilliert/v02/chat/train.jsonl --valid daten/destilliert/v02/chat/valid.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from kochassistent.studio_api import api, hochladen


def starten(konfig: Path, train: Path, valid: Path | None) -> None:
    k = json.loads(konfig.read_text(encoding="utf-8"))
    lauf = k.get("project_name", konfig.stem)
    k["local_datasets"] = [hochladen(train, f"{lauf}-train.jsonl")]
    k["local_eval_datasets"] = [hochladen(valid, f"{lauf}-valid.jsonl")] if valid else []
    k["datenstand"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in (train, valid) if p}
    gestartet = konfig.with_name(konfig.stem + ".gestartet.json")
    body = {x: y for x, y in k.items() if x != "datenstand"}
    r = api("POST", "/api/train/start", body)
    k["job_id"] = r.get("job_id")
    gestartet.write_text(json.dumps(k, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False), f"\nKonfiguration mit Datenstand: {gestartet}")


def status() -> None:
    s = api("GET", "/api/train/status")
    d, mh = s.get("details") or {}, s.get("metric_history") or {}
    print(f"{s['phase']} · Schritt {d.get('step')}/{d.get('total_steps')} · Verlust {d.get('loss')} · "
          f"Rest {round((d.get('eta_seconds') or 0) / 60)} min · Fehler {s.get('error')}")
    if mh.get("eval_loss"):
        print("Eval:", ", ".join(f"{st}: {v:.3f}" for st, v in zip(mh["eval_steps"], mh["eval_loss"])))


def _zeitmarke(a: dict) -> int:
    endung = a["adapter_path"].rsplit("_", 1)[-1]
    return int(endung) if endung.isdigit() else 0


def warten(konfig: Path, takt: int = 300) -> int:
    """Wartet auf das Ende des Laufs aus <konfig>.gestartet.json; 0 bei «completed», sonst 1."""
    gestartet = konfig.with_name(konfig.stem + ".gestartet.json")
    k = json.loads(gestartet.read_text(encoding="utf-8"))
    while True:
        try:
            s = api("GET", "/api/train/status")
        except Exception as exc:  # SSH- oder API-Aussetzer: weiter warten
            print(f"Status nicht lesbar: {exc}", file=sys.stderr, flush=True)
            time.sleep(takt)
            continue
        if s.get("job_id") == k["job_id"] and not s.get("is_training_running") and s.get("phase") not in ("idle", None):
            break
        d = s.get("details") or {}
        print(f"{time.strftime('%H:%M')} {s.get('phase')} · Schritt {d.get('step')}/{d.get('total_steps')} · "
              f"Verlust {d.get('loss')}", flush=True)
        time.sleep(takt)
    print(f"Ende: {s.get('phase')} · {s.get('message')} · Fehler {s.get('error')}", flush=True)
    if s.get("phase") != "completed":
        return 1
    neu = [a for a in api("GET", "/api/models/loras")["loras"] if a["base_model"] == k["model_name"]]
    k["adapter_path"] = max(neu, key=_zeitmarke)["adapter_path"]
    gestartet.write_text(json.dumps(k, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(k["adapter_path"])
    return 0


def adapter() -> None:
    for a in api("GET", "/api/models/loras")["loras"]:
        print(a["base_model"], a["adapter_path"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("starten")
    s.add_argument("--konfig", type=Path, required=True)
    s.add_argument("--train", type=Path, required=True)
    s.add_argument("--valid", type=Path)
    sub.add_parser("status")
    w = sub.add_parser("warten")
    w.add_argument("--konfig", type=Path, required=True)
    sub.add_parser("adapter")
    a = ap.parse_args(argv)
    if a.befehl == "warten":
        return warten(a.konfig)
    {"starten": lambda: starten(a.konfig, a.train, a.valid), "status": status, "adapter": adapter}[a.befehl]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
