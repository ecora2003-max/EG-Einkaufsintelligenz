# Status und Wiederaufnahme — EG-Einkaufsintelligenz

**Datum:** 31.10.2026, **Vertrag:** EG-Architecture `1.0.0-draft` (zuletzt gelesen `d22862739bd0e3ef8451ce029e54f7c33ee53e40`). **Status: `READY_FOR_INTEGRATION` für den ausschließlich offline arbeitenden Python-Referenzkern**, ausdrücklich **nicht** `SOURCE_VERIFIED` oder `INTEGRATED`.

## Tatsächlich implementiert

- Deterministischer, zustandsfreier Python-Fachkern `eg_shopping/engine.py` und standardisierte JSON-CLI `eg_shopping/cli.py`, keine externen APIs/DB/Room-Abhängigkeiten.
- `compare_catalog` und `compare_prices`: alle tatsächlich gelieferten Händler- und regulären Preis-Snapshots, exakte Grundpreise, Mengenbasis-/Gebindekontrolle, Rote/Orange/Graue parallele Signale, markenunabhängige FoodType-Vergleiche, explizite Substitution, Ausschluss unbewiesener Online-/Coupon-/Pfand-Konditionen, Zeit-, Filial- und Quellenprüfung, `comparison.result`-Envelope.
- `project_needs`: FEFO-Chargen, gesperrter Bestand, plan-/historiebezogene Rohbedarfe, kumulative Horizonte 1/7/28/56 Tage und Duplikatprüfung; Baseline nur mit bestätigter Verbrauchsbeobachtung und Mindestumfang.
- `pack_optimizer.py` / `suggest_purchases`: beschränkte genaue Mischgebinde-Aufrechnung, bekannte Teilsumme, Budgets, periodenbezogene Unsicherheit, aggregierte Lagerplatzprüfung, konservative Haltbarkeitskontrolle.
- `evaluate_offer_interest`, `list_offer_interests`: getrennte Angebotsinteressen und Einkaufslisten-Vorschläge ohne Kaufbuchung.
- `evaluate_past_purchase`: nur bestätigte historische Käufe und im historischen Zeitpunkt bereits beobachtete, datums- und marktgültige Alternativen.
- Synthetische Fixture `examples/compare_request.json`; kopiertes JSON-Schema und Beispiele aus Architektur.

## Verifizierte Tests

**Historischer GitHub-Actions-Testlauf (früherer Stand):** https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41220132440  
**Geprüfter Head:** `20adc0685b33562b1170aaf36fa724e8d856a8d1` (PR-Merge-Commit `894d580`, main-Basis `9518b7a69c8b7e5dd6ecea3d4676823c620c9155`) (PR-Merge-Checkout inkl. vorangegangener `main`-Änderungen).  
**Runner:** Python 3.12.15 auf Ubuntu.  
**Kommandos:**
```sh
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```
**Ergebnis:** 62 Tests / **62 bestanden, 0 fehlgeschlagen, 0 übersprungen**, darunter formale Validierung der Architektur-Beispielnachrichten und `comparison.result`. Logs belegen dieses Ergebnis. Vorheriger CI-Lauf mit einem Testproblem (Formatvalidierung; nicht-failendes Invalidbeispiel) war **fehlgeschlagen** und wurde durch stärkere Negativprobe und Installation `jsonschema[format]` korrigiert. Weitere Commits nach diesem Lauf (Dokumentation) sind noch auf neuen CI-Status zu prüfen; der zuvor bestandene Testlauf belegt nicht jede spätere Codeänderung.

## Historische offene Punkte (neuester Status am Dokumentende maßgeblich)

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

## Verifikation 31.10.2026, vierter Meilenstein
CI https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41221288821 : 77/77 bestanden, 0 fehlgeschlagen, 0 uebersprungen; `python -m unittest discover -s tests -v` nach `jsonschema[format]==4.23.0`, getestet gegen main `2735680577135551b4fc9ed8a7d4bee148de24aa` im PR-Merge `5dfd03e`. Historische Kaufersparnis wurde korrigiert: ein guenstigerer Einheitspreis bei groesserem Mindestgebinde beweist keine niedrigeren damaligen Ausgaben. Ausgewiesen werden erforderliche Packungen, damals belegbare Waren-/Checkout-Kosten, tatsaechliche Ersparnis oder nur `unitOnlyAlternatives`. Unbekanntes Pfand bleibt null. STATUS weiterhin PARTIAL_READY bis restliche Randbedingungen/Integration geprueft sind.

## Abschluss der Offline-Modulabnahme – 31.10.2026
**Abnahmestatus: READY_FOR_INTEGRATION (nur deterministischer, rein offline arbeitender Referenzkern)**. Alle 18 individuellen Pflichtszenarien sind durch ausgeführte Tests belegt, Zuordnung in `docs/ACCEPTANCE_REPORT.md`. Aktuelle CI https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41221646056 : 82/82 Pass, 0 Fail, 0 Skip, getestet main `4593b195860432426c878d8535b969f05f779db7` im PR-Merge `ebde5c7`, Python 3.12, Befehl `python -m pip install 'jsonschema[format]==4.23.0'` und `python -m unittest discover -s tests -v`. Vergleich, Einkauf, Bedarfsprognose, Angebotsinteresse, historischer Kauf, nachgewiesene Angebotsvorverlegung, CLI und Schema-Export sind offline lauffähig. End-to-End-CLI mit synthetischen JSON-Dateien getestet. Genaue Kotlin-Portierung beschrieben in `docs/KOTLIN_MIGRATION_SPEC.md`.

**Freigabegrenze:** Dieser Status gilt nicht fuer reale Supermarkt-Datenbeschaffung, Filialpreise, Lizenzrechte, Live-APIs, Android-Installation, Room/Compose-Oberflaechen, Migrations- oder Geraetetests. Architektur-Contract bleibt `1.0.0-draft`. Nachzuziehende App-Integration und abweichende Vertragsfreigaben bleiben Codex/Architektursteuerung vorbehalten. Keine Nutzer- oder Lagerbuchung im Modul. Optionale Weiterentwicklungen (globale Laden-/Warenkorbroute, Coupon-Kombinationen, Retouren-Pfand) sind keine behaupteten bestehenden Faehigkeiten. Ab jetzt nur bei Regression, freigegebener Vertragsaenderung oder neuer Anforderung weiterentwickeln; sonst offline als uebergabereif belassen.

## Wiederaufnahme- und Testnachweis 31.10.2026 – erneute unabhängige Prüfung

Aktueller Status: `READY_FOR_INTEGRATION` nur für den deterministischen Offline-Referenzkern; weder Live-Quellrechte noch Haupt-App-Integration sind freigegeben. Eigene Architekturdateien bleiben unverändert, Vertrag `1.0.0-draft`, Architektur SHA `d22862739bd0e3ef8451ce029e54f7c33ee53e40`.

**Neu implementierte Korrekturen:** Angebote eines identischen `productId` verschiedener Supermärkte werden über eindeutige `priceObservation.observationId` getrennt verarbeitet und nach Filiale/Händler ausgewiesen. Konservativer Check der Preisquellen, Bio-/GTIN-/Variantenattribute, Produkt-/Quellenbedingungen, Marktscope, Preisart und Gültigkeit. Bei nicht belegtem Preis sind Cash-Checkout, verifizierte Gesamtkosten und verbleibender Etat `null`; nur separate geschätzte Checkout-Kosten können angezeigt werden. Für belegte Angebote ist die Budgetgrenze auf Warenpreis **plus Pfand** bezogen. Reguläre Tagespreise werden anhand Europe/Berlin eingeordnet; kettenweiter statt belegter lokaler Preis erzeugt Grau, unbekannte Filiale ist kein sicherer Einkaufspunkt. Doppelte IDs und Quellenzeitpunkte nach Entscheidung lösen keinen falschen positiven Preisbeweis aus.

**Echte CI-Evidenz:** Der erste Prüflauf [41222176171](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222176171) umfasste 85 Tests und scheiterte mit 2 Fehlern; beide behoben. Der nächste Lauf [41222463623](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222463623) bestand 89/89. Letzter fachlicher Testlauf [41222789227](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222789227): **92 bestanden, 0 fehlgeschlagen, 0 übersprungen**, Python 3.12 / Ubuntu. PR-Merge-Checkout `571a9c7` auf Basis des Fachcode-Commits `1373cac61f7ec8b41fe505044cdb2e4409df6974`. PR #3 wurde anschließend erfolgreich ins eigene Repo gemergt (Merge-SHA `739da6b657b12330adcb7e844892d1e617acc516`); seither nur Dokumentation verändert. Prüfkommandos:

```bash
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

**Offene Integrations- und Qualitätsgrenzen:** Keine belegte Live-Abdeckung sämtlicher Filialen oder Nutzungsrechte, keine garantierte Liefer-/Regalverfügbarkeit, keine global optimierte Mehr-FoodType-Route, keine vollständige Coupon-/Versandkosten- oder Pfandrückgabeoptimierung. Noch kein Kotlin-Port, kein Room/Compose-/Android-Integrationstest; `INTEGRATED` bleibt Codex vorbehalten. Bei erneuter Aktivierung erst AGENTS/ACCEPTANCE/STATUS und Architektur sowie aktuelle GitHub-Actions-Logs lesen und **nur bei neuer Anforderung, Regression oder neuer freigegebener Vertragsversion** den bereits abgenommenen Offline-Kern ändern. Neue Implementierungen ausschließlich im eigenen Schreibrepo, alle Tests erneut ausführen und diesen Abschnitt aktualisieren.

## Abschlusskontrolle und Vertragsbeobachtung – 31.10.2026, 18:20 CET

**Abgenommener Stand:** `READY_FOR_INTEGRATION` ausschließlich für den unveränderten deterministischen Offline-Referenzkern auf Basis `contracts/v1` (`1.0.0-draft`), nicht für Android oder Live-Händlerquellen. Geprüfter Repository-Head vor diesem reinen Dokumentationscommit: `bc6859271da1a507673967e2a97c585ecc59f130`.

**Tatsächlich ausgeführte CI auf genau diesem Head:** [GitHub Actions Run 41222960098](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222960098), 31.10.2026 17:07 UTC, Python 3.12, Ubuntu. Befehle: `python -m pip install 'jsonschema[format]==4.23.0'` und `python -m unittest discover -s tests -v`. Aus dem Joblog: **92 Pass, 0 Fail, 0 Error, 0 Skip** (`Ran 92 tests ... OK`). Keine lokalen Tests in dieser Kontrolle ausgeführt; CI-Protokoll direkt geprüft. Die Abnahmematrix in `docs/ACCEPTANCE_REPORT.md` bleibt für die bestehenden 18 Pflichtfälle maßgeblich.

**Neue Architekturquelle:** `EG-Architecture` Head `25541fc877751f81848ac160cb0d9577cbcf83c8`. Neben unverändertem `contracts/v1` liegt nun **`contracts/v1.1` (`1.1.0-draft`)** mit vier additiven Shopping-Nachrichtentypen (`shopping.need.projection`, `shopping.purchase.suggestion`, `shopping.offer.interest`, `shopping.past.comparison`). Die bisherigen `PriceObservation`- und `ComparisonResult`-Definitionen sind inhaltlich unverändert. Architektur-CI [41224097675](https://github.com/ecora2003-max/EG-Architecture/actions/runs/41224097675): 14 positive / 24 negative Vertragsbeispiele bestanden. **Dieser neue Draft ist nicht als stabile, mit Codex abgestimmte Integrationsversion freigegeben und wird vom Modul derzeit nicht als `1.1.0-draft`-Envelope exportiert.** Keine stillschweigende Versionsumstellung.

**Offen / Grenzen:** Gemeinsame v1.1-Freigabe und entsprechende Adapter-/Schema-Abnahme; Codex-Kotlin-/Room-/Compose-Integration; Händlerquellenrechte, echte Filial- und Marktpreisabdeckung; globale Mehr-FoodType-/Routenoptimierung, vollständige Coupon-/Pfand-Retourenmodelle. Keine behauptete absolute Bestpreis- oder Live-Verfügbarkeitsgarantie.

**Nächster Schritt und Wiederaufnahme:** Bis zur ausdrücklichen Vertragsfreigabe oder einem reproduzierbaren Regressionstest **keine weiteren Fachcodeänderungen**. Bei neuer Anforderung Architektur-Commit und Entscheidungen frisch lesen, v1.1-Feldabbildung als getrennten Adapter entwickeln, Schema-Positiv-/Negativtests und gesamte Offline-Suite erneut ausführen; Ergebnis mit Commit-SHA und CI-Logs hier dokumentieren. Nur dieses Repository darf beschrieben werden; `INTEGRATED` bleibt Codex vorbehalten.

## Entwicklungsfortsetzung 31.10.2026, 18:22–18:30 Uhr Berlin – experimenteller v1.1-Adapter

**Aktuelle Architekturbasis:** `EG-Architecture` main `ecd26097eb5678296a14de9d9b5db79ccea9be64`. Neu existiert `contracts/v1.1` mit vier Shopping-Nachrichten im Status **`1.1.0-draft`**. Die beiden Dateien wurden als unveränderte **Testkopien** unter `contracts/v1.1/` in dieses Repository übernommen. Architektur- und Haupt-App-Repositories wurden nicht geschrieben.

**Implementiert:** `eg_shopping/draft_v11.py` als ausschließlich direkt importierbarer, eigenständiger experimenteller Adapter für `shopping.need.projection`, `shopping.purchase.suggestion`, `shopping.offer.interest`, `shopping.past.comparison`. Es gibt **keine** automatische 1.1-Versionsumschaltung, keine CLI-Freigabe und keine Änderung der vorhandenen `1.0.0-draft`-Envelopes. Die Ausgaben dokumentieren unbekannte Werte und Referenzen; keine Kauf-/Bestandsbuchungen. Nicht bekannte Rohbedarfs-Einheiten werden **nicht erfunden**: Typisierte Bedarfszeilen bleiben aus, und die unveränderten IDs, Fälligkeitsdaten und Null-Mengen werden in einer `unknownNeeds[]`-Extension mit `completeness=PARTIAL` transportiert. Bei gemischten Packungen mit fehlender Angebotsbeobachtungs-ID sind `expectedCents` und `checkoutCents` ausdrücklich `null`, selbst bei vom Host behauptetem `priceEvidenceVerified=true`.

**Tatsächlich ausgeführte neue Testnachweise:**

- [GitHub Actions 41224489521](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224489521): **106 bestanden / 0 fehlgeschlagen / 0 übersprungen**, PR-Merge `6d2ff53` mit main-Stand `2c25588dd183e2c6d8c73ba318d47bb54f0981d1`.
- [GitHub Actions 41224632634](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224632634): **106 bestanden / 0 fehlgeschlagen / 0 übersprungen**, PR-Merge `004077f`, main-Stand `d59093b7e1eed61d39d88fa345aa74b10d91eb38` (unbekannte Bedarfe verlustfrei als Extension).
- **Neuester fachlich verbindlicher Test:** [GitHub Actions 41224765046](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224765046), Python 3.12/Ubuntu, PR-Merge `67084be` auf main-Stand `f56ade91d2192d41cb21ac780d6f9937d6722702`: **107 bestanden, 0 fehlgeschlagen, 0 übersprungen**. PR #5 wurde anschließend unter Commit `da08f07122a4924f1437b0bb2a1a6e9c524762c7` in das einzige Schreibrepository gemergt.

**Ausgeführte Befehle auf GitHub Actions:**

```bash
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

`tests/test_draft_v11.py` validiert die **neun** kanonischen Architektur-Beispielnachrichten mit `jsonschema.Draft202012Validator` und Formatchecker; alle vier experimentellen Adapter mit Positiv-/Negativfällen; zusätzlich laufen alle bisherigen 1.0-Offline-Abnahmetests. Der neue Draft ist daher **SCHEMA_TESTED / EXPERIMENTAL**, keinesfalls als fertiger gemeinsamer Integrationsvertrag freigegeben. Der **bereits abgenommene unveränderte v1.0-Offline-Kern** bleibt `READY_FOR_INTEGRATION`.

**Offene v1.1-Freigabefragen:** Vollständig typisierbarer unbekannter `Quantity.unit`-Wert, `packageLines[]` für gemischte Gebinde und Definition der `savingsProvenCents`-Bezugsgröße (Warenpreis oder Checkout). Dazu stehen begründete Anforderungen im **eigenen** `docs/CONTRACT_CHANGE_REQUEST.md` und Feldzuordnungen in `docs/V11_DRAFT_COMPATIBILITY.md`. Keine automatische v1.1-Freigabe ohne Architektur-ADR und Codex-Abnehmerprüfung, keine Android- oder Live-Datenabnahme. Die nächsten Ausführungen sollen zuerst Version/SHAs und CI erneut lesen; bei neuem Architekturentscheid Schema/Adapter aktualisieren und vollständige Tests ausführen, sonst den abgenommenen Referenzkern nicht ohne Anlass verändern.

**Quellvertrags-Nachprüfung (31.10.2026, ca. 18:30 CET):** Architektur-Head nun `1cf2f3fb774ca676a4231d04bf383d941403ee29` (nur Dokumentation der Schema-CI); kanonische `contracts/v1.1/contract.schema.json`-Blob-SHA weiterhin unverändert `f4755a0a2dfbd8c4f58f2778fa21800b9e3ffbdc`. Die lokale Testkopie basiert somit auf derselben Architektur-Schemaversion; keine neue Freigabe angenommen. Alle Fachcodeänderungen wurden vor den letzten Dokumentationscommits durch CI 41224765046 getestet.


## ADR-014/016 unabhängige Neuabnahme – 31.10.2026, Prüfbasis vor CI

**Geprüfte Ausgangs-SHAs:** Einkaufsintelligenz `acfa4be64e2f671b27e917da8eeb23e3716a071a`, Architektur `e20fae968e5253f2f6ecf7d4268b31293ae271ce`; verbindliche Händlermatrix `policies/retailer-source-capabilities.v1.json` Version 1.0.1, Rechte-Richtlinie `docs/PRICE_RIGHTS_AND_DISPLAY.md`. Alte CI 41224765046: 107/107 grün, **kein** Nachweis für ADR-014/016.

**Unabhängiger Befund:** Im alten Fachkern schloss `_valid` zwar `RESTRICTED`, aber nicht `UNVERIFIED` für die App-Anzeige aus. Expliziter `usageContext`, Rechtebeleg, ADR-016-Händlerscope und bestätigte lokale Bonidentität fehlten. Die bisherige Freigabe gilt daher **nicht** für diese neuen Produktiv-Anzeigeanforderungen.

**Neue Implementierung auf `audit/adr016-display-policy-20261031`:** `source_policy.py` mit getrenntem funktionalen Händler- und quellenbezogenen Rechte-Gate; `engine.py`, `cli.py`, `stockup.py` mit explizitem Nutzungskontext und fehlender Coverage/Grau; private datierte Bonposition ohne Buchung; synthetische Negativ-/Regressionstests `tests/test_source_policy.py`. Der bisherige `RESEARCH_ONLY`-Default ist bewusst rückwärtskompatibel, aber kein Produktiv-App-Default.

**Testkommandos:** `python -m pip install 'jsonschema[format]==4.23.0'` und `python -m unittest discover -s tests -v`. **Zum Zeitpunkt dieses Eintrags: neuer Code CI noch SKIP / nicht verifiziert; keine neue Freigabe.** Der neue v1.1-Entwurf bleibt `1.1.0-draft`, nicht stabil. Risiken: Rechtebelege werden in diesem Offline-Kern nur strukturell geprüft (Host muss unabhängig Registry prüfen); keine realen Quellrechte/Filialabdeckung, keine Android-/Room-/Compose-Integration, keine dauerhaft persistierte Bon-Idempotenz, keine globale Einkaufsoptimierung. Nächster Schritt: PR-CI auf aktuellem HEAD prüfen, Fehler beheben, Status mit Pass/Fail/Skip und SHA aktualisieren; `INTEGRATED` nur Codex.


## ADR-014/016 Prüfergebnis und Architekturabgleich – 31.10.2026, 19:00 CET

**Neuster gelesener Architektur-HEAD:** `f1984378d81f4d49ca93e5da195ecbc4d7260f80`. Händler-Policy-Blob `06a05d5c47be8d67fb75dfca11821d8793be86fb` unverändert; `PRICE_RIGHTS_AND_DISPLAY.md`-Blob `26e4df51a6b4b8e2cbd898311d69ff2d274de745`. ADR-017 hat inzwischen den **nicht freigegebenen** v1.1-Draft verändert: lokale Testkopien wurden auf Architektur-Schema `dca777d219307a90bf3d4dff6189fbf12476c508` und Beispiele `dc8eb8155564d2c595bf5b4b5676d0b92aeba0b9` aktualisiert, **ohne** v1.0-CLI-Vertragswechsel.

**CI-Nachweise (echte GitHub-Actions-Joblogs):** [41227197394](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41227197394), Commit `92a764fce3601fec5940cb6d04afdc1a47a72142`: **119 Pass, 0 Fail, 0 Error, 0 Skip**. Nach Schemaaktualisierung [41227315544](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41227315544), Commit `9efa38924fb5929b56286eacdd3e57f5818f839f`: **119 Pass, 0 Fail, 0 Error, 0 Skip**. Runner: Python 3.12, Ubuntu. Exakte Befehle: `python -m pip install 'jsonschema[format]==4.23.0'` und `python -m unittest discover -s tests -v`. Kein lokaler Lauf (SKIP: lokale GitHub-Checkout-Umgebung nicht vorhanden); CI vollständig ausgeführt.

**Prüfkriterien:** bisherige 18 Pflichtszenarien plus 12 neue ADR-014/016-Negativ-/Positivtests, vollständige Zuordnung in `docs/ACCEPTANCE_REPORT.md`. Alle acht Händleroperationen geprüft; Penny/Kaufland/EDEKA/Netto regulär blockiert, Angebote unter explizitem synthetischem Beleg zugelassen; APP_DISPLAY UNVERIFIED/RESTRICTED blockiert, Coverage/Grau statt Marktbestpreis; private bestätigte Bonposition ausschließlich historisch und ohne Seiteneffekte; RESEARCH_ONLY abwärtskompatibel. Status des neuen Anzeige-Gates: **OFFLINE_VERIFIED**; bisheriger v1.0-Referenzkern bleibt nur offline `READY_FOR_INTEGRATION`.

**Verbleibende Risiken/Schranken:** `displayPermission` ist ein nur strukturell geprüftes, vom Host unabhängig zu verifizierendes Berechtigungsobjekt, kein Rechtstitel; produktiver App-Handler darf `RESEARCH_ONLY` nicht als Default nutzen. Keine realen Quellenrechte/Live-Filialpreise, keine Android-UI-Doppelfilter-/Room-/Geräteprüfungen, keine dauerhaft transaktionale Bon-Idempotenz, keine v1.1-Freigabe, keine globale Mehrmarktoptimierung. Nächster Schritt: CI auf finalem Dokumentations-HEAD prüfen, PR #6 nur bei Grün ins eigene Repo mergen, danach HEAD und CI-Abnahme dokumentieren; `INTEGRATED` bleibt Codex vorbehalten.
