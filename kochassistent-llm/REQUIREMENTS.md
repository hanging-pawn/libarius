# Kochassistent-LLM — Anforderungen

Die Anforderungen werden **nicht hier** gepflegt. Führend ist das Dokument im Projekt-Vault
(Obsidian, privat):

`Projekte/Libarius/01_Anforderungen/2026-11-11_Anforderungen_Kochassistent-LLM.md`

Stand: Entwurf v0.3.1, 53 Anforderungen, IDs `REQ-001` bis `REQ-110`. Eine Kopie hier würde
auseinanderlaufen; darum steht in diesem Repo nur der Verweis.

## Kurzfassung

- **Zweck:** Ein kleines Sprachmodell, mit Wissen aus echten Kochbüchern und Fachartikeln
  feinabgestimmt, bewertet ein Rezept (Machbarkeit, Effizienz, Verhältnisse, Technik, Risiko)
  und schlägt begründete Änderungen vor.
- **Echte Lösungen:** Die Lösung jedes Trainingsbeispiels steht in der Quelle. Jeder Schritt des
  Denkwegs stützt sich auf eine Fundstelle, eine nachrechenbare Rechnung oder eine Angabe des Rezepts.
- **Umfang:** Kochen allgemein, Backen eingeschlossen; Rückfall auf zwei Modelle, wenn eines nicht reicht.
- **Zielgerät:** iPhone 15 Pro. **Training:** lokal mit Unsloth Studio.
- **Nicht im Repo:** Bücher, abgeleitete Daten, Goldset, Modellgewichte.

## Abgrenzung

- Isoliert von der App: `index.html` und `config.json` bleiben unberührt.
- Kein Rechner, kein Rezeptgenerator, keine Instanz für Lebensmittelsicherheit.
- Einzige Schnittstelle: das Austauschformat `rezept/1` ([FORMAT.md](../FORMAT.md)) als Eingabe.

## Bezug im Code

Code, Schema und Tests nennen die Anforderung, der sie dienen, mit ihrer ID (`REQ-018`).
Arbeitspakete stehen im Jira-Projekt LIBAR, Meilensteine M11 bis M14.
