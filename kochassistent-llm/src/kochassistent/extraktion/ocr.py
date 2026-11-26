"""OCR-Pfad für Scans (REQ-004): Seite rendern, Vision-OCR (macOS), Fraktur-Nachkorrektur.

Vision ist im System enthalten; das Swift-Programm wird beim ersten Aufruf nach
`daten/cache/` übersetzt (gitignored). Fraktur liest Vision mit typischen Verwechslungen
(d→b, s→f, ch→d)); `fraktur_korrigiere` behebt die häufigsten auf Wortebene. Zahlen
werden von der Korrektur nie verändert.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
CACHE = HIER.parents[2] / "daten" / "cache"
QUELLE_SWIFT = HIER / "ocr_vision.swift"

# Aus korpus.py: Fehlformen der Fraktur-OCR und ihre Gegenstücke.
FRAKTUR_FALSCH = re.compile(
    r"(?<![\wäöüß])(unb|bie|ber|bas|ift|fid\)|nid\)t|fic|ftc|fte|bcn|bem|beb|wirb|wcrben|merben|aud\)|nod\)|bod\)|mufj|mufe|Sutter|©)(?![\wäöüß])")
FRAKTUR_RICHTIG = re.compile(
    r"(?<![\wäöüß])(und|die|der|das|ist|sich|nicht|sie|den|dem|des|wird|werden|auch|noch|doch|muss|muß|Butter)(?![\wäöüß])")

WORTKORREKTUR = {
    "unb": "und", "bie": "die", "ber": "der", "bas": "das", "ba8": "das", "baß": "das", "bae": "das",
    "ift": "ist", "fie": "sie", "fo": "so", "fich": "sich", "fid": "sich", "bem": "dem", "ben": "den",
    "beê": "des", "bes": "des", "wirb": "wird", "mirb": "wird", "merben": "werden", "werben": "werden",
    "worben": "worden", "bann": "dann", "baffelbe": "dasselbe", "biefe": "diese", "biefer": "dieser",
    "biefes": "dieses", "bies": "dies", "bis": "bis", "bi8": "bis", "beiben": "beiden", "Geiten": "Seiten",
    "man": "man", "nad": "nach", "aud": "auch", "nod": "noch", "bod": "doch", "body": "doch",
    "Butter": "Butter", "Sutter": "Butter", "mit": "mit", "fein": "fein", "ober": "oder", "ganz": "ganz",
}


def _binaer() -> Path:
    ziel = CACHE / "ocr_vision"
    if not ziel.exists() or ziel.stat().st_mtime < QUELLE_SWIFT.stat().st_mtime:
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(ziel), str(QUELLE_SWIFT)], check=True, capture_output=True)
    return ziel


def ocr_bilder(bilder: list[Path]) -> dict[str, list[str]]:
    if not bilder:
        return {}
    erg = subprocess.run([str(_binaer()), *map(str, bilder)], check=True, capture_output=True, text=True)
    aus = {}
    for zeile in erg.stdout.splitlines():
        d = json.loads(zeile)
        aus[d["datei"]] = d["zeilen"]
    return aus


def ocr_pdf_seiten(pdf: Path, seiten: list[int], dpi: int = 300, block: int = 10) -> dict[int, str]:
    """1-basierte Seitennummern → OCR-Text je Seite."""
    import pymupdf

    texte: dict[int, str] = {}
    with pymupdf.open(pdf) as doc, tempfile.TemporaryDirectory() as tmp:
        for start in range(0, len(seiten), block):
            teil = seiten[start:start + block]
            bilder = []
            for s in teil:
                p = Path(tmp) / f"s{s:05d}.png"
                doc[s - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY).save(p)
                bilder.append(p)
            erg = ocr_bilder(bilder)
            for s, b in zip(teil, bilder):
                texte[s] = "\n".join(erg.get(str(b), []))
            for b in bilder:
                b.unlink()
    return texte


def fraktur_quote(text: str) -> float:
    """Anteil der Fraktur-Fehlformen an allen Treffern beider Listen (0 = sauber, ~1 = unbrauchbar)."""
    f, r = len(FRAKTUR_FALSCH.findall(text)), len(FRAKTUR_RICHTIG.findall(text))
    return f / (f + r) if f + r else 0.0


def fraktur_korrigiere(text: str) -> str:
    """Häufige Fraktur-Verwechslungen beheben. Ziffern bleiben unberührt."""
    text = re.sub(r"(?<=[a-zäöü])d\)", "ch", text)       # «nad)», «mad)t» → «nach», «macht»
    text = re.sub(r"(?<=\w)=\n", "", text)                # Trennstrich der Fraktur als «=»
    text = re.sub(r"(?<=\w)[-—]\n(?=[a-zäöü])", "", text)

    def wort(m: re.Match) -> str:
        w = m.group(0)
        return WORTKORREKTUR.get(w, w)

    return re.sub(r"(?<![\w])[A-Za-zäöüßê8]+(?![\w])", wort, text)
