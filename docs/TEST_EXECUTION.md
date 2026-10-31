# Offline-Testausführung

CI-Prüfung: `python -m pip install jsonschema[format]==4.23.0 && python -m unittest discover -s tests -v`.

GitHub Actions testet bei Push und Pull Request. Live-Quellen sind ausdrücklich nicht Gegenstand dieses Tests.

Acceptance expansion 31.10.2026: `tests/test_pack_optimizer.py` verifies exact mixed-pack selection, budget, multibuy thresholds, capacity, shelf life, search limits and immutable snapshots. This CI run exercises current main merged into PR; results must be checked, not assumed.
