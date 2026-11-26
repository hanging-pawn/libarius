"""Extraktion einer Quelle in typisierte Abschnitte mit Fundstelle (LIBAR-106).

  python -m kochassistent.extraktion <quelleId> [--seiten 41-90] [--stichprobe <datei.md>]

Schreibt nach `daten/roh/<quelleId>/` (gitignored, REQ-105):
  abschnitte.jsonl          ein Abschnitt je Zeile: typ, fundstelle, bereich, text, mengen, ueberholt_pruefen
  zahlen_abweichungen.tsv   Zahlen, die die zwei unabhängigen Wege verschieden zählen
  bericht.json              Kennzahlen (Typen, Bereiche, Markierte, Zahlenabweichungsquote)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

from . import einheiten, klassifikation, ocr, schreibweise, tei, zahlen

PROJEKT = Path(__file__).resolve().parents[3]
KONFIG = PROJEKT / "konfig"


def quellen_ordner() -> Path:
    if env := os.environ.get("KOCHASSISTENT_QUELLEN"):
        return Path(env).expanduser()
    lokal = KONFIG / "pfade.lokal.toml"
    if not lokal.exists():
        sys.exit("Quellenordner fehlt: konfig/pfade.beispiel.toml nach pfade.lokal.toml kopieren oder KOCHASSISTENT_QUELLEN setzen")
    return Path(tomllib.loads(lokal.read_text("utf-8"))["quellen"]).expanduser()


def lade_quelle(qid: str) -> dict:
    alle = json.loads((KONFIG / "quellen.json").read_text("utf-8"))["quellen"]
    if qid not in alle:
        sys.exit(f"Unbekannte Quelle {qid}; bekannt: {', '.join(alle)}")
    return alle[qid] | {"id": qid}


def _seiten_text(von: str | None, bis: str | None) -> str:
    if not von:
        return "o. S."
    return f"S. {von}" if von == bis or not bis else f"S. {von}–{bis}"


def baue_abschnitt(q: dict, nr: int, titel_o: str, kapitel_o: list[str], text_o: str, fundstelle: dict, textweg: str) -> dict:
    titel = schreibweise.modernisiere(titel_o)
    kapitel = [schreibweise.modernisiere(k) for k in kapitel_o]
    text = schreibweise.modernisiere(text_o)
    mengen = einheiten.finde_mengen(text, q["id"])
    typ, grund = klassifikation.klassifiziere(titel, text, len(mengen), kapitel)
    ueberholt = klassifikation.ueberholt(kapitel, titel, text, q.get("ueberholt_kapitel", []))
    fundstelle = fundstelle | {"kapitel": kapitel, "titel": titel}
    pfad = " › ".join([*kapitel, titel] if titel else kapitel)
    return {
        "id": f"{q['id']}-{nr:04d}",
        "quelle": q["id"],
        "typ": typ,
        "typ_grund": grund,
        "bereich": klassifikation.bereich(kapitel, titel, q.get("backen_kapitel", [])),
        "fundstelle": fundstelle,
        "fundstelle_text": f"{q.get('kurz', q['id'])}, {_seiten_text(fundstelle.get('seite_von'), fundstelle.get('seite_bis'))} · {pfad}",
        "titel_original": titel_o,
        "titel": titel,
        "text_original": text_o,
        "text": text,
        "mengen": [m.als_dict() for m in mengen],
        "ueberholt_pruefen": ueberholt is not None,
        "ueberholt_grund": ueberholt,
        "training": ueberholt is None,
        "textweg": textweg,
    }


def extrahiere_tei(q: dict, pfad: Path) -> tuple[list[dict], dict]:
    leser = tei.lies(pfad)
    abschnitte = []
    for i, r in enumerate(leser.abschnitte, 1):
        fs = {"seite_von": r.seite_von, "seite_bis": r.seite_bis, "faksimile_von": r.faks_von, "faksimile_bis": r.faks_bis}
        abschnitte.append(baue_abschnitt(q, i, r.titel, r.kapitel, r.text, fs, "transkription"))

    # Zahlenprüfung. Weg A: ElementTree-Leser, Zähler per Regex. Weg B: XML-Quelltext per Muster
    # zerlegt, Zähler als Zeichenautomat. Je Seite verglichen.
    roh_b = tei.seiten_roh(pfad)
    zeilen, abw, gesamt = [], 0, 0
    for faks in sorted(set(leser.seiten_text) | set(roh_b)):
        a = zahlen.zahlen_muster("".join(leser.seiten_text.get(faks, [])))
        b = zahlen.zahlen_zeichen(roh_b.get(faks, ""))
        x, n = zahlen.abweichung(a, b)
        abw, gesamt = abw + x, gesamt + n
        zeilen += [(faks, z, ca, cb) for z, ca, cb in zahlen.vergleiche(a, b)]
    # Ausgabe gegen Quelle: Zahlen aller Abschnitte (Original) gegen den ganzen Body (Weg B).
    a_aus = sum((zahlen.zahlen_muster(s["titel_original"] + " " + s["text_original"]) for s in abschnitte), Counter())
    kapitel_koepfe = {k for s in abschnitte for k in s["fundstelle"]["kapitel"]}
    eigene_titel = {s["titel"] for s in abschnitte}
    for k in kapitel_koepfe - eigene_titel:
        a_aus += zahlen.zahlen_muster(k)
    b_ges = sum((zahlen.zahlen_zeichen(t) for t in roh_b.values()), Counter())
    aus_abw, aus_ges = zahlen.abweichung(a_aus, b_ges)
    pruefung = {
        "verfahren": "Weg A ElementTree + Regex-Zähler je Seite gegen Weg B Quelltext-Muster + Zeichenautomat je Seite; zusätzlich Zahlen der geschriebenen Abschnitte gegen den ganzen Body",
        "zahlen_gesamt": gesamt, "abweichend": abw, "quote": abw / gesamt if gesamt else 0.0,
        "ausgabe_gegen_quelle": {"zahlen_gesamt": aus_ges, "abweichend": aus_abw, "quote": aus_abw / aus_ges if aus_ges else 0.0,
                                 "abweichungen": [list(t) for t in zahlen.vergleiche(a_aus, b_ges)[:40]]},
        "zeilen": zeilen,
    }
    return abschnitte, pruefung


UEBERSCHRIFT = re.compile(r"^\s*(\d{1,3})\.\s+[A-ZÄÖÜ][^\n]{2,80}$", re.M)


def _seitenbereich(angabe: str | None, anzahl: int) -> list[int]:
    if not angabe:
        return list(range(1, anzahl + 1))
    von, _, bis = angabe.partition("-")
    return list(range(int(von), min(int(bis or von), anzahl) + 1))


def extrahiere_scan(q: dict, pfad: Path, seiten_angabe: str | None) -> tuple[list[dict], dict]:
    import pymupdf

    with pymupdf.open(pfad) as doc:
        seiten = _seitenbereich(seiten_angabe or q.get("seiten"), len(doc))
        schicht = {s: doc[s - 1].get_text("text") for s in seiten}
    ocr_roh = ocr.ocr_pdf_seiten(pfad, seiten)
    ocr_text = {s: ocr.fraktur_korrigiere(t) for s, t in ocr_roh.items()}

    # Zahlenprüfung: Textschicht (fremde OCR im PDF) gegen eigene Vision-OCR, je Seite.
    zeilen, abw, gesamt = [], 0, 0
    for s in seiten:
        a = zahlen.zahlen_muster(ocr_text[s])
        b = zahlen.zahlen_zeichen(schicht[s])
        x, n = zahlen.abweichung(a, b)
        abw, gesamt = abw + x, gesamt + n
        zeilen += [(f"PDF-S. {s}", z, ca, cb) for z, ca, cb in zahlen.vergleiche(a, b)]
    # Zweiter, unabhängiger OCR-Durchgang mit anderer Auflösung: eigene OCR gegen eigene OCR.
    ocr_zwei = {s: ocr.fraktur_korrigiere(t) for s, t in ocr.ocr_pdf_seiten(pfad, seiten, dpi=200).items()}
    zeilen2, abw2, gesamt2 = [], 0, 0
    for s in seiten:
        a = zahlen.zahlen_muster(ocr_text[s])
        b = zahlen.zahlen_zeichen(ocr_zwei[s])
        x, n = zahlen.abweichung(a, b)
        abw2, gesamt2 = abw2 + x, gesamt2 + n
        zeilen2 += [(f"PDF-S. {s} (OCR 300 gegen 200 dpi)", z, ca, cb) for z, ca, cb in zahlen.vergleiche(a, b)]
    quote_vor = ocr.fraktur_quote("\n".join(ocr_roh.values()))
    quote_nach = ocr.fraktur_quote("\n".join(ocr_text.values()))

    # Abschnitte: an nummerierten Überschriften zerlegen; Fundstelle = PDF-Seite.
    abschnitte, nr, titel, puffer, start = [], 0, "", [], seiten[0]
    def schliesse(bis: int) -> None:
        nonlocal nr
        text = " ".join(" ".join(puffer).split())
        if len(re.sub(r"\W", "", text)) >= 15:
            nr += 1
            fs = {"seite_von": str(start), "seite_bis": str(bis), "seitenart": "PDF-Seite"}
            abschnitte.append(baue_abschnitt(q, nr, titel, [], text, fs, "ocr"))
    for s in seiten:
        zeilen_s = ocr_text[s].splitlines()
        if zeilen_s and re.fullmatch(r"\s*\d{1,4}\s*", zeilen_s[0]):
            zeilen_s = zeilen_s[1:]  # lebende Seitenzahl
        for z in zeilen_s:
            if UEBERSCHRIFT.match(z):
                schliesse(s)
                titel, puffer, start = z.strip(), [], s
            else:
                puffer.append(z[:-1] if z.endswith(("-", "=", "—")) else z + " ")
    schliesse(seiten[-1])
    pruefung = {
        "verfahren": "Textschicht des PDF (fremde OCR) gegen eigene Vision-OCR mit Fraktur-Nachkorrektur, je Seite",
        "seiten": [seiten[0], seiten[-1]], "zahlen_gesamt": gesamt, "abweichend": abw,
        "quote": abw / gesamt if gesamt else 0.0,
        "ocr_gegen_ocr": {"verfahren": "Vision-OCR 300 dpi gegen 200 dpi, je Seite", "zahlen_gesamt": gesamt2,
                          "abweichend": abw2, "quote": abw2 / gesamt2 if gesamt2 else 0.0},
        "fraktur_fehlerquote_vor_korrektur": round(quote_vor, 3),
        "fraktur_fehlerquote_nach_korrektur": round(quote_nach, 3),
        "zeilen": zeilen + zeilen2,
    }
    return abschnitte, pruefung


def schreibe_stichprobe(q: dict, abschnitte: list[dict], ziel: Path, n: int = 50, saat: int = 106) -> list[dict]:
    auswahl = random.Random(saat).sample(abschnitte, min(n, len(abschnitte)))
    auswahl.sort(key=lambda s: s["id"])

    def zelle(t: str, max_len: int = 700) -> str:
        t = " ".join(t.split()).replace("|", "/")
        return t if len(t) <= max_len else t[:max_len].rsplit(" ", 1)[0] + " …"

    zeilen = [
        "---",
        "projekt: Libarius (LIBAR)",
        "typ: Prüfblatt",
        "ticket: LIBAR-106",
        f"quelle: {q['id']}",
        "---",
        f"# Stichprobe Extraktion — {q.get('kurz', q['id'])}",
        "",
        f"**Quelle:** {q['titel']} ({q.get('ausgabe', '')}).  ",
        f"**Auswahl:** {len(auswahl)} von {len(abschnitte)} Abschnitten, zufällig (Saat {saat}).  ",
        "**Prüfen:** Stimmt der Typ (Rezept, Technik, Grundverhaeltnis, Fehlerbild, Warenkunde, Befund), "
        "stimmt die Fundstelle (Seite, Kapitel), ist der Text vollständig? In die letzte Spalte `ok` oder `falsch` "
        "eintragen, bei `falsch` kurz warum. Ziel nach REQ-002 (Vorschlag): mindestens 95 % `ok`.",
        "",
        "| Nr | ID | Fundstelle | Typ | Bereich | Markiert | Text (heutige Schreibweise) | ok/falsch |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(auswahl, 1):
        mark = "ueberholt_pruefen" if s["ueberholt_pruefen"] else "—"
        zeilen.append(f"| {i} | {s['id']} | {zelle(s['fundstelle_text'], 200)} | {s['typ']} | {s['bereich']} | {mark} | {zelle(s['text'])} |  |")
    zeilen.append("")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(zeilen), "utf-8")
    return auswahl


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kochassistent.extraktion", description=__doc__.split("\n")[0])
    ap.add_argument("quelle", help="Quellen-ID aus konfig/quellen.json, z. B. G1")
    ap.add_argument("--seiten", help="nur für Scans: Seitenbereich 41-90")
    ap.add_argument("--aus", type=Path, help="Zielordner (Standard daten/roh/<quelleId>)")
    ap.add_argument("--stichprobe", type=Path, help="Prüfblatt mit 50 zufälligen Abschnitten schreiben")
    args = ap.parse_args(argv)

    q = lade_quelle(args.quelle)
    pfad = quellen_ordner() / q["datei"]
    if not pfad.exists():
        sys.exit(f"Datei fehlt: {pfad}")
    if q["format"] == "tei":
        abschnitte, pruefung = extrahiere_tei(q, pfad)
    elif q["format"] == "scan":
        abschnitte, pruefung = extrahiere_scan(q, pfad, args.seiten)
    else:
        sys.exit(f"Format {q['format']} nicht unterstützt")

    aus = args.aus or PROJEKT / "daten" / "roh" / q["id"]
    aus.mkdir(parents=True, exist_ok=True)
    with (aus / "abschnitte.jsonl").open("w", encoding="utf-8") as f:
        for s in abschnitte:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with (aus / "zahlen_abweichungen.tsv").open("w", encoding="utf-8") as f:
        f.write("seite\tzahl\tanzahl_weg_a\tanzahl_weg_b\n")
        for z in pruefung["zeilen"]:
            f.write("\t".join(map(str, z)) + "\n")

    einheiten_genutzt = Counter(m["einheit"] for s in abschnitte for m in s["mengen"])
    bericht = {
        "quelle": q["id"],
        "abschnitte": len(abschnitte),
        "typen": dict(Counter(s["typ"] for s in abschnitte).most_common()),
        "bereiche": dict(Counter(s["bereich"] for s in abschnitte).most_common()),
        "ueberholt_pruefen": sum(s["ueberholt_pruefen"] for s in abschnitte),
        "trainingsfaehig": sum(s["training"] for s in abschnitte),
        "trainingsfaehig_mit_markierung": sum(s["training"] and s["ueberholt_pruefen"] for s in abschnitte),
        "ohne_fundstelle": sum(not s["fundstelle"].get("seite_von") for s in abschnitte),
        "mengen": sum(einheiten_genutzt.values()),
        "einheiten": dict(einheiten_genutzt.most_common()),
        "zahlenpruefung": {k: v for k, v in pruefung.items() if k != "zeilen"},
    }
    (aus / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
    if args.stichprobe:
        schreibe_stichprobe(q, abschnitte, args.stichprobe)
        bericht["stichprobe"] = str(args.stichprobe)
    zp = bericht["zahlenpruefung"]
    print(f"{q['id']}: {len(abschnitte)} Abschnitte → {aus / 'abschnitte.jsonl'}")
    print(f"  Typen {bericht['typen']} · Bereiche {bericht['bereiche']}")
    print(f"  ueberholt_pruefen {bericht['ueberholt_pruefen']} · trainingsfähig {bericht['trainingsfaehig']} (davon markiert {bericht['trainingsfaehig_mit_markierung']})")
    print(f"  Zahlen: {zp['abweichend']} von {zp['zahlen_gesamt']} abweichend ({zp['quote']:.4%})")
    if "ocr_gegen_ocr" in zp:
        z2 = zp["ocr_gegen_ocr"]
        print(f"  Zahlen OCR gegen OCR: {z2['abweichend']} von {z2['zahlen_gesamt']} abweichend ({z2['quote']:.4%})")
    return 0
