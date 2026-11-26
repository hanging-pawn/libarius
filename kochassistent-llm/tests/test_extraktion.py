"""Tests der Extraktion (LIBAR-106). Alle Texte sind erfunden, nicht aus einem Buch."""
import json
from collections import Counter
from pathlib import Path

import pytest

from kochassistent.extraktion import einheiten, klassifikation, ocr, schreibweise, tei, zahlen
from kochassistent.extraktion.pipeline import baue_abschnitt, extrahiere_tei

TABELLE = Path(__file__).resolve().parents[1] / "konfig" / "einheiten.json"

# Einheitswörter, die im Pilotbuch nach einer Zahl vorkommen (Erhebung LIBAR-106).
PILOT_EINHEITEN = [
    "Pfund", "Pfd.", "Loth", "Quentchen", "Gran", "Maß", "Schoppengläser", "Flaschen", "Scheffel",
    "Eßlöffel", "Löffel", "Theelöffel", "Tasse", "Tassen", "Obertasse", "Untertassen", "Weinglas", "Glas",
    "Becher", "Messerspitzen", "Zoll", "Elle", "Finger", "Grad Hitze", "Grad Tralles", "Sgr.", "Pfennige",
    "Dutzend",
]


# --- Einheitentabelle ---------------------------------------------------------------------

def test_tabelle_jede_einheit_hat_wert_oder_begruendung_und_herkunft():
    daten = json.loads(TABELLE.read_text("utf-8"))
    for e in daten["einheiten"]:
        assert e["herkunft"].strip(), e["id"]
        assert e["sicherheit"] in daten["sicherheit_stufen"], e["id"]
        if e["metrisch"] is None:
            assert e["sicherheit"] in ("kein_wert", "buch"), e["id"]
        else:
            assert e["metrisch"]["wert"] > 0 and e["metrisch"]["einheit"], e["id"]


def test_tabelle_deckt_alle_einheiten_des_pilotbuchs():
    assert einheiten.ungedeckte_einheiten(set(PILOT_EINHEITEN)) == set()


@pytest.mark.parametrize("text, einheit, wert, metrisch", [
    ("man nimmt ½ Pfund Butter", "pfund", 0.5, 233.856),
    ("dazu 4 Loth Zucker", "loth", 4, 58.464),
    ("1 ½ Pfund Mehl", "pfund", 1.5, 701.567),
    ("1½ Pfund Mehl", "pfund", 1.5, 701.567),
    ("Ein halbes Pfund Kalbfleisch", "pfund", 0.5, 233.856),
    ("Ein Viertel Maß Milch", "mass", 0.25, 286.25),
    ("2 Quentchen Zimt", "quentchen", 2, 7.308),
    ("3 Eßlöffel Rahm", "esslöffel", 3, 45.0),
    ("einen Zoll breit", "zoll", 1, 2.615),
])
def test_umrechnung(text, einheit, wert, metrisch):
    m = einheiten.finde_mengen(text, "G1")
    assert len(m) == 1
    assert m[0].einheit == einheit and m[0].wert == pytest.approx(wert)
    assert m[0].metrisch_wert == pytest.approx(metrisch, abs=0.01)
    assert m[0].original.strip() in text


def test_spanne_behaelt_beide_werte():
    m = einheiten.finde_mengen("4 bis 6 Loth Butter, 1—2 Tassen Wasser", "G1")
    assert [(x.einheit, x.wert, x.wert_bis) for x in m] == [("loth", 4, 6), ("tasse", 1, 2)]
    assert m[0].metrisch_wert_bis == pytest.approx(87.696)


def test_preis_wird_markiert_nicht_umgerechnet():
    m = einheiten.finde_mengen("für 1 Sgr. Weissbrot", "G1")
    assert m[0].metrisch_wert is None and m[0].markierung == "nicht_ueberfuehrbar_preis"


def test_ofenstufe_ohne_temperatur():
    m = einheiten.finde_mengen("bei 2 Grad Hitze backen", "G1")
    assert m[0].einheit == "grad_hitze" and m[0].metrisch_wert is None


def test_pfund_der_auflage_1858_ist_zollpfund():
    assert einheiten.finde_mengen("1 Pfund", "G1b")[0].metrisch_wert == 500.0


def test_finger_nur_als_mass():
    assert einheiten.finde_mengen("mit zwei Fingern greifen", "G1") == []
    assert einheiten.finde_mengen("zwei Finger breit abschneiden", "G1")[0].metrisch_wert == 4.0


# --- Schreibweise ----------------------------------------------------------------------------

def test_modernisierung_behaelt_zahlen():
    alt = "Man nimmt 2 Theile Waſſer, ½ Loth Zimmet, daß es gahr wird; 3 Theelöffel nöthig."
    neu = schreibweise.modernisiere(alt)
    assert "ſ" not in neu
    assert "Teile" in neu and "Zimt" in neu and "dass" in neu and "gar" in neu and "Teelöffel" in neu and "nötig" in neu
    assert zahlen.zahlen_muster(alt) == zahlen.zahlen_muster(neu)


def test_modernisierung_iren():
    assert schreibweise.modernisiere("passiren, garnirt, Wirt") == "passieren, garniert, Wirt"


# --- Klassifikation --------------------------------------------------------------------------

@pytest.mark.parametrize("titel, text, mengen, typ", [
    ("12. Apfelkuchen.", "Man nimmt 1 Pfund Mehl, ½ Pfund Butter und 4 Eier und backt es.", 3, "Rezept"),
    ("40. Schnee zu schlagen.", "Das Eiweiss wird in einer kalten Schüssel geschlagen, bis es steht.", 0, "Technik"),
    ("1. Vom Spicken.", "Man zieht den Speck mit der Nadel durch das Fleisch.", 0, "Technik"),
    ("3. Grog.", "Man vermischt 2 Teile Wasser mit einem Teil Rum.", 0, "Grundverhaeltnis"),
    ("2. Erkennungszeichen der frischen Fische.", "Frische Fische haben rote Kiemen.", 0, "Warenkunde"),
    ("5. Wenn der Teig misslingt.", "Ist der Teig zu weich, so gibt man Mehl hinzu.", 0, "Fehlerbild"),
    ("Ergebnis", "Die Studie hat gemessen, dass signifikant weniger Keime überleben.", 0, "Befund"),
])
def test_typen(titel, text, mengen, typ):
    assert klassifikation.klassifiziere(titel, text, mengen)[0] == typ


def test_speisefolge_ist_technik():
    assert klassifikation.klassifiziere("", "Suppe. Braten. Pudding.", 0, ["Anhang.", "Arrangements zu Gesellschaften"])[0] == "Technik"


def test_bereich():
    assert klassifikation.bereich(["Q. Backwerk."], "3. Mandeltorte.", ["Q. Backwerk"]) == "backen"
    assert klassifikation.bereich(["B. Suppen."], "7. Hefekuchen zur Suppe.", []) == "backen"
    assert klassifikation.bereich(["B. Suppen."], "7. Erbsensuppe.", []) == "kochen"


@pytest.mark.parametrize("kapitel, titel, text, markiert", [
    (["R. Vom Einmachen der Früchte."], "4. Kirschen.", "Kirschen mit Zucker.", True),
    (["B. Suppen."], "7. Suppe für Kranke.", "Eine leichte Brühe.", True),
    (["A. Regeln."], "1. Kochgeschirre.", "In kupfernen Kesseln bleibt die Speise gerne grün.", True),
    (["B. Suppen."], "8. Erbsensuppe.", "Erbsen werden weich gekocht.", False),
    (["B. Suppen."], "9. Brotsuppe.", "Ein gesundes Brot wird gerieben.", False),
])
def test_ueberholt(kapitel, titel, text, markiert):
    assert (klassifikation.ueberholt(kapitel, titel, text, ["R. Vom Einmachen"]) is not None) == markiert


def test_markierter_abschnitt_ist_nicht_trainingsfaehig():
    q = {"id": "T", "kurz": "Test", "ueberholt_kapitel": ["R. Vom Einmachen"], "backen_kapitel": []}
    s = baue_abschnitt(q, 1, "4. Kirschen.", ["R. Vom Einmachen der Früchte."], "4 Pfund Kirschen.", {"seite_von": "3", "seite_bis": "3"}, "transkription")
    assert s["ueberholt_pruefen"] and not s["training"]
    assert s["fundstelle_text"] == "Test, S. 3 · R. Vom Einmachen der Früchte. › 4. Kirschen."


# --- Zahlenprüfung ---------------------------------------------------------------------------

def test_zwei_zaehler_stimmen_ueberein():
    t = "Man nimmt 1 ½ Pfund, ¼ Maß, 12 Eier, 3½ Loth und 1—2 Stunden bei 2 Grad."
    assert zahlen.zahlen_muster(t) == zahlen.zahlen_zeichen(t) == Counter({"1.5": 1, "0.25": 1, "12": 1, "3.5": 1, "1": 1, "2": 2})


def test_abweichung():
    a, b = Counter({"2": 2, "1.5": 1}), Counter({"2": 1, "1": 1})
    assert zahlen.vergleiche(a, b)[0] in {("2", 2, 1), ("1.5", 1, 0), ("1", 0, 1)}
    assert zahlen.abweichung(a, b) == (3, 2)


# --- TEI-Leser -------------------------------------------------------------------------------

TEI_TEST = """<?xml version="1.0" encoding="utf-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/><text><front><pb facs="#f0001" n="[I]"/><p>Titel</p></front>
<body><pb facs="#f0010" n="1"/><div n="1"><head>A. Regeln.</head><lb/><p>Allgemeine Regel für die<lb/>
Küche mit 2 Theilen.</p><lb/>
<div n="2"><head>1. Ein Ku-<lb/>chen.</head><lb/><p>Man nimmt ½ Pfund Mehl und<lb/>
4 Loth Zu-<lb/>cker,<pb facs="#f0011" n="2"/><fw place="top" type="header">Regeln.</fw><lb/>
dann <choice><sic>Butterr</sic><corr>Butter</corr></choice> dazu.</p></div>
<div n="2"><head>2. Kurz.</head><p>x</p></div></div></body><back/></text></TEI>"""


@pytest.fixture
def tei_datei(tmp_path):
    p = tmp_path / "test.xml"
    p.write_text(TEI_TEST, "utf-8")
    return p


def test_tei_abschnitte_mit_fundstelle(tei_datei):
    leser = tei.lies(tei_datei)
    assert [r.titel for r in leser.abschnitte] == ["A. Regeln.", "1. Ein Kuchen."]
    regel, kuchen = leser.abschnitte
    assert regel.text == "Allgemeine Regel für die Küche mit 2 Theilen." and regel.kapitel == []
    assert kuchen.kapitel == ["A. Regeln."]
    assert kuchen.text == "Man nimmt ½ Pfund Mehl und 4 Loth Zucker, dann Butter dazu."
    assert (kuchen.seite_von, kuchen.seite_bis, kuchen.faks_von, kuchen.faks_bis) == ("1", "2", "f0010", "f0011")


def test_tei_zahlenwege_gleich(tei_datei):
    q = {"id": "T", "kurz": "Test", "ueberholt_kapitel": [], "backen_kapitel": []}
    abschnitte, pruefung = extrahiere_tei(q, tei_datei)
    assert pruefung["abweichend"] == 0 and pruefung["zahlen_gesamt"] == 5
    # «2. Kurz.» hat zu wenig Text und fällt weg: die Gegenprüfung meldet seine Titelzahl als fehlend.
    assert pruefung["ausgabe_gegen_quelle"]["abweichungen"] == [["2", 1, 2]]  # «2 Theilen» bleibt, «2. Kurz.» fehlt
    assert all(s["typ"] in klassifikation.TYPEN and s["bereich"] in klassifikation.BEREICHE and s["fundstelle"]["seite_von"] for s in abschnitte)


# --- OCR-Nachkorrektur -----------------------------------------------------------------------

def test_fraktur_korrektur_behaelt_zahlen():
    roh = "Man nimmt 1½ Bfund unb bie Butter nad) 3 Stunden; bas ift gut. 18 Eier"
    neu = ocr.fraktur_korrigiere(roh)
    assert "und die Butter nach 3 Stunden; das ist gut" in neu
    assert ocr.fraktur_korrigiere("ba8 Mehl") == "das Mehl"  # «8» mitten im Wort ist ein gelesenes «s»
    assert zahlen.zahlen_muster(roh) == zahlen.zahlen_muster(neu)
    assert ocr.fraktur_quote(neu) < ocr.fraktur_quote(roh)
