# Abnahmeprotokoll – Offline-Fachkern (31.10.2026)

**Vertrag:** `EG-Architecture 1.0.0-draft`, zuletzt gelesen `d22862739bd0e3ef8451ce029e54f7c33ee53e40`. Kein Produktions-/Händler-API-/Android-Test. **Letzter belegter Test:** GitHub Actions https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222789227, PR-Merge `571a9c7` gegen main `1373cac61f7ec8b41fe505044cdb2e4409df6974`, **92 bestanden / 0 fehlgeschlagen / 0 übersprungen**.

```bash
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

## Pflichtfall → ausführbarer Nachweis

| Nr. | Pflicht aus docs/ACCEPTANCE.md | Test(e) |
| --- | --- | --- |
| 1 | Bio-Hafer 1,99 vs. Bio 1,79; rot, 20 Cent, kg | `test_red_and_exact_saving_and_rate` |
| 2 | Konventionelle Alternative 0,99; orange parallel | `test_red_orange_and_grey_coexist` |
| 3 | Penny/EDEKA/Netto-Lücken, grau | `test_red_orange_and_grey_coexist`, `test_no_absolute_best_price_with_unknown_coverage` |
| 4 | Bio unbekannt ist nicht false | `test_unknown_bio_is_not_false` |
| 5 | Marke vs. Eigenmarke | `test_brand_private_label_comparable` |
| 6 | Süßes Müsli nicht automatisch wie Hafer | `test_sweetened_muesli_not_oats` |
| 7 | 2×500g-Gebinde und Packungspreis | `test_multi_pack_cheaper_per_kg_not_per_pack`, `test_mix_better_than_single_cheapest_unit_rate` |
| 8 | Ananas 1 Stück, kein geratener kg-Preis | `test_piece_not_kg_or_inferred_weight` |
| 9 | Liter-/Abtropfgewichts-Grenze | `test_litre_conversion_and_drained_basis`, `test_unconfirmed_quantity_no_conversion` |
| 10 | Angebot beginnt erst morgen | `test_tomorrow_sale_not_now_and_other_date_reported` |
| 11 | Online, Versand, App-Coupon, Pfand | `test_online_shipping_and_coupon_and_deposit_separated`, `test_deposit_cash_counts_against_budget` |
| 12 | Historischer Kauf ohne Rückschau | `test_confirmed_past_purchase_no_future_hindsight`, `test_past_cheaper_unit_rate_does_not_prove_money_saved` |
| 13 | Altpreis und historische Beobachtung nicht aktuell | `test_old_price_and_historical_paid_not_current`, `test_stale_regular_not_claimed_as_current` |
| 14 | Kochplan + Portionsverzehr ohne doppelte Rohware | `test_preparation_and_consumed_portions_not_counted_twice`, `test_actual_consumed_prepared_portions_do_not_create_raw_baseline` |
| 15 | Fehlender Etat/Bestand/Kapazität = UNKNOWN | `test_unsafe_lot_excluded_unknown_stock_not_zero`, `test_missing_source_and_deposit_never_claims_cash_budget`, `test_unknown_demand_explicit_null_not_zero` |
| 16 | Rabatt und Mindestpackzahl nur bei erfüllbaren Bedingungen | `test_multibuy_only_when_threshold_achieved`, `test_coupon_without_explicit_proof_excluded` |
| 17 | Gesperrte Chargen nicht nutzbar | `test_unsafe_lot_excluded_unknown_stock_not_zero`, `test_expires_before_need` |
| 18 | Angebotsinteresse bucht keinen Kauf | `test_interest_is_proposal_never_purchase` |

Weitere nachgewiesene Tests: Acht-Händler-Katalog mit regulären Preisen, FEFO in 1/7/28/56-Tage-Horizonten, budget-/kapazitätsbegrenzte Mischgebinde, gebietsbezogene Interessenfilter, Zukunftsangebots-Vorziehen nur mit bekannten Beweisen, Schema-Konformität sämtlicher Beispielnachrichten und des `comparison.result`-Exports, fehlender Zeitstempel, fehlende Packungszahl, alternative Retailer-Stores und bewusst falsche Daten.

## Integrationsgrenzen

Die Engine arbeitet offline auf standardisierten Daten-Snapshots. **Keine** API-Abdeckung, Live-Händlerverfügbarkeit, Nutzungsrechte fremder Webseiten, fehlerfreie Kamera-/Android-Migration oder globale Einkaufsrouten-Optimierung ist damit bewiesen. Eine reine Python-Referenz mit dokumentiertem Kotlin-Migrationspfad ist mit dem Architekturentwurf vereinbar; `INTEGRATED` darf nur Codex nach realer App-Integration und Prüfung setzen. Erweiterte Interessen-/Nachkauf-DTOs sind noch als Änderungsantrag dokumentiert, kein freigegebener neuer gemeinsamer Vertrag.

**Zusätzlicher CLI-End-to-End-Nachweis:** `tests/test_cli.py` prüft das dokumentierte Input-JSON gegen einen echten `python -m eg_shopping`-Prozess, negative CLI-Fehler mit Exit 2 sowie seiteneffektfreie Bedarfsberechnung. Kotlin-Portspezifikation: `docs/KOTLIN_MIGRATION_SPEC.md`. Diese beiden Prüfungen ergänzen die 18 Pflichtszenarien, ersetzen keine Geräte-/App-Tests.

## Nachprüfung der Quellen- und Einkaufsbeweiskette (31.10.2026)

CI-Run [41222176171](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222176171) schlug zunächst mit **85 Tests, 2 Fehlern** fehl (ein bewusst widersprüchliches Datumsintervall und fehlende Rückgabe präziser Ablehnungsgründe). Nach Korrektur und ergänzender Prüfung: [41222463623](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222463623) **89/89 grün**; anschließend [41222789227](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41222789227) **92/92 grün**. Neue Regressionstests belegen: lokale Kalendertage Europe/Berlin, Rot plus Grau bei nur kettenweiter statt bestätigter Filialgültigkeit, Unbekannt-Scope und nach Entscheidungszeitpunkt beobachtete Preise, doppelte Beobachtungs-IDs, Auswahl belegter Preise vor fraglichen Quoten, Checkout-Budget inkl. Pfand, Varianten-/Bio-Konflikte, unbestätigte Coupons und mehrere Händlerangebote für **dieselbe** Produktidentität.

**Kernbegrenzung:** Selbst vollständig grüne synthetische Tests bescheinigen keine Supermarkt-API-Vollständigkeit, rechtliche Quellenfreigabe, Echtzeitverfügbarkeit oder Android-Integration. Die Abnahme gilt nur für die offline ausführbare Referenzlogik.

## Nachabnahme der aktualisierten Architekturvorgaben, 31.10.2026

**Geprüfter aktueller Fachcode:** main-Commit 05ec7fdeed29fc80392e35478fcfd4e923268ecf, erfolgreich auch als PR-Merge d97624e in GitHub Actions [41228078142](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41228078142). Befehle: python -m pip install 'jsonschema[format]==4.23.0' und python -m unittest discover -s tests -v, Python 3.12/Ubuntu. **127 Tests bestanden, 0 Fehler, 0 übersprungen.** Dokumentiert im CI-Job 124616327776. Nachfolgender Merge #8: a3d14e76867ed0b2f576a8eb7d11c34db1362f26; nur Dokumentationscommits seitdem.

Vorheriger Prüflauf 41227713718 mit 124 Tests, 1 Fehlversuch: falsche Erwartung von 11 wörtlichen Architektur-Fixtures; das Schema-Repository enthält 9 wörtliche Nachrichten und zusätzliche generierte Positivtests. Die Testannahme wurde berichtigt, nicht das Schema abgeschwächt. Danach 41227774941 mit 124/124 grün und 41227901176 mit 126/126 grün. Der letzte 127er-Lauf erfasst auch die abschließende Rechtehärtung.

Neu tatsächlich geprüfte Anforderungen:
- ADR-014: kein sichtbarer APP_DISPLAY-Preis, Preislink oder Ersparniswert aus externen Quellen mit UNVERIFIED/RESTRICTED; zusätzliche Quellrechtsreferenz und vertrauenswürdige Hostfreigabe erforderlich. Fehlende Quellen erzeugen Datenlücke und grau statt Bestpreisbehauptung. Keine Umgehung über den untrusted JSON-CLI-Pfad.
- ADR-016: gezielte reguläre Produktpreisabfragen nur ALDI_NORD, ALDI_SUED, REWE, LIDL; PENNY, KAUFLAND, EDEKA und NETTO_MD werden dafür abgewiesen, veröffentlichte Aktionen bleiben funktional möglich. Quelle-/Anzeige-Rechte separat geprüft.
- Eigener bestätigter datierter Bon als PRIVATE_USER_HISTORY ist kein aktueller Händlerpreis. Historische Fremdalternativen und Vorverlegung werden separat auf Quellenrechte geprüft. Keine Bestands-/Kaufbuchung.
- ADR-017: typisierte unknownNeeds[] mit echter null-Datenlage und dueDate|null, packageLines[] mit ursprünglichen ID-/Mengen-/Cents-/Pfandangaben und überprüfter Arithmetik, PROVEN nur bei nachgewiesener positiver historischer Warenpreisersparnis; savingsBasis verpflichtend MERCHANDISE_ONLY.
- Die bisherigen 18 Pflichtfälle des eigenen docs/ACCEPTANCE.md sowie die JSON-Schemaverträge des unveränderten 1.0.0-draft verbleiben Teil derselben durchlaufenen Test-Suite.

Verwendete Quellvertragsstände: EG-Architecture HEAD d7aa7dda1f0a34b52102b35785195e7ade26ceb4; v1.1-Schema-Blob dca777d219307a90bf3d4dff6189fbf12476c508; Händler-Policy-Blob 06a05d5c47be8d67fb75dfca11821d8793be86fb. Beide Kopien unverändert im einzigen eigenen Schreibrepository.

**Begrenzung des Nachweises:** Das Ergebnis beweist die lokale deterministische Modullogik und das experimentelle Schema-Mapping, nicht die Authentizität einer echten Hostfreigabe, nicht tatsächliche externe Datenrechte, nicht Supermarkt-Live-Abdeckung, nicht Android-Hardware/Room und keine Produktionsintegration. Status: Offline-Kern READY_FOR_INTEGRATION, opt-in-v1.1 SCHEMA_TESTED/EXPERIMENTAL, App INTEGRATED durch Codex noch offen.
