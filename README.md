# libarius

Browser-App zur Rezeptverwaltung: Rezepte aus zwei Excel-Datenbanken in OneDrive anzeigen,
auf beliebige Mengen skalieren (Bäckerprozent), Kosten und Nährwerte rechnen,
Backprotokoll führen und drucken.

Der Name kommt aus dem Lateinischen: *libarius* ist der Kuchen- und Feingebäckbäcker.

**Live:** https://hanging-pawn.github.io/libarius/

## Was hier liegt

| Datei | Inhalt |
|---|---|
| `index.html` | die ganze App — HTML, CSS und JS in einer Datei, kein Build |
| `config.json` | Azure-App-ID, OneDrive-Pfade, Redirect-URI, Alias-Tabelle |

Im Repo liegen **nur App-Code und Konfiguration** — keine Rezepte, keine Nährwertdaten,
keine Tokens. Die Daten bleiben in OneDrive.

## Aufbau der App

Gemäss Feinkonzept AP-0206 §2, alles innerhalb von `index.html`:

```
CONFIG · Model · Calc · Data · Store · View · Dev · App
```

- **Calc** ist ein reiner Rechenkern ohne DOM- und ohne Netzzugriff — beim Start läuft ein
  Selbsttest gegen feste Referenzwerte, das Ergebnis steht in der Fusszeile.
- **Data** kapselt MSAL-Login und Microsoft Graph. Alles andere kennt weder Login noch Netz.

## Stand

| Bereich | AP | Stand |
|---|---|---|
| UI-Grundgerüst, Liste, Suche, Phasen | AP-0301 | steht |
| Skalierung, Einheiten | AP-0303 | steht |
| Kosten, Nährwerte | AP-0304 | steht |
| Login + OneDrive laden | AP-0302 | implementiert — Abnahme (Mac + iPad) durch Gianluca aussteht |
| Backprotokoll erfassen + speichern | AP-0305 | abgenommen (Live-Test Gianluca 02.09.2026 gegen echtes OneDrive) |
| Druck / PDF | AP-0306 | implementiert — Layout/Seitenumbrüche im echten PDF-Druck nicht live geprüft, Abnahme durch Gianluca aussteht |
| Excel-Import Altdateien | AP-0316 | steht — Erkenner + Import-Dialog-Anschluss |
| Service-Schnittstelle (LLM-Import, Rohstoff-Recherche) | AP-0318 | App-Seite steht — Dienst selbst noch nicht deployt, siehe unten |
| Entwicklungsmodus — Versionen + Versuchsprotokoll | AP-0311 | abgenommen 03.09.2026 — Spalte „Entwicklung (JSON)“ liegt in Rezepte.xlsx; das erste echte Speichern gegen OneDrive steht als Restrisiko aus |
| Entwicklungsmodus — Zielwerte, Referenz-Vergleich, Substitution | AP-0312–0314 | offen |

Ohne Anmeldung läuft die App mit zwei eingebauten Beispielrezepten. Nach Anmeldung lädt sie
`Rezepte.xlsx` und `Rohstoffe.xlsx` direkt aus OneDrive (Pfade in `config.json`, änderbar über
«Andere Datenbank öffnen»).

## Entwickeln

Kein Build, kein Paketmanager. `index.html` bearbeiten, im Browser neu laden.
Für den Login braucht es eine http-Origin — lokal etwa:

```bash
python3 -m http.server 8080     # dann http://localhost:8080
```

## Backup & Restore (AP-0305)

Vor jedem Schreibzugriff auf `Rezepte.xlsx` (Backprotokoll-Eintrag speichern, Import
übernehmen) legt die App automatisch eine Sicherungskopie in `config.json.backupOrdner`
an (produktiv `/04_Casa La Rocca/Küche/Backups`) — **eine Datei pro Tag**,
`Rezepte_backup_JJJJ-MM-TT.xlsx`. Mehrfaches Speichern am selben Tag ersetzt nur diese
eine Tagesdatei, der Ordner wird bei Bedarf automatisch angelegt.

Das eigentliche Schreiben nutzt für das Backprotokoll gezielte Zell-Updates über die
Microsoft Graph Excel Workbook API statt eines Ganzdatei-Uploads (Entscheid O-9 —
Pilotbefund AP-0302: ein SheetJS-Ganzdatei-PUT verliert alle Dropdowns und die fixierte
Kopfzeile bei jedem Speichern). Vor jedem Schreiben prüft die App den `eTag` von
`Rezepte.xlsx` gegen den beim letzten Laden gemerkten Stand — hat sich die Datei
zwischenzeitlich extern geändert, bricht die App ab, meldet den Konflikt und lädt den
Bestand neu, statt blind zu überschreiben.

**Restore:** In OneDrive nach `Küche/Backups/` navigieren, die gewünschte Tagesdatei
(`Rezepte_backup_JJJJ-MM-TT.xlsx`) öffnen, herunterladen und über die produktive
`Rezepte.xlsx` unter `Küche/Rezepte.xlsx` hochladen (ersetzen) — oder die Backup-Datei in
OneDrive kopieren und auf `Rezepte.xlsx` umbenennen. Backups älter als ~90 Tage bei
Gelegenheit von Hand in einen Archiv-Unterordner verschieben, nie automatisch löschen
(CLAUDE.md-Grundregel).

## Entwicklungsmodus (AP-0311)

Schema und Ablauf gemäss Spezifikation `02_konzept/AP-0203_spez_rezeptentwicklung.md` §1.1+§3.
Eine eigene Spalte **„Entwicklung (JSON)“** in `Rezepte.xlsx` trägt je Rezept `status`
(`entwicklung`/`produktiv`), `zielwerte` (Baustein 2, AP-0312, hier nicht ausgewertet),
`aktivV` (Nummer der gerade aktiven Version), `versionen[]` (v, Datum, Notiz, Phasen im
selben Format wie „Phasen (JSON)“) und `versuche[]` (Datum, Version, `soll_g`/`ist_g`,
Bewertung 1–5, Erkenntnis — bewusst snake_case wie in der Spezifikation, kein Alias des
camelCase `sollG`/`istG` aus dem produktiven Backprotokoll, dessen Schwund-Logik diese Werte
ausdrücklich nicht speisen).

**Fehlt die Spalte in `Rezepte.xlsx`** (produktiv aktuell der Fall), bleibt `entwicklung` für
jedes Rezept `null` und die App verhält sich exakt wie ohne dieses AP — die Spalte muss vor
dem ersten produktiven Einsatz von Hand ergänzt werden (rein additiv, kein Migrationsschritt
nötig). Schreibpfad identisch zu Backup & Restore oben: eTag-Konflikterkennung, Backup vor
jedem Schreiben, gezielte Zell-Updates statt Ganzdatei-PUT — „Befördern“ schreibt zusätzlich
„Phasen (JSON)“ neu, die Versionsliste selbst bleibt in jedem Fall vollständig erhalten
(nichts wird gelöscht, CLAUDE.md-Grundregel).

Workflow: **Entwicklungsmodus starten** kopiert die aktuelle Rezeptur als v1. **+ Neue
Version**/**Bearbeiten** editieren die Phasen einer Version als JSON (Prüfung wie beim
Import, `Import.phasenFehler`). **Vergleichen** zeigt die Differenz zweier Versionen
(Zutat/%/Δ, geänderte Schritte je Phase). **+ Neuer Versuch** protokolliert Soll/Ist-Gewicht
und Bewertung, unabhängig vom produktiven Backprotokoll. **Version befördern** setzt eine
gewählte Version — nach Bestätigungsdialog — als produktive Rezeptur; alle Versionen bleiben
danach als Verlauf sichtbar.

## Service — LLM-Import + Rohstoff-Recherche (AP-0318)

Die App kennt genau eine Aussengrenze, den Namespace `Service` (Feinkonzept §6b.5):

```js
Service.verfuegbar()                // false ohne konfigurierten Dienst
Service.rezeptAusText(text)         // -> { format:"rezept/1", rezepte:[…] }
Service.rezeptAusBild(dataUrl)      // -> dito
Service.rohstoffRecherche(namen[])  // -> [{ name, kostenProKg, quelle, stand, naehrwerte, gefunden }, …]
```

Ohne `config.json.serviceUrl` ist `Service.verfuegbar()` `false` und **jeder** zugehörige
Knopf (KI-Import im Import-Dialog, «Preise aktualisieren» im Kosten-Block) bleibt komplett
ausgeblendet — die App funktioniert vollständig ohne diesen Dienst, wie von FR-1211 verlangt.
Eine Modellantwort wird nie ungeprüft übernommen: `rezeptAusText`/`rezeptAusBild` landen wie
jeder andere Import im bestehenden Prüf-/Vorschau-Dialog aus AP-0315 (Import.pruefen() gegen
`rezept/1`); `rohstoffRecherche` landet in einem Freigabe-Dialog, geschrieben wird nur, was
dort einzeln angehakt wurde (gleiches Prinzip wie die Cowork-Recherche in AP-0317).

**Entscheid O-7 (01.09.2026):** fertiger Anbieter, dahinter eine selbst gehostete
**Azure Function** — passt zur bestehenden Azure-Anmeldung (MSAL/Graph-Login läuft bereits
über Azure) und hält den API-Schlüssel als Function-App-Einstellung, nie im Repo.

### `config.json`

```json
{
  "serviceUrl": "https://<function-app-name>.azurewebsites.net/api"
}
```

Feld weglassen oder leer lassen = kein Dienst konfiguriert.

### Vertragsformat

Die App ruft `POST {serviceUrl}/rezept-aus-text`, `/rezept-aus-bild`, `/rohstoff-recherche`
mit JSON-Body auf und erwartet JSON zurück:

| Route | Body rein | Antwort |
|---|---|---|
| `/rezept-aus-text` | `{ "text": "…" }` | `{ "format":"rezept/1", "rezepte":[…] }` — Schema in `FORMAT.md` |
| `/rezept-aus-bild` | `{ "bild": "data:image/…;base64,…" }` | dito |
| `/rohstoff-recherche` | `{ "namen": ["Weissmehl 00", …] }` | `[{ "name", "kostenProKg", "quelle", "stand", "naehrwerte":{"kcal","eiweiss","fett","kh"}, "gefunden" }, …]` |

### Referenzimplementierung (Azure Function, Node.js v4-Programmiermodell)

Dieser Code liegt **ausserhalb** dieses Repos (eigenes Azure-Function-App-Projekt) — hier nur
als Startpunkt dokumentiert. Einrichtung, Deployment und der API-Schlüssel sind Gianlucas
eigener Schritt, nicht Teil dieses Repos.

```bash
npm install @anthropic-ai/sdk zod @azure/functions
```

```js
// src/functions/rezeptAusText.js
const { app } = require("@azure/functions");
const Anthropic = require("@anthropic-ai/sdk");
const { z } = require("zod");
const { zodOutputFormat } = require("@anthropic-ai/sdk/helpers/zod");

// Schema deckungsgleich mit rezept/1 (FORMAT.md) — Pflichtfelder aus Import.pruefen().
const Rezept1Schema = z.object({
  format: z.literal("rezept/1"),
  rezepte: z.array(z.object({
    name: z.string(), kategorie: z.string(),
    unterkategorie: z.string().nullable(), quelle: z.string().nullable(),
    basisName: z.string(), basisMengeG: z.number().positive(),
    sollgewichtG: z.number().positive(), portionen: z.number().positive(),
    einheit: z.string(),
    phasen: z.array(z.object({
      name: z.string(),
      zutaten: z.array(z.object({
        name: z.string(), prozent: z.number().positive(),
        einheit: z.enum(["g","kg","ml","l","stk"])
      })),
      schritte: z.array(z.object({ nr: z.number(), text: z.string() }))
    })),
    backprotokoll: z.array(z.any()), entwicklung: z.any().nullable()
  }))
});

const client = new Anthropic(); // liest ANTHROPIC_API_KEY aus den Function-App-Einstellungen

app.http("rezeptAusText", {
  methods: ["POST"], authLevel: "anonymous", route: "rezept-aus-text",
  handler: async (request) => {
    const { text } = await request.json();
    const response = await client.messages.parse({
      model: "claude-opus-5", max_tokens: 16000,
      system: "Überführe das Rezept aus dem Nutzertext ins Format rezept/1. " +
        "Bäckerprozente nur, wenn im Text eindeutig — sonst prozent weglassen/0, nichts schätzen.",
      messages: [{ role: "user", content: text }],
      output_config: { format: zodOutputFormat(Rezept1Schema) }
    });
    if(!response.parsed_output) return { status: 502, jsonBody: { fehler: "Antwort nicht auswertbar" } };
    return { jsonBody: response.parsed_output };
  }
});
```

`rezeptAusBild` entspricht `rezeptAusText`, nur mit einem `image`-Content-Block
(`{ type:"image", source:{ type:"base64", media_type:"image/…", data:"…" } }` — die App liefert
den Data-URL direkt, `media_type`/`data` daraus abtrennen) statt reinem Text.
`rohstoffRecherche` nutzt denselben `messages.parse()`-Aufruf mit dem Websuche-Tool
(`web_search`) und einem Zod-Array-Schema für die Antwortliste — Details in der
`claude-api`-Skill-Dokumentation.

CORS auf der Function App auf die Pages-Origin (`https://hanging-pawn.github.io`) beschränken.
`authLevel: "anonymous"`, weil die App selbst keine Zugangsdaten mitschickt — `serviceUrl` in
`config.json` ist die einzige Kopplung. **Das ist eine bewusste Lücke, kein Versehen:** wer die
Funktions-URL kennt, kann sie unabhängig von CORS direkt aufrufen (Browser-Restriktionen
schützen nur gegen Aufrufe aus fremden Webseiten, nicht gegen curl/Postman) und Kosten am
Anthropic-Schlüssel verursachen. Für den privaten Gebrauch reicht ein hartes Zahlungslimit auf
dem Anthropic-Konto als Auffangnetz; bei echtem Missbrauchsrisiko einen einfachen geteilten
Schlüssel einführen (z. B. `x-service-key`-Header, den `Service._aufruf()` in `index.html`
mitschickt und der in `config.json` **nicht** als Geheimnis, sondern nur als Referenz auf den
Namen der Function-App-Einstellung steht — der Wert selbst bleibt serverseitig).

## Deployment

```bash
git add -A && git commit -m "…" && git push
```

GitHub Pages veröffentlicht `main` / root. Ein weiterer Schritt ist nicht nötig.

## Einrichtung (einmalig)

1. Repo auf GitHub anlegen (public), diesen Ordner pushen.
2. Settings → Pages → Source `main` / `/ (root)`. URL notieren.
3. Azure-Portal → App-Registrierung → Authentifizierung → Plattform **SPA** →
   Redirect-URI = die Pages-URL. Berechtigungen `Files.ReadWrite` und `User.Read`.
4. Die Pages-URL in `config.json` unter `redirectUri` eintragen.

Details: `Projekte/rezeptverwaltung/02_konzept/AP-0201_adr_hosting.md`

## Dokumentation

Lastenheft, Anforderungskatalog, User Stories und Feinkonzept liegen in OneDrive unter
`04_Casa La Rocca/Küche/` — nicht in diesem Repo, weil das Repo öffentlich ist.
