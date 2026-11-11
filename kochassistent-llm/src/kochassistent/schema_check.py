"""Prüft Trainingsbeispiele (JSONL) gegen schema/trainingsbeispiel.schema.json.

Aufruf: python -m kochassistent.schema_check <datei.jsonl>
Ausgabe: eine Zeile je ungültiges Beispiel (Zeile, Pfad, verletzte Regel). Exit 0 nur, wenn alle gültig sind.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PFAD = Path(__file__).resolve().parents[2] / "schema" / "trainingsbeispiel.schema.json"


def lade_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PFAD.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _pfad(fehler) -> str:
    teile = [str(p) for p in fehler.absolute_path]
    return "/".join(teile) if teile else "(Beispiel)"


def pruefe_zeilen(zeilen, validator: Draft202012Validator | None = None) -> list[str]:
    """Gibt eine Meldung je Verstoss zurück; leere Liste = alles gültig."""
    validator = validator or lade_validator()
    meldungen: list[str] = []
    for nr, roh in enumerate(zeilen, start=1):
        if not roh.strip():
            continue
        try:
            beispiel = json.loads(roh)
        except json.JSONDecodeError as exc:
            meldungen.append(f"Zeile {nr}: ungültig — Regel json: {exc.msg}")
            continue
        for fehler in sorted(validator.iter_errors(beispiel), key=lambda e: list(e.absolute_path)):
            meldungen.append(
                f"Zeile {nr}: ungültig — Regel {fehler.validator} bei {_pfad(fehler)}: {fehler.message}"
            )
    return meldungen


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Aufruf: python -m kochassistent.schema_check <datei.jsonl>", file=sys.stderr)
        return 2
    datei = Path(argv[0])
    try:
        zeilen = datei.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"Datei nicht lesbar: {exc}", file=sys.stderr)
        return 2
    meldungen = pruefe_zeilen(zeilen)
    for m in meldungen:
        print(m)
    return 1 if meldungen else 0


if __name__ == "__main__":
    sys.exit(main())
