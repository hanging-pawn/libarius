"""Laufprotokoll `konfig/laeufe/<lauf>.json` (Schema `schema/laufprotokoll.schema.json`, LIBAR-117).

  neu          Protokoll aus einer API-Konfiguration und den Datensätzen anlegen (Status «geplant»)
  nachtragen   Protokoll aus einer vorhandenen <name>.gestartet.json bauen (Läufe vor diesem Format)
  pruefen      Protokolle gegen das Schema prüfen
  vergleichen  zwei Protokolle: was unterscheidet sich (Einstellungen, Datenstand, Version, Ergebnis)

Aufruf: python -m kochassistent.training.laufprotokoll vergleichen konfig/laeufe/a.json konfig/laeufe/b.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[3]
LAEUFE = PROJEKT / "konfig" / "laeufe"
SCHEMA = PROJEKT / "schema" / "laufprotokoll.schema.json"
NICHT_EINSTELLUNG = {"local_datasets", "local_eval_datasets", "datenstand", "job_id", "adapter_path", "project_name"}
STANDARD_STUDIO = {"version": "unbekannt", "rechner": "studio", "backend": "MLX", "weg": "api"}


def sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(PROJEKT))
    except ValueError:
        return str(p)


def neu(lauf: str, konfig: dict, train: Path, valid: Path | None, *, studio: dict | None = None,
        export: dict | None = None, zweck: str = "", wiederholt: str | None = None) -> dict:
    datensaetze = [{"rolle": r, "datei": _rel(p), "sha256": sha256(p), "zeilen": sum(1 for _ in p.open("rb"))}
                   for r, p in (("train", train), ("valid", valid)) if p]
    d = {
        "format": "laufprotokoll/1",
        "lauf": lauf,
        "zweck": zweck,
        "basismodell": konfig["model_name"],
        "einstellungen": {k: v for k, v in konfig.items() if k not in NICHT_EINSTELLUNG},
        "datensaetze": datensaetze,
        "saat": int(konfig.get("random_seed", 3407)),
        "studio": STANDARD_STUDIO | {"job_id": None} | (studio or {}),
        "export": export or {"format": "keiner"},
        "ergebnis": {"status": "geplant"},
    }
    if wiederholt:
        d["wiederholt"] = wiederholt
    return d


def nachtragen(gestartet: Path, lauf: str, *, beleg: str, ergebnis: dict | None = None, studio: dict | None = None,
               zweck: str = "") -> dict:
    k = json.loads(gestartet.read_text("utf-8"))
    namen = list((k.get("datenstand") or {}).items())
    pfade = (k.get("local_datasets") or []) + (k.get("local_eval_datasets") or [])
    datensaetze = []
    for i, (name, h) in enumerate(namen):
        eintrag = {"rolle": "train" if "train" in name else "valid", "datei": name, "sha256": h}
        if i < len(pfade):
            eintrag["studio_pfad"] = pfade[i]
        datensaetze.append(eintrag)
    return {
        "format": "laufprotokoll/1",
        "lauf": lauf,
        "zweck": zweck,
        "nachgetragen": f"aus {_rel(gestartet)} (lokal, gitignored); Datenstand dort nur als 16-stelliger Hash-Anfang",
        "basismodell": k["model_name"],
        "einstellungen": {x: y for x, y in k.items() if x not in NICHT_EINSTELLUNG},
        "datensaetze": datensaetze,
        "saat": int(k.get("random_seed", 3407)),
        "studio": STANDARD_STUDIO | {"job_id": k.get("job_id")} | (studio or {}),
        "export": {"format": "keiner"},
        "ergebnis": {"status": "fertig", "adapter_pfad": k.get("adapter_path"), "beleg": beleg} | (ergebnis or {}),
    }


def pruefe(d: dict) -> list[str]:
    from jsonschema import Draft202012Validator

    v = Draft202012Validator(json.loads(SCHEMA.read_text("utf-8")))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(wurzel)'}: {e.message}" for e in v.iter_errors(d)]


def _flach(d: dict, praefix: str = "") -> dict:
    aus = {}
    for k, v in d.items():
        if isinstance(v, dict):
            aus |= _flach(v, f"{praefix}{k}.")
        else:
            aus[f"{praefix}{k}"] = v
    return aus


def vergleiche(a: dict, b: dict) -> list[tuple[str, object, object]]:
    """→ [(Feld, Wert in a, Wert in b)] für jedes Feld, das sich unterscheidet; Datensätze nach Rolle."""
    fa = _flach({k: v for k, v in a.items() if k not in ("datensaetze", "lauf", "zweck", "wiederholt", "nachgetragen")})
    fb = _flach({k: v for k, v in b.items() if k not in ("datensaetze", "lauf", "zweck", "wiederholt", "nachgetragen")})
    for d, f in ((a, fa), (b, fb)):
        for s in d["datensaetze"]:
            f[f"datensatz.{s['rolle']}.sha256"] = s["sha256"]
    return [(k, fa.get(k), fb.get(k)) for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]


def schreibe(d: dict, ziel: Path | None = None) -> Path:
    fehler = pruefe(d)
    if fehler:
        raise ValueError("Laufprotokoll ungültig: " + "; ".join(fehler))
    ziel = ziel or LAEUFE / f"{d['lauf']}.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return ziel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    n = sub.add_parser("neu")
    n.add_argument("lauf")
    n.add_argument("--konfig", type=Path, required=True)
    n.add_argument("--train", type=Path, required=True)
    n.add_argument("--valid", type=Path)
    n.add_argument("--export", default="keiner", choices=["keiner", "lora", "merged-16bit", "gguf", "mlx"])
    n.add_argument("--studio-version", default="unbekannt")
    n.add_argument("--wiederholt")
    n.add_argument("--zweck", default="")
    t = sub.add_parser("nachtragen")
    t.add_argument("lauf")
    t.add_argument("--gestartet", type=Path, required=True)
    t.add_argument("--beleg", required=True)
    t.add_argument("--zweck", default="")
    p = sub.add_parser("pruefen")
    p.add_argument("dateien", type=Path, nargs="+")
    v = sub.add_parser("vergleichen")
    v.add_argument("a", type=Path)
    v.add_argument("b", type=Path)
    a = ap.parse_args(argv)

    if a.befehl == "neu":
        k = json.loads(a.konfig.read_text("utf-8"))
        d = neu(a.lauf, k, a.train, a.valid, studio={"version": a.studio_version}, export={"format": a.export},
                zweck=a.zweck, wiederholt=a.wiederholt)
        print(schreibe(d))
    elif a.befehl == "nachtragen":
        print(schreibe(nachtragen(a.gestartet, a.lauf, beleg=a.beleg, zweck=a.zweck)))
    elif a.befehl == "pruefen":
        schlecht = 0
        for f in a.dateien:
            fehler = pruefe(json.loads(f.read_text("utf-8")))
            schlecht += bool(fehler)
            print(f"{f}: {'ok' if not fehler else '; '.join(fehler)}")
        return 1 if schlecht else 0
    else:
        diff = vergleiche(json.loads(a.a.read_text("utf-8")), json.loads(a.b.read_text("utf-8")))
        for feld, x, y in diff:
            print(f"{feld}: {json.dumps(x, ensure_ascii=False)} → {json.dumps(y, ensure_ascii=False)}")
        if not diff:
            print("keine Unterschiede")
    return 0


if __name__ == "__main__":
    sys.exit(main())
