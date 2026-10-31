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


## Zusatzmatrix ADR-014/016 – unabhängig neu geprüft, 31.10.2026

**Quelle:** Architektur-Head `f1984378d81f4d49ca93e5da195ecbc4d7260f80` (ADR-017 neu, v1.1 weiterhin Draft), `docs/PRICE_RIGHTS_AND_DISPLAY.md`, `docs/RETAILER_SOURCE_POLICY.md`, `policies/retailer-source-capabilities.v1.json` v1.0.1. Die unveränderte Händler-Policy ist in `eg_shopping/source_policy.py` offline umgesetzt. Diese Ergänzung erweitert die bestehenden 18 Pflichtfälle, ersetzt sie nicht.

| Zusätzlicher Abnahmefall | Ausführbarer Nachweis in `tests/test_source_policy.py` |
| --- | --- |
| ALDI Nord/Süd, REWE, Lidl beide Operationen; übrige vier nur Angebote | `test_capability_matrix_eight_retailers` |
| Forschungsmodus bleibt getrennt von Anzeige | `test_research_is_separate_from_display` |
| Fremde UNVERIFIED/RESTRICTED und fehlende Anzeigeerlaubnis: kein Preis, kein Link, Grau | `test_unverified_restricted_and_missing_permission_never_visible` |
| Reguläre Penny/Kaufland/EDEKA/Netto-Snapshots können nicht als Angebote umdeklariert werden | `test_restricted_retailer_regular_snapshot_not_relabelled` |
| Erlaubte Operationen bei allen acht Händlern (mit synthetischen, expliziten Rechtebelegen) | `test_positive_regular_four_and_offers_eight` |
| Unzulässiges Vergleichsziel/Katalog: kein Preisexport, Coverage unvollständig | `test_target_and_catalog_exclusion_no_price_leak` |
| CLI-Opt-in, ungültiger Kontext und Rückwärtskompatibilität | `test_cli_opt_in_and_backward_compatibility` |
| Interessenliste blendet unberechtigte Quellen aus und meldet Grau | `test_offer_interest_excludes_unlicensed_source` |
| Einkaufsvorschlag kann keinen ausgefilterten Preis als bewiesene Kosten verwenden | `test_purchase_proposal_cannot_use_unverified_snapshot` |
| Unbestätigter OCR-Entwurf, fehlende Bonidentität: keine Preis-/Bestandsbuchung | `test_ocr_draft_or_missing_identity_no_price_or_booking` |
| Bestätigter eigener Bon nur datiert/historisch, deterministisch idempotent | `test_confirmed_local_receipt_dated_idempotent_and_not_current` |
| Eigener Bon legalisiert keine fremden Preisalternativen | `test_private_receipt_cannot_legalize_external_price` |

**Echte CI:** [Run 41227197394](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41227197394), Head `92a764fce3601fec5940cb6d04afdc1a47a72142`: **119 Pass, 0 Fail, 0 Skip**. Nach Aktualisierung der lokalen v1.1-Draft-Schema-/Beispielkopien auf die neuesten Architektur-Blobs (`dca777d219307a90bf3d4dff6189fbf12476c508`, `dc8eb8155564d2c595bf5b4b5676d0b92aeba0b9`) erneut [Run 41227315544](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41227315544), Head `9efa38924fb5929b56286eacdd3e57f5818f839f`: **119 Pass, 0 Fail, 0 Skip**. Kommandos: `python -m pip install 'jsonschema[format]==4.23.0'`; `python -m unittest discover -s tests -v` (Python 3.12, GitHub Actions Ubuntu). Nur synthetische Offline-Fälle.

**Nicht durch diese Abnahme bewiesen:** echte Rechte-Registry/Signatur und Quelle-zu-Verwendungszweck-Freigabe, Live-Quellen, Android-UI-Zweitgate, dauerhafte Bon-Transaktionsdeduplizierung, v1.1-Stabilisierung und Codex-Integration. Der neue Nutzungsmodus ist **OFFLINE_VERIFIED**, nicht `SOURCE_VERIFIED` oder `INTEGRATED`.
