"""Automatische Prüfungen der Destillation (kochassistent.destillation.qa), ohne Lehrer-Modell."""
from kochassistent.destillation.qa import laengster_wortlaut, pruefe, rechnung_pruefen, zahlen

STUECK = {"historisch": False, "text": "Für ein Weissbrot nimmt man 500 g Mehl und 350 g Wasser. Bei 230 °C backen, "
                                      "nach 10 Minuten auf 200 °C zurückschalten."}


def beispiel(**aenderung):
    b = {"aufgabe": "bewerten", "bereich": "backen",
         "frage": "Ich habe 500 g Mehl und 350 g Wasser. Ist das für ein Weissbrot richtig?",
         "antwort": "Ja. Das Wasser macht 70 Prozent des Mehlgewichts aus, das passt für ein Weissbrot. Gebacken wird "
                    "zuerst heiss bei 230 °C und nach 10 Minuten bei 200 °C weiter.",
         "denkweg": [{"text": "350 g Wasser auf 500 g Mehl", "art": "rechnung", "rechnung": "350 / 500 = 0.7"},
                     {"text": "Die Quelle nennt dieses Verhältnis.", "art": "beleg"}],
         "beleg": {"art": "grundverhaeltnis", "aussage": "Weissbrot mit 500 g Mehl auf 350 g Wasser."}}
    b.update(aenderung)
    return b


def test_gutes_beispiel_besteht():
    assert pruefe(beispiel(), STUECK) == []


def test_erfundene_zahl_wird_verworfen():
    g = pruefe(beispiel(antwort="Ja, aber backe es 45 Minuten bei 230 °C, dann ist die Kruste schön dunkel."), STUECK)
    assert any(x.startswith("zahl-nicht-belegt:45") for x in g)


def test_falsche_rechnung_wird_verworfen():
    b = beispiel(denkweg=[{"text": "x", "art": "rechnung", "rechnung": "350 / 500 = 0.8"}])
    assert "rechnung-falsch" in pruefe(b, STUECK)


def test_prozent_aus_rechnung_ist_erlaubt():
    ok, zs = rechnung_pruefen("350 g / 500 g = 0,7")
    assert ok and 70 in zs


def test_sz_wird_zu_ss():
    b = beispiel(antwort="Das Wasser macht 70 Prozent aus, das passt gut für ein Weissbrot. Man backt es heiß bei 230 °C.")
    pruefe(b, STUECK)
    assert "ß" not in b["antwort"]


def test_wortlaut_und_textbezug():
    b = beispiel(frage="Was steht im Text über Weissbrot?",
                 antwort="Für ein Weissbrot nimmt man 500 g Mehl und 350 g Wasser. Bei 230 °C backen, so steht es da.")
    g = pruefe(b, STUECK)
    assert "frage-verweist-auf-text" in g and any(x.startswith("wortlaut") for x in g)


def test_sicherheit_aus_altem_buch():
    b = beispiel(antwort="Das Brot ist bei 230 °C gebacken und damit frei von Keimen; so bleibt es lange haltbar und gesund.")
    assert "sicherheit-aus-altem-buch" in pruefe(b, {**STUECK, "historisch": True})


def test_zahlen_tausender_und_aufzaehlung():
    assert zahlen("1.000 g und 2,5 l") == {1000.0, 2.5}
    assert zahlen("1. Mehl sieben\n2. Wasser") == set()
    assert laengster_wortlaut("abc def", "xx abc def yy") == 7


def test_zahlwoerter_werden_geprueft():
    assert {10.0, 4.0} <= zahlen("nach zehn Minuten, four days")
    g = pruefe(beispiel(antwort="Das Wasser macht 70 Prozent aus. Backe es zwanzig Minuten bei 230 °C, dann bei 200 °C."), STUECK)
    assert any(x.startswith("zahl-nicht-belegt:20") for x in g)


def test_antwort_verweist_auf_autor():
    b = beispiel(antwort="Der Autor nimmt 70 Prozent Wasser, das passt für ein Weissbrot bei 230 °C und später 200 °C.")
    assert "antwort-verweist-auf-text" in pruefe(b, STUECK)


# ---------- Umschreiben mit Überlegung (Versuch 03) ----------

from kochassistent.destillation import begruendet  # noqa: E402

STUECK_U = {"text": "Den Teig 20 Minuten bei 180 Grad backen. Bei zu heissem Ofen fällt der Biskuit zusammen.",
            "historisch": False}
B_U = {"frage": "Warum fällt mein Biskuit zusammen?", "denkweg": [{"text": "x", "art": "beleg"}]}


def test_umschrift_besteht():
    neu = {"ueberlegung": "Ist der Ofen zu heiss, bildet sich die Kruste, bevor der Schaum innen stabil ist.",
           "antwort": "Backe ihn 20 Minuten bei 180 Grad."}
    assert begruendet.pruefe_neu(B_U, neu, STUECK_U) == []
    assert begruendet.zusammensetzen(neu["ueberlegung"], neu["antwort"]).startswith("**Überlegung:**")


def test_umschrift_verwirft_neue_zahl_und_verweis():
    neu = {"ueberlegung": "Laut dem Text bildet sich bei zu viel Hitze die Kruste zu früh, das ist bekannt.",
           "antwort": "Backe ihn 25 Minuten bei 170 Grad."}
    g = begruendet.pruefe_neu(B_U, neu, STUECK_U)
    assert any(x.startswith("zahl-nicht-belegt") for x in g) and "verweist-auf-text" in g


def test_umschrift_verwirft_frage_mit_anleitungsbezug():
    neu = {"ueberlegung": "Ist der Ofen zu heiss, bildet sich die Kruste, bevor der Schaum innen stabil ist.",
           "antwort": "Backe ihn 20 Minuten bei 180 Grad."}
    b = {**B_U, "frage": "Was sagt die Anleitung dazu, wenn der Biskuit zusammenfällt?"}
    assert "frage-verweist-auf-text" in begruendet.pruefe_neu(b, neu, STUECK_U)
