import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
FIX = WURZEL / "tests" / "fixtures"

# Fixture -> Wort, das die Meldung enthalten muss (verletzte Regel)
UNGUELTIG = {
    "ungueltig_ohne_belege.jsonl": ("required", "belege"),
    "ungueltig_schritt_ohne_stuetze.jsonl": ("required", "stuetze"),
    "ungueltig_befund_ohne_bedingungen.jsonl": ("required", "bedingungen"),
    "ungueltig_unbekannter_bereich.jsonl": ("enum", "bereich"),
}


def lauf(datei: Path):
    return subprocess.run(
        [sys.executable, "-m", "kochassistent.schema_check", str(datei)],
        cwd=WURZEL, capture_output=True, text=True,
        env={"PYTHONPATH": str(WURZEL / "src"), "PATH": ""},
    )


def test_gueltig_exit_0():
    r = lauf(FIX / "gueltig.jsonl")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout == ""


@pytest.mark.parametrize("name,regel", UNGUELTIG.items())
def test_ungueltig_nennt_regel(name, regel):
    r = lauf(FIX / name)
    assert r.returncode != 0
    zeilen = r.stdout.strip().splitlines()
    assert len(zeilen) >= 1
    for wort in regel:
        assert wort in r.stdout, r.stdout


def test_fixtures_vollstaendig():
    assert {p.name for p in FIX.glob("ungueltig_*.jsonl")} == set(UNGUELTIG)
