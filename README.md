# EG-Einkaufsintelligenz

> **Verbindliche Einweisung für den zuständigen Entwicklungs-Chat:** [AGENTS.md](AGENTS.md) · [Entwicklungsauftrag](docs/DEVELOPMENT_MANDATE.md) · [Abnahmetests und Fertigstellung](docs/ACCEPTANCE.md) · [Integrationsschnittstellen](docs/INTEGRATION.md) · [Status](docs/STATUS.md). Gemeinsame Verträge: [EG-Architecture](https://github.com/ecora2003-max/EG-Architecture). **Nur dieses Modulrepo bearbeiten; Architektur und private Haupt-App ausschließlich lesen. Tests nach jeder fachlichen Änderung verpflichtend.**

## Auftrag
Dieses Repository ist eine unabhängig entwickelte, testbare Zulieferkomponente für die Android-App „Ernährungsgedächtnis“. Es enthält ausdrücklich **keine** zweite produktive Datenbank. Die Komponenten werden erst nach vollständiger Modulabnahme von Codex in die bestehende App integriert.

## Ausführbarer Referenzkern

- Python >=3.10, ohne Pflichtserver, Runtime-Drittbibliotheken, Netzwerk oder Datenbank.
- `eg_shopping/engine.py`: Preisvergleiche, historische Einkaufsauswertung, Bestands-/Bedarfsprojektion, getrennte Angebotsinteressen.
- `eg_shopping/pack_optimizer.py`: exakte, begrenzte Mischgebindeoptimierung mit Kosten-, Budget-, Lager- und Haltbarkeitsprüfungen; keine globale Marktpreisgarantie.
- `eg_shopping/cli.py`: JSON-Objekt auf stdin → JSON-Ergebnis auf stdout oder standardisierter Fehler auf stderr.
- Vertrags- und synthetische Beispieldaten: `contracts/v1/`, `examples/compare_request.json`.
- API, Ein-/Ausgaben, Unsicherheiten, Android-Port: `docs/INTEGRATION.md`.
- Offene Fälle, CI-Protokoll und Wiederaufnahmepunkt: `docs/STATUS.md`.

```bash
python -m eg_shopping < examples/compare_request.json
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

**CI-Stand 31.10.2026:** 92/92 bestandene Offline- und Vertrags-Tests (https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222789227). Das beweist keine Live-Datenabdeckung oder Android-Integration. Der gemeinsame Vertrag ist `1.0.0-draft`; Status des **Offline-Referenzkerns: `READY_FOR_INTEGRATION`**; Android-Haupt-App und Live-Quellen sind ausdrücklich nicht integriert.

Neu verifiziert: `eg_shopping/stockup.py` für quellengebundene vorgezogene Käufe. Angebotsinteressen erlauben FoodType- und durch Host belegte Laufwegfilter.

**Abnahme und exakte Kotlin-Portierung:** [`docs/ACCEPTANCE_REPORT.md`](docs/ACCEPTANCE_REPORT.md), [`docs/KOTLIN_MIGRATION_SPEC.md`](docs/KOTLIN_MIGRATION_SPEC.md), [`examples/EXPECTED_RESULTS.md`](examples/EXPECTED_RESULTS.md). Die dokumentierte Testbasis ist synthetisch und rein offline.

**Weitere geprüfte Invarianten:** Ein Produkt darf mehrere filialbezogene Preisbeobachtungen haben; belegte gegen nur behauptete/abgelaufene Preise werden getrennt. Unbekannte Checkout- und Pfandbedingungen liefern keine verifizierten Endkosten. Referenzlauf: [92 bestandene Tests](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222789227).

## Experimenteller Shopping-Vertrag 1.1 (noch nicht freigegeben)

Die neue Architekturversion `1.1.0-draft` wird nur über **expliziten Import** von `eg_shopping.draft_v11` testweise abgebildet; es erfolgt keine Änderung der bestehenden CLI und kein stiller Wechsel vom `1.0.0-draft`-Vertrag. Vier Shopping-Nachrichtentypen, die beiden unveränderten Architektur-Testkopien und Positiv-/Negativtests sind unter `docs/V11_DRAFT_COMPATIBILITY.md`, `contracts/v1.1/` und `tests/test_draft_v11.py` dokumentiert.

**Neuster CI-Lauf:** [107/107 bestandene Tests](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224765046) für v1.0 und den optionalen v1.1-Draft gemeinsam. Die spätere Vertragsfreigabe und produktive Android-Integration sind davon ausdrücklich **nicht** umfasst.
