"""Frage-Antwort-Paare aus Korpus-Stücken destillieren (Versuch 02, Vorstufe zu LIBAR-113).

Ein lokales Lehrer-Modell in der Unsloth-Studio-App formuliert je Stück 0–3 Beispiele, nur aus diesem
Stück. Jedes Beispiel durchläuft automatische Prüfungen, danach prüft das Lehrer-Modell in einem zweiten
Durchgang, ob die Antwort ganz in der Passage steht. Was eine Prüfung nicht besteht, wird verworfen,
nicht angepasst (REQ-013).

  auswahl   Stücke aus daten/korpus/<v>/ wählen → <aus>/stuecke.jsonl
  erzeugen  Beispiele erzeugen und prüfen → <aus>/beispiele.jsonl, verworfen.jsonl (fortsetzbar)
  bericht   Datenbericht: Anzahl je Aufgabe, Bereich, Quellenart, Rechtsstatus, Verwerfgründe
  export    Chat-Format für Unsloth, Trennung nach Quelle (REQ-019) → train.jsonl, valid.jsonl

Prüfungen: Pflichtfelder und Werte · Schweizer Schreibweise (ß → ss, REQ-104) · jede Zahl der Antwort
steht in der Passage, in der Frage oder ist Ergebnis einer nachgerechneten Rechnung (REQ-015, REQ-035) ·
kein Wortlaut über 60 Zeichen aus der Passage (REQ-105) · Frage verweist nicht auf «den Text» ·
kein Sicherheits- oder Haltbarkeitswissen aus historischen Büchern (REQ-008) · Lehrer bestätigt,
dass die Antwort in der Passage steht (REQ-010, REQ-013).
"""
from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures as cf
import csv
import hashlib
import json
import operator
import random
import re
import sys
import threading
from difflib import SequenceMatcher
from pathlib import Path

AUFGABEN = {"wissen", "fehlerbild", "bewerten", "aendern"}
BEREICHE = {"backen", "kochen"}
BELEG_ARTEN = {"rezept", "technik", "grundverhaeltnis", "fehlerbild", "warenkunde", "befund"}
STUETZEN = {"beleg", "rechnung", "eingabe"}
MAX_WORTLAUT = 60

TEXTBEZUG = re.compile(r"\b(im|laut|gemäss|gemäß|dem|diesem|der|dieser|die|diese)\s+(Text|Abschnitt|Passage|Artikel|"
                       r"Buch|Quelle|Studie|Kapitel|Auszug)\b|\bder Autor|\bdie Autorin|\bwie beschrieben\b", re.I)
SICHERHEIT = re.compile(r"Salmonell|Listeri|Bakteri|Keim|Erreger|Toxin|Gift|Vergiftung|Schimmel|Botulismus|"
                        r"Lebensmittelsicherheit|haltbar|Haltbar|konservier|Konservier|einmach|Einmach|Gesundheit|"
                        r"gesund|Krankheit|Kerntemperatur|verdau|nahrhaft|Nährwert|Zerfall|zersetz|verderb|verdorb|"
                        r"faul|Fäulnis|aufbewahr|lagern|Lagerung", re.I)
WAEHRUNG = re.compile(r"Franken|\bCHF\b|\bFr\.", re.I)
ZAHL = re.compile(r"(?<![\w.,])\d{1,3}(?:[.’']\d{3})+(?![\d,])|\d+(?:[.,]\d+)?")
AUFZAEHLUNG = re.compile(r"(?m)^\s*\d+[.)]\s")
# Zahlwörter (de, en, fr) für die Zahlenprüfung; nicht «ein» (Artikel), «sieben» (Mehl sieben), «halb» (halbe Stunde)
ZAHLWOERTER = {
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "acht": 8, "neun": 9, "zehn": 10, "elf": 11,
    "zwölf": 12, "fünfzehn": 15, "zwanzig": 20, "dreissig": 30, "dreißig": 30, "vierzig": 40, "fünfzig": 50,
    "sechzig": 60, "hundert": 100, "tausend": 1000, "eineinhalb": 1.5, "anderthalb": 1.5, "zweieinhalb": 2.5,
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "hundred": 100,
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "dix": 10, "vingt": 20, "trente": 30,
    "dozen": 12, "dutzend": 12,
}
ZAHLWORT = re.compile(r"\b(" + "|".join(sorted(ZAHLWOERTER, key=len, reverse=True)) + r")\b", re.I)


# ---------- Quellen und Auswahl ----------

def quellenart(pfad: str) -> tuple[str, str, str | None, bool]:
    """(art, rechtsstatus, lizenzhinweis, historisch) aus dem Ablagepfad der Quelle."""
    if "cooking science" in pfad:  # von Gianluca bezogene Paper, Lizenz je Artikel nicht geprüft
        return "paper", "geschuetzt", "ungeprueft", False
    rel = pfad.split("Kochassistent-Quellen/")[-1]
    nc_nd = "/nc-nd/" in f"/{rel}"
    if rel.startswith("buecher/"):
        return "buch-historisch", "gemeinfrei", None, True
    art = "artikel" if rel.startswith("artikel") else "leitfaden" if rel.startswith("leitfaeden") else "lehrbuch"
    return art, "offen", "nc-nd" if nc_nd else None, False


def auswahl(korpus: Path, aus: Path, max_je_buch: int, seed: int) -> None:
    pfade = {}
    for r in csv.DictReader(open(korpus / "bericht.tsv", encoding="utf-8"), delimiter="\t"):
        if r["status"] == "aufgenommen":
            pfade[r["datei"].rsplit("/", 1)[-1]] = r["datei"]
    je_quelle = collections.defaultdict(list)
    for zeile in open(korpus / "korpus_meta.jsonl", encoding="utf-8"):
        s = json.loads(zeile)
        art, status, lizenz, hist = quellenart(pfade[s["datei"]])
        sid = hashlib.sha1(s["text"].encode()).hexdigest()[:12]
        je_quelle[s["quelle"]].append({"stueck": sid, "quelle": s["quelle"], "datei": s["datei"], "stelle": s["fundstelle"],
                                       "art": art, "rechtsstatus": status, "lizenz": lizenz, "historisch": hist,
                                       "text": s["text"]})
    rnd = random.Random(seed)
    gewaehlt = []
    for q, liste in sorted(je_quelle.items()):
        if liste[0]["historisch"] and len(liste) > max_je_buch:
            liste = rnd.sample(liste, max_je_buch)  # alte Bücher drosseln, sonst dominieren sie (Versuch 01)
        gewaehlt += liste
    rnd.shuffle(gewaehlt)
    aus.mkdir(parents=True, exist_ok=True)
    with open(aus / "stuecke.jsonl", "w", encoding="utf-8") as f:
        for s in gewaehlt:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    z = collections.Counter(s["art"] for s in gewaehlt)
    print(f"{len(gewaehlt)} Stücke aus {len(je_quelle)} Quellen: " + ", ".join(f"{k} {v}" for k, v in z.most_common()))


# ---------- Prüfungen (ohne Modell) ----------

def zahl_norm(s: str) -> float | None:
    s = s.replace("’", "").replace("'", "")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return round(float(s.replace(",", ".")), 4)
    except ValueError:
        return None


def zahlen(text: str) -> set[float]:
    text = AUFZAEHLUNG.sub(" ", text)
    werte = {z for z in (zahl_norm(m) for m in ZAHL.findall(text)) if z is not None}
    return werte | {float(ZAHLWOERTER[w.lower()]) for w in ZAHLWORT.findall(text)}


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _rechne(knoten):
    if isinstance(knoten, ast.Expression):
        return _rechne(knoten.body)
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, (int, float)):
        return float(knoten.value)
    if isinstance(knoten, ast.BinOp) and type(knoten.op) in _OPS:
        return _OPS[type(knoten.op)](_rechne(knoten.left), _rechne(knoten.right))
    if isinstance(knoten, ast.UnaryOp) and isinstance(knoten.op, ast.USub):
        return -_rechne(knoten.operand)
    raise ValueError("nicht erlaubt")


def rechnung_pruefen(rechnung: str) -> tuple[bool, set[float]]:
    """«720 / 1000 = 0.72» → (stimmt, {beteiligte Zahlen}). Toleranz 1 % für gerundete Ergebnisse."""
    r = rechnung.replace("×", "*").replace("·", "*").replace(":", "/").replace("−", "-").replace("–", "-")
    r = re.sub(r"(?<=\d),(?=\d)", ".", r)
    r = re.sub(r"[^\d.+\-*/()= ]", " ", r)  # Einheiten und % weg
    if r.count("=") != 1:
        return False, set()
    links, rechts = r.split("=")
    try:
        soll = _rechne(ast.parse(links.strip(), mode="eval"))
        ist = float(rechts.strip())
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
        return False, set()
    ok = abs(soll - ist) <= max(0.01 * abs(soll), 0.005)
    zs = zahlen(rechts) | {round(soll, 4)}
    zs |= {round(ist * 100, 4), round(ist / 100, 4)}  # 0.8 ↔ 80 %
    return ok, zs


def laengster_wortlaut(a: str, b: str) -> int:
    a, b = re.sub(r"\s+", " ", a.lower()), re.sub(r"\s+", " ", b.lower())
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size


def schweiz(s: str) -> str:
    return s.replace("ß", "ss")


def pruefe(b: dict, stueck: dict) -> list[str]:
    """Gründe zum Verwerfen; leere Liste = besteht. Normalisiert ß → ss am Beispiel selbst."""
    gruende = []
    for feld in ("aufgabe", "bereich", "frage", "antwort", "denkweg", "beleg"):
        if not b.get(feld):
            gruende.append(f"fehlt:{feld}")
    if gruende:
        return gruende
    if b["aufgabe"] not in AUFGABEN:
        gruende.append("aufgabe")
    if b["bereich"] not in BEREICHE:
        gruende.append("bereich")
    beleg = b["beleg"] if isinstance(b["beleg"], dict) else {}
    if beleg.get("art") not in BELEG_ARTEN or not beleg.get("aussage"):
        gruende.append("beleg")
    elif beleg["art"] == "befund" and not beleg.get("bedingungen"):
        gruende.append("befund-ohne-bedingungen")  # REQ-065
    for k in ("frage", "antwort"):
        b[k] = schweiz(str(b[k]).strip())
    if isinstance(beleg, dict) and beleg.get("aussage"):
        beleg["aussage"] = schweiz(beleg["aussage"])
    if not isinstance(b["denkweg"], list) or not all(isinstance(s, dict) for s in b["denkweg"]):
        return gruende + ["denkweg"]
    erlaubt = zahlen(stueck["text"]) | zahlen(b["frage"])
    for s in b["denkweg"]:
        s["text"] = schweiz(str(s.get("text", "")))
        if s.get("art") not in STUETZEN:
            gruende.append("stuetze")
        elif s["art"] == "rechnung":
            ok, zs = rechnung_pruefen(str(s.get("rechnung", "")))
            if not ok:
                gruende.append("rechnung-falsch")  # REQ-015
            erlaubt |= zs
    fremde = sorted(zahlen(b["antwort"] + " " + " ".join(s["text"] for s in b["denkweg"])) - erlaubt)
    if fremde:
        gruende.append("zahl-nicht-belegt:" + ",".join(f"{z:g}" for z in fremde[:5]))  # REQ-035
    if (n := laengster_wortlaut(b["antwort"], stueck["text"])) > MAX_WORTLAUT:
        gruende.append(f"wortlaut:{n}")  # REQ-105
    if TEXTBEZUG.search(b["frage"]):
        gruende.append("frage-verweist-auf-text")
    if re.search(r"\bder Autor|\bdie Autorin|\b(die|der|diese|dieser) (Passage|Text|Abschnitt)\b", b["antwort"], re.I):
        gruende.append("antwort-verweist-auf-text")
    if WAEHRUNG.search(b["frage"] + " " + b["antwort"]) and not WAEHRUNG.search(stueck["text"]):
        gruende.append("waehrung-umgedeutet")
    if stueck["historisch"] and SICHERHEIT.search(b["frage"] + " " + b["antwort"]):
        gruende.append("sicherheit-aus-altem-buch")  # REQ-008
    if len(b["antwort"]) < 60:
        gruende.append("antwort-zu-kurz")
    return gruende


# ---------- Lehrer-Modell ----------

SYSTEM = ("Du bist Redaktor für einen Kochassistenten. Du formulierst Lernbeispiele ausschliesslich aus der Passage, "
          "die du bekommst. Dein eigenes Wissen ist keine Quelle: Was nicht in der Passage steht, schreibst du nicht. "
          "Du antwortest nur mit JSON.")

ARTBESCHREIBUNG = {
    "buch-historisch": "historisches Kochbuch (19. oder frühes 20. Jahrhundert), alte Masse und Schreibweise",
    "artikel": "begutachteter Fachartikel", "paper": "begutachteter Fachartikel",
    "leitfaden": "Leitfaden einer Behörde", "lehrbuch": "offenes Lehrbuch für Köche und Bäcker",
}

AUFTRAG = """Quelle: {art}. Fundstelle: {stelle}.

PASSAGE
\"\"\"
{text}
\"\"\"

Erzeuge 0 bis 3 Lernbeispiele aus dieser Passage. Lieber keines als ein schwaches. Geeignet sind Inhalte, die eine
Köchin oder ein Hobbybäcker heute brauchen kann: Verhältnisse und Mengen, Techniken und ihr Zweck, Fehlerbilder
(Fehler → Ursache → Abhilfe), Zeiten und Temperaturen, Warenkunde, Befunde aus Versuchen, Risiken beim Zubereiten.
Ungeeignet: Inhaltsverzeichnisse, Literaturangaben, Methodik von Studien (Labor, Prüfpersonen, Statistik), Bauvorschriften
und Einrichtung von Betrieben (Lampen, Fenster, Böden, Schädlingsgeräte), Verwaltung, Werbung, reine Rezeptlisten ohne Erklärung.

Mische die Aufgaben: Wenn die Passage es hergibt, ist mindestens ein Beispiel vom Typ "fehlerbild", "bewerten" oder
"aendern". Ein "bewerten" oder "aendern" stellt ein konkretes Rezept oder konkrete Mengen in die Frage.

Regeln:
- aufgabe: "wissen" (Regel, Verhältnis, Technik erklären), "fehlerbild" (Fehler → Ursache → Abhilfe), "bewerten"
  (die Frage nennt Mengen oder ein kurzes Rezept aus der Passage, die Antwort beurteilt es) oder "aendern"
  (Antwort nennt Änderung, erwartete Wirkung und Begründung).
- bereich: "backen" oder "kochen".
- frage: so, wie sie jemand in der Küche stellt; ohne Bezug auf «den Text», «die Studie» oder «das Buch»; für sich verständlich.
- antwort: Deutsch, heutige Rechtschreibung, Schweizer Schreibweise (ss statt ß), 2 bis 6 Sätze, in eigenen Worten –
  übernimm keine Sätze aus der Passage. Nur Aussagen, die in der Passage stehen; kein Hinweis auf Autor, Text oder Studie.
  Zahlen, Einheiten und Währungen genau wie in der Passage, als Ziffern; rechne nicht um, ausser als Rechnung im Denkweg.
  Die Antwort darf sich nicht selbst widersprechen.
- Befunde aus Versuchen: nenne die Bedingungen (Produkt, Menge, Temperatur, Verfahren) und verallgemeinere nicht darüber hinaus.
{zusatz}- denkweg: 1 bis 4 Schritte. Jeder Schritt hat "art": "beleg" (Aussage aus der Passage), "eingabe" (Angabe aus der
  Frage) oder "rechnung" mit Feld "rechnung" als nachrechenbarem Ausdruck, z. B. "400 / 500 = 0.8".
- beleg: "art" eine von rezept, technik, grundverhaeltnis, fehlerbild, warenkunde, befund; "aussage" in eigenen Worten;
  bei befund zusätzlich "bedingungen".

Antwort nur als JSON:
{{"beispiele": [{{"aufgabe": "...", "bereich": "...", "frage": "...", "antwort": "...",
  "denkweg": [{{"text": "...", "art": "beleg"}}, {{"text": "...", "art": "rechnung", "rechnung": "..."}}],
  "beleg": {{"art": "...", "aussage": "...", "bedingungen": "..."}}}}]}}"""

ZUSATZ_HISTORISCH = ("- Historisches Buch: keine Beispiele zu Lebensmittelsicherheit, Haltbarmachen, Einmachen oder Gesundheit "
                     "(veraltet). Alte Masse (Pfund, Lot, Quart …) unverändert übernehmen.\n")

RICHTER = """PASSAGE
\"\"\"
{text}
\"\"\"

FRAGE: {frage}
ANTWORT: {antwort}

Prüfe streng: Steht jede Aussage der Antwort in der Passage oder folgt sie direkt daraus? Allgemeinwissen, das nicht in der
Passage steht, zählt als nicht gestützt. Stimmen alle Zahlen und Bedingungen mit der Passage überein?
Antwort nur als JSON: {{"gestuetzt": true oder false, "grund": "ein Satz"}}"""


def json_aus(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?|\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


def verarbeite(stueck: dict, chat) -> tuple[list[dict], list[dict]]:
    auftrag = AUFTRAG.format(art=ARTBESCHREIBUNG[stueck["art"]], stelle=stueck["stelle"], text=stueck["text"],
                             zusatz=ZUSATZ_HISTORISCH if stueck["historisch"] else "")
    try:
        roh = json_aus(chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": auftrag}],
                            temperatur=0.4, max_tokens=2500, json_modus=True))
    except Exception as exc:  # Netz, Zeitüberschreitung, kaputtes JSON: festhalten, weiter
        return [], [{"stueck": stueck["stueck"], "gruende": [f"lehrer-fehler:{type(exc).__name__}"]}]
    gut, schlecht = [], []
    for i, b in enumerate(roh.get("beispiele") or []):
        if not isinstance(b, dict):
            continue
        gruende = pruefe(b, stueck)
        urteil = None
        if not gruende:
            try:
                urteil = json_aus(chat([{"role": "user", "content": RICHTER.format(text=stueck["text"], frage=b["frage"],
                                                                                     antwort=b["antwort"])}],
                                       temperatur=0.0, max_tokens=200, json_modus=True))
            except Exception as exc:
                urteil = {"gestuetzt": False, "grund": f"richter-fehler:{type(exc).__name__}"}
            if urteil.get("gestuetzt") is not True:
                gruende.append("richter:nicht-gestuetzt")
        datensatz = {
            "id": f"{stueck['stueck']}-{i}", "stueck": stueck["stueck"], "quelle": stueck["quelle"],
            "stelle": stueck["stelle"], "quellenart": stueck["art"], "rechtsstatus": stueck["rechtsstatus"],
            "lizenz": stueck["lizenz"], **{k: b.get(k) for k in ("aufgabe", "bereich", "frage", "antwort", "denkweg", "beleg")},
            "pruefung": {"loesungAusQuelle": not gruende, "richter": urteil, "status": "automatisch" if not gruende else "verworfen"},
        }
        (schlecht if gruende else gut).append({**datensatz, "gruende": gruende} if gruende else datensatz)
    if not roh.get("beispiele"):
        schlecht.append({"stueck": stueck["stueck"], "gruende": ["keine-beispiele"]})
    return gut, schlecht


def erzeugen(aus: Path, parallel: int, grenze: int | None) -> None:
    from kochassistent.studio_api import chat
    erledigt = set()
    log = aus / "erledigt.txt"
    if log.exists():
        erledigt = set(log.read_text().split())
    stuecke = [json.loads(z) for z in open(aus / "stuecke.jsonl", encoding="utf-8")]
    offen = [s for s in stuecke if s["stueck"] not in erledigt][: grenze or None]
    print(f"{len(offen)} offene Stücke (schon erledigt: {len(erledigt)})", flush=True)
    sperre = threading.Lock()
    f_gut = open(aus / "beispiele.jsonl", "a", encoding="utf-8")
    f_schlecht = open(aus / "verworfen.jsonl", "a", encoding="utf-8")
    f_log = open(log, "a")
    n_gut = n_schlecht = 0
    with cf.ThreadPoolExecutor(parallel) as pool:
        zukunft = {pool.submit(verarbeite, s, chat): s for s in offen}
        for i, z in enumerate(cf.as_completed(zukunft), 1):
            gut, schlecht = z.result()
            with sperre:
                for b in gut:
                    f_gut.write(json.dumps(b, ensure_ascii=False) + "\n")
                for b in schlecht:
                    f_schlecht.write(json.dumps(b, ensure_ascii=False) + "\n")
                if not any("lehrer-fehler" in g for b in schlecht for g in b["gruende"]):
                    f_log.write(zukunft[z]["stueck"] + "\n")  # Lehrer-Fehler beim nächsten Lauf wiederholen
                for f in (f_gut, f_schlecht, f_log):
                    f.flush()
                n_gut += len(gut); n_schlecht += sum(1 for b in schlecht if "id" in b)
            if i % 10 == 0 or i == len(offen):
                print(f"{i}/{len(offen)} Stücke · {n_gut} Beispiele angenommen · {n_schlecht} verworfen", flush=True)


# ---------- Bericht und Export ----------

def bericht(aus: Path) -> None:
    gut = [json.loads(z) for z in open(aus / "beispiele.jsonl", encoding="utf-8")]
    schlecht = [json.loads(z) for z in open(aus / "verworfen.jsonl", encoding="utf-8")]
    beisp = [b for b in schlecht if "id" in b]
    print(f"angenommen {len(gut)} · verworfen {len(beisp)} Beispiele · Stücke ohne Beispiel "
          f"{sum(1 for b in schlecht if b['gruende'] == ['keine-beispiele'])}")
    for feld in ("aufgabe", "bereich", "quellenart", "rechtsstatus", "lizenz"):
        print(f"{feld}: " + ", ".join(f"{k} {v} ({v / max(1, len(gut)):.0%})" for k, v in collections.Counter(b[feld] for b in gut).most_common()))
    quellen = collections.Counter(b["quelle"] for b in gut)
    if quellen:
        q, n = quellen.most_common(1)[0]
        print(f"Quellen: {len(quellen)}, grösste {q} mit {n / len(gut):.0%} (REQ-006: ≤ 40 %)")
    gr = collections.Counter(g.split(":")[0] for b in schlecht for g in b["gruende"])
    print("Verwerfgründe: " + ", ".join(f"{k} {v}" for k, v in gr.most_common()))


def export(aus: Path, ziel: Path, valid_anteil: float, ohne: list[str]) -> None:
    gut = [json.loads(z) for z in open(aus / "beispiele.jsonl", encoding="utf-8")]
    gut = [b for b in gut if b["rechtsstatus"] not in ohne and (b["lizenz"] or "") not in ohne]
    gut = list({b["id"]: b for b in reversed(gut)}.values())[::-1]  # doppelte nach Abbruch und Fortsetzen
    ziel.mkdir(parents=True, exist_ok=True)
    n = collections.Counter()
    with open(ziel / "train.jsonl", "w", encoding="utf-8") as t, open(ziel / "valid.jsonl", "w", encoding="utf-8") as v:
        for b in gut:
            # Trennung nach Quelle (REQ-019): eine Quelle liegt ganz in train oder ganz in valid
            teil = v if int(hashlib.sha1(b["quelle"].encode()).hexdigest(), 16) % 1000 < valid_anteil * 1000 else t
            teil.write(json.dumps({"messages": [{"role": "user", "content": b["frage"]},
                                                {"role": "assistant", "content": b["antwort"]}]}, ensure_ascii=False) + "\n")
            n["valid" if teil is v else "train"] += 1
    print(f"train {n['train']} · valid {n['valid']} → {ziel}" + (f" (ohne {', '.join(ohne)})" if ohne else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    a = sub.add_parser("auswahl"); a.add_argument("--korpus", type=Path, required=True); a.add_argument("--aus", type=Path, required=True)
    a.add_argument("--max-je-buch", type=int, default=30); a.add_argument("--seed", type=int, default=3407)
    e = sub.add_parser("erzeugen"); e.add_argument("--aus", type=Path, required=True)
    e.add_argument("--parallel", type=int, default=4); e.add_argument("--grenze", type=int)
    b = sub.add_parser("bericht"); b.add_argument("--aus", type=Path, required=True)
    x = sub.add_parser("export"); x.add_argument("--aus", type=Path, required=True); x.add_argument("--ziel", type=Path, required=True)
    x.add_argument("--valid-anteil", type=float, default=0.06)
    x.add_argument("--ohne", nargs="*", default=[], help="Rechtsstatus oder Lizenz ausschliessen, z. B. geschuetzt nc-nd")
    a = ap.parse_args(argv)
    if a.befehl == "auswahl":
        auswahl(a.korpus, a.aus, a.max_je_buch, a.seed)
    elif a.befehl == "erzeugen":
        erzeugen(a.aus, a.parallel, a.grenze)
    elif a.befehl == "bericht":
        bericht(a.aus)
    else:
        export(a.aus, a.ziel, a.valid_anteil, a.ohne)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
