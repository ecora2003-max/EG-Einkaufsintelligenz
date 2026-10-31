"""Synthetic acceptance and regression tests; python -m unittest discover -s tests -v."""
import copy
import unittest

from eg_shopping import (DomainError, compare_catalog, compare_prices, comparison_envelope,
    evaluate_offer_interest, evaluate_past_purchase, list_offer_interests,
    project_needs, suggest_purchases)


DATE = "2026-10-31"
NOW = "2026-10-31T15:00:00+01:00"


def quantity(amount=500, unit="g", basis="NET", count=1, confirmed=True):
    return {"amount": amount, "unit": unit, "basis": basis,
            "packageCount": count, "confirmed": confirmed}


def observation(oid, cents, *, organic=True, food="oats-fine", q=None,
                kind="SALE", store=None, retailer=None, form="fine",
                at=NOW, start=DATE, until="2026-11-06", quality="CONFIRMED",
                brand_kind="PRIVATE_LABEL", brand_name="Home", attrs=None,
                scope="STORE_CONFIRMED", availability="IN_STOCK_REPORTED",
                conditional=None, shipping=None, deposit=0):
    retailer = retailer or "MARKET_" + oid
    store = store or "STORE_" + oid
    data = {"observationId": oid,
            "article": {"label": "Synthetic " + oid, "foodTypeId": food,
                        "gtin": None, "brandName": brand_name,
                        "brandKind": brand_kind, "organic": organic,
                        "attributes": attrs if attrs is not None else {"form": form},
                        "quantity": q or quantity()},
            "scope": {"retailerId": retailer, "storeId": store, "scopeType": scope},
            "priceCents": cents, "currency": "EUR", "priceKind": kind,
            "validFrom": start, "validUntil": until,
            "source": {"origin": "synthetic", "observedAt": at,
                       "dataQuality": quality, "rightsStatus": "UNVERIFIED"},
            "availability": availability, "conditional": conditional or [],
            "depositCents": deposit}
    if shipping is not None:
        data["shippingCents"] = shipping
    return data


def compare(target, *others, coverage=None, **kw):
    return compare_prices(target, list(others), DATE, as_of=NOW, coverage=coverage, **kw)


def with_price_evidence(product):
    product = copy.deepcopy(product)
    product["depositCents"] = 0
    product["priceObservation"] = observation(
        "PRICE-" + product["productId"], product["priceCents"],
        food=product["foodTypeId"], q=product["quantity"], deposit=0)
    return product


class Comparisons(unittest.TestCase):
    def setUp(self):
        self.target = observation("BASE", 199)

    def test_red_and_exact_saving_and_rate(self):
        result = compare(self.target, observation("BIO", 179), coverage={"complete": True})
        self.assertEqual(result["signals"], ["RED_SAME_BIO_CHEAPER"])
        a = result["alternatives"][0]
        self.assertEqual((a["basis"], a["priceDifferenceCents"]), ("kg", -20))
        self.assertEqual(a["pricePerBaseUnitMilliCents"], 358000)
        self.assertEqual(a["exactUnitRateCents"], {"numerator": 358, "denominator": 1})
        self.assertFalse(result["incomplete"])
        self.assertNotIn("CHEAPEST_MARKET", result["bestPriceClaim"])

    def test_red_orange_and_grey_coexist(self):
        r = compare(self.target, observation("RED", 179),
                    observation("ORANGE", 99, organic=False),
                    coverage={"complete": False, "gaps": ["Penny/EDEKA/Netto unknown"]})
        self.assertEqual(r["signals"], ["RED_SAME_BIO_CHEAPER",
                         "ORANGE_DIFFERENT_BIO_CHEAPER", "GREY_MAY_BE_CHEAPER"])
        self.assertEqual(len(r["alternatives"]), 2)
        self.assertTrue(r["incomplete"])
        self.assertTrue(any("Penny/EDEKA/Netto" in x for x in r["gaps"]))

    def test_unknown_bio_is_not_false(self):
        r = compare(self.target, observation("MYSTERY", 50, organic=None),
                    coverage={"complete": True})
        self.assertEqual(r["signals"], ["GREY_MAY_BE_CHEAPER"])
        self.assertEqual(r["alternatives"][0]["bioDifference"], "UNKNOWN")

    def test_brand_private_label_comparable(self):
        a = observation("BRAND", 130, brand_kind="MANUFACTURER", brand_name="Brand")
        r = compare(self.target, a, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["comparability"], "SAME_FOOD_VARIANT")
        self.assertIn("brand/private-label difference", r["alternatives"][0]["evidence"])

    def test_sweetened_muesli_not_oats(self):
        a = observation("MUESLI", 50, food="sweet-muesli")
        self.assertEqual(compare(self.target, a, coverage={"complete": True})["alternatives"], [])
        a = observation("SWEET", 50, attrs={"form": "fine", "sweetened": True})
        self.assertEqual(compare(self.target, a, coverage={"complete": True})["alternatives"], [])

    def test_explicit_substitute_is_not_automatic_red(self):
        a = observation("SUB", 50, food="sweet-muesli")
        matches = [{"targetId": "BASE", "candidateId": "SUB",
                    "matchLevel": "FUNCTIONAL_SUBSTITUTE",
                    "status": "CONFIRMED_BY_USER", "evidence": ["explicit substitution"]}]
        r = compare(self.target, a, matches=matches, coverage={"complete": True})
        self.assertEqual(r["signals"], [])
        self.assertEqual(r["alternatives"][0]["comparability"], "FUNCTIONAL_SUBSTITUTE")

    def test_multi_pack_cheaper_per_kg_not_per_pack(self):
        target = observation("T", 120)
        alt = observation("MULTI", 230, q=quantity(500, count=2))
        r = compare(target, alt, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["priceDifferenceCents"], -5)
        self.assertEqual(r["alternatives"][0]["exactUnitRateCents"]["numerator"], 230)

    def test_litre_conversion_and_drained_basis(self):
        target = observation("LITRE", 240, q=quantity(1000, "ml"))
        alt = observation("HALF", 100, q=quantity(500, "ml"))
        r = compare(target, alt, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["priceDifferenceCents"], -40)
        self.assertEqual(r["alternatives"][0]["basis"], "l")
        drained = observation("DRAIN", 50, q=quantity(500, basis="DRAINED"))
        self.assertEqual(compare(self.target, drained)["alternatives"], [])

    def test_explicit_null_package_count_and_missing_timestamp_stay_unknown(self):
        alt = observation("NOCOUNT", 30)
        alt["article"]["quantity"]["packageCount"] = None
        r = compare(self.target, alt, coverage={"complete": True})
        self.assertFalse(r["alternatives"])
        self.assertIn("GREY_MAY_BE_CHEAPER", r["signals"])
        missing_time = observation("NOTIME", 30)
        del missing_time["source"]["observedAt"]
        r = compare(self.target, missing_time, coverage={"complete": True})
        self.assertFalse(r["alternatives"])
        self.assertIn("GREY_MAY_BE_CHEAPER", r["signals"])
        self.assertTrue(any("timestamp" in gap for gap in r["gaps"]))

    def test_unconfirmed_quantity_no_conversion(self):
        a = observation("BADQ", 30, q=quantity(500, confirmed=False))
        self.assertEqual(compare(self.target, a)["alternatives"], [])
        with self.assertRaises(DomainError):
            compare(observation("BADTARGET", 150, q=quantity(500, confirmed=False)), self.target)

    def test_piece_not_kg_or_inferred_weight(self):
        fruit = observation("PINEAPPLE", 200, food="pineapple", q=quantity(1, "piece", "PIECE"))
        fruit_cheaper = observation("PINEAPPLE2", 150, food="pineapple",
                                    q=quantity(1, "piece", "PIECE"))
        r = compare(fruit, fruit_cheaper, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["basis"], "piece")
        self.assertEqual(compare(fruit, self.target)["alternatives"], [])

    def test_tomorrow_sale_not_now_and_other_date_reported(self):
        tomorrow = observation("FUTURE", 70, start="2026-11-01", until="2026-11-04")
        r = compare(self.target, tomorrow, coverage={"complete": True})
        self.assertEqual(r["signals"], [])
        self.assertEqual([x["observationId"] for x in r["otherDayOffers"]], ["FUTURE"])

    def test_reference_or_stale_target_is_not_a_current_price(self):
        ref = observation("REFERENCE_TARGET", 199, kind="REFERENCE_OLD")
        with self.assertRaises(DomainError):
            compare(ref, observation("CHEAPER", 100))
        stale = observation("STALE_TARGET", 199, kind="LISTED_REGULAR",
                            at="2026-10-01T10:00:00+02:00",
                            start=None, until=None)
        with self.assertRaises(DomainError):
            compare(stale, observation("CHEAPER", 100))

    def test_old_price_and_historical_paid_not_current(self):
        old = observation("OLD", 30, kind="REFERENCE_OLD")
        paid = observation("PAID", 30, kind="HISTORICAL_PAID")
        r = compare(self.target, old, paid, coverage={"complete": True})
        self.assertEqual(len(r["alternatives"]), 0)

    def test_stale_regular_not_claimed_as_current(self):
        stale = observation("STALE", 30, kind="LISTED_REGULAR",
                            at="2026-10-01T10:00:00+02:00", start=None, until=None)
        self.assertEqual(compare(self.target, stale)["alternatives"], [])

    def test_regular_prices_compared_with_sale(self):
        regular = observation("ALDI", 175, kind="LISTED_REGULAR",
                              start=None, until=None, retailer="ALDI_NORD")
        self.assertEqual(compare(self.target, regular)["signals"][0], "RED_SAME_BIO_CHEAPER")

    def test_unknown_deposit_is_not_silent_zero_checkout(self):
        alt = observation("DEPOSIT_UNKNOWN", 50, deposit=None)
        r = compare(self.target, alt, coverage={"complete": True})
        self.assertIsNone(r["alternatives"][0]["checkoutCents"])
        self.assertIn("GREY_MAY_BE_CHEAPER", r["signals"])
        self.assertTrue(any("deposit" in gap for gap in r["gaps"]))

    def test_online_shipping_and_coupon_and_deposit_separated(self):
        online = observation("ONLINE", 50, kind="ONLINE_LISTED", scope="ONLINE",
                             shipping=200, start=None, until=None)
        self.assertEqual(compare(self.target, online, allow_online=True)["alternatives"], [])
        online["shippingCents"] = 20
        r = compare(self.target, online, allow_online=True, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["checkoutCents"], 70)
        coupon = observation("COUPON", 50, conditional=["app coupon"])
        self.assertEqual(compare(self.target, coupon)["alternatives"], [])
        deposit = observation("DEPOSIT", 100, deposit=25)
        r = compare(self.target, deposit, coverage={"complete": True})
        self.assertEqual(r["alternatives"][0]["checkoutCents"], 125)
        self.assertEqual(r["alternatives"][0]["priceDifferenceCents"], -99)

    def test_future_observed_not_available(self):
        a = observation("FUT_OBS", 50, at="2026-11-01T10:00:00+01:00")
        self.assertEqual(compare(self.target, a)["alternatives"], [])

    def test_store_filter_and_out_of_stock(self):
        alt = observation("A", 20, retailer="PENNY", store="P1")
        self.assertEqual(compare(self.target, alt, allowed_stores={"PENNY": ["P2"]})["alternatives"], [])
        alt["availability"] = "OUT_OF_STOCK_REPORTED"
        self.assertEqual(compare(self.target, alt)["alternatives"], [])

    def test_unknown_source_quality_excluded(self):
        a = observation("LOW", 10, quality="ESTIMATED")
        self.assertEqual(compare(self.target, a)["alternatives"], [])

    def test_invalid_price_or_date_fails_closed(self):
        with self.assertRaises(DomainError):
            compare(self.target, observation("NEG", -1))
        with self.assertRaises(DomainError):
            compare(self.target, observation("NAIVE", 25, at="2026-10-31T15:00:00"))
        with self.assertRaises(DomainError):
            compare(self.target, observation("REVERSE", 25, start="2026-11-06", until=DATE))
        with self.assertRaises(DomainError):
            compare_prices(self.target, [], "2026-13-99", as_of=NOW)

    def test_no_absolute_best_price_with_unknown_coverage(self):
        r = compare(self.target, observation("CHEAP", 10))
        self.assertIn("GREY_MAY_BE_CHEAPER", r["signals"])
        self.assertEqual(r["bestPriceClaim"], "CHEAPEST_KNOWN_MATCHING_ONLY")

    def test_deterministic_independent_of_input_order(self):
        a, b = observation("A", 80), observation("B", 95)
        self.assertEqual(compare(self.target, a, b), compare(self.target, b, a))


    def test_catalog_all_eight_and_regular(self):
        retailers = ["LIDL", "ALDI_NORD", "ALDI_SUED", "REWE", "PENNY",
                     "EDEKA", "NETTO_MD", "KAUFLAND"]
        catalog = [observation(f"R{i}", 199-i*10, retailer=name) for i, name in enumerate(retailers)]
        catalog.append(observation("REGULAR", 88, retailer="REWE",
                                   kind="LISTED_REGULAR", start=None, until=None))
        result = compare_catalog(catalog, DATE, as_of=NOW, coverage={"complete": False})
        self.assertEqual(len(result["comparisons"]), 9)
        self.assertFalse(result["omittedTargets"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["comparisons"][0]["signals"])

    def test_combined_capacity_not_reused_for_multiple_products(self):
        view = {"totals": [
            {"foodTypeId": "oats", "quantityToBuy": 500, "unit": "g", "basis": "NET"},
            {"foodTypeId": "rice", "quantityToBuy": 500, "unit": "g", "basis": "NET"}],
            "needs": [
            {"foodTypeId": "oats", "quantityToBuy": 500, "dueDate": DATE},
            {"foodTypeId": "rice", "quantityToBuy": 500, "dueDate": DATE}]}
        ps = [{"productId": i.upper(), "foodTypeId": i, "quantity": quantity(500),
               "priceCents": 100, "shelfLifeDays": 60, "storageClass": "DRY",
               "packageVolumeMl": 800} for i in ("oats", "rice")]
        ps = [with_price_evidence(p) for p in ps]
        b = {"amountCents": 250, "periodStart": DATE, "periodEnd": DATE}
        out = suggest_purchases(view, ps, shopping_date=DATE, as_of=NOW,
                                budget=b, capacity={"DRY": 1000})
        self.assertEqual(out["items"][0]["status"], "FEASIBLE_NOT_PURCHASED")
        self.assertIn("insufficient confirmed storage volume", out["items"][1]["reasons"])

    def test_schema_contract(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema optional dependency absent")
        import json
        from pathlib import Path
        schema = json.loads((Path(__file__).parent.parent /
                             "contracts/v1/contract.schema.json").read_text())
        example = json.loads((Path(__file__).parent.parent /
                              "contracts/v1/examples.json").read_text())
        for message in example:
            jsonschema.validate(message, schema, format_checker=jsonschema.FormatChecker())
        r = compare(self.target, observation("ALT", 100))
        envelope = comparison_envelope(r, created_at=NOW, trace_id="synthetic-01")
        jsonschema.validate(envelope, schema, format_checker=jsonschema.FormatChecker())
        bad = copy.deepcopy(envelope)
        bad["meta"]["createdAt"] = None
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema, format_checker=jsonschema.FormatChecker())


class Projections(unittest.TestCase):
    def test_fefo_stock_not_reused_across_horizons(self):
        stock = [{"lotId": "LOT1", "foodTypeId": "oats",
                  "quantity": quantity(8), "usableUntil": "2026-11-06",
                  "safe": True, "available": True}]
        demands = [{"eventId": "e1", "foodTypeId": "oats", "dueDate": DATE,
                    "quantity": quantity(5), "kind": "PREPARATION_RAW"},
                   {"eventId": "e2", "foodTypeId": "oats", "dueDate": "2026-11-01",
                    "quantity": quantity(6), "kind": "PREPARATION_RAW"}]
        r = project_needs({"asOf": DATE, "stock": stock, "demands": demands})
        self.assertEqual(r["horizons"]["1"]["totals"], [])
        self.assertEqual(r["horizons"]["7"]["totals"][0]["quantityToBuy"], 3)
        self.assertEqual(r["horizons"]["28"]["totals"][0]["quantityToBuy"], 3)
        self.assertEqual(r["horizons"]["56"]["totals"][0]["quantityToBuy"], 3)
        self.assertEqual(r["sideEffects"], [])

    def test_preparation_and_consumed_portions_not_counted_twice(self):
        rows = [{"eventId": "cook", "foodTypeId": "oats", "dueDate": DATE,
                 "quantity": quantity(100), "kind": "PREPARATION_RAW"},
                {"eventId": "eat1", "foodTypeId": "oats", "dueDate": DATE,
                 "quantity": quantity(100), "kind": "PORTION_CONSUMPTION"},
                {"eventId": "eat2", "foodTypeId": "oats", "dueDate": "2026-11-01",
                 "quantity": quantity(100), "kind": "PORTION_CONSUMPTION"}]
        r = project_needs({"asOf": DATE, "stock": [], "demands": rows})
        self.assertEqual(r["horizons"]["7"]["totals"][0]["quantityToBuy"], 100)

    def test_unsafe_lot_excluded_unknown_stock_not_zero(self):
        r = project_needs({"asOf": DATE, "stock": [
           {"lotId": "BAD", "foodTypeId": "oats", "quantity": quantity(99),
            "usableUntil": "2026-11-03", "safe": False, "available": True}],
           "demands": [{"eventId": "e1", "foodTypeId": "oats", "dueDate": DATE,
                        "quantity": quantity(20)}]})
        self.assertEqual(r["horizons"]["1"]["totals"][0]["quantityToBuy"], 20)
        self.assertFalse(r["snapshotComplete"])
        unknown = project_needs({"asOf": DATE, "stock": None, "demands": None})
        self.assertFalse(unknown["snapshotComplete"])
        self.assertIn("stock snapshot UNKNOWN", unknown["warnings"])

    def test_expires_before_need(self):
        stock = [{"lotId": "OLD", "foodTypeId": "oats", "quantity": quantity(100),
                  "usableUntil": DATE, "safe": True, "available": True}]
        demand = [{"eventId": "later", "foodTypeId": "oats",
                   "dueDate": "2026-11-02", "quantity": quantity(30)}]
        r = project_needs({"asOf": DATE, "stock": stock, "demands": demand})
        self.assertEqual(r["horizons"]["7"]["totals"][0]["quantityToBuy"], 30)

    def test_duplicates_rejected(self):
        row = {"eventId": "D", "foodTypeId": "oats", "dueDate": DATE,
               "quantity": quantity(10)}
        with self.assertRaises(DomainError):
            project_needs({"asOf": DATE, "stock": [], "demands": [row, row]})

    def test_unknown_demand_explicit_null_not_zero(self):
        snapshot = {"asOf": DATE, "stock": [], "demands": [
            {"eventId": "missing", "foodTypeId": "oats", "dueDate": DATE,
             "quantity": None, "kind": "PREPARATION_RAW"}]}
        r = project_needs(snapshot)
        self.assertEqual(r["horizons"]["1"]["totals"], [])
        self.assertIsNone(r["unknownNeeds"][0]["quantityToBuy"])
        self.assertEqual(r["unknownNeeds"][0]["eventId"], "missing")
        self.assertFalse(r["snapshotComplete"])

    def test_actual_consumed_prepared_portions_do_not_create_raw_baseline(self):
        history = [{"eventId": str(i), "date": f"2026-10-{i+10}",
                    "foodTypeId": "oats", "quantity": quantity(70),
                    "confirmed": True, "kind": "PORTION_CONSUMPTION"}
                   for i in range(3)]
        r = project_needs({"asOf": DATE, "stock": [], "demands": [],
                           "consumptionHistory": history,
                           "historyStart": "2026-10-10",
                           "historyUntil": "2026-10-16"})
        self.assertEqual(r["horizons"]["7"]["totals"], [])
        self.assertEqual(r["unknownNeeds"], [])

    def test_baseline_actual_events_not_planned_on_same_day(self):
        hist = [{"eventId": str(i), "foodTypeId": "oats", "date": "2026-10-" + str(i+10),
                 "quantity": quantity(70), "confirmed": True} for i in range(3)]
        plan = [{"eventId": "planned-today", "foodTypeId": "oats",
                 "dueDate": DATE, "quantity": quantity(100)}]
        r = project_needs({"asOf": DATE, "stock": [], "demands": plan,
                           "consumptionHistory": hist, "historyStart": "2026-10-10",
                           "historyUntil": "2026-10-16"})
        # 210/7 = 30 daily. Day 1 plan substitutes baseline; next 6 days baseline.
        self.assertEqual(r["horizons"]["7"]["totals"][0]["quantityToBuy"], 280)
        self.assertEqual(r["horizons"]["1"]["totals"][0]["quantityToBuy"], 100)

    def test_insufficient_consumption_history_not_extrapolated(self):
        hist = [{"eventId": "1", "foodTypeId": "oats", "date": "2026-10-30",
                 "quantity": quantity(100), "confirmed": True}]
        r = project_needs({"asOf": DATE, "stock": [], "demands": [],
                           "consumptionHistory": hist, "historyStart": "2026-10-30",
                           "historyUntil": "2026-10-30"})
        self.assertEqual(r["horizons"]["7"]["totals"], [])
        self.assertTrue(r["warnings"])

    def test_purchase_budget_shelf_capacity_and_unknown(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 750,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 750, "dueDate": "2026-11-02"}]}
        products = [{"productId": "OATS500", "foodTypeId": "oats",
                     "quantity": quantity(500), "priceCents": 120,
                     "storageClass": "DRY", "packageVolumeMl": 750, "shelfLifeDays": 30}]
        products = [with_price_evidence(p) for p in products]
        budget = {"amountCents": 300, "periodStart": DATE, "periodEnd": "2026-11-03"}
        r = suggest_purchases(view, products, shopping_date=DATE, budget=budget,
                              capacity={"DRY": 2000}, as_of=NOW)
        self.assertEqual((r["items"][0]["packs"], r["totalCostCents"]), (2, 240))
        self.assertEqual(r["budgetRemainingCents"], 60)
        self.assertEqual(r["items"][0]["status"], "FEASIBLE_NOT_PURCHASED")
        self.assertEqual(suggest_purchases(view, products, shopping_date=DATE)["items"][0]["status"], "REVIEW")
        self.assertEqual(suggest_purchases(view, products, shopping_date=DATE,
               budget={"amountCents": 100, "periodStart": DATE, "periodEnd": DATE},
               capacity={"DRY": 100})["items"][0]["status"], "REVIEW")
        self.assertIn("insufficient confirmed storage volume",
                 suggest_purchases(view, products, shopping_date=DATE,
                   budget=budget, capacity={"DRY": 100})["items"][0]["reasons"])

    def test_missing_price_unknown_total_not_zero(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 100,
                            "unit": "g", "basis": "NET"}], "needs": []}
        r = suggest_purchases(view, [], shopping_date=DATE)
        self.assertIsNone(r["totalCostCents"])
        self.assertIsNone(r["items"][0]["costCents"])


class InterestsAndHistory(unittest.TestCase):
    def test_interest_is_proposal_never_purchase(self):
        s = {"interests": {}, "hiddenProducts": []}
        old = copy.deepcopy(s)
        r = evaluate_offer_interest(s, {"action": "INTERESTED", "productId": "P"})
        self.assertEqual(s, old)
        self.assertEqual(r["proposedState"]["interests"]["P"], "INTERESTED")
        self.assertFalse(r["purchaseRecorded"])
        self.assertFalse(r["stockChanged"])
        r2 = evaluate_offer_interest(s, {"action": "ADD_TO_SHOPPING_LIST", "productId": "P"})
        self.assertEqual(r2["proposedState"]["shoppingListProposals"], ["P"])

    def test_offer_dedup_and_market_filter(self):
        a = observation("X1", 170, retailer="REWE", store="R1")
        b = observation("X2", 160, retailer="LIDL", store="L1")
        for obs in (a, b):
            obs["article"]["gtin"] = "4000000000000"
        rows = list_offer_interests([a, b], {}, DATE, as_of=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bestKnownObservationId"], "X2")
        self.assertEqual(rows[0]["otherObservationIds"], ["X1"])
        filtered = list_offer_interests([a, b], {}, DATE, as_of=NOW,
                                        preferred_retailers=["REWE"])
        self.assertEqual(filtered[0]["bestKnownObservationId"], "X1")

    def test_confirmed_past_purchase_no_future_hindsight(self):
        p = observation("PURCHASE", 199, kind="HISTORICAL_PAID",
                        at="2026-10-15T12:00:00+02:00", start=None, until=None)
        p["purchaseAt"] = "2026-10-15T12:00:00+02:00"
        p["confirmed"] = True
        old = observation("OLD_VALID", 179, at="2026-10-14T09:00:00+02:00",
                          start="2026-10-14", until="2026-10-16",
                          retailer="LIDL", store="L123")
        future = observation("HINDSIGHT", 20, at="2026-10-31T10:00:00+01:00",
                             start="2026-10-14", until="2026-10-16",
                             retailer="LIDL", store="L123")
        r = evaluate_past_purchase(p, [old, future],
                                   accessible_stores={"LIDL": ["L123"]},
                                   coverage={"complete": True})
        self.assertEqual(r["status"], "EVIDENCED_ALTERNATIVES")
        self.assertEqual([a["observationId"] for a in r["comparison"]["alternatives"]],
                         ["OLD_VALID"])
        self.assertTrue(r["noHindsight"])
        self.assertEqual(evaluate_past_purchase(
            dict(p, confirmed=False), [old],
            accessible_stores={"LIDL": ["L123"]})["status"], "UNKNOWN")

    def test_past_purchase_store_scope_must_be_proven(self):
        p = observation("P", 199, kind="HISTORICAL_PAID",
                        at="2026-10-15T12:00:00+02:00")
        p["purchaseAt"] = "2026-10-15T12:00:00+02:00"
        p["confirmed"] = True
        alt = observation("NO_STORE", 10, at="2026-10-14T12:00:00+02:00",
                          start="2026-10-14", until="2026-10-16",
                          retailer="REWE", scope="CHAIN_WIDE_REPORTED")
        r = evaluate_past_purchase(p, [alt], accessible_stores={"REWE": ["R1"]})
        self.assertEqual(r["status"], "NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()
