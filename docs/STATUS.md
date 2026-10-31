# Status und Wiederaufnahme — EG-Einkaufsintelligenz

**Datum:** 31.10.2026, **Vertrag:** EG-Architecture `1.0.0-draft` (zuletzt gelesen `d22862739bd0e3ef8451ce029e54f7c33ee53e40`). **Status: `PARTIAL_READY / OFFLINE_VERIFIED`**, ausdrücklich noch **nicht** `READY_FOR_INTEGRATION` oder `INTEGRATED`.

## Tatsächlich implementiert

- Deterministischer, zustandsfreier Python-Fachkern `eg_shopping/engine.py` und standardisierte JSON-CLI `eg_shopping/cli.py`, keine externen APIs/DB/Room-Abhängigkeiten.
- `compare_catalog` und `compare_prices`: alle tatsächlich gelieferten Händler- und regulären Preis-Snapshots, exakte Grundpreise, Mengenbasis-/Gebindekontrolle, Rote/Orange/Graue parallele Signale, markenunabhängige FoodType-Vergleiche, explizite Substitution, Ausschluss unbewiesener Online-/Coupon-/Pfand-Konditionen, Zeit-, Filial- und Quellenprüfung, `comparison.result`-Envelope.
- `project_needs`: FEFO-Chargen, gesperrter Bestand, plan-/historiebezogene Rohbedarfe, kumulative Horizonte 1/7/28/56 Tage und Duplikatprüfung; Baseline nur mit bestätigter Verbrauchsbeobachtung und Mindestumfang.
- `pack_optimizer.py` / `suggest_purchases`: beschränkte genaue Mischgebinde-Aufrechnung, bekannte Teilsumme, Budgets, periodenbezogene Unsicherheit, aggregierte Lagerplatzprüfung, konservative Haltbarkeitskontrolle.
- `evaluate_offer_interest`, `list_offer_interests`: getrennte Angebotsinteressen und Einkaufslisten-Vorschläge ohne Kaufbuchung.
- `evaluate_past_purchase`: nur bestätigte historische Käufe und im historischen Zeitpunkt bereits beobachtete, datums- und marktgültige Alternativen.
- Synthetische Fixture `examples/compare_request.json`; kopiertes JSON-Schema und Beispiele aus Architektur.

## Verifizierte Tests

**GitHub Actions PR #1, aktuell grün:** https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41220132440  
**Geprüfter Head:** `20adc0685b33562b1170aaf36fa724e8d856a8d1` (PR-Merge-Commit `894d580`, main-Basis `9518b7a69c8b7e5dd6ecea3d4676823c620c9155`) (PR-Merge-Checkout inkl. vorangegangener `main`-Änderungen).  
**Runner:** Python 3.12.15 auf Ubuntu.  
**Kommandos:**
```sh
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```
**Ergebnis:** 62 Tests / **62 bestanden, 0 fehlgeschlagen, 0 übersprungen**, darunter formale Validierung der Architektur-Beispielnachrichten und `comparison.result`. Logs belegen dieses Ergebnis. Vorheriger CI-Lauf mit einem Testproblem (Formatvalidierung; nicht-failendes Invalidbeispiel) war **fehlgeschlagen** und wurde durch stärkere Negativprobe und Installation `jsonschema[format]` korrigiert. Weitere Commits nach diesem Lauf (Dokumentation) sind noch auf neuen CI-Status zu prüfen; der zuvor bestandene Testlauf belegt nicht jede spätere Codeänderung.

## Noch offene Punkte, keine unbelegte Vollständigkeitsmeldung

1. **Konditionale Preise und Staffel-/Mehrfachkaufoptimierung:** Bisher werden Coupons/Mitgliedschaft/Mindestmengen konservativ ausgeschlossen; kein Erfüllungsnachweis aus gesondertem Bedingungen-DTO.
2. **Einkaufsoptimierung:** Exakte begrenzte Mischgebindesuche mit `max_nodes=250000`, bis zu acht Varianten pro FoodType (`pack_optimizer.py`); jedoch keine globale Optimierung über mehrere FoodTypes, Distanz-/Laufwegen, Shop-Splitting, Gesamtbudget, Mindestmengen und Verderbsmaximierung. Die aktuelle Packungsauswahl kann teurer als eine andere Packungs-Mischung sein.
3. **Verbrauchsmodell:** Ein konservativer Baseline-Durchschnitt, keine Saison-/Anomalie-/Mindest-/Prognoseintervall-Modelle. Unbekannte Planmengen erscheinen als `unknownNeeds[]` mit `quantityToBuy=null`; zubereitete Portionsverzehre erzeugen auch in der Verbrauchsbaseline keine Rohwaren-Doppelzählung.
4. **Zeit- und Evidenzqualität:** Grunddaten sind konservativ, jedoch fehlen reichhaltige Nachweise zu Store-/Region- und Verfügbarkeitsdurchsetzung für manche Snapshot-Formen. `coverage.complete` ist nur übernommen und nicht gegen Prüfquellen deduktiv validiert. Bekannte große Marktabdeckung nie behauptet.
5. **Haltbarkeit/Planung:** `usableUntil` und `shelfLifeDays` sind nur vom Host geprüfte Eingaben; kein MHD/Verbrauchsdatum-Validator und keine belegte Kühlkettenprüfung. Angebotspreis-Vorziehen und Aufteilung nach früherem Bedarf derzeit nicht fachlich optimiert.
6. **Android:** Kein produktiver Kotlin-Port, keine Room-, Compose-, API- und Hardware-Integration; nur Integrationsskizze in `docs/INTEGRATION.md`.
7. **Testabdeckung:** 62/62 synthetische Tests sind kein Nachweis der vollständigen Anforderungen. Offene Felder: globale Budgetoptimierung, Herkunftsvalidierung von Nachkaufpreisen, Coupons, rückgabefähiger Pfand-Cashflow, Kühlkette und Android-Port.
8. **Vertragserweiterung:** Separate ShoppingNeed-/OfferInterest-/HistoricalReport-DTOs sind **modulintern**, noch nicht in EG-Architecture abgestimmt. Änderungsvorschlag ist in `docs/CONTRACT_CHANGE_REQUEST.md` dokumentiert; Freigabe durch Architektursteuerung ausstehend.

## Konkreter Wiederaufnahmepfad

1. Zu Beginn jeder Wiederaufnahme die `main`-SHAs der Architektur und dieses Repos sowie `AGENTS.md`, `docs/ACCEPTANCE.md`, `docs/INTEGRATION.md`, den CI-Stand und diese Datei lesen. Änderungen an anderen Repositories unterlassen.
2. CI für neueste Änderung prüfen; falls rot, Joblogs lesen, Fehler gezielt korrigieren und Tests erneut ausführen. Bestehenden Prüfstand dokumentieren; keine grünen Tests behaupten, wenn sie nicht ausgeführt wurden.
3. Bedingungs-DTO (Coupon/Mindestmenge, Kanal, Pfand, Versand, Preiszeitfenster) und exakte budget-/kapazitätsgebundene Mischgebindeauswahl nur mit belegbarer Konformität implementieren, negative Tests nach jeder Funktionsänderung.
4. Für Bedarf/Planung zusätzliche Tests und konservative Fehlermeldungen bei fehlendem Stand, Budget, Lager-/Kühlkapazität, nicht-haltbarer Vorverlegung und zusammengesetzten Koch-/Verzehr-Events.
5. `docs/CONTRACT_CHANGE_REQUEST.md` für erweiterte DTOs dokumentieren (Architektur selbst **nur lesen**).
6. Erneut komplette `docs/ACCEPTANCE.md`-Matrix und JSON-Schema-Tests laufen lassen. Nur bei lückenlos dokumentierter Abnahme `READY_FOR_INTEGRATION` setzen; `INTEGRATED` ausschließlich Codex.

**Datenschutz und Lizenz:** Ausschließlich synthetische Testdaten. Kein Live-Scraping, keine Drittanbieter-Berechtigungen beansprucht; keine Nutzer-/Bon-Daten, kein Bezahl-API- oder Server-Zwang.

## Verifikation und Fortsetzung 31.10.2026
CI-Run 41219610231 (54 Tests, 4 Fail/6 Error) und Run 41220076006 (59 Tests, 1 Fail) haben echte Defekte aufgedeckt. Sie wurden korrigiert. Run 41220132440 beweist 59/59 bestandene Tests auf dem aktuellen fachlichen Code. Fehlende Packungszahl und Quellenzeitpunkt erzeugen keine Nullannahmen; unbekannter Pfandbetrag bleibt `checkoutCents=null` und löst Grau aus. Offene Sicherheitsschranke: `suggest_purchases` benötigt strengere Nachweise für Preiszeitpunkt und Pfand-/Versandcashflow; keine globale Marktpreis- oder Einkaufsoptimalität behaupten. Folgeaufgabe: Herkunftsvalidierung und zusätzliche Negativtests, danach erneuter CI-Lauf.

## Verifikation 31.10.2026, zweiter Meilenstein
Run: https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41220579678 . Testbasis: main 69b1b3c537de9f804189d09c9005ac7c02ab8b31, PR-Merge 01a0287. Befehl: `python -m unittest discover -s tests -v`, nach Installation von `jsonschema[format]==4.23.0`. Ergebnis: 62 Pass, 0 Fail, 0 Skip. Seit diesem Test wurden nur Dokumente geändert. Neu: `suggest_purchases(..., as_of=...)` prüft Preisbelege (`priceObservation`) und lässt ohne passenden Beleg nur REVIEW zu. Pfand wird getrennt vom Warenpreis als Cash-Bedarf ausgewiesen, bei Unbekanntem bleibt Checkout null. Offene Risiken: globale Warenkorboptimierung, Gutschein-/Staffelkonditionen, Versand sowie Kotlin-Haupt-App-Integration. STATUS bleibt PARTIAL_READY.

## Verifikation 31.10.2026, dritter Meilenstein
CI https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41220994053 : 74 Tests, 74 Pass, 0 Fail, 0 Skip. Kommando `python -m unittest discover -s tests -v` nach `python -m pip install 'jsonschema[format]==4.23.0'`. Gepruefter main-Commit `1e05e203eb98acfe788c6d69ea0738e0b49fe86e`, PR-Merge-Commit `6341005`.

Neu: `eg_shopping/stockup.py` belegt moegliche fruehe Einkaeufe anhand heute gueltigem Angebot, bereits bekanntem Zukunftspreis, gleicher Variante, Budget inkl. Pfand, Lagerkapazitaet und Haltbarkeit. Ohne Belege kein behaupteter Spareffekt. CLI-Port `evaluateEarlyPurchase`; Interessenfilter fuer FoodTypes und vom Host uebergebene filialspezifische Gehdistanzen. Alles nur Vorschlaege, keine Buchungen. Status bleibt `PARTIAL_READY`: globale standort- und budgetuebergreifende Optimierung, komplexe Coupons/Versand, Herkunftsrechte externer Daten und Android-Port nicht abgenommen. Folge: weitere robuste Vertrags-/Fehlerfallpruefungen und detaillierte Kotlin-Portspezifikation. Dokumentationscommits nach CI aendern keine Fachlogik.
