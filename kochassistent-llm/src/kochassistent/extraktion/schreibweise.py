"""Alte Rechtschreibung in heutige (REQ-007). Zahlen bleiben unangetastet.

Regelbasiert und bewusst eng: langes s, th → t in bekannten Stämmen, eine Wortliste für
häufige Formen des 19. Jahrhunderts. Was nicht sicher ist, bleibt wie es steht. Der
Originaltext bleibt am Abschnitt erhalten.
"""
from __future__ import annotations

import re

# Ganze Wörter (Kleinschreibung); Grossschreibung am Wortanfang wird übernommen.
WOERTER = {
    "daß": "dass", "muß": "muss", "läßt": "lässt", "läßt's": "lässt's", "faßt": "fasst", "paßt": "passt",
    "mußt": "musst", "gewiß": "gewiss", "laß": "lass", "eßlöffel": "esslöffel",
    "eßlöffeln": "esslöffeln", "naß": "nass", "blaß": "blass", "indeß": "indes",
    "brod": "brot", "brode": "brote", "weißbrod": "weissbrot", "schwarzbrod": "schwarzbrot",
    "gahr": "gar", "gahre": "gare", "gahren": "garen", "zimmet": "zimt", "lorberblätter": "lorbeerblätter",
    "lorberblatt": "lorbeerblatt", "lorberblättern": "lorbeerblättern", "citrone": "zitrone",
    "compote": "kompott", "blangiren": "blanchieren", "blangirt": "blanchiert",
    "glanciren": "glasieren", "passiren": "passieren", "passirt": "passiert", "garniren": "garnieren",
    "garnirt": "garniert", "giebt": "gibt", "seyn": "sein", "bey": "bei", "hülfe": "hilfe",
    "anmerk.": "anmerkung:", "gefrornes": "gefrorenes", "gefrornem": "gefrorenem",
    "hefen": "hefe", "hefenteig": "hefeteig",
}
# th → t in Stämmen, in denen das h heute wegfällt (nicht in «Thymian», «Methode»).
TH_STAEMME = re.compile(
    r"\b([Tt])h(eil|ee|un|ut|at|ier|ür|on|ran|rän|au)", re.UNICODE
)
TH_WOERTER = {"nöthig": "nötig", "roth": "rot", "rothe": "rote", "rothen": "roten", "muth": "mut",
              "gluth": "glut", "werth": "wert", "noth": "not", "rath": "rat", "drath": "draht",
              "blüthe": "blüte", "muskatblüthe": "muskatblüte", "theelöffel": "teelöffel",
              "zuthaten": "zutaten", "drittheil": "drittel", "viertheil": "viertel"}
WORTGRENZE = re.compile(r"[A-Za-zÄÖÜäöüßſ]+\.?")


def _fall(alt: str, neu: str) -> str:
    return neu[:1].upper() + neu[1:] if alt[:1].isupper() else neu


def modernisiere(text: str) -> str:
    text = text.replace("ſ", "s").replace("’", "'")

    def ersetze(m: re.Match) -> str:
        w = m.group(0)
        k = w.lower()
        for tabelle in (WOERTER, TH_WOERTER):
            if k in tabelle:
                return _fall(w, tabelle[k])
            if k.endswith(".") and k[:-1] in tabelle and not tabelle[k[:-1]].endswith(":"):
                return _fall(w, tabelle[k[:-1]]) + "."
        w = TH_STAEMME.sub(lambda t: t.group(1) + t.group(2), w)
        return w

    text = WORTGRENZE.sub(ersetze, text)
    text = re.sub(r"(?<=[a-zäöü]{2})(?<!w)iren\b", "ieren", text)
    text = re.sub(r"(?<=[a-zäöü]{2})(?<!w)irt\b", "iert", text)
    return text
