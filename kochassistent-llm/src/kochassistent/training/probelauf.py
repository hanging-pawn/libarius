"""Erfundener Probedatensatz für den Probelauf in Unsloth Studio (LIBAR-117).

50 Beispiele im Trainingsschema (`schema/trainingsbeispiel.schema.json`), alle aus erfundenen
Zahlen gerechnet, kein Buchtext. Daraus die Chat-Dateien, die Studio liest (format_type chatml):

  python -m kochassistent.training.probelauf [--aus daten/probelauf]

  <aus>/beispiele.jsonl    50 Beispiele im Trainingsschema
  <aus>/chat/train.jsonl   45 Beispiele als {"messages": [...]}
  <aus>/chat/valid.jsonl    5 Beispiele

Gleiche Saat → byte-gleiche Dateien, damit der zweite Lauf denselben Datenstand hat.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[3]
SAAT = 117

# (Name, Wasseranteil von, bis) — erfundene Richtwerte, nur für den Probelauf
TEIGE = [("Brotteig", 0.65, 0.80), ("Pizzateig", 0.60, 0.70), ("Brötchenteig", 0.55, 0.65), ("Ciabattateig", 0.75, 0.90)]


def _beispiel(i: int, r: random.Random) -> dict:
    name, lo, hi = r.choice(TEIGE)
    mehl = r.choice([250, 300, 400, 500, 750, 1000])
    wasser = round(mehl * r.uniform(lo - 0.1, hi + 0.1) / 5) * 5
    anteil = wasser / mehl
    prozent = round(anteil * 100)
    ok = round(lo * 100) <= prozent <= round(hi * 100)  # auf ganze Prozent, wie im Text
    urteil = "ok" if ok else "kritisch"
    if ok:
        begruendung = f"{prozent} Prozent Wasser liegen im Bereich {round(lo * 100)} bis {round(hi * 100)} Prozent."
        vorschlaege = []
    else:
        ziel = round(mehl * (lo + hi) / 2 / 5) * 5
        richtung = "zu fest" if prozent < round(lo * 100) else "zu weich"
        begruendung = f"{prozent} Prozent Wasser liegen ausserhalb von {round(lo * 100)} bis {round(hi * 100)} Prozent, der Teig wird {richtung}."
        vorschlaege = [{"aenderung": f"Wasser auf {ziel} g setzen", "wirkung": "Teig im üblichen Bereich",
                        "begruendung": f"{ziel} / {mehl} = {ziel / mehl:.2f} liegt in der Mitte des Bereichs"}]
    return {
        "id": f"probe-{i:03d}",
        "aufgabe": "bewerten",
        "bereich": "backen",
        "rechtsstatus": "gemeinfrei",
        "eingabe": {"frage": f"Ein {name} mit {mehl} g Mehl und {wasser} g Wasser: passt das Verhältnis?"},
        "denkweg": [
            {"text": f"Der Wasseranteil beträgt {prozent} Prozent des Mehls.",
             "stuetze": {"art": "rechnung", "rechnung": f"{wasser} / {mehl} = {anteil:.2f}"}},
            {"text": f"Für {name} gilt {round(lo * 100)} bis {round(hi * 100)} Prozent.", "stuetze": {"art": "beleg", "belegId": "b1"}},
        ],
        "ausgabe": {"kriterien": [{"kriterium": "verhaeltnisse", "urteil": urteil, "begruendung": begruendung}],
                    "vorschlaege": vorschlaege},
        "belege": [{"id": "b1", "quelleId": "erfunden-probelauf", "stelle": "erfunden",
                    "aussage": f"{name} liegt bei {round(lo * 100)} bis {round(hi * 100)} Prozent Wasser (erfundener Richtwert).",
                    "art": "grundverhaeltnis"}],
        "pruefung": {"loesungAusQuelle": True, "rechnungenGeprueft": True, "status": "automatisch"},
    }


def als_chat(b: dict) -> dict:
    schritte = " ".join(s["text"] for s in b["denkweg"])
    k = b["ausgabe"]["kriterien"][0]
    antwort = f"**Überlegung:** {schritte}\n\n**Antwort:** {k['urteil']}. {k['begruendung']}"
    for v in b["ausgabe"]["vorschlaege"]:
        antwort += f" Vorschlag: {v['aenderung']} ({v['begruendung']})."
    return {"messages": [{"role": "user", "content": b["eingabe"]["frage"]}, {"role": "assistant", "content": antwort}]}


def erzeuge(aus: Path, n: int = 50, saat: int = SAAT, valid: int = 5) -> list[dict]:
    r = random.Random(saat)
    beispiele = [_beispiel(i, r) for i in range(1, n + 1)]
    (aus / "chat").mkdir(parents=True, exist_ok=True)
    zeilen = lambda xs: "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in xs)
    (aus / "beispiele.jsonl").write_text(zeilen(beispiele), "utf-8")
    chats = [als_chat(b) for b in beispiele]
    (aus / "chat" / "train.jsonl").write_text(zeilen(chats[valid:]), "utf-8")
    (aus / "chat" / "valid.jsonl").write_text(zeilen(chats[:valid]), "utf-8")
    return beispiele


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aus", type=Path, default=PROJEKT / "daten" / "probelauf")
    a = ap.parse_args(argv)
    erzeuge(a.aus)
    print(f"50 Beispiele → {a.aus}/beispiele.jsonl, chat/train.jsonl (45), chat/valid.jsonl (5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
