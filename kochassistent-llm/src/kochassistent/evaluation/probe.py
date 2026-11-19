"""Prüffragen an Basismodell und Adapter stellen und nebeneinander als Markdown schreiben.

Lädt den Adapter in der Unsloth-Studio-App und schaltet je Anfrage mit use_adapter zwischen Basis und Adapter um.
Kein Ersatz für die Evaluation gegen das Goldset (REQ-040 bis REQ-043), nur ein schneller Blick nach einem Lauf.

Aufruf: python -m kochassistent.evaluation.probe --adapter <adapter_path> --aus modelle/versuch-02.probe.md
        (adapter_path aus: python -m kochassistent.training.studio adapter)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from kochassistent.studio_api import api, chat


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--fragen", type=Path, default=Path("konfig/probe-fragen.txt"))
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--max-tokens", type=int, default=1200)
    a = ap.parse_args(argv)
    api("POST", "/api/inference/load", {"model_path": a.adapter, "is_lora": True, "load_in_4bit": False,
                                        "max_seq_length": 4096}, timeout=1800)
    fragen = [z.strip() for z in a.fragen.read_text(encoding="utf-8").splitlines() if z.strip() and not z.startswith("#")]
    a.aus.parent.mkdir(parents=True, exist_ok=True)
    with open(a.aus, "w", encoding="utf-8") as out:
        out.write(f"# Prüffragen — Basis gegen Adapter\n\nAdapter: `{a.adapter.rsplit('/', 1)[-1]}`, "
                  f"temperature 0.3, seed 1, ohne Denkmodus, max. {a.max_tokens} Tokens\n\n")
        for i, f in enumerate(fragen, 1):
            out.write(f"## {i}. {f}\n\n")
            for name, an in (("Basis", False), ("Adapter", True)):
                text = chat([{"role": "user", "content": f}], temperatur=0.3, max_tokens=a.max_tokens, seed=1,
                            extra={"use_adapter": an})
                out.write(f"### {name}\n\n{text.strip()}\n\n")
                out.flush()
            print(f"{i}/{len(fragen)}", flush=True)
    print(a.aus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
