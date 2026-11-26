"""Abschnittstyp, Bereich und Markierung `ueberholt_pruefen` (REQ-002, REQ-008).

Regelbasiert, damit jede Zuordnung nachvollziehbar ist: die Funktion gibt neben dem Typ den
Grund zurück. Die Handprüfung (Stichprobe 50 Abschnitte) misst die Trefferquote.
"""
from __future__ import annotations

import re

TYPEN = ("Rezept", "Technik", "Grundverhaeltnis", "Fehlerbild", "Warenkunde", "Befund")
BEREICHE = ("kochen", "backen")

BEFUND = re.compile(
    r"\b(Studie|Studien|Proband\w*|signifikant\w*|untersucht\w*|gemessen\w*|Messung\w*|Versuchsreihe|"
    r"stud(y|ies)|significant\w*|participants|we (found|measured|observed)|results? (show|indicate)|p\s?<\s?0[.,]\d+)\b",
    re.I,
)
FEHLER = re.compile(
    r"\b(misslingt|mißlingt|misslungen|mißrathen|missraten|verdirbt|verdorben|Fehler|fehlerhaft|"
    r"fällt zusammen|zusammenfallen|sitzen bleibt|sitzenbleiben|gerinnt|gerinnen|brennt an|anbrennen|"
    r"klumpig|zähe wird|zäh wird|schliffig|Ursache)\b",
    re.I,
)
FEHLER_TITEL = re.compile(r"\b(Fehler|Ursache|misslingt|mißlingt|verdorben|Mittel gegen|zu helfen|retten)\b", re.I)
WAREN_TITEL = re.compile(
    r"\b(Erkennungszeichen|Kennzeichen|Einkauf|Güte|Auswahl|Sorten|zu erkennen|Beschaffenheit|Warenkunde)\b", re.I
)
WAREN_TEXT = re.compile(r"\b(erkennt man|kennt man|Kennzeichen|daran erkennen|beim Einkauf|kauft man)\b", re.I)
VERHAELTNIS = re.compile(
    r"(\bVerhältni(s|ß)\b|\bauf (je|jedes|jede|ein|eine|einen|\d+[½¼¾]?)\s+(Pfund|Maß|Ei|Eier|Loth|Tasse|Theil|Teil)\b"
    r".{0,80}?\b(nimmt|rechnet|gehör|kommt|kommen|gibt|braucht|nehme)|"
    r"\b(\d+|ein|zwei|drei|vier|fünf|sechs)\s+(Theile?|Teile?)\b.{0,120}?\b(\d+|einem|einen|ein)\s+(Theil|Teil)\b)",
    re.I | re.S,
)
TECHNIK_TITEL = re.compile(
    r"^(\d+\.\s*)?(Vom|Von dem|Von der|Von den|Über|Ueber|Etwas über|Regeln|Allgemeine|Im Allgemeinen|"
    r"Behandlung|Art und Weise|Verfahren)\b|\bzu\s+\w+en\.?$|\bzu\s+\w+en\b.{0,30}$",
    re.I,
)
BACKEN = re.compile(
    r"\b(\w*kuchen\w*|\w*torte\w*|\w*teig\w*|\w*brot\w*|\w*brod\w*|\w*gebäck\w*|backwerk|zwieback|waffel\w*|"
    r"pastete\w*|plätzchen|makronen|macronen|brezel\w*|biscuit\w*|bisquit\w*|kringel\w*|krapfen|auflauf|aufläufe)\b",
    re.I,
)
SPEISEFOLGE = re.compile(r"\b(Arrangements|Speisezettel|Küchenzettel|Speisefolge)\b", re.I)
UEBERHOLT = re.compile(
    r"\b(einmach\w*|eingemacht\w*|einzumachen|einkoch\w*|haltbar\w*|aufzubewahren|aufbewahr\w*|"
    r"schwefel\w*|pökel\w*|pöckel\w*|einpöckeln|räucher\w*|salpeter|konservier\w*|"
    r"gesund\w*|ungesund\w*|krank\w*|heilsam\w*|heilt|arznei\w*|verdaulich\w*|unverdaulich\w*|"
    r"stärkend\w*|gift\w*|grünspan|vergift\w*|blei(?:ern\w*)?|kupfern\w*|messingen\w*)\b",
    re.I,
)
# Ein einzelner beiläufiger Treffer («gesunde Eier») markiert noch nicht; Kapitel zur
# Haltbarmachung markieren immer.
UEBERHOLT_SCHWELLE = 2
STARKE_SICHERHEIT = re.compile(r"\b(gift\w*|grünspan|vergift\w*|kupfern\w*|blei(?:ern\w*)?|salpeter|krank\w*|heilsam\w*|arznei\w*)\b", re.I)


def klassifiziere(titel: str, text: str, anzahl_mengen: int, kapitel: list[str] | None = None) -> tuple[str, str]:
    """→ (Typ, Grund). Reihenfolge: Befund, Fehlerbild, Warenkunde, Grundverhältnis, Technik, Rezept."""
    if SPEISEFOLGE.search(" ".join([*(kapitel or []), titel])):
        return "Technik", "Speisefolge (Menüplanung)"
    befund = len(BEFUND.findall(text))
    if befund >= 2:
        return "Befund", f"{befund} Studienmerkmale"
    if FEHLER_TITEL.search(titel):
        return "Fehlerbild", "Titel nennt Fehler oder Abhilfe"
    fehler = len(FEHLER.findall(text))
    if fehler >= 3 and anzahl_mengen <= 2:
        return "Fehlerbild", f"{fehler} Fehlermerkmale, kaum Mengen"
    if WAREN_TITEL.search(titel):
        return "Warenkunde", "Titel nennt Erkennen oder Güte der Ware"
    if len(WAREN_TEXT.findall(text)) >= 2 and anzahl_mengen <= 1:
        return "Warenkunde", "Text beschreibt Erkennen der Ware"
    if VERHAELTNIS.search(text) and anzahl_mengen <= 4:
        return "Grundverhaeltnis", "Verhältnisangabe bei wenigen Einzelmengen"
    if TECHNIK_TITEL.search(titel.strip()) and anzahl_mengen <= 2:
        return "Technik", "Titel beschreibt Verfahren, kaum Mengen"
    return "Rezept", f"{anzahl_mengen} Mengen"


def bereich(kapitel: list[str], titel: str, backen_kapitel: list[str]) -> str:
    for k in kapitel:
        if any(k.startswith(b) for b in backen_kapitel):
            return "backen"
    return "backen" if BACKEN.search(titel) else "kochen"


def ueberholt(kapitel: list[str], titel: str, text: str, ueberholt_kapitel: list[str]) -> str | None:
    """→ Grund der Markierung oder None. Markierte Abschnitte sind nicht trainingsfähig."""
    for k in kapitel:
        if any(k.startswith(u) for u in ueberholt_kapitel):
            return f"Kapitel zur Haltbarmachung: {k}"
    if UEBERHOLT.search(titel):
        return f"Titel: {UEBERHOLT.search(titel).group(0)}"
    stark = STARKE_SICHERHEIT.findall(text)
    if stark:
        return f"Sicherheit/Gesundheit: {stark[0]}"
    treffer = UEBERHOLT.findall(text)
    if len(treffer) >= UEBERHOLT_SCHWELLE:
        return "Haltbarmachung/Gesundheit: " + ", ".join(sorted({t.lower() for t in treffer})[:4])
    return None
