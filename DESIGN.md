# DESIGN.md — Gestaltung libarius

Vorlage ist der Entwurf **«Libarius UI Mockups»** vom 09.09.2026
(Claude-Design-Projekt `dbe360cc-a23b-40e7-8b4c-eccf8e8b19e6`, Dateien
`libarius.dc.html`, `Rezeptur.dc.html`, `Rezeptur2.dc.html`).
Übernommen ist er als `design/libarius.css` plus vier Referenzseiten — und seit dem
09.09.2026 auch in der Anwendung selbst: `index.html` trägt am Ende ihres `<style>`-Blocks
die «Gestaltungsschicht». Siehe «Stand der Umstellung».

**Gegenprüfung erfolgt 09.09.2026** (AP-0403, abgenommen): Protokoll in
`Projekte/libarius-bedienung/04_qualitaet/AP-0403_design_review_output.md` — 59 Befunde
R-01–R-59, davon 13 mit Entscheidbedarf (dort Abschnitt 10), und die Fortsetzung der
Korrekturtabelle K-10 bis K-21 — **eingearbeitet am 10.09.2026**, nachdem die 13 Fragen
entschieden waren (siehe «Entscheide vom 10.09.2026»). Dringend und ohne Entscheidbedarf:
R-30, Variantentabelle Achse/Spalten um 99 px versetzt — entfällt mit dem Overlay aus R-09,
bis dahin ein Fehler im laufenden Betrieb.

| Datei | Inhalt |
|---|---|
| `design/libarius.css` | Marken, Raster, Bausteine — die einzige Quelle der Masse |
| `design/index.html` | Übersicht der Referenzseiten |
| `design/stilblatt.html` | Farben, Schrift, Raster, Bedienelemente, Symbole (Artboard 1g) |
| `design/stilblatt-nachtrag.html` | Marker, Zustände, Meldungen, Overlay-Rahmen (Nachtrag 10.09.2026, K-21) |
| `design/entwurf-kochen.html` | Hauptansicht, ein Rezept und Menü (Artboards 2a, 2b) |
| `design/entwurf-cue.html` | Cue-Spalte der linken Schiene, Cornell-Schnitt W/M/K (AP-0202 libarius-gestaltung, 10.09.2026) |
| `design/entwurf-rezeptur.html` | Rezeptur im Detail und Entwicklungsmodus (1c, 1d) |
| `design/entwurf-kochmodus.html` | Kochmodus im 38er-Raster (1e) |
| `design/_ikonen.svg.html` | Symbolsatz zum Einsetzen in eine Seite |

Die Referenzseiten laufen ohne Anmeldung und ohne Daten, mit fest eingetragenem
Beispielrezept. Sie sind Vorlage, nicht Anwendung.

## Grundsatz

Papier mit Linienraster. Keine Karten, keine Schatten, keine Rundungen, keine Fotos,
kein Dunkelmodus. Rot ist ausschliesslich Linie.

## Raster

Ein Schritt = **28 px**. Die Rasterlinie liegt **19 px** unter der Zeilenoberkante, also
knapp unter der Schriftgrundlinie: Text sitzt auf der Linie, nicht darüber.
Jedes Element ist ein ganzzahliges Vielfaches von 28 hoch.

- Bedienelement = **56 px** (zwei Zeilen). Es ersetzt seine Rasterlinie durch eine
  Graphitlinie bei 47 px.
- Seitenrand **40 px**, Spaltenabstand **32 px** — auch links und rechts jeder Randlinie.
- Kochmodus: gleiches System mit Schritt **38 px**, Linie bei **26 px**, Bedienelement 76 px.

## Farben

| Marke | Wert | Rolle |
|---|---|---|
| Papier | `#faf8f5` | Grundfläche |
| Leinwand | `#edeae4` | Fläche um die Artboards, nur in den Entwürfen |
| Linie | `#e4ded6` | Rasterlinie, Notizlinie |
| Graphit | `#2a2724` | Text, Bedienlinien, Kästchen |
| Nebentext | `#7a716a` | Nebentext, Einheiten, Metadaten |
| Notiz | `#5f574f` | Notiztext auf der Zutatenzeile |
| Rot | `#a63a2b` | nur Linie und Korrekturwert |

## Schrift

Fira Sans, tabellarische Ziffern durchgehend.

| Grad | Zeile | Wofür |
|---|---|---|
| 26 Medium | 28, zwei Zeilen hoch | Rezepttitel |
| 17 Medium | 28 | Phasentitel |
| 15 Regular | 28 | Fliesstext, Zutaten, Arbeitsschritte |
| 13 Regular | 28 | Nebentext, Kategorien, Metadaten |
| Kochmodus 36 / 22 / 17 | 38 | Titel / Fliesstext / Nebentext |

## Die rote Linie — drei Rollen, mehr nicht

1. **Randlinie** — senkrecht, volle Höhe, links der Rezeptur, 1.5 px.
2. **Trenner** — eine Rasterzeile, deren Linie rot und 1.5 px ist: zwischen Kopf, Phasen
   und Metadaten.
3. **Korrektur** — Sollmenge durchgestrichen in Nebentext, neuer Wert rot.

## Marker, Zustände, Meldungen, Overlays

Nachtrag 10.09.2026 zu Artboard 1g (AP-0201 libarius-gestaltung; O-20: R-44, R-45, K-21).
Gezeichnet in `design/stilblatt-nachtrag.html`, Bausteine am Ende von `design/libarius.css`.

**Lesart**: gerade Linie = da · Wellenlinie = falsch · Punktlinie = kommt noch ·
doppelt starke Linie = hier bist du. Hover ändert die Schrift, Fokus die Linie.
Kein Zustand nutzt Rot, keiner ändert eine Höhe.

### Textmarker

Eigenes Mittel neben den drei roten Rollen — keine vierte Rolle. Er sieht aus, als
hätte jemand mit dem Leuchtstift markiert.

| Marke | Pigment | Deckkraft | Art |
|---|---|---|---|
| `--lb-marker-gelb` | `#f9d73a` | 55 % | Warnung |
| `--lb-marker-gruen` | `#8fd46a` | 45 % | Erfolg |
| `--lb-marker-rot` | `#f37a82` | 38 % | Fehler |

- **Marker-Rot ist nicht Linienrot**: hell und rosé. `--lb-rot` (#a63a2b) bleibt Linie und Korrekturwert.
- **Form**: deckt Mittel- und Oberlängen (~15 von 28 px), nicht die ganze Rasterzeile; steigt nach
  rechts um ~2 px; obere und untere Kante unruhig, Rand leicht satter als die Fläche; Ansatz links
  8 px dunkler, dort setzt der Stift auf; steht 0.25 em über den Text hinaus.
- **Durchscheinend**: Text bleibt Graphit, die Rasterlinie scheint durch.
- **Umbruch**: jede Textzeile ist ein eigener Strich mit eigenem Ansatz (`box-decoration-break:clone`),
  nie ein Rechteck über mehrere Zeilen.
- **Element** `<mark>`. Die Art steht als Wort im markierten Text («Gespeichert», «Warnung», «Fehler»);
  die Farbe allein trägt keine Bedeutung.
- **Gilt für** Meldungen: Kennung und Kernsatz, nie den ganzen Meldungstext.
- **Gilt nicht für** Korrekturen (Rolle 3), Hover, Fokus, aktiv, Feldfehler, Überschriften,
  Abweichungen im Vergleich (Graphit + ▲) und den Druck (Meldungen sind `noprint`).
  Eigene Notizen markieren ist neue Funktion mit eigenem Datenfeld (Backlog, O-20).

### Zustände

| Zustand | Anklickbare Zeile, 56 px | Eingabefeld, 56 px |
|---|---|---|
| Ruhe | Text auf der unteren Linie (47) | Etikett 13 Nebentext oben, Wert unten, Graphitlinie 1 px bei 47 |
| aktiv | Unterstreichung Graphit 1 px, Versatz 5 (Bestand) | — |
| Hover | Unterstreichung **Nebentext** 1 px, Versatz 5 | Etikett und Platzhalter dunkler, Linie bleibt |
| Fokus (`:focus-visible`) | Graphitlinie 2 px bei 47, volle Zeilenbreite | Graphitlinie 2 px, Etikett Graphit, Einfügemarke |
| Fehler | Wellenlinie Graphit unter dem Namen, Grund 13 px mit «!» | Wellenlinie Graphit statt gerader Linie, Grund 13 px mit «!» rechts in der Etikettzeile |
| ladend | Punktlinie Nebentext an der Stelle des Textes, pulsiert 1.6 s | Punktlinie Graphit statt gerader Linie, Wert «…» |

- Text einer anklickbaren 56-px-Zeile steht auf der **unteren** Linie, wie beim Feld; die obere
  Zeile bleibt Luft oder trägt das Etikett.
- Bricht der Text um, bleibt die Luftzeile oben und die Zeile wächst um 28 je weitere Textzeile.
  Ohne Luftzeile läuft der Eintrag in den vorigen hinein (gesehen im Entwurf der Cue-Spalte,
  AP-0202 libarius-gestaltung).
- Ein Fehlergrund steht in einer Zeile, die es schon gibt — ein Fehler verschiebt nichts.
- Pulsieren nur über die Deckkraft; bei `prefers-reduced-motion` steht es still.
- Knöpfe verhalten sich wie anklickbare Zeilen.
- Nebentext mitten in einer 15-px-Textzeile bekommt `line-height:1`, sonst wird die Zeile 29 px hoch.

### Meldungen

Kennungszeile mit Marker («Art · Kernsatz»), darunter Text 15 Graphit auf den Linien, bei Bedarf
Aktionen als 56-px-Zeile, danach eine Zeile Abstand. Keine Randlinie, keine Fläche, kein Rahmen.

| Stelle | Wo | Beispiel |
|---|---|---|
| global | `#meldungen`, oben in der Mittelspalte hinter der Randlinie | Gespeichert · Phasen nach Rezepte.xlsx geschrieben |
| Formular | im Bereich, direkt über dem Formular, das sie betrifft | Warnung · Ungespeicherter Entwurf vom 09.09.2026 |
| Bereich | in der Schiene des Bereichs, über dessen Inhalt (AP-0201 §1, Zustand «fehler») | Fehler · Rezepte.xlsx konnte nicht gelesen werden |

Jede Art darf an jeder Stelle stehen; die Stelle folgt dem Bereich, nicht der Art.

### Overlay-Rahmen

- Papier mit eigenem Linienraster, **Randlinie links** (Rolle 1), Schleier Graphit 10 % dahinter.
  Kein Rahmen rundum, kein Schatten, keine Rundung (R-37).
- **Oberkante** auf einer Rasterlinie, 56 px unter dem Fensterrand. Ist die Seite um einen Rest
  gescrollt, rückt sie auf die nächste Linie (`--lb-versatz`, beim Scrollen gesetzt) — sonst stehen
  die Linien im Overlay neben denen der Seite.
- **Höhe** auf ganze Rasterzeilen abgerundet, unten mindestens eine Zeile Luft (K-4).
- **Kopf** 56 px: Titel 17 Medium auf der Linie, Schliessen × rechts innerhalb des Rahmens (K-5).
- **Innen** 32 px Gasse nach der Randlinie; das Raster scrollt mit dem Inhalt.
- Zwei Lagen: `--mitte` mit der Randlinie auf der Randlinie der Rezeptur (Breite legt AP-0304 fest),
  `--b7` 640 px zentriert.

## Spalten der Hauptansicht

**Rollen** (K-9, O-20): links die Rezeptliste mit Cue-Spalte und darunter die Einkaufsliste
(B1/B2), Mitte die Rezeptur mit den Metadaten (B3/B5), rechts die Notizsection (B4). Der
Entwicklungsmodus (B6) verlässt die rechte Schiene und wird Overlay über der Rezeptur
(O-20/R-09, AP-0304). Massstab ist AP-0201 §1 mit dem Nachtrag vom 10.09.2026.

**Masse der Anwendung** (gemessen 10.09.2026 in `index.html`, Chromium): fünf Spalten
Schiene · Randlinie · Rezeptur · Randlinie · Schiene. Bei **1440 px** mit beiden Schienen offen
**280 / 1.5 / 609 / 1.5 / 340**, dazu 40 px Rand und 32 px Gasse beidseitig jeder Randlinie
(40 + 280 + 32 + 1.5 + 32 + 609 + 32 + 1.5 + 32 + 340 + 40 = 1440). Die Rezeptur ist höchstens
760 px breit. Bei **1024 px** mit offener linker Schiene **240 / 1.5 / 638.5** — Gasse und
Randlinie der geschlossenen Seite fallen mit weg (R-59).

*Herkunft, überholt (K-11):* ~~**Zur Rollenverteilung siehe K-9.** Der Entwurf zeigt rechts die
Einkaufsliste; verbindlich ist AP-0201 §1: links Rezeptliste **und** Einkaufsliste, rechts
Notizsection und Entwicklung. Die Masse unten gelten unverändert, die Rollen der äusseren Spalten
nicht.~~ Fünf Spalten im Entwurf: Schiene · Randlinie · Rezeptur · Randlinie · Einkaufsliste.
Bei 1440 px sind das 200 / 1.5 / 757 / 1.5 / 272 bei 40 px Rand und 32 px Gassen.

**Gerätestufen der Anwendung** (E-2: Mac und iPad gleichrangig; AP-0201 §2.1, R-53, K-12):

| Stufe | Breite | Verhalten |
|---|---|---|
| W | ab 1280 px | beide Schienen offen möglich, links 280, rechts 340; die linke vollständig zuklappbar (R-10) |
| M | 860–1279 px | Schienen 240 px, höchstens eine offen (AP-0201 §2.2); die offene schiebt die Rezeptur |
| K | unter 860 px | Schiene als Overlay min(62vw, 520 px) mit Schleier, Seitenrand 24 px, rechte Randlinie entfällt, Zutatennamen linksbündig |

*Herkunft, überholt (K-12):* Gerätestufen des Entwurfs in `design/libarius.css`, 1200 / 900 px.

| Breite | Verhalten |
|---|---|
| ab 1200 px | drei Spalten |
| 900–1199 px | Einkaufsliste rückt unter die Rezeptur, mit rotem Trenner davor |
| unter 900 px | Schiene wird Overlay, Notizspalte entfällt, Zutatennamen linksbündig |

## Zutatenzeile

**Zur Notizspalte siehe K-9**: die Notiz bleibt in der rechten Schiene (AP-0201 B4), sie
wandert nicht in die Zutatenzeile. Was die dafür gezeichneten 240 px heute tragen, klärt
AP-0403 Schritt 7.

Name rechtsbündig an die Menge, Notiz auf derselben Zeile rechts daneben:
`Name (dehnbar, rechtsbündig) · Menge 96 · Einheit 32 · Notiz 240`.
Der Name gehört zur Menge, die Notiz gehört zur Zutat — die Zutat wird nicht wiederholt.
Ohne Notizspalte (Kochmodus, Druck, schmale Geräte) steht der Name wieder links.

## Korrekturen am Entwurf

Der Entwurf ist ein Entwurf: mehrere Objekte stehen nicht auf ihrer Kante. Durchgang 2
(Artboards 2a/2b) ist bereits sauber und gilt deshalb als kanonisch. Was abweicht:

| # | Fundstelle | Im Entwurf | Übernommen als |
|---|---|---|---|
| K-1 | 1a | Gassen 32 / 48 / 30.5 / 48 px zwischen den vier Spalten | einheitlich 32 px, beidseitig jeder Randlinie (so wie 2a) |
| K-2 | 1b | Schiene versteckt, Rezeptur endet bei 1008, Notizen ab 1128 — 120 px Loch | Rezeptur nimmt die frei werdende Breite auf |
| K-3 | 1c, 1d | Randlinie bei 248, rechts bleiben 280 px — Block nicht mittig | links und rechts gleich viel Luft |
| K-4 | 1d | Overlay `top:56` aber `bottom:0` — unten kein Rand | unten eine Rasterzeile Luft |
| K-5 | 1e | Schliessen-× bündig in der Ecke, während alles andere 40 px Rand hat | × innerhalb des Seitenrandes |
| K-6 | 1f | iPad: Kopfzeile 24, Randlinie 64, rechter Rand 32 px | 24 px links wie rechts |
| K-7 | 1c/1e/1g gegen 2a | Mengenspalte in 140, 200 und 96 px | 96 px im 28er-Raster, 200 px im 38er-Raster |
| K-8 | 1a | Kopfzeilenslots 200 px breit, erste Spalte aber 120 px | Slots so breit wie Schiene (200) und Einkaufsliste (272) |
| K-9 | 1a, 2a, 2b | Bereiche neu angeordnet: Einkaufsliste als dritte Spalte rechts, Notiz in der Zutatenzeile, keine rechte Schiene | **gilt nicht** — Entscheid vom 09.09.2026 (Gianluca, O-17.4): Einkaufsliste bleibt links unter der Rezeptliste, rechte Schiene mit Notizsection und Entwicklung bleibt. Massstab ist AP-0201 §1. Die Schicht baut bereits so; siehe «Noch nicht übernommen». **Teil «und Entwicklung» überholt** durch O-20/R-09 (10.09.2026): der Entwicklungsmodus wird Overlay, rechts bleibt die Notizsection |
| K-10 | 1c, 2a, Stilblatt | Sollmenge zuerst, korrigierter Wert danach | **gilt nicht** — AP-0201 §3.2: korrigierte Menge an der Stelle der Sollmenge, Soll durchgestrichen daneben |
| K-11 | 2a | Schiene 200, Einkaufsliste 272 | **gilt nicht** — App 280 / 340 nach AP-0201 §1; auf Stufe M bleiben 240, dafür wird AP-0201 angepasst (O-20/R-12). **Angepasst 10.09.2026** (AP-0203): AP-0201 §1 nennt 240 px als Mindestbreite von B1 und B4 |
| K-12 | `libarius.css` | Gerätestufen 1200 / 900 | **gilt nicht** — AP-0201 §2.1: 1280 / 860 |
| K-13 | 2a | Kopfzeile eine Rasterzeile (28) | 56 px — Entscheid 1, Tippziele |
| K-14 | 1c, 2a | Zutatenzeile Name · Menge · Einheit · Notiz | Name · Bäckerprozent 64 · Menge 96 mit Einheit im Text; Notizspalte entfällt (K-9) |
| K-15 | 1c, 2a | Phasen immer offen, Titel ohne Pfeil | klappbar mit `›`, Summary 56 (AP-0201 §4.1, Entscheid 1) |
| K-16 | 2a | Metadatenzeile 28, Pfeil rechts | 56 px (Entscheid 1); Pfeil wandert nach rechts (R-25) |
| K-17 | 1e | Kochmodus ohne Bedienelemente und Metadaten | **übernommen wie gezeichnet** — Entscheid 10.09.2026 (O-20): Skalierung, Aktionen und Metadaten fallen weg, nur das Rezept bleibt |
| K-18 | 1e, 1c | Randlinie direkt an der mittigen Rezeptur | zu übernehmen — App hat sie heute am Seitenrand (R-11, R-28) |
| K-19 | 2a | Skalierung rechts vom Titel auf derselben 56-px-Zeile | zu übernehmen (R-24) |
| K-20 | 1d | Entwicklungsmodus als Overlay, `.lb-vergleich`, `.lb-protokoll` | **gilt** — Entscheid 10.09.2026 (O-20/R-09): O-17.2 wird sofort umgesetzt, B6 verlässt die rechte Schiene. Eigenes AP; `.lb-protokoll` dient auch dem Versuchs- und Verfahrensformular |
| K-21 | Stilblatt | keine Zustände, keine Meldungen, keine Overlays | **Nachtrag bestellt** — Entscheid 10.09.2026 (O-20): Marker, Hover, Fokus, Fehler, ladend, Meldungen und Overlay-Rahmen werden gezeichnet. **Gezeichnet 10.09.2026** (AP-0201 libarius-gestaltung): `design/stilblatt-nachtrag.html`, Regeln im Abschnitt «Marker, Zustände, Meldungen, Overlays» |

Zwei Ergänzungen ohne Vorbild im Entwurf, weil die Anwendung sie braucht:

- **Metadatenzeilen** (Nährwerte, Kosten, Verfahren, Herkunft) aus `Rezeptur.dc.html`
  bleiben erhalten; Durchgang 2 hatte sie nur weggelassen, nicht gestrichen. Sie
  entsprechen dem Ausklapper aus AP-0304.
- **Umbrechende Protokollwerte**: im Entwurf ist die Protokollzeile 28 px hoch und der
  Text passt. In der Anwendung tut er das nicht immer — die Linie wiederholt sich dann
  je Textzeile, statt dass der Text aus seiner Zelle läuft.

## Entscheide vom 09.09.2026

1. **Tippziele bleiben 44 px** (Gianluca). Gelöst mit dem Bedienmass des Entwurfs selbst:
   jede anklickbare Zeile ist **56 px** hoch — zwei Rasterzeilen und damit ≥ 44 px. Nicht
   anklickbare Zeilen (Zutaten, Arbeitsschritte, Metadatenwerte) bleiben 28 px. Damit
   stehen Tippziel und Raster nicht mehr gegeneinander.
   Eine Ausnahme: die Variantentabelle des Entwicklungsmodus (AP-0308) bleibt bei 28 px.
   Achse und Wertespalten müssen Zeile für Zeile aneinander ausgerichtet bleiben, und
   56 px würden die Tabelle auf die doppelte Höhe ziehen. Sie war schon vor der Umstellung
   34 px dicht — die Erreichbarkeit wird also nicht schlechter, nur rastertreu.
   *Präzisiert 10.09.2026 (Punkt 9, R-35/R-56): die Ausnahme gilt nur für die Zellen;
   Leiste, Kopf und Fuss werden 56 px.*
2. **Dunkelmodus geht ins Backlog** (Gianluca). Nichts wird gelöscht. Die Schicht rechnet
   deshalb nicht mit festen Farben, sondern mit den bestehenden Marken `--bg`, `--line`,
   `--ink`, `--muted`, `--rot` — deren Werte im Hellmodus bereits exakt die des Entwurfs
   sind. Der Dunkelmodus trägt die neue Optik dadurch unverändert mit.
3. **Fira Sans** kommt von Google Fonts, mit Systemschrift als Fallback — wie schon MSAL
   und SheetJS von einem CDN kommen. Soll die App auch ohne Netz in ihrer Schrift starten,
   ist die Schrift ins Repo zu legen; das ist ein eigener Schritt.
4. **Rechtsbündige Zutatennamen** sind übernommen wie gezeichnet (Durchgang 2). Sie sind
   ungewohnt und gehören in AP-0401 auf die Prüfliste.

## Entscheide vom 10.09.2026 — aus dem Design-Review AP-0403

Dreizehn Fragen, Frage für Frage entschieden. Vollständig in `entscheide.md` unter **O-20**,
Herleitung im Reviewprotokoll `AP-0403_design_review_output.md`.

5. **Entwicklungsmodus wird Overlay** (R-09, K-20). O-17.2 gilt und wird sofort umgesetzt;
   B6 verlässt die rechte Schiene, die dann nur noch die Notizen trägt. Eigenes AP.
6. **Schienenbreite** bleibt auf Stufe M bei 240 px; AP-0201 §1 wird nach unten angepasst
   (R-12). Trägt nur, weil die rechte Schiene nach Punkt 5 leichter wird.
7. **Cue-Spalte wird entworfen** (R-13) — Kategoriegruppen allein erfüllen O-17.3 nicht.
   *Nachtrag 10.09.2026 (Gianluca): die Kategorie-Auswahl `#kategorie` entfällt; Cue und
   Rezeptliste trennt eine Linie in Linienfarbe, nicht Rot. Entwurf `design/entwurf-cue.html`,
   Bau AP-0310.*
8. **Kopfzeile**: Suche-Symbol öffnet die Schiene und setzt den Fokus ins Suchfeld (R-02);
   «Alle exportieren» und «Andere Datenbank öffnen» wandern in ein Menü hinter das
   Anmelde-Symbol (R-03). Beschriftungen fallen weg (R-01, schon durch O-17.1 gedeckt).
9. **Schienenkopf 56 px** (R-15). **Tippziel-Ausnahme eng**: nur die Zellen der
   Variantentabelle bleiben 28 px, Leiste, Kopf und Fuss werden 56 (R-35 — präzisiert
   Entscheid 1, der die Ausnahme stillschweigend ausgedehnt hatte).
10. **Arbeitsschritte werden wieder nummeriert**, Ziffer als 13-px-Nebentext (R-26).
11. **Kochmodus zeigt nur das Rezept** (K-17) — Skalierung, Aktionen, Metadaten weg.
12. **Meldungen als Textmarker** (R-44): gelb, grün, rot, durchscheinend, unruhige Kanten,
    leichte Schräge — es soll aussehen wie von Hand markiert, nicht wie eine Farbfläche.
    Der Marker gilt ausdrücklich **auch für eigene Notizen**: markieren können, was beim
    Kochen wichtig war. Neue Funktion mit eigenem Datenfeld, eigenes AP.
13. **Rot bleibt bei drei Rollen** (R-45); Hover und Fokus werden Unterstreichung und
    Graphit. Der Marker ist keine vierte Rolle für Rot — er ist ein eigenes Mittel mit
    eigener Anmutung.
14. **Stilblatt-Nachtrag bestellt** (K-21): Marker, Zustände, Meldungen, Overlay-Rahmen
    werden gezeichnet, nicht beschrieben.

Offen bis AP-0401: rechtsbündige Zutatennamen (R-29) — Entscheid am Gerät.
*Präzisiert 10.09.2026: AP-0401 meint den Sprint `libarius-bedienung`; im Sprint
`libarius-gestaltung` trägt AP-0402 (Bedientest Mac und iPad) den Prüfpunkt.*

## Stand der Umstellung

Übernommen in `index.html`:

- Papier mit 28-px-Linienraster über die ganze Fläche; Kochmodus mit 38-px-Raster.
- Fira Sans 15/28, Titel 26 auf zwei Zeilen, Phase 17, Nebentext 13, tabellarische Ziffern.
- Karten, Schatten, Rundungen und Farbflächen sind weg. Zwischen Kopf, Zubereitung,
  Phasen und Metadaten steht der rote Trenner.
- Rote Linie in allen drei Rollen: Randlinien links und rechts der Rezeptur als eigene
  Rasterspalten, Trenner, Korrekturwert.
- Bedienelemente ohne Rahmen: Suchfeld, Kategorie, Skalierung und Formularfelder tragen
  eine Graphitlinie bei 47 px, Kästchen sind 12 px mit 2-px-Papierring.
- Kopfzeile eine Bedienzeile hoch, mit den Symbolen des Entwurfs (Schiene, Import,
  Kochmodus, Anmeldung) und dem Namen des offenen Rezepts in der Mitte.
- Kochmodus mit Randlinie links, Inhalt 960 px, Schliessen innerhalb des Seitenrandes.

Nachgemessen im Browser: Zutatenzeile 28 px, anklickbare Zeilen 56 px, Kopfzeile 56 px;
`#rezeptbereich` und jeder Block darin sind ein ganzzahliges Vielfaches von 28 px
(gemessen 980 px = 35 × 28, kein Kind ausserhalb des Rasters). **Präzisiert 10.09.2026
(R-54):** das galt im gemessenen Zustand mit geschlossenen Metablöcken; mit offenem
Protokollblock lag der Bereich 1 px daneben (R-20, `table.log`). Nach AP-0303
(libarius-gestaltung) nachgemessen bei 1440 px: Grundzustand 952 = 34 × 28, alle acht `details`
offen 1876 = 67 × 28, jede Blockhöhe auf 28. Ausserhalb stehen nur die fünf Kurzwerte der
Metablock-Zeilen, 14 px unter der Zeilenoberkante — Folge der mittigen Textlage (siehe «Offene
Punkte»). Der `<style>`-Block parst
mit 359 Regeln fehlerfrei, `selfTest()` unverändert 82/82 grün, kein Waagrecht-Überlauf
bei 1440, 1200, 1120, 1000, 834 und 700 px. Unter 860 px stehen die Zutatennamen wieder
linksbündig und die Schiene wird zum Overlay.

**Nach AP-0304/0306/0307 (libarius-gestaltung, 10.09.2026):** Entwicklungsmodus (B6) ist
Overlay über der Rezeptur statt Reiter der rechten Schiene (O-20/R-09) — Achsen- und
Spaltenköpfe/-füsse auf identischer Höhe (4×56/2×56), R-30 damit behoben; Kochmodus zeigt
nur noch das Rezept (K-17), Randlinie sitzt eine Gasse vor dem Text statt am Seitenrand
(R-28); Meldungen sind Textmarker in drei Farben statt einer roten Randlinie (R-44), Rot ist
auf drei Rollen zurückgeführt (R-45, Tabelle unten). `selfTest()` nach allen drei APs
unverändert 82/82 grün.

**R-45, Fundstellen einzeln entschieden (AP-0307):**

| Stelle | Entscheid | Warum |
|---|---|---|
| `.navgruppe .punkt` (offene Korrektur) | **bleibt Rot** | gehört zur Korrektur, Rolle 3 — keine vierte Rolle, sondern dieselbe |
| `.warn-inline` (unbekannter Rohstoff, Importfehler) | Graphit + „!"-Glyphe | das Wort selbst erklärt die Warnung, Farbe war Verdopplung |
| `.editorzeile/.editorschritt button.entfernen` (Löschsymbol) | Graphit → Nebentext | zurückhaltendes Werkzeugsymbol, keine Warnung |
| `.entw-delta.entw-auf/.entw-ab` (Diff-Pfeil) | Nebentext | Pfeilrichtung (▲/▼) trägt die Aussage bereits |
| `table.vergleich td.abw` (Referenz-Vergleich „> 20 %") | Graphit | dieselbe Glyphe wie im Druck, dort schon Schwarz |
| Hover (Knöpfe, Kopfzeile) | Unterstreichung Nebentext bzw. Graphit → Nebentext bei reinen Symbolen | wie `.lb-bedienzeile:hover` |
| Fokus (Eingabefelder) | Graphitlinie 2 px statt 1 px farbig | wie im Stilblatt-Nachtrag spezifiziert |

Noch **nicht** übernommen, mit Grund:

| Was | Warum nicht |
|---|---|
| Notiz auf der Zutatenzeile (Durchgang 2) | Es gibt keine Notiz je Zutat. `Korrekturen` führt je Rezept eine freie Notiz und je Zutat eine Mengenkorrektur — die Korrektur erscheint bereits in der roten Rolle 3. Eine Notiz je Zutat ist eine Datenmodell-Änderung und braucht ein eigenes AP. |
| Einkaufsliste in der rechten Spalte | Sie steht laut AP-0201 §1 links (B2), rechts liegen Notizen und Entwicklung (B4/B6) — *Entwicklung überholt durch O-20/R-09: B6 wird Overlay über der Rezeptur*. Das ist eine Layoutentscheidung des Sprints, keine Gestaltungsfrage — sie umzuhängen berührt `View.notizsection()`, `Layout.*` und den Druckpfad. |
| Rezept-Tabs und Menüname (Durchgang 2) | Mehrere gleichzeitig geöffnete Rezepte und Menüs gibt es in der Anwendung nicht. Neue Funktion, eigenes AP. |
| Alte Regeln oberhalb der Schicht | Bleiben stehen (CLAUDE.md Regel 1). Erst entfernen, wenn nachweislich keine Regel mehr darauf zeigt. |

## Offene Punkte

- Schrift lokal ablegen, falls die App ohne Netz in Fira Sans starten soll.
- Dunkelmodus entscheiden (Backlog).
- Rund zwanzig Vorlagen tragen Inline-Abstände von .4–.9 rem, die aus dem Raster fallen.
  Die Schicht hebt sie gesammelt über `.actions[style]`, `.hint[style]` und
  `textarea[style]` auf. Sauberer wäre, die Abstände in den Vorlagen selbst zu entfernen —
  eigener Aufräumschritt, ohne sichtbare Wirkung.
- AP-0401 prüft zusätzlich: rechtsbündige Zutatennamen, Bedienbarkeit der 28-px-Zeilen in
  der Variantentabelle, Druck mit dem neuen Raster.
- **Gemessen 10.09.2026** (AP-0201 libarius-gestaltung, 1440 px, Fira Sans geladen): die
  anklickbaren 56-px-Zeilen der App — Rezeptliste, Einkaufsliste, Phasen- und Metablock-Zeilen —
  setzen ihren Text mittig, Grundlinie bei 33 statt auf der Linie bei 47. Der Text steht damit
  zwischen den Linien. Regel dafür: «Zustände», Text auf der unteren Linie.

Der Rechenkern `Calc.*` ist unberührt.
