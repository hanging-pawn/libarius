"""Erzeugt die Fixtures in tests/fixtures/ (erfundene Beispiele, nicht aus einem Buch)."""
import copy
import json
from pathlib import Path

ZIEL = Path(__file__).parent / "fixtures"

GUELTIG = {
    "id": "fix-001",
    "aufgabe": "bewerten",
    "bereich": "backen",
    "rechtsstatus": "gemeinfrei",
    "eingabe": {"frage": "Ist das Verhältnis Mehl zu Wasser für ein Brot sinnvoll?"},
    "denkweg": [
        {
            "text": "Das Wasser macht 72 Prozent des Mehls aus.",
            "stuetze": {"art": "rechnung", "rechnung": "720 / 1000 = 0.72"},
        },
        {"text": "Dieser Wert liegt im üblichen Bereich.", "stuetze": {"art": "beleg", "belegId": "b1"}},
    ],
    "ausgabe": {
        "kriterien": [{"kriterium": "verhaeltnisse", "urteil": "ok", "begruendung": "72 Prozent Wasser."}],
        "vorschlaege": [],
    },
    "belege": [
        {
            "id": "b1",
            "quelleId": "erfunden-001",
            "stelle": "Kapitel 1",
            "aussage": "Brotteige liegen meist zwischen 65 und 80 Prozent Wasser.",
            "art": "grundverhaeltnis",
        }
    ],
    "pruefung": {"loesungAusQuelle": True, "rechnungenGeprueft": True, "status": "automatisch"},
}


def variante(aendere):
    b = copy.deepcopy(GUELTIG)
    aendere(b)
    return b


UNGUELTIG = {
    "ungueltig_ohne_belege.jsonl": variante(lambda b: b.pop("belege")),
    "ungueltig_schritt_ohne_stuetze.jsonl": variante(lambda b: b["denkweg"][0].pop("stuetze")),
    "ungueltig_befund_ohne_bedingungen.jsonl": variante(
        lambda b: b["belege"][0].update(art="befund")
    ),
    "ungueltig_unbekannter_bereich.jsonl": variante(lambda b: b.update(bereich="grillen")),
}

if __name__ == "__main__":
    ZIEL.mkdir(exist_ok=True)
    (ZIEL / "gueltig.jsonl").write_text(json.dumps(GUELTIG, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, bsp in UNGUELTIG.items():
        (ZIEL / name).write_text(json.dumps(bsp, ensure_ascii=False) + "\n", encoding="utf-8")
