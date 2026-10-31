# Abnahmeprotokoll – Offline-Fachkern (31.10.2026)

**Vertrag:** `EG-Architecture 1.0.0-draft`, zuletzt gelesen `d22862739bd0e3ef8451ce029e54f7c33ee53e40`. Kein Produktions-/Händler-API-/Android-Test. **Letzter belegter Test:** GitHub Actions https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41221646056, PR-Merge `ebde5c7` gegen main `4593b195860432426c878d8535b969f05f779db7`, **82 bestanden / 0 fehlgeschlagen / 0 übersprungen**.

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
