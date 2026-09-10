# Einrichtung — abgeschlossen am 01.09.2026

> Diese Anleitung ist vollständig durchlaufen. Sie bleibt als Nachweis stehen;
> die Platzhalter sind durch die echten Werte ersetzt. Nichts davon ist noch zu tun.

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
git remote add origin https://github.com/hanging-pawn/libarius.git
git push -u origin main
```

## 2. GitHub Pages aktivieren

Repo → **Settings → Pages** → Source: Branch `main`, Ordner `/ (root)` → Save.
Nach ein bis zwei Minuten ist die Seite unter https://hanging-pawn.github.io/libarius/
erreichbar.

## 3. Azure-Redirect-URI eintragen

portal.azure.com → **App-Registrierungen** → **libarius**
(clientId `4c4bbfe6-8742-4d43-bd49-6b4b6e959fce`; hiess früher «Rezeptverwaltung Küche»,
umbenannt am 01.09.2026) → **Authentifizierung**
→ Plattform hinzufügen → **Single-Page-Anwendung (SPA)**
→ Redirect-URI = `https://hanging-pawn.github.io/libarius/` → Speichern.

`http://localhost` darf als zweite URI für lokale Tests stehen bleiben.

Die API-Berechtigungen `Files.ReadWrite` und `User.Read` (delegiert) sind am 01.09.2026
gesetzt und zugestimmt. Die Redirect-URI wurde am 01.09.2026 ergänzt — die SPA-Plattform
führt jetzt `http://localhost` und `https://hanging-pawn.github.io/libarius/`.

## 4. URL in die Konfiguration eintragen

In `config.json` das Feld `redirectUri` auf `https://hanging-pawn.github.io/libarius/`
setzen, dann:

```bash
git add config.json && git commit -m "Redirect-URI eingetragen" && git push
```

## Fertig — abgeschlossen am 01.09.2026

- [x] https://hanging-pawn.github.io/libarius/ zeigt die App mit den zwei Beispielrezepten
- [x] die Fusszeile meldet «Selbsttest: 12/12 ok»
- [x] `config.json` enthält die echte Pages-URL
- [x] Azure hat die Pages-URL als SPA-Redirect-URI

**AP-0302** (Login + OneDrive laden) ist damit startbereit.

---

Referenz: `Projekte/rezeptverwaltung/02_konzept/AP-0201_adr_hosting.md`
