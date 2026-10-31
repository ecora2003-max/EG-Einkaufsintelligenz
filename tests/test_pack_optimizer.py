"""Exhaustive mixed-package search regression and negative safety cases."""
import copy
import unittest

from eg_shopping import suggest_purchases
from eg_shopping.pack_optimizer import PackSearchError, optimize_package_mix

DATE = "2026-10-31"
DUE = "2026-11-02"


def pack(pid, size, cents, *, min_packs=1, vol=700, shelf=30, **extra):
    result = {"productId": pid, "amount": size, "priceCents": cents,
              "minPacks": min_packs, "shelfLifeDays": shelf,
              "storageClass": "DRY", "packageVolumeMl": vol}
    result.update(extra)
    return result


def optimize(quantity, candidates, **kw):
    return optimize_package_mix(quantity, candidates, shopping_date=DATE,
                                last_due_date=DUE, budget_cents=kw.pop("budget", 3000),
                                capacity_ml=kw.pop("capacity", {"DRY": 10000}), **kw)


def base_q(amount):
    return {"amount": amount, "unit": "g", "basis": "NET", "confirmed": True}


def with_evidence(p):
    p = copy.deepcopy(p)
    p["depositCents"] = 0
    p["priceObservation"] = {
        "observationId": "PRICE-" + p["productId"],
        "article": {"label": "Synthetic " + p["productId"],
                    "foodTypeId": p["foodTypeId"], "organic": False,
                    "brandKind": "PRIVATE_LABEL", "quantity": p["quantity"]},
        "scope": {"retailerId": "SYNTHETIC", "storeId": "S1",
                  "scopeType": "STORE_CONFIRMED"},
        "priceCents": p["priceCents"], "currency": "EUR",
        "priceKind": "LISTED_REGULAR", "validFrom": DATE, "validUntil": DUE,
        "depositCents": 0,
        "source": {"origin": "fixture", "observedAt": "2026-10-31T14:00:00+01:00",
                   "dataQuality": "CONFIRMED", "rightsStatus": "UNVERIFIED"},
        "availability": "IN_STOCK_REPORTED",
    }
    return p


class MixedPackaging(unittest.TestCase):
    def test_mix_better_than_single_cheapest_unit_rate(self):
        # 1kg at 210c has better €/kg, but 1kg+0.5kg costs 330c
        # compared with 2x1kg (420c) or 3x0.5kg (360c).
        result = optimize(1500, [pack("KILO", 1000, 210), pack("HALF", 500, 120)])
        self.assertEqual(result["status"], "FEASIBLE_NOT_PURCHASED")
        self.assertEqual(result["costCents"], 330)
        self.assertEqual(result["quantityBought"], 1500)
        self.assertEqual(result["items"], [
            {"productId": "HALF", "packs": 1, "quantityBought": 500, "costCents": 120},
            {"productId": "KILO", "packs": 1, "quantityBought": 1000, "costCents": 210}])
        self.assertTrue(result["optimalityProven"])

    def test_multibuy_only_when_threshold_achieved(self):
        two_for = pack("TWO", 500, 100, min_packs=2)
        normal = pack("ONE", 500, 120)
        result = optimize(500, [two_for, normal])
        self.assertEqual(result["items"][0]["productId"], "ONE")
        result = optimize(1000, [two_for, normal])
        self.assertEqual(result["items"][0]["productId"], "TWO")
        self.assertEqual(result["items"][0]["packs"], 2)
        self.assertEqual(result["costCents"], 200)

    def test_coupon_without_explicit_proof_excluded(self):
        r = optimize(500, [pack("COUPON", 500, 20, conditional=["app membership"]),
                           pack("REG", 500, 120)])
        self.assertEqual(r["items"][0]["productId"], "REG")
        self.assertEqual(r["rejected"][0]["productId"], "COUPON")

    def test_budget_picks_feasible_not_cheapest_oversized(self):
        expensive = pack("BIG", 1000, 300, vol=2500)
        small = pack("SMALL", 500, 110, vol=600)
        r = optimize(500, [expensive, small], budget=120)
        self.assertEqual(r["items"][0]["productId"], "SMALL")
        self.assertEqual(r["status"], "FEASIBLE_NOT_PURCHASED")

    def test_capacity_selects_other_pack_mix(self):
        high_volume = pack("BULKY", 500, 80, vol=900)
        small_volume = pack("COMPACT", 500, 100, vol=200)
        r = optimize(1000, [high_volume, small_volume], capacity={"DRY": 600})
        self.assertEqual(r["items"], [{"productId": "COMPACT", "packs": 2,
                                       "quantityBought": 1000, "costCents": 200}])
        self.assertEqual(r["status"], "FEASIBLE_NOT_PURCHASED")

    def test_shelf_life_blocks_early_bulk_purchase(self):
        a = pack("SHORT", 500, 10, shelf=1)
        b = pack("LONG", 500, 100, shelf=30)
        r = optimize(500, [a, b])
        self.assertEqual(r["items"][0]["productId"], "LONG")
        self.assertEqual(r["status"], "FEASIBLE_NOT_PURCHASED")

    def test_future_sale_excluded(self):
        r = optimize(500, [pack("TOMORROW", 500, 10, priceKind="SALE",
                                validFrom="2026-11-01", validUntil="2026-11-07"),
                           pack("TODAY", 500, 100)])
        self.assertEqual(r["items"][0]["productId"], "TODAY")
        self.assertEqual(r["rejected"][0]["reason"], "price not valid on shopping date")

    def test_missing_sale_dates_and_online_shipping_declined(self):
        r = optimize(500, [pack("SALE", 500, 10, priceKind="SALE"),
                           pack("ONLINE", 500, 20, priceKind="ONLINE_LISTED", shippingCents=0),
                           pack("REG", 500, 100)])
        self.assertEqual(r["items"][0]["productId"], "REG")
        self.assertEqual(len(r["rejected"]), 2)

    def test_reference_old_not_current_price(self):
        r = optimize(500, [pack("OLD", 500, 5, priceKind="REFERENCE_OLD"),
                           pack("REG", 500, 100)])
        self.assertEqual(r["costCents"], 100)

    def test_out_of_stock_maxpacks_and_no_solution(self):
        r = optimize(1000, [pack("EXPIRED", 500, 1, maxPacks=0),
                            pack("STOCK", 500, 10, maxPacks=1)])
        self.assertEqual(r["status"], "NO_FEASIBLE_MIX")
        self.assertFalse(r["items"])

    def test_unknown_capacity_is_review_not_success(self):
        r = optimize(500, [pack("PACK", 500, 100)], capacity=None)
        self.assertEqual(r["status"], "REVIEW")
        self.assertIn("available storage volume UNKNOWN", r["warnings"])
        self.assertEqual(r["costCents"], 100)

    def test_overbudget_still_review_and_cost_visible(self):
        r = optimize(500, [pack("PACK", 500, 100)], budget=0)
        self.assertEqual(r["status"], "REVIEW")
        self.assertIn("budget exceeded", r["warnings"])
        self.assertEqual(r["costCents"], 100)

    def test_search_limit_reports_no_proven_optimum(self):
        r = optimize(4000, [pack(str(i), 500, 50+i) for i in range(7)],
                     max_nodes=10)
        self.assertEqual(r["status"], "SEARCH_LIMIT")
        self.assertFalse(r["optimalityProven"])

    def test_more_than_eight_products_declined(self):
        r = optimize(500, [pack(str(i), 500, i+1) for i in range(9)])
        self.assertEqual(r["status"], "SEARCH_LIMIT")

    def test_duplicates_negative_and_zero_rejected(self):
        with self.assertRaises(PackSearchError):
            optimize(500, [pack("DUP", 500, 1), pack("DUP", 500, 2)])
        with self.assertRaises(PackSearchError):
            optimize(500, [pack("NEG", 500, -1)])
        with self.assertRaises(PackSearchError):
            optimize(0, [pack("X", 500, 1)])
        with self.assertRaises(PackSearchError):
            optimize(500, [pack("X", 0, 1)])

    def test_deterministic_and_inputs_unchanged(self):
        arr = [pack("Z", 1000, 220), pack("A", 500, 115)]
        old = copy.deepcopy(arr)
        a, b = optimize(1500, arr), optimize(1500, list(reversed(arr)))
        self.assertEqual(a, b)
        self.assertEqual(arr, old)

    def test_verified_offer_selected_over_invalid_cheaper_source(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 500,
                           "dueDate": DATE}]}
        cheap = with_evidence({"productId": "CHEAP", "foodTypeId": "oats",
                               "quantity": base_q(500), "priceCents": 80,
                               "shelfLifeDays": 30, "storageClass": "DRY",
                               "packageVolumeMl": 500})
        cheap["priceObservation"]["validUntil"] = "2026-10-01"
        # A fully valid, more expensive offer is a better evidence-based choice.
        good = with_evidence({"productId": "GOOD", "foodTypeId": "oats",
                              "quantity": base_q(500), "priceCents": 120,
                              "shelfLifeDays": 30, "storageClass": "DRY",
                              "packageVolumeMl": 500})
        r = suggest_purchases(view, [cheap, good], shopping_date=DATE,
            as_of="2026-10-31T15:00:00+01:00",
            budget={"amountCents": 200, "periodStart": DATE, "periodEnd": DATE},
            capacity={"DRY": 1000})
        self.assertEqual(r["items"][0]["mix"][0]["productId"], "GOOD")
        self.assertEqual(r["totalCheckoutCents"], 120)
        self.assertEqual(r["knownSubtotalCents"], 120)
        self.assertEqual(r["items"][0]["status"], "REVIEW")  # incomplete sources

    def test_budget_optimizes_cash_including_refundable_deposit(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 500,
                           "dueDate": DATE}]}
        cheap = with_evidence({"productId": "CHEAP", "foodTypeId": "oats",
                               "quantity": base_q(500), "priceCents": 80,
                               "shelfLifeDays": 30, "storageClass": "DRY",
                               "packageVolumeMl": 500})
        cheap["depositCents"] = 150
        cheap["priceObservation"]["depositCents"] = 150
        good = with_evidence({"productId": "GOOD", "foodTypeId": "oats",
                              "quantity": base_q(500), "priceCents": 110,
                              "shelfLifeDays": 30, "storageClass": "DRY",
                              "packageVolumeMl": 500})
        r = suggest_purchases(view, [cheap, good], shopping_date=DATE,
            as_of="2026-10-31T15:00:00+01:00",
            budget={"amountCents": 130, "periodStart": DATE, "periodEnd": DATE},
            capacity={"DRY": 1000})
        self.assertEqual(r["items"][0]["mix"][0]["productId"], "GOOD")
        self.assertEqual(r["items"][0]["status"], "FEASIBLE_NOT_PURCHASED")
        self.assertEqual(r["totalCostCents"], 110)
        self.assertEqual(r["totalCheckoutCents"], 110)
        self.assertEqual(r["budgetRemainingCents"], 20)

    def test_duplicate_product_ids_rejected(self):
        from eg_shopping import DomainError
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}], "needs": []}
        p = with_evidence({"productId": "REUSED", "foodTypeId": "oats",
                           "quantity": base_q(500), "priceCents": 100,
                           "shelfLifeDays": 30, "storageClass": "DRY",
                           "packageVolumeMl": 500})
        with self.assertRaises(DomainError):
            suggest_purchases(view, [p, copy.deepcopy(p)],
                shopping_date=DATE, as_of="2026-10-31T15:00:00+01:00")

    def test_missing_source_and_deposit_never_claims_cash_budget(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 500, "dueDate": DATE}]}
        bare = {"productId": "P", "foodTypeId": "oats", "quantity": base_q(500),
                "priceCents": 120, "shelfLifeDays": 30,
                "storageClass": "DRY", "packageVolumeMl": 800}
        budget = {"amountCents": 200, "periodStart": DATE, "periodEnd": DATE}
        r = suggest_purchases(view, [bare], shopping_date=DATE,
                              budget=budget, capacity={"DRY": 1000})
        self.assertEqual(r["items"][0]["status"], "REVIEW")
        self.assertIsNone(r["items"][0]["checkoutCents"])
        self.assertIsNone(r["totalCheckoutCents"])
        self.assertIsNone(r["budgetRemainingCents"])
        self.assertEqual(r["knownSubtotalCents"], 120)

    def test_deposit_cash_counts_against_budget(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 500, "dueDate": DATE}]}
        p = with_evidence({"productId": "P", "foodTypeId": "oats",
                           "quantity": base_q(500), "priceCents": 120,
                           "shelfLifeDays": 30, "storageClass": "DRY",
                           "packageVolumeMl": 800})
        p["depositCents"] = 25
        p["priceObservation"]["depositCents"] = 25
        budget = {"amountCents": 140, "periodStart": DATE, "periodEnd": DATE}
        r = suggest_purchases(view, [p], shopping_date=DATE,
                              as_of="2026-10-31T15:00:00+01:00",
                              budget=budget, capacity={"DRY": 1000})
        self.assertEqual(r["totalCostCents"], 120)
        self.assertEqual(r["totalCheckoutCents"], 145)
        self.assertEqual(r["budgetRemainingCents"], -5)
        self.assertEqual(r["items"][0]["status"], "REVIEW")
        self.assertIn("checkout cash budget exceeded", r["items"][0]["reasons"])

    def test_stale_observation_forces_review(self):
        view = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "unit": "g", "basis": "NET"}],
                "needs": [{"foodTypeId": "oats", "quantityToBuy": 500, "dueDate": DATE}]}
        p = with_evidence({"productId": "P", "foodTypeId": "oats",
                           "quantity": base_q(500), "priceCents": 120,
                           "shelfLifeDays": 30, "storageClass": "DRY",
                           "packageVolumeMl": 800})
        p["priceObservation"]["validFrom"] = "2026-10-01"
        p["priceObservation"]["validUntil"] = "2026-10-15"
        budget = {"amountCents": 200, "periodStart": DATE, "periodEnd": DATE}
        r = suggest_purchases(view, [p], shopping_date=DATE,
                              as_of="2026-10-31T15:00:00+01:00",
                              budget=budget, capacity={"DRY": 1000})
        self.assertEqual(r["items"][0]["status"], "REVIEW")
        self.assertIn("not valid on shopping date", r["items"][0]["reasons"])

    def test_suggest_purchase_mix_and_budget_after_allocation(self):
        view = {
            "totals": [{"foodTypeId": "oats", "quantityToBuy": 1500,
                        "unit": "g", "basis": "NET"}],
            "needs": [{"foodTypeId": "oats", "quantityToBuy": 1500, "unit": "g",
                       "basis": "NET", "dueDate": DUE}]}
        products = [{"productId": "KILO", "foodTypeId": "oats",
                     "quantity": base_q(1000), "priceCents": 210,
                     "storageClass": "DRY", "packageVolumeMl": 1000,
                     "shelfLifeDays": 30},
                    {"productId": "HALF", "foodTypeId": "oats",
                     "quantity": base_q(500), "priceCents": 120,
                     "storageClass": "DRY", "packageVolumeMl": 500,
                     "shelfLifeDays": 30}]
        products = [with_evidence(p) for p in products]
        budget = {"amountCents": 400, "periodStart": DATE, "periodEnd": "2026-11-07"}
        r = suggest_purchases(view, products, shopping_date=DATE,
                              budget=budget, capacity={"DRY": 2000},
                              as_of="2026-10-31T15:00:00+01:00")
        self.assertEqual(r["totalCostCents"], 330)
        self.assertEqual(r["budgetRemainingCents"], 70)
        self.assertIsNone(r["items"][0]["productId"])
        self.assertEqual(len(r["items"][0]["mix"]), 2)
        self.assertEqual(r["items"][0]["status"], "FEASIBLE_NOT_PURCHASED")
        self.assertEqual(r["sideEffects"], [])


if __name__ == "__main__":
    unittest.main()
