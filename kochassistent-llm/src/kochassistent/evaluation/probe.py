"""Prüffragen an Basismodell und Adapter stellen und nebeneinander als Markdown schreiben.

Lädt den Adapter in der Unsloth-Studio-App und schaltet je Anfrage mit use_adapter zwischen Basis und Adapter um.
Kein Ersatz für die Evaluation gegen das Goldset (REQ-040 bis REQ-043), nur ein schneller Blick nach einem Lauf.

Aufruf: python -m kochassistent.evaluation.probe --adapter <adapter_path> --aus modelle/versuch-02.probe.md
        (adapter_path aus: python -m kochassistent.training.studio adapter)
        --system konfig/systemanweisung-01.txt  Systemanweisung vor jede Frage (Gegenprobe ohne Training)
        --nur basis|adapter                     nur eine Seite befragen
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kochassistent.modelle import ModellFehlt, sicherstellen
from kochassistent.studio_api import api, chat


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--fragen", type=Path, default=Path("konfig/probe-fragen.txt"))
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--max-tokens", type=int, default=1200)
    ap.add_argument("--system", type=Path, help="Datei mit Systemanweisung")
    ap.add_argument("--nur", choices=("basis", "adapter"))
    a = ap.parse_args(argv)
    basis = next((l["base_model"] for l in api("GET", "/api/models/loras")["loras"] if l["adapter_path"] == a.adapter), None)
    if basis is None:
        print(f"Adapter nicht gefunden: {a.adapter}", file=sys.stderr)
        return 2
    try:
        sicherstellen(basis)  # Basis des Adapters muss da sein, sonst lädt die App sie still nach
    except ModellFehlt as exc:
        print(exc, file=sys.stderr)
        return 2
    geladen = {m["id"] for m in api("GET", "/api/inference/loaded-models")["data"] if m.get("loaded")}
    if a.adapter.rsplit("/", 1)[-1] not in geladen:
        api("POST", "/api/inference/load", {"model_path": a.adapter, "is_lora": True, "load_in_4bit": False,
                                            "max_seq_length": 4096}, timeout=1800)
    system = a.system.read_text(encoding="utf-8").strip() if a.system else None
    seiten = [(n, an) for n, an in (("Basis", False), ("Adapter", True)) if a.nur in (None, n.lower())]
    fragen = [z.strip() for z in a.fragen.read_text(encoding="utf-8").splitlines() if z.strip() and not z.startswith("#")]
    a.aus.parent.mkdir(parents=True, exist_ok=True)
    with open(a.aus, "w", encoding="utf-8") as out:
        out.write(f"# Prüffragen — Basis gegen Adapter\n\nAdapter: `{a.adapter.rsplit('/', 1)[-1]}`, "
                  f"temperature 0.3, seed 1, ohne Denkmodus, max. {a.max_tokens} Tokens"
                  + (f", Systemanweisung `{a.system}`:\n\n> " + system.replace("\n", "\n> ") if system else "")
                  + "\n\n")
        for i, f in enumerate(fragen, 1):
            out.write(f"## {i}. {f}\n\n")
            for name, an in seiten:
                nachrichten = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": f}]
                text = chat(nachrichten, temperatur=0.3, max_tokens=a.max_tokens, seed=1,
                            extra={"use_adapter": an})
                out.write(f"### {name}\n\n{text.strip()}\n\n")
                out.flush()
            print(f"{i}/{len(fragen)}", flush=True)
    print(a.aus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
