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

**CI-Stand 31.10.2026:** 62/62 bestandene Offline- und Vertrags-Tests (https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41220579678). Das beweist keine Live-Datenabdeckung oder Android-Integration. Der gemeinsame Vertrag ist `1.0.0-draft`; produktiver Status **`PARTIAL_READY`**.
