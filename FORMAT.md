# Austauschformat `rezept/1`

AP-0315. Format für Import und Export von Rezepten — identisch mit dem internen Datenmodell
(Feinkonzept AP-0206 §3), abzüglich der Laufzeitfelder `_raw`, `nameKey` und `rohstoff`.
`format` erlaubt später eine Version 2, ohne alte Dateien unbrauchbar zu machen.

## Aufbau

```json
{
  "format": "rezept/1",
  "rezepte": [
    {
      "name": "Sauerteigbrot hell",
      "kategorie": "Backen",
      "unterkategorie": "Brot",
      "quelle": "Hausrezept",
      "basisName": "Weissmehl 00",
      "basisMengeG": 1000,
      "sollgewichtG": 1600,
      "portionen": 2,
      "einheit": "Stk",
      "phasen": [
        {
          "name": "Autolyse",
          "zutaten": [
            { "name": "Weissmehl 00", "prozent": 1.0, "einheit": "g" }
          ],
          "schritte": [
            { "nr": 1, "text": "Mehl und Wasser mischen, 30 Min. ruhen lassen." }
          ]
        }
      ],
      "backprotokoll": [
        { "datum": "2026-03-15", "sollG": 1600, "istG": 1470, "notizen": "Kruste zu hell." }
      ],
      "entwicklung": null
    }
  ]
}
```

## Felder

### Wurzel

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `format` | string | ja | muss exakt `"rezept/1"` sein |
| `rezepte` | Array\<Rezept\> | ja | mindestens 1 Eintrag |

### Rezept

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `name` | string | ja | nicht leer; Grundlage der Namenskonflikt-Prüfung (FR-1205) |
| `kategorie` | string | ja | nicht leer |
| `unterkategorie` | string \| null | nein | Default `null` |
| `quelle` | string \| null | nein | Default `null` |
| `basisName` | string | ja | Name des Basis-Rohstoffs |
| `basisMengeG` | number > 0 | ja | |
| `sollgewichtG` | number > 0 | ja | |
| `portionen` | number > 0 | ja | |
| `einheit` | string | ja | z. B. `"Stk"` |
| `phasen` | Array\<Phase\> | ja | mindestens 1 Eintrag |
| `backprotokoll` | Array\<Backeintrag\> | nein | Default `[]` |
| `entwicklung` | Entwicklung \| null | nein | Default `null` — Struktur siehe unten. Wird in v1 **nicht** geprüft, aber unverändert durchgereicht (Export → Import ist verlustfrei) |

### Phase

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `name` | string | ja | nicht leer |
| `zutaten` | Array\<Zutat\> | ja | darf leer sein (z. B. reine Back-Phase ohne eigene Zutaten) |
| `schritte` | Array\<Schritt\> | ja | darf leer sein |

### Zutat

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `name` | string | ja | nicht leer; wird beim Import gegen `Rohstoffe.xlsx` aufgelöst (§6b.3) |
| `prozent` | number > 0 | ja | Faktor, nicht Prozentzahl (`0.65`, nicht `65`) |
| `einheit` | string | ja | eine von `g`, `kg`, `ml`, `l`, `stk` |

### Schritt

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `nr` | number | ja | fortlaufend innerhalb der Phase |
| `text` | string | ja | nicht leer |

### Backeintrag

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `datum` | string | ja | Format `JJJJ-MM-TT` |
| `sollG` | number > 0 | ja | |
| `istG` | number > 0 | ja | |
| `notizen` | string \| null | nein | Default `null` |

### Entwicklung (AP-0311)

Entspricht der Excel-Spalte «Entwicklung (JSON)» in `Rezepte.xlsx` und der Spezifikation
AP-0203 §1.1. Fehlt die Spalte oder ist die Zelle leer, bleibt `entwicklung` `null` und das
Rezept verhält sich wie ohne Entwicklungsmodus.

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `status` | `"entwicklung"` \| `"produktiv"` | ja | `"produktiv"` nach dem Befördern; der Verlauf bleibt erhalten |
| `zielwerte` | object | ja | je Kennzahl ein Faktor oder `null`, z. B. `hydration_pct`, `salz_pct` (AP-0312) |
| `aktivV` | number | ja | Versionsnummer der aktuell bearbeiteten Version; ohne Treffer gilt die letzte |
| `versionen` | Array\<Version\> | ja | mindestens 1 Eintrag; wird nie gekürzt |
| `versuche` | Array\<Versuch\> | ja | darf leer sein |

#### Version

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `v` | number | ja | fortlaufend ab 1, nur `+ Neue Version` erhöht sie |
| `datum` | string | ja | Format `JJJJ-MM-TT` |
| `notiz` | string | ja | Kurznotiz, was gegenüber der Vorversion geändert wurde |
| `phasen` | Array\<Phase\> | ja | identisches Format wie `phasen` oben |

#### Versuch

Feldnamen bewusst `soll_g`/`ist_g` (Spezifikation AP-0203 §1.1) — abweichend vom
Backeintrag oben, der `sollG`/`istG` verwendet.

| Feld | Typ | Pflicht | Bemerkung |
|---|---|---|---|
| `datum` | string | ja | Format `JJJJ-MM-TT` |
| `version` | number | ja | referenziert `versionen[].v` |
| `soll_g` | number > 0 | ja | |
| `ist_g` | number > 0 | ja | |
| `bewertung` | number 1–5 | ja | |
| `erkenntnis` | string \| null | nein | Default `null` |

**Befördern** kopiert `phasen` der gewählten Version nach `phasen` des Rezepts und setzt
`status` auf `"produktiv"`. Die Versionsliste bleibt vollständig erhalten — die bisherige
produktive Rezeptur ist weiterhin als Version abrufbar.

**Grössenwarnung:** Die App warnt ab 25'000 Zeichen pro Zelle (Excel-Limit 32'767).

## Prüfung

`Import.pruefen(daten)` validiert gegen dieses Schema und liefert
`{ ok: boolean, fehler: [{ pfad, meldung }] }`. `pfad` benennt Feld **und** Position exakt,
z. B. `rezepte[0].phasen[1].zutaten[2].prozent`. Schlägt die Prüfung fehl, wird nichts
übernommen (§6b.2).

## Ablauf Import (für jeden Zulieferer derselbe, §6b.2)

```
Quelle → parsen → prüfen (Schema) → Rohstoffe auflösen → VORSCHAU → übernehmen
```

- **Rohstoff-Auflösung** (§6b.3): unbekannte Zutatennamen werden gesammelt und im Dialog je
  Name zur Entscheidung vorgelegt — bestehendem Rohstoff zuordnen (wird als Alias gemerkt) oder
  als unbekannt übernehmen. Zuordnungen landen im Blatt **«Aliase»** in `Rohstoffe.xlsx`
  (Spalten `Variante`, `Zielname`, `Gelernt am`) — nicht in `localStorage`, damit sie
  geräteübergreifend wirken.
- **Namenskonflikt** (FR-1205): trifft der Import auf ein Rezept mit demselben Namen wie ein
  bestehendes, fragt die App nach — neu anlegen (eigene ID) oder als Version an das bestehende
  Rezept anhängen. Nie wird stillschweigend überschrieben.
- **Vorschau**: zeigt das Rezept genau so, wie es danach in der Rezeptansicht erscheint,
  inklusive berechneter Mengen. Ohne Vorschau kein Übernehmen (FR-1203).

## Export

Export erzeugt exakt dieses Format — einzeln (aktuelles Rezept) oder gesamt (ganzer Bestand).
Laufzeitfelder (`_raw`, `nameKey`, `rohstoff` je Zutat) werden entfernt. Ein Export, gefolgt von
einem Import derselben Datei, ergibt denselben Bestand (Rundlauf, geprüft im Selbsttest der App).

## Freitext-Zerlegung (Ausbau, FR-1209)

`Import.freitextZerlegen(text)` ist eine **regelbasierte Vorstufe**, kein Parser mit Anspruch auf
Vollständigkeit: sie erkennt Mengen mit Einheit (`250 g`, `1.5 l`, `3 Stk`), Phasenüberschriften
(kurze Zeile ohne Menge, meist grossgeschrieben oder mit Doppelpunkt) und nummerierte Schritte
(`1.`, `2)` u. ä.). Was sie nicht sicher erkennt, bleibt leer — das Ergebnis geht unverändert in
denselben Prüf- und Vorschau-Dialog wie jeder andere Import.
