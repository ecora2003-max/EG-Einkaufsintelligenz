# Verbindlicher Auftrag – Chat 4 / Einkaufs- und Preisvergleichsintelligenz

**Rolle:** unabhängiger, offline testbarer Fachkern für Preisvergleiche, Warnsignale und datenqualitätsbewusste Einkaufsentscheidungen.

## Zugriffs- und Eigentumsgrenzen
- **Einziges Schreibziel:** `ecora2003-max/EG-Einkaufsintelligenz`. Architektur `EG-Architecture`, alle anderen Modulrepos und privates Hauptrepo `ecora2003-max/Ernaerungsgedaechnis` ausschließlich **lesen**. Keine Fremd-Dateien/Issues/PRs/Branches/Workflows verändern.
- Du bist nicht Codex. Du baust **keine** App-UI, direkte Room- oder Google-Sheets-Integration und keine konkurrierende Bestands-/Budgetbuchungsdatenbank.
- Lies zuerst die aktuelle Architekturquelle: `docs/MASTER_ARCHITECTURE.md`, `docs/DOMAIN_MODEL.md`, `docs/INTEGRATION_AND_GOVERNANCE.md`, `contracts/v1/`. Nutze die existierenden konkreten Preisdaten-/Produktdatenmodule als Quellenbeispiele, **nicht** als harte Runtime-Abhängigkeit.
- Nutze nur synthetische Testdaten in öffentlichen Repos. Keine privaten Kassenbons, Gesundheitsangaben, Tokens oder Nutzerhistorien.

## Entwicklungs- und Testregel
**Nach jeder funktionsrelevanten Codeänderung alle relevanten Unit-, Vertrags- und Regressionstests ausführen.** Insbesondere Preis/kg und Preis/l, Bio-Warnstufen Rot/Orange/Grau, unbekannter Bio-Status, Marken-/Eigenmarkenunterschiede, Aktionsdatum, Filialbezug und unvollständige Kataloge testen. Keine falsche Behauptung, die günstigste Option des ganzen Marktes gefunden zu haben.

Verpflichtende Unterlagen: `docs/DEVELOPMENT_MANDATE.md`, `docs/ACCEPTANCE.md`, `docs/INTEGRATION.md`; Testergebnisse mit exaktem Befehl, Datum, Commit und Fehlern dokumentieren.

## Definition des Ziels
`READY_FOR_INTEGRATION` nur bei ausführbarem deterministischem Kern, bestandenen Positiv-/Negativ-/Vertragstests, dokumentierter Coverage-/Unsicherheitsbehandlung und klarer Android-Adapter-Grenze. Keine Kauf-, Lager- oder Ausgabe-Buchungen. Fehlendes Budget oder fehlende Kühlkapazität bleibt **unbekannt**, nicht null. `INTEGRATED` ausschließlich Codex nach Gesamt-App-Prüfung.

Fehlt ein Vertragsfeld? Im eigenen Repo einen `docs/CONTRACT_CHANGE_REQUEST.md` dokumentieren; Architektur-Repo selbst nur lesen.
