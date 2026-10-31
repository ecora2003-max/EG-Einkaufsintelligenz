# Status und Wiederaufnahme — EG-Einkaufsintelligenz

**Datum:** 31.10.2026, **Vertrag:** EG-Architecture `1.0.0-draft` (zuletzt gelesen `d22862739bd0e3ef8451ce029e54f7c33ee53e40`). **Status: `PARTIAL_READY / OFFLINE_VERIFIED`**, ausdrücklich noch **nicht** `READY_FOR_INTEGRATION` oder `INTEGRATED`.

## Tatsächlich implementiert

- Deterministischer, zustandsfreier Python-Fachkern `eg_shopping/engine.py` und standardisierte JSON-CLI `eg_shopping/cli.py`, keine externen APIs/DB/Room-Abhängigkeiten.
- `compare_catalog` und `compare_prices`: alle tatsächlich gelieferten Händler- und regulären Preis-Snapshots, exakte Grundpreise, Mengenbasis-/Gebindekontrolle, Rote/Orange/Graue parallele Signale, markenunabhängige FoodType-Vergleiche, explizite Substitution, Ausschluss unbewiesener Online-/Coupon-/Pfand-Konditionen, Zeit-, Filial- und Quellenprüfung, `comparison.result`-Envelope.
- `project_needs`: FEFO-Chargen, gesperrter Bestand, plan-/historiebezogene Rohbedarfe, kumulative Horizonte 1/7/28/56 Tage und Duplikatprüfung; Baseline nur mit bestätigter Verbrauchsbeobachtung und Mindestumfang.
- `suggest_purchases`: Packungsaufrechnung, bekannte Teilsumme, Budgets, periodenbezogene Unsicherheit, aggregierte Lagerplatzprüfung, konservative Haltbarkeitskontrolle.
- `evaluate_offer_interest`, `list_offer_interests`: getrennte Angebotsinteressen und Einkaufslisten-Vorschläge ohne Kaufbuchung.
- `evaluate_past_purchase`: nur bestätigte historische Käufe und im historischen Zeitpunkt bereits beobachtete, datums- und marktgültige Alternativen.
- Synthetische Fixture `examples/compare_request.json`; kopiertes JSON-Schema und Beispiele aus Architektur.

## Verifizierte Tests

**GitHub Actions PR #1:** https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41218890394  
**Geprüfter Head:** `740d14dab5ecb8804b1d4cd01dd2e58356f91594` (PR-Merge-Checkout inkl. vorangegangener `main`-Änderungen).  
**Runner:** Python 3.12.15 auf Ubuntu.  
**Kommandos:**
```sh
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```
**Ergebnis:** 37 Tests / **37 bestanden, 0 fehlgeschlagen, 0 übersprungen**, darunter formale Validierung der Architektur-Beispielnachrichten und `comparison.result`. Logs belegen dieses Ergebnis. Vorheriger CI-Lauf mit einem Testproblem (Formatvalidierung; nicht-failendes Invalidbeispiel) war **fehlgeschlagen** und wurde durch stärkere Negativprobe und Installation `jsonschema[format]` korrigiert. Weitere Commits nach diesem Lauf (Dokumentation) sind noch auf neuen CI-Status zu prüfen; der zuvor bestandene Testlauf belegt nicht jede spätere Codeänderung.

## Noch offene Punkte, keine unbelegte Vollständigkeitsmeldung

1. **Konditionale Preise und Staffel-/Mehrfachkaufoptimierung:** Bisher werden Coupons/Mitgliedschaft/Mindestmengen konservativ ausgeschlossen; kein Erfüllungsnachweis aus gesondertem Bedingungen-DTO.
2. **Einkaufsoptimierung:** Einfaches einzelnes günstigstes Preis-/Packungsverhältnis je FoodType, keine globale Kombination aus unterschiedlichen Gebindegrößen, Distanz-/Laufwegen, Shop-Splitting, Gesamtbudget, Mindestmengen und Verderbsmaximierung. Die aktuelle Packungsauswahl kann teurer als eine andere Packungs-Mischung sein.
3. **Verbrauchsmodell:** Ein konservativer Baseline-Durchschnitt, keine Saison-/Anomalie-/Mindest-/Prognoseintervall-Modelle. Unbekannte Planmengen werden gewarnt, aber noch nicht als eigener ungewisser Nachkaufpositionstyp ausgewiesen.
4. **Zeit- und Evidenzqualität:** Grunddaten sind konservativ, jedoch fehlen reichhaltige Nachweise zu Store-/Region- und Verfügbarkeitsdurchsetzung für manche Snapshot-Formen. `coverage.complete` ist nur übernommen und nicht gegen Prüfquellen deduktiv validiert. Bekannte große Marktabdeckung nie behauptet.
5. **Haltbarkeit/Planung:** `usableUntil` und `shelfLifeDays` sind nur vom Host geprüfte Eingaben; kein MHD/Verbrauchsdatum-Validator und keine belegte Kühlkettenprüfung. Angebotspreis-Vorziehen und Aufteilung nach früherem Bedarf derzeit nicht fachlich optimiert.
6. **Android:** Kein produktiver Kotlin-Port, keine Room-, Compose-, API- und Hardware-Integration; nur Integrationsskizze in `docs/INTEGRATION.md`.
7. **Testabdeckung:** Weitere Randfälle für Bedingungen, Budgetperioden, abgelaufene Chargen, Stückbündel, mögliche Geld-Nachrundung, Duplicate-Snapshots und mehrfache Varianten ergänzen. Tests 37/37 sind kein Nachweis vollständiger Anforderungen.
8. **Vertragserweiterung:** Separate ShoppingNeed-/OfferInterest-/HistoricalReport-DTOs sind **modulintern**, noch nicht in EG-Architecture abgestimmt. Änderungsvorschlag im eigenen Repo erforderlich.

## Konkreter Wiederaufnahmepfad

1. Zu Beginn jeder Wiederaufnahme die `main`-SHAs der Architektur und dieses Repos sowie `AGENTS.md`, `docs/ACCEPTANCE.md`, `docs/INTEGRATION.md`, den CI-Stand und diese Datei lesen. Änderungen an anderen Repositories unterlassen.
2. CI für neueste Änderung prüfen; falls rot, Joblogs lesen, Fehler gezielt korrigieren und Tests erneut ausführen. Bestehenden Prüfstand dokumentieren; keine grünen Tests behaupten, wenn sie nicht ausgeführt wurden.
3. Bedingungs-DTO (Coupon/Mindestmenge, Kanal, Pfand, Versand, Preiszeitfenster) und exakte budget-/kapazitätsgebundene Mischgebindeauswahl nur mit belegbarer Konformität implementieren, negative Tests nach jeder Funktionsänderung.
4. Für Bedarf/Planung zusätzliche Tests und konservative Fehlermeldungen bei fehlendem Stand, Budget, Lager-/Kühlkapazität, nicht-haltbarer Vorverlegung und zusammengesetzten Koch-/Verzehr-Events.
5. `docs/CONTRACT_CHANGE_REQUEST.md` für erweiterte DTOs dokumentieren (Architektur selbst **nur lesen**).
6. Erneut komplette `docs/ACCEPTANCE.md`-Matrix und JSON-Schema-Tests laufen lassen. Nur bei lückenlos dokumentierter Abnahme `READY_FOR_INTEGRATION` setzen; `INTEGRATED` ausschließlich Codex.

**Datenschutz und Lizenz:** Ausschließlich synthetische Testdaten. Kein Live-Scraping, keine Drittanbieter-Berechtigungen beansprucht; keine Nutzer-/Bon-Daten, kein Bezahl-API- oder Server-Zwang.
