"""Zahlenprüfung (REQ-004): jede Zahl auf zwei unabhängigen Wegen ziehen, Abweichungen listen.

Zwei Zähler, absichtlich verschieden gebaut:
- `zahlen_muster`: regulärer Ausdruck über Ziffernfolgen und Bruchzeichen.
- `zahlen_zeichen`: Zeichen-für-Zeichen-Automat ohne Regex.
Beide liefern normierte Zahlwerte als Text («1½» → «1.5», «¾» → «0.75»).
"""
from __future__ import annotations

import re
from collections import Counter

BRUECHE = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}
_B = "".join(BRUECHE)
MUSTER = re.compile(rf"(\d+)(?:[  ]?([{_B}]))?|([{_B}])")


def _norm(wert: float) -> str:
    return f"{wert:.4f}".rstrip("0").rstrip(".")


def zahlen_muster(text: str) -> Counter:
    c: Counter = Counter()
    for m in MUSTER.finditer(text):
        if m.group(3):
            c[_norm(BRUECHE[m.group(3)])] += 1
        else:
            c[_norm(int(m.group(1)) + (BRUECHE[m.group(2)] if m.group(2) else 0))] += 1
    return c


def zahlen_zeichen(text: str) -> Counter:
    c: Counter = Counter()
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if "0" <= ch <= "9":
            j = i
            while j < n and "0" <= text[j] <= "9":
                j += 1
            wert = float(text[i:j])
            k = j + 1 if j < n and text[j] in "  " else j
            if k < n and text[k] in BRUECHE:
                wert += BRUECHE[text[k]]
                j = k + 1
            c[_norm(wert)] += 1
            i = j
        elif ch in BRUECHE:
            c[_norm(BRUECHE[ch])] += 1
            i += 1
        else:
            i += 1
    return c


def vergleiche(a: Counter, b: Counter) -> list[tuple[str, int, int]]:
    """→ [(Zahl, Anzahl Weg A, Anzahl Weg B)] für jede Zahl mit ungleicher Anzahl."""
    return sorted(((z, a[z], b[z]) for z in set(a) | set(b) if a[z] != b[z]), key=lambda t: (-abs(t[1] - t[2]), t[0]))


def abweichung(a: Counter, b: Counter) -> tuple[int, int]:
    """→ (abweichende Zahlen, Zahlen gesamt nach Weg B)."""
    return sum(abs(x - y) for _, x, y in vergleiche(a, b)), sum(b.values())
