# libarius

Browser-App zur Rezeptverwaltung: Rezepte aus zwei Excel-Datenbanken in OneDrive anzeigen,
auf beliebige Mengen skalieren (Bäckerprozent), Kosten und Nährwerte rechnen,
Backprotokoll führen und drucken.

Der Name kommt aus dem Lateinischen: *libarius* ist der Kuchen- und Feingebäckbäcker.

**Live:** `https://<benutzername>.github.io/libarius/`

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
| Login + OneDrive laden | AP-0302 | offen — `Data` ist noch ein Stub |
| Backprotokoll erfassen + speichern | AP-0305 | offen |
| Druck / PDF | AP-0306 | Print-CSS steht |
| Entwicklungsmodus | AP-0311–0314 | offen |

Bis AP-0302 läuft die App mit zwei eingebauten Beispielrezepten.

## Entwickeln

Kein Build, kein Paketmanager. `index.html` bearbeiten, im Browser neu laden.
Für den Login braucht es eine http-Origin — lokal etwa:

```bash
python3 -m http.server 8080     # dann http://localhost:8080
```

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
