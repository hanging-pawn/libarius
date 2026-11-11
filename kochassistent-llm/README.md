# Kochassistent-LLM

Unterprojekt von Libarius: ein kleines Sprachmodell, mit Wissen aus echten Kochbüchern und Fachartikeln
feinabgestimmt. Es bewertet ein Rezept (Machbarkeit, Effizienz, Verhältnisse, Technik,
Risiko) und schlägt begründete Änderungen vor. Wunsch: lokal auf dem Mobilgerät.

**Stand:** Gerüst und Anforderungsentwurf. Noch kein Code, keine Daten, kein Modell.
**Anforderungen:** führend im Projekt-Vault, IDs `REQ-nnn`; hier nur der Verweis [REQUIREMENTS.md](REQUIREMENTS.md).
**Plan:** Jira LIBAR, Meilensteine M11 bis M14.

## Isoliert

Das Unterprojekt hängt nicht an der App: `index.html` und `config.json` bleiben unberührt,
die App lädt nichts aus diesem Ordner. Einzige gemeinsame Schnittstelle ist das
Austauschformat `rezept/1` ([FORMAT.md](../FORMAT.md)) als Eingabe des Modells.

## Was hier liegt

| Pfad | Inhalt | Im Repo |
|---|---|---|
| `REQUIREMENTS.md` | Verweis auf die Anforderungen im Vault, Kurzfassung | ja |
| `schema/` | Schema für Trainingsbeispiele und Ausgabeformat (Entwurf) | ja |
| `src/kochassistent/` | Pipeline: `extraktion` → `destillation` → `training` → `evaluation` (leer) | ja |
| `konfig/` | Einstellungen je Trainingslauf; `pfade.beispiel.toml` als Vorlage für die lokalen Pfade | ja |
| iCloud Drive | Kochbücher und Fachartikel (PDF, EPUB, Scans) — Pfad in `konfig/pfade.lokal.toml` | **nein** |
| `daten/` | `roh/` extrahierte Abschnitte, `destilliert/` Beispiele, `splits/` Trainings-/Testteile | **nein** |
| `eval/goldset/` | von Hand geprüfte Testfälle | **nein** |
| `modelle/` | Basismodelle, Adapter, Exporte | **nein** |

Das Repo ist öffentlich. Die Bücher liegen in iCloud Drive, alles daraus Abgeleitete bleibt
lokal — `.gitignore` in diesem Ordner sperrt es (REQ-105).

## Einrichten

- **Gerät:** iPhone 15 Pro als Referenz.
- **Training:** lokal auf dem Mac mit Unsloth Studio.
- **Pfade:** `konfig/pfade.beispiel.toml` nach `konfig/pfade.lokal.toml` kopieren und den Quellenordner in iCloud Drive eintragen.
- **Python-Pipeline:** Abhängigkeiten folgen mit dem Lehrer-Modell-Benchmark (REQ-050). Vorgesehen ist Python ≥ 3.11 in einer eigenen Umgebung in diesem Ordner.
