"""TEI-P5-Transkription (Deutsches Textarchiv) in Rohabschnitte mit Fundstelle.

Ein Abschnitt ist der eigene Text eines `<div>` ohne die Texte seiner Unter-`<div>`s: ein
Rezept, oder der einleitende Regelteil eines Kapitels. Seitenzahl kommt aus `<pb n=…>`,
die Bildnummer aus `facs`. Kolumnentitel (`<fw>`) und Abbildungen fallen weg, bei
`<choice>` gilt die Korrektur.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

NS = "{http://www.tei-c.org/ns/1.0}"
WEG = {"fw", "figure", "note", "cb", "milestone"}
ABSATZ = "\u2029"  # Absatzende; «\n» steht für einen Zeilenumbruch (<lb/>)


@dataclass
class Roh:
    titel: str
    kapitel: list[str]
    text: str
    seite_von: str | None
    seite_bis: str | None
    faks_von: str | None
    faks_bis: str | None


@dataclass
class Leser:
    seite: str | None = None
    faks: str | None = None
    abschnitte: list[Roh] = field(default_factory=list)
    # Text je Seite in Lesereihenfolge, für die Zahlenprüfung (Weg A)
    seiten_text: dict[str, list[str]] = field(default_factory=dict)

    def _notiere(self, s: str) -> None:
        if s:
            self.seiten_text.setdefault(self.faks or "?", []).append(s)

    def lauf(self, e: ET.Element, puffer: list[tuple[str, str | None, str | None]]) -> None:
        tag = e.tag.replace(NS, "")
        if tag == "pb":
            self.seite = (e.get("n") or "").strip("[]") or None
            self.faks = (e.get("facs") or "").lstrip("#") or None
        elif tag == "lb":
            puffer.append(("\n", self.seite, self.faks))
        elif tag in WEG:
            pass
        elif tag == "choice":
            wahl = e.find(f"{NS}corr")
            if wahl is None:
                wahl = e.find(f"{NS}reg")
            if wahl is not None:
                self._text(wahl.text or "", puffer)
                for k in wahl:
                    self.lauf(k, puffer)
        else:
            self._text(e.text or "", puffer)
            for k in e:
                self.lauf(k, puffer)
        if tag in ("p", "head", "item", "list"):
            puffer.append((ABSATZ, self.seite, self.faks))
        self._text(e.tail or "", puffer)

    def _text(self, s: str, puffer: list) -> None:
        if s:
            puffer.append((s, self.seite, self.faks))
            self._notiere(s)

    def div(self, d: ET.Element, kapitel: list[str]) -> None:
        titel_puffer: list = []
        eigen: list = []
        self._text(d.text or "", eigen)
        titel = ""
        for k in d:
            tag = k.tag.replace(NS, "")
            if tag == "div":
                if not titel:
                    titel = fuege(titel_puffer)
                self._abschliessen(titel, kapitel, eigen)
                eigen = []
                self.div(k, kapitel + [titel] if titel else kapitel)
                self._text(k.tail or "", eigen)
            elif tag == "head" and not titel_puffer:
                tail, k.tail = k.tail, None
                self.lauf(k, titel_puffer)
                k.tail = tail
                titel = fuege(titel_puffer)
                self._text(k.tail or "", eigen)
            else:
                self.lauf(k, eigen)
        self._abschliessen(titel or fuege(titel_puffer), kapitel, eigen)

    def _abschliessen(self, titel: str, kapitel: list[str], puffer: list) -> None:
        text = fuege(puffer)
        if len(re.sub(r"\W", "", text)) < 15:
            return
        mit_seite = [(s, f) for t, s, f in puffer if t.strip()]
        self.abschnitte.append(Roh(
            titel=titel, kapitel=list(kapitel), text=text,
            seite_von=mit_seite[0][0], seite_bis=mit_seite[-1][0],
            faks_von=mit_seite[0][1], faks_bis=mit_seite[-1][1],
        ))


def fuege(puffer: list) -> str:
    roh = "".join(t for t, _, _ in puffer)
    # Zeilenumbrüche im XML-Quelltext sind Leerraum; nur <lb/> zählt als Zeile.
    roh = re.sub(r"[ \t\r]*\n[ \t\r]*", "\n", roh)
    roh = re.sub(r"\n+", "\n", roh)
    roh = re.sub(r"\s*\u2029\s*", "\u2029", roh)
    roh = re.sub(r"-\n(?=(und|oder|wie|als|so|bis)\b)", "- ", roh)  # «Suppen-\nund Ragout»
    roh = re.sub(r"(?<=\w)[-¬]\n(?=\w)", "", roh)                     # Silbentrennung
    roh = roh.replace("\n", " ")
    roh = re.sub(r"\u2029+", "\n\n", roh)
    roh = re.sub(r"[ \t]{2,}", " ", roh)
    return roh.strip()


def lies(pfad: Path) -> Leser:
    wurzel = ET.parse(pfad).getroot()
    leser = Leser()
    text = wurzel.find(f"{NS}text")
    # Seitenstand aus dem Vorspann übernehmen, damit der erste Abschnitt eine Seite hat
    front = text.find(f"{NS}front")
    if front is not None:
        for pb in front.iter(f"{NS}pb"):
            leser.seite = (pb.get("n") or "").strip("[]") or None
            leser.faks = (pb.get("facs") or "").lstrip("#") or None
        leser.seiten_text.clear()
    body = text.find(f"{NS}body")
    leser._text(body.text or "", [])
    for k in body:
        if k.tag == f"{NS}div":
            leser.div(k, [])
        else:
            leser.lauf(k, [])
    return leser


def seiten_roh(pfad: Path) -> dict[str, str]:
    """Weg B der Zahlenprüfung: Text je Seite direkt aus dem XML-Quelltext, ohne XML-Parser.

    Unabhängig vom Weg A über ElementTree: zerlegt an `<pb`, entfernt Kolumnentitel,
    Abbildungen, Anmerkungen und `<sic>` per Muster, dann alle übrigen Tags.
    """
    roh = Path(pfad).read_text("utf-8")
    body = roh[roh.index("<body"): roh.index("</body>")]
    teile = re.split(r'<pb\b[^>]*?facs="#([^"]+)"[^>]*/>', body)
    seiten: dict[str, str] = {}
    for i in range(1, len(teile), 2):
        faks, inhalt = teile[i], teile[i + 1]
        inhalt = re.sub(r"<(fw|figure|note|sic|orig)\b[^>]*>.*?</\1>", " ", inhalt, flags=re.S)
        inhalt = re.sub(r"<(fw|figure|note|sic|orig)\b[^>]*/>", " ", inhalt)
        inhalt = re.sub(r"<[^>]+>", " ", inhalt)
        inhalt = inhalt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        seiten[faks] = seiten.get(faks, "") + inhalt
    return seiten
