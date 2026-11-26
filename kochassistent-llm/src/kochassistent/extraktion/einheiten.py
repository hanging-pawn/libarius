"""Mengenangaben finden und nach `konfig/einheiten.json` metrisch umrechnen (REQ-007).

Der Originalwert bleibt immer erhalten; die Umrechnung steht daneben. Was sich nicht
eindeutig umrechnen lässt (Preisangaben, Ofenstufen), wird markiert statt geraten (REQ-003).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

TABELLE = Path(__file__).resolve().parents[3] / "konfig" / "einheiten.json"

BRUECHE = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}
ZAHLWORTE = {
    "ein": 1, "eine": 1, "einen": 1, "einem": 1, "einer": 1, "eines": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
    "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "zwanzig": 20, "dreißig": 30, "dreissig": 30,
    "anderthalb": 1.5, "halb": 0.5, "halbe": 0.5, "halben": 0.5, "halbes": 0.5, "halber": 0.5,
    "viertel": 0.25, "drittel": 1 / 3, "achtel": 0.125,
}
_BRUCH = "".join(BRUECHE)
# Ziffernzahl mit optionalem Bruch: «3», «1 ½», «1½», «¼», «3/4»
ZIFFER = rf"(?:\d+(?:\s?[{_BRUCH}]|\s?\d+/\d+)?|[{_BRUCH}]|\d+/\d+)"
WORT = r"(?:" + "|".join(sorted(ZAHLWORTE, key=len, reverse=True)) + r")"
# «ein halbes», «ein Viertel», «anderthalb»
WORTZAHL = rf"(?:{WORT}(?:\s+{WORT})?)"
ZAHL = rf"(?:{ZIFFER}|{WORTZAHL})"
SPANNE = rf"(?P<von>{ZAHL})(?:\s*(?:—|–|-|bis)\s*(?P<bis>{ZAHL}))?"


def zahl_wert(roh: str) -> float:
    """«1 ½» → 1.5, «ein halbes» → 0.5, «Ein Viertel» → 0.25, «3/4» → 0.75."""
    roh = roh.strip()
    if m := re.fullmatch(rf"(\d+)\s?([{_BRUCH}])", roh):
        return int(m.group(1)) + BRUECHE[m.group(2)]
    if m := re.fullmatch(r"(\d+)\s(\d+)/(\d+)", roh):
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    if m := re.fullmatch(r"(\d+)/(\d+)", roh):
        return int(m.group(1)) / int(m.group(2))
    if roh in BRUECHE:
        return BRUECHE[roh]
    if roh.isdigit():
        return float(roh)
    teile = roh.lower().split()
    werte = [ZAHLWORTE[t] for t in teile]
    if len(werte) == 2 and werte[0] == 1 and werte[1] < 1:
        return werte[1]  # «ein halbes», «ein Viertel»
    if len(werte) == 2:
        return werte[0] * werte[1] if werte[1] < 1 else werte[0] + werte[1]
    return werte[0]


@dataclass
class Einheit:
    id: str
    formen: list[str]
    groesse: str
    metrisch: dict | None
    sicherheit: str
    herkunft: str
    abweichend: dict = field(default_factory=dict)

    def wert_fuer(self, quelle: str | None) -> dict | None:
        if quelle and quelle in self.abweichend:
            return self.abweichend[quelle]
        return self.metrisch


@lru_cache(maxsize=4)
def lade(pfad: str = str(TABELLE)) -> tuple[Einheit, ...]:
    daten = json.loads(Path(pfad).read_text("utf-8"))
    return tuple(
        Einheit(e["id"], e["formen"], e["groesse"], e.get("metrisch"), e["sicherheit"], e["herkunft"], e.get("abweichend", {}))
        for e in daten["einheiten"]
    )


@lru_cache(maxsize=4)
def _muster(pfad: str = str(TABELLE)) -> tuple[re.Pattern, dict[str, Einheit]]:
    form_zu = {}
    for e in lade(pfad):
        for f in e.formen:
            form_zu[f.lower()] = e
    formen = sorted(form_zu, key=len, reverse=True)
    alt = "|".join(re.escape(f) for f in formen)
    muster = re.compile(
        rf"(?<![\w]){SPANNE}\s+(?:(?:kleine[snmr]?|große[snmr]?|grosse[snmr]?|gute[snmr]?|gehäufte[snmr]?|starke[snmr]?|volle[snmr]?|halbe[snmr]?)\s+)?(?P<einheit>{alt})(?![\wäöüß])",
        re.IGNORECASE,
    )
    return muster, form_zu


@dataclass
class Menge:
    original: str
    wert: float
    wert_bis: float | None
    einheit: str
    metrisch_wert: float | None
    metrisch_wert_bis: float | None
    metrisch_einheit: str | None
    sicherheit: str
    markierung: str | None = None

    def als_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def finde_mengen(text: str, quelle: str | None = None, tabelle: str = str(TABELLE)) -> list[Menge]:
    muster, form_zu = _muster(tabelle)
    mengen = []
    for m in muster.finditer(text):
        e = form_zu[m.group("einheit").lower()]
        if e.id == "finger" and not re.search(r"(breit|dick)$", m.group("einheit")) and not re.match(r"\s*(breit|dick)", text[m.end():]):
            continue
        if e.id in ("fuss", "taler"):
            continue  # im Pilotbuch kein Mass (Körperteil, Dickenvergleich)
        von = zahl_wert(m.group("von"))
        bis = zahl_wert(m.group("bis")) if m.group("bis") else None
        metr = e.wert_fuer(quelle)
        mw = round(von * metr["wert"], 3) if metr else None
        mb = round(bis * metr["wert"], 3) if metr and bis is not None else None
        markierung = None
        if e.groesse == "preis":
            markierung = "nicht_ueberfuehrbar_preis"
        elif e.groesse == "ofenstufe":
            markierung = "ofenstufe_ohne_temperatur"
        mengen.append(Menge(m.group(0), von, bis, e.id, mw, mb, metr["einheit"] if metr else None, e.sicherheit, markierung))
    return mengen


def ungedeckte_einheiten(einheitsworte: set[str], tabelle: str = str(TABELLE)) -> set[str]:
    """Welche der gefundenen Einheitswörter fehlen in der Tabelle (für die Abnahme)."""
    _, form_zu = _muster(tabelle)
    return {w for w in einheitsworte if w.lower() not in form_zu}
