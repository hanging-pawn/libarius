"""Angenommene Beispiele in begründete Antworten umschreiben: erst Überlegung, dann Antwort (Versuch 03, LIBAR-117).

Versuch 02 lernte nur Kurzantworten; der gespeicherte Denkweg gibt fast nur die Belegstelle wieder, oft im Wortlaut
und mit «die Passage …». Hier formt der Lehrer aus Frage, Kurzantwort, Stützen und Kernaussage eine Antwort, die das
Warum erklärt. Neue Fakten sind verboten; dieselben Prüfungen wie bei der Erzeugung laufen auf dem neuen Text, dazu
der Lehrer-Richter gegen die Passage. Verworfen wird, nicht nachgebessert (REQ-013).

  umschreiben  --aus v02 --ziel v03 [--parallel 4] [--grenze N]   fortsetzbar über erledigt.txt (Beispiel-IDs)
  danach       qa bericht / qa export mit --aus v03 (gleiches Format wie v02)
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import threading
from pathlib import Path

from kochassistent.destillation.qa import (MAX_WORTLAUT, RICHTER, SICHERHEIT, SYSTEM, TEXTBEZUG, json_aus,
                                           laengster_wortlaut, rechnung_pruefen, schweiz, zahlen)

AUFTRAG = """Eine Person fragt einen Kochassistenten. Schreibe die Antwort neu, so dass sie das Warum erklärt.

FRAGE: {frage}
KURZANTWORT: {antwort}
KERNAUSSAGE: {kern}
STÜTZEN:
{stuetzen}

Schreibe zwei Teile:
- "ueberlegung": 1 bis 3 Sätze. Erkläre den Grund: Ursache, Prinzip oder Rechnung, die zur Antwort führt. Bei
  Mengen und Verhältnissen die Rechnung mit den Zahlen zeigen.
- "antwort": 1 bis 3 Sätze. Das Ergebnis oder was die Person konkret tun soll.

Regeln:
- Nur was in Kurzantwort, Kernaussage und Stützen steht. Kein eigenes Wissen, keine neuen Zahlen, Zeiten oder Temperaturen.
- Eigene Worte; keine Sätze aus den Stützen übernehmen.
- Kein Verweis auf Text, Passage, Quelle, Buch, Autor oder Studie. Erkläre es, als wüsstest du es.
- Sprich die Person mit «du» an. Schweizer Schreibweise: ss statt ß.
- Zahlen, Einheiten und Währungen genau wie in der Kurzantwort oder den Stützen.

Antwort nur als JSON: {{"ueberlegung": "...", "antwort": "..."}}"""

VERWEIS = TEXTBEZUG.pattern + r"|\b(die|der|diese|dieser) (Passage|Text|Abschnitt)\b"
# Fragen wie «Was sagt die Anleitung dazu?» setzen einen Text voraus, den die fragende Person nicht hat
FRAGE_VERWEIS = TEXTBEZUG.pattern + (r"|\b(laut|gemäss|nach) (der |dem )?(Anleitung|Rezept)\b"
                                     r"|was (sagt|empfiehlt) (die|das) (Anleitung|Rezept)")


def zusammensetzen(ueberlegung: str, antwort: str) -> str:
    return f"**Überlegung:** {ueberlegung.strip()}\n\n**Antwort:** {antwort.strip()}"


def pruefe_neu(b: dict, neu: dict, stueck: dict) -> list[str]:
    """Gründe zum Verwerfen der umgeschriebenen Antwort; leere Liste = besteht."""
    import re
    u, a = (schweiz(str(neu.get(k, "")).strip()) for k in ("ueberlegung", "antwort"))
    if not u or not a:
        return ["fehlt:" + ("ueberlegung" if not u else "antwort")]
    neu["ueberlegung"], neu["antwort"] = u, a
    text = u + " " + a
    gruende = ["frage-verweist-auf-text"] if re.search(FRAGE_VERWEIS, b["frage"], re.I) else []
    erlaubt = zahlen(stueck["text"]) | zahlen(b["frage"])
    for s in b["denkweg"]:
        if s.get("art") == "rechnung":
            erlaubt |= rechnung_pruefen(str(s.get("rechnung", "")))[1]
    if fremde := sorted(zahlen(text) - erlaubt):
        gruende.append("zahl-nicht-belegt:" + ",".join(f"{z:g}" for z in fremde[:5]))  # REQ-035
    if (n := laengster_wortlaut(text, stueck["text"])) > MAX_WORTLAUT:
        gruende.append(f"wortlaut:{n}")  # REQ-105
    if re.search(VERWEIS, text, re.I):
        gruende.append("verweist-auf-text")
    if stueck["historisch"] and SICHERHEIT.search(text):
        gruende.append("sicherheit-aus-altem-buch")  # REQ-008
    if len(u) < 40:
        gruende.append("ueberlegung-zu-kurz")
    if len(text) > 1400:
        gruende.append("zu-lang")
    return gruende


def verarbeite(b: dict, stueck: dict, chat) -> tuple[dict | None, dict | None]:
    stuetzen = "\n".join(f"- {s['text']}" + (f" (Rechnung: {s['rechnung']})" if s.get("rechnung") else "")
                         for s in b["denkweg"])
    try:
        neu = json_aus(chat([{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": AUFTRAG.format(frage=b["frage"], antwort=b["antwort"],
                                                                       kern=b["beleg"]["aussage"], stuetzen=stuetzen)}],
                            temperatur=0.4, max_tokens=700, json_modus=True))
    except Exception as exc:  # Lehrer nicht erreichbar: nicht als erledigt markieren
        return None, {"id": b["id"], "gruende": [f"lehrer-fehler:{type(exc).__name__}"]}
    gruende = pruefe_neu(b, neu, stueck)
    urteil = None
    if not gruende:
        try:
            urteil = json_aus(chat([{"role": "user", "content": RICHTER.format(
                text=stueck["text"], frage=b["frage"], antwort=neu["ueberlegung"] + " " + neu["antwort"])}],
                temperatur=0.0, max_tokens=200, json_modus=True))
        except Exception as exc:
            urteil = {"gestuetzt": False, "grund": f"richter-fehler:{type(exc).__name__}"}
        if urteil.get("gestuetzt") is not True:
            gruende.append("richter:nicht-gestuetzt")  # REQ-010
    if gruende:
        return None, {"id": b["id"], "quelle": b["quelle"], "frage": b["frage"], "neu": neu, "richter": urteil,
                      "gruende": gruende}
    return {**b, "antwort_kurz": b["antwort"], "antwort": zusammensetzen(neu["ueberlegung"], neu["antwort"]),
            "ueberlegung": neu["ueberlegung"], "pruefung": {**b["pruefung"], "umschrift_richter": urteil}}, None


def umschreiben(aus: Path, ziel: Path, parallel: int, grenze: int | None) -> None:
    from kochassistent.studio_api import chat
    stuecke = {s["stueck"]: s for s in map(json.loads, open(aus / "stuecke.jsonl", encoding="utf-8"))}
    beispiele = list({b["id"]: b for b in map(json.loads, open(aus / "beispiele.jsonl", encoding="utf-8"))}.values())
    ziel.mkdir(parents=True, exist_ok=True)
    log = ziel / "erledigt.txt"
    erledigt = set(log.read_text().split()) if log.exists() else set()
    offen = [b for b in beispiele if b["id"] not in erledigt][: grenze or None]
    print(f"{len(offen)} offene Beispiele (schon erledigt: {len(erledigt)})", flush=True)
    sperre = threading.Lock()
    f_gut, f_schlecht, f_log = (open(ziel / n, "a", encoding="utf-8")
                                for n in ("beispiele.jsonl", "verworfen.jsonl", "erledigt.txt"))
    n = collections.Counter()
    with cf.ThreadPoolExecutor(parallel) as pool:
        zukunft = {pool.submit(verarbeite, b, stuecke[b["stueck"]], chat): b for b in offen}
        for i, z in enumerate(cf.as_completed(zukunft), 1):
            gut, schlecht = z.result()
            with sperre:
                if gut:
                    f_gut.write(json.dumps(gut, ensure_ascii=False) + "\n"); n["gut"] += 1
                if schlecht:
                    f_schlecht.write(json.dumps(schlecht, ensure_ascii=False) + "\n"); n["schlecht"] += 1
                if not (schlecht and any(g.startswith("lehrer-fehler") for g in schlecht["gruende"])):
                    f_log.write(zukunft[z]["id"] + "\n")
                for f in (f_gut, f_schlecht, f_log):
                    f.flush()
            if i % 20 == 0 or i == len(offen):
                print(f"{i}/{len(offen)} · {n['gut']} angenommen · {n['schlecht']} verworfen", flush=True)
    # Für qa bericht/export: Stücke mitführen
    if not (ziel / "stuecke.jsonl").exists():
        (ziel / "stuecke.jsonl").write_text((aus / "stuecke.jsonl").read_text(encoding="utf-8"), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    u = sub.add_parser("umschreiben")
    u.add_argument("--aus", type=Path, required=True); u.add_argument("--ziel", type=Path, required=True)
    u.add_argument("--parallel", type=int, default=4); u.add_argument("--grenze", type=int)
    a = ap.parse_args(argv)
    umschreiben(a.aus, a.ziel, a.parallel, a.grenze)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
