# Einrichtung — einmalig, ca. 20 Minuten

## 0. Sperrdateien entfernen (zuerst, sonst geht kein git-Befehl)

Das Repo ist bereits initialisiert und der erste Commit liegt vor. Beim Anlegen sind aber
neun leere Sperrdateien liegengeblieben, die ich aus der Cowork-Sitzung heraus nicht
löschen darf. Einmal im Terminal:

```bash
cd ~/Library/CloudStorage/OneDrive-Persönlich/04_Casa\ La\ Rocca/Küche/kochen
find .git \( -name '*.lock' -o -name 'tmp_obj_*' \) -delete
git status          # SETUP.md steht noch als unversioniert drin
git add -A && git commit -m "SETUP.md"
git log --oneline   # muss zwei Commits zeigen
```

Falls dabei etwas schiefgeht: `rm -rf .git` und danach

```bash
git init -b main && git add -A && git commit -m "Initial: libarius"
```

## 1. GitHub-Repo anlegen und pushen

```bash
# auf github.com: New repository → Name "libarius" → Public → Create (ohne README)
git remote add origin https://github.com/<benutzername>/libarius.git
git push -u origin main
```

## 2. GitHub Pages aktivieren

Repo → **Settings → Pages** → Source: Branch `main`, Ordner `/ (root)` → Save.
Nach ein bis zwei Minuten ist die Seite unter `https://<benutzername>.github.io/libarius/`
erreichbar. **URL notieren** — sie wird zweimal gebraucht.

## 3. Azure-Redirect-URI eintragen

portal.azure.com → **App-Registrierungen** → **libarius**
(clientId `4c4bbfe6-8742-4d43-bd49-6b4b6e959fce`; hiess früher «Rezeptverwaltung Küche»,
umbenannt am 01.09.2026) → **Authentifizierung**
→ Plattform hinzufügen → **Single-Page-Anwendung (SPA)**
→ Redirect-URI = die Pages-URL aus Schritt 2 → Speichern.

`http://localhost` darf als zweite URI für lokale Tests stehen bleiben.

Die API-Berechtigungen `Files.ReadWrite` und `User.Read` (delegiert) sind am 01.09.2026
bereits gesetzt und zugestimmt — nur noch die Redirect-URI fehlt.

## 4. URL in die Konfiguration eintragen

In `config.json` das Feld `redirectUri` auf die Pages-URL setzen (statt
`https://BENUTZERNAME.github.io/libarius/`), dann:

```bash
git add config.json && git commit -m "Redirect-URI eingetragen" && git push
```

## Fertig, wenn

- [ ] `https://<benutzername>.github.io/libarius/` zeigt die App mit den zwei Beispielrezepten
- [ ] die Fusszeile meldet «Selbsttest: 12/12 ok»
- [ ] `config.json` enthält die echte Pages-URL
- [ ] Azure hat die Pages-URL als SPA-Redirect-URI

Danach ist **AP-0302** (Login + OneDrive laden) startbereit.

---

Referenz: `Projekte/rezeptverwaltung/02_konzept/AP-0201_adr_hosting.md`
