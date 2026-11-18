"""Rohtext-Korpus für einen ersten Trainingsversuch (Weitertraining auf Fachtext, «raw»).

Liest Quellordner (PDF, TXT, EPUB, archive.org-OCR), zieht den Text heraus, filtert
Fachartikel ohne Kochbezug aus, zerlegt in Stücke mit Fundstelle und schreibt:

  <aus>/korpus_meta.jsonl   ein Stück je Zeile: text, quelle, datei, fundstelle
  <aus>/train.jsonl         nur {"text": ...}, für Unsloth (format_type raw)
  <aus>/valid.jsonl         dito, rund 3 % der Stücke, nach Hash fest zugeteilt
  <aus>/bericht.tsv         je Datei: aufgenommen/verworfen, Grund, Zeichen, Kochbezug

Dient REQ-002 (Fundstelle je Abschnitt) nur vorläufig: die Fundstelle ist Datei + Seite.
Die eigentliche Extraktion des Pilotbuchs ist LIBAR-106. Aufruf:

  python -m kochassistent.extraktion.korpus --aus daten/korpus/v01 <ordner> [<ordner> ...]
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import zipfile
from pathlib import Path

# Begriffe mit Kochbezug (de/en/fr). Zählt Treffer je 1000 Wörter.
KOCHWORTE = re.compile(
    r"\b(cook(s|ed|ing|ery)?|bak(e|ed|es|ing|ery)|bread(s)?|dough(s)?|oven(s)?|recipe(s)?|flour|roast(ed|ing)?|"
    r"boil(ed|ing)?|fr(y|ied|ying)|sous[- ]vide|kitchen(s)?|culinary|gastronom\w*|sauce(s)?|batter|pastry|"
    r"cake(s)?|doneness|sourdough|marinat\w*|grill(ed|ing)?|stew(ed|ing)?|simmer\w*|steam(ed|ing)|"
    r"chef(s)?|dish(es)?|meal(s)?|consumer(s)?|household|home|"
    r"koch\w*|back(en|t|ofen|zeit)|brot\w*|teig\w*|ofen|rezept\w*|mehl|braten|gebraten|sieden|küche|kuchen|"
    r"cuisine|cuire|cuisson|farine|recette(s)?)\b",
    re.IGNORECASE,
)
VERWERFEN_NAME = re.compile(r"^(Editorial-Board|Contributors|Foreword|Erratum|Corrigendum|Retraction)", re.I)
# Fraktur-OCR (archive.org, Google Books) liest d als b, s als f, ch als d): «unb bie fid)».
# Gemessen an v01: unbrauchbare Scans liegen bei 0,96–0,98, saubere Texte unter 0,05.
FRAKTUR_FALSCH = re.compile(
    r"(?<![\wäöüß])(unb|bie|ber|bas|ift|fid\)|nid\)t|fic|ftc|fte|bcn|bem|beb|wirb|wcrben|merben|aud\)|nod\)|bod\)|mufj|mufe|Sutter|©)(?![\wäöüß])")
FRAKTUR_RICHTIG = re.compile(
    r"(?<![\wäöüß])(und|die|der|das|ist|sich|nicht|sie|den|dem|des|wird|werden|auch|noch|doch|muss|muß|Butter)(?![\wäöüß])")
LITERATUR = re.compile(r"\n\s*(References|REFERENCES|Literatur(verzeichnis)?|Bibliography|Références)\s*\n")
GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
GUTENBERG_ENDE = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", re.I)


def text_pdf(pfad: Path) -> list[tuple[str, str]]:
    import pymupdf

    seiten = []
    with pymupdf.open(pfad) as doc:
        for i, seite in enumerate(doc, 1):
            seiten.append((f"S. {i}", seite.get_text("text")))
    return seiten


def text_epub(pfad: Path) -> list[tuple[str, str]]:
    teile = []
    with zipfile.ZipFile(pfad) as z:
        namen = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        for n in namen:
            roh = z.read(n).decode("utf-8", "ignore")
            roh = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", roh)
            roh = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</div>", "\n", roh)
            roh = html.unescape(re.sub(r"<[^>]+>", " ", roh))
            teile.append((Path(n).name, roh))
    return teile


def text_txt(pfad: Path) -> list[tuple[str, str]]:
    roh = pfad.read_text("utf-8", errors="ignore")
    if m := GUTENBERG_START.search(roh):
        roh = roh[m.end():]
    if m := GUTENBERG_ENDE.search(roh):
        roh = roh[: m.start()]
    return [("Text", roh)]


def text_markup(pfad: Path) -> list[tuple[str, str]]:
    """JATS-XML (Europe PMC) oder HTML-Seite: Literaturliste, Skripte, Navigation weg, Tags zu Absätzen."""
    roh = pfad.read_text("utf-8", errors="ignore")
    roh = re.sub(r"(?is)<(script|style|head|nav|footer|header|ref-list|back|front-stub|table-wrap-foot|teiHeader)\b.*?</\1>", " ", roh)
    roh = re.sub(r"(?is)<(article-meta|journal-meta)\b.*?</\1>", lambda m: " ".join(
        re.findall(r"(?is)<(?:article-title|abstract)\b.*?</(?:article-title|abstract)>", m.group(0))), roh)
    roh = re.sub(r"(?i)</?(p|sec|title|h\d|li|div|tr|br|caption|abstract|article-title)\b[^>]*>", "\n\n", roh)
    roh = html.unescape(re.sub(r"<[^>]+>", " ", roh))
    return [("Text", roh)]


def art(pfad: Path) -> str:
    """Dateityp nach Inhalt (manche Downloads tragen eine irreführende Endung)."""
    kopf = pfad.open("rb").read(512)
    if kopf.startswith(b"%PDF"):
        return "pdf"
    if kopf.startswith(b"PK"):
        return "epub" if pfad.suffix.lower() == ".epub" else "zip"
    k = kopf.lstrip().lower()
    if k.startswith((b"<?xml", b"<!doctype article", b"<article")):
        return "xml"
    if k.startswith((b"<!doctype html", b"<html")) or pfad.suffix.lower() in (".html", ".htm"):
        return "html"
    return "txt"


def saeubern(text: str) -> str:
    text = text.replace("\r", "").replace("­", "").replace("ſ", "s")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # Trennung am Zeilenende
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<![.!?:;\n])\n(?!\n)", " ", text)   # Zeilen zu Absätzen
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def kochbezug(text: str) -> float:
    woerter = max(1, len(text.split()))
    return 1000 * len(KOCHWORTE.findall(text)) / woerter


def fraktur_fehler(text: str) -> float:
    """Anteil falsch gelesener deutscher Funktionswörter; 0 bei zu wenig Belegen (z. B. englischer Text)."""
    f, r = len(FRAKTUR_FALSCH.findall(text)), len(FRAKTUR_RICHTIG.findall(text))
    return f / (f + r) if f + r >= 10 else 0.0


def stuecke(seiten: list[tuple[str, str]], ziel: int) -> list[tuple[str, str]]:
    """Fasst Absätze zu Stücken von etwa `ziel` Zeichen; Fundstelle = erste–letzte Seite."""
    aus, puffer, von, bis = [], [], None, None
    laenge = 0
    for ort, roh in seiten:
        for absatz in saeubern(roh).split("\n\n"):
            absatz = absatz.strip()
            if len(absatz) < 3:
                continue
            if von is None:
                von = ort
            bis = ort
            puffer.append(absatz)
            laenge += len(absatz)
            if laenge >= ziel:
                aus.append((von if von == bis else f"{von}–{bis}", "\n\n".join(puffer)))
                puffer, von, laenge = [], None, 0
    if puffer and laenge > 200:
        aus.append((von if von == bis else f"{von}–{bis}", "\n\n".join(puffer)))
    return aus


def dateien(ordner: list[Path]) -> list[Path]:
    alle = []
    for o in ordner:
        alle += [p for p in o.rglob("*") if p.is_file() and p.suffix.lower() in (".pdf", ".txt", ".epub", ".xml", ".html", ".htm")]
    # archive.org: OCR-Text vorziehen, PDF desselben Identifiers überspringen
    djvu = {str(p)[: -len(".djvu.txt")] for p in alle if p.name.endswith(".djvu.txt")}
    alle = [p for p in alle if not (p.suffix.lower() == ".pdf" and str(p)[:-4] in djvu)]
    # gleiches Werk in mehreren Formaten (X.djvu.txt, X.epub, X.pdf): nur eines, OCR-Text vor EPUB vor PDF
    def rang(p: Path) -> int:
        return 0 if p.name.endswith(".djvu.txt") else 1 if p.suffix.lower() == ".epub" else 2
    gesehen, eindeutig = set(), []
    for p in sorted(alle, key=lambda p: (rang(p), str(p))):
        schluessel = (p.parent, p.name.removesuffix(".djvu.txt") if rang(p) == 0 else p.stem)
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eindeutig.append(p)
    return sorted(eindeutig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ordner", nargs="+", type=Path)
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--stueck", type=int, default=5000, help="Zielgrösse je Stück in Zeichen (≈ 1300 Tokens)")
    ap.add_argument("--min-kochbezug", type=float, default=6.0, help="Treffer je 1000 Wörter, darunter verworfen (nur Paper-Sammlung «cooking science»)")
    ap.add_argument("--valid-anteil", type=float, default=0.03)
    a = ap.parse_args(argv)
    a.aus.mkdir(parents=True, exist_ok=True)

    meta = open(a.aus / "korpus_meta.jsonl", "w", encoding="utf-8")
    train = open(a.aus / "train.jsonl", "w", encoding="utf-8")
    valid = open(a.aus / "valid.jsonl", "w", encoding="utf-8")
    bericht = open(a.aus / "bericht.tsv", "w", encoding="utf-8")
    bericht.write("status\tgrund\tzeichen\tkochbezug\tstuecke\tdatei\n")
    n_train = n_valid = 0
    for pfad in dateien(a.ordner):
        rel = str(pfad)
        if VERWERFEN_NAME.match(pfad.name):
            bericht.write(f"verworfen\tkein Fachtext\t0\t0\t0\t{rel}\n"); continue
        try:
            typ = art(pfad)
            if typ == "zip":
                bericht.write(f"verworfen\tArchiv\t0\t0\t0\t{rel}\n"); continue
            seiten = {"pdf": text_pdf, "epub": text_epub, "xml": text_markup, "html": text_markup}.get(typ, text_txt)(pfad)
        except Exception as e:  # beschädigte Datei: festhalten, weitermachen
            bericht.write(f"fehler\t{type(e).__name__}: {e}\t0\t0\t0\t{rel}\n"); continue
        ist_artikel = "/artikel/" in rel or "cooking science" in rel
        if ist_artikel:  # Literaturverzeichnis am Ende abschneiden
            gesamt = "\n".join(t for _, t in seiten)
            if (m := list(LITERATUR.finditer(gesamt))) and m[-1].start() > 0.5 * len(gesamt):
                rest = m[-1].start()
                gekuerzt, zaehler = [], 0
                for ort, t in seiten:
                    if zaehler + len(t) + 1 > rest:
                        gekuerzt.append((ort, t[: max(0, rest - zaehler)])); break
                    gekuerzt.append((ort, t)); zaehler += len(t) + 1
                seiten = gekuerzt
        volltext = " ".join(t for _, t in seiten)
        zeichen = len(volltext)
        bezug = kochbezug(volltext)
        if zeichen < 2000:
            bericht.write(f"verworfen\tkaum Text (Scan ohne OCR?)\t{zeichen}\t{bezug:.1f}\t0\t{rel}\n"); continue
        # Nur die unsortierte Paper-Sammlung filtern; artikel/ ist von Hand für die Lücken ausgewählt
        # (Lebensmittelsicherheit trifft die Kochwörter kaum, z. B. Salmonellen in Mayonnaise).
        if "cooking science" in rel and bezug < a.min_kochbezug:
            bericht.write(f"verworfen\tkein Kochbezug\t{zeichen}\t{bezug:.1f}\t0\t{rel}\n"); continue
        alle = stuecke(seiten, a.stueck)
        teile = [(o, t) for o, t in alle if fraktur_fehler(t) <= 0.3]
        if len(teile) < 0.5 * len(alle):
            bericht.write(f"verworfen\tFraktur-OCR unbrauchbar ({len(alle) - len(teile)}/{len(alle)} Stücke)\t{zeichen}\t{bezug:.1f}\t0\t{rel}\n"); continue
        quelle = pfad.stem[:60] if "cooking science" in rel else pfad.name.split("_")[0]
        for ort, t in teile:
            h = int(hashlib.sha1(t.encode()).hexdigest(), 16) % 10000
            zeile = json.dumps({"text": t}, ensure_ascii=False) + "\n"
            if h < a.valid_anteil * 10000:
                valid.write(zeile); n_valid += 1
            else:
                train.write(zeile); n_train += 1
            meta.write(json.dumps({"text": t, "quelle": quelle, "datei": pfad.name, "fundstelle": ort}, ensure_ascii=False) + "\n")
        bericht.write(f"aufgenommen\t-\t{zeichen}\t{bezug:.1f}\t{len(teile)}\t{rel}\n")
    for f in (meta, train, valid, bericht):
        f.close()
    print(f"{n_train} Trainings-, {n_valid} Validierungsstücke → {a.aus}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
