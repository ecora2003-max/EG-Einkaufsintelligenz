"""Synthetic early-purchase proof cases."""
import copy
import unittest

from eg_shopping import DomainError, evaluate_early_purchase

DAY = "2026-10-31"
DUE = "2026-11-03"
ASOF = "2026-10-31T15:00:00+01:00"
NEED = {"foodTypeId": "oats-fine", "dueDate": DUE,
        "quantityToBuy": 750, "unit": "g", "basis": "NET"}
BUDGET = {"amountCents": 400, "periodStart": DAY, "periodEnd": DAY}
CAPACITY = {"DRY": 2000}


def obs(oid, cents, *, start=DAY, until="2026-11-10",
        kind="SALE", observed="2026-10-31T12:00:00+01:00",
        organic=True, food="oats-fine", amount=500, deposit=0,
        scope="STORE_CONFIRMED", store="L1"):
    return {"observationId": oid,
            "article": {"label": "synthetic oats", "foodTypeId": food,
                        "organic": organic, "brandKind": "PRIVATE_LABEL",
                        "attributes": {"form": "fine"},
                        "quantity": {"amount": amount, "unit": "g",
                                     "basis": "NET", "confirmed": True}},
            "scope": {"retailerId": "EXAMPLE", "storeId": store,
                      "scopeType": scope},
            "priceCents": cents, "currency": "EUR", "priceKind": kind,
            "validFrom": start, "validUntil": until,
            "depositCents": deposit, "conditional": [],
            "source": {"origin": "synthetic", "observedAt": observed,
                       "rightsStatus": "UNVERIFIED", "dataQuality": "CONFIRMED"},
            "availability": "IN_STOCK_REPORTED"}


def evaluate(need=None, current=None, future=None, **kwargs):
    return evaluate_early_purchase(
        copy.deepcopy(need if need is not None else NEED),
        copy.deepcopy(current if current is not None else obs("NOW", 100)),
        shopping_date=DAY, as_of=ASOF,
        budget=copy.deepcopy(kwargs.pop("budget", BUDGET)),
        capacity=copy.deepcopy(kwargs.pop("capacity", CAPACITY)),
        shelf_life_days=kwargs.pop("shelf", 7),
        storage_class=kwargs.pop("storage", "DRY"),
        package_volume_ml=kwargs.pop("volume", 500),
        future_price=copy.deepcopy(future if future is not None else
             obs("FUTURE", 130, start=DUE, kind="LISTED_REGULAR")),
        **kwargs)


class EarlyPurchase(unittest.TestCase):
    def test_evidenced_early_saving_and_pack_rounding(self):
        r = evaluate()
        self.assertEqual(r["status"], "ADVANCE_FEASIBLE_NOT_PURCHASED")
        self.assertEqual(r["packs"], 2)
        self.assertEqual(r["merchandiseCents"], 200)
        self.assertEqual(r["checkoutCents"], 200)
        self.assertEqual(r["futureComparableCents"], 260)
        self.assertEqual(r["savingsProvenCents"], 60)
        self.assertEqual(r["sideEffects"], [])

    def test_no_future_price_no_savings_claim(self):
        r = evaluate_early_purchase(NEED, obs("NOW", 100),
                                    shopping_date=DAY, as_of=ASOF,
                                    budget=BUDGET, capacity=CAPACITY,
                                    shelf_life_days=7, storage_class="DRY",
                                    package_volume_ml=500)
        self.assertEqual(r["status"], "REVIEW")
        self.assertIsNone(r["savingsProvenCents"])

    def test_future_price_not_observed_as_of_cannot_be_used(self):
        r = evaluate(future=obs("FUTURE", 140, start=DUE,
                                kind="LISTED_REGULAR",
                                observed="2026-11-03T08:00:00+01:00"))
        self.assertEqual(r["status"], "REVIEW")
        self.assertIsNone(r["savingsProvenCents"])
        self.assertTrue(any("after decision time" in x for x in r["reasons"]))

    def test_early_purchase_not_better_is_not_recommended(self):
        r = evaluate(future=obs("FUTURE", 90, start=DUE,
                                kind="LISTED_REGULAR"))
        self.assertEqual(r["status"], "REVIEW")
        self.assertIsNone(r["savingsProvenCents"])

    def test_missing_budget_capacity_or_shelf_forces_review(self):
        self.assertEqual(evaluate(budget=None)["status"], "REVIEW")
        self.assertEqual(evaluate(capacity=None)["status"], "REVIEW")
        self.assertEqual(evaluate(shelf=None)["status"], "REVIEW")
        self.assertEqual(evaluate(shelf=1)["status"], "REVIEW")
        self.assertEqual(evaluate(capacity={"DRY": 500})["status"], "REVIEW")

    def test_unknown_deposit_keeps_checkout_unknown(self):
        r = evaluate(current=obs("NOW", 100, deposit=None))
        self.assertIsNone(r["checkoutCents"])
        self.assertEqual(r["status"], "REVIEW")

    def test_known_deposit_requires_cash_budget(self):
        r = evaluate(current=obs("NOW", 100, deposit=25),
                     budget={"amountCents": 240, "periodStart": DAY,
                             "periodEnd": DAY})
        self.assertEqual(r["checkoutCents"], 250)
        self.assertEqual(r["status"], "REVIEW")

    def test_incompatible_food_types_cannot_be_used(self):
        r = evaluate(future=obs("OTHER", 200, start=DUE,
                                kind="LISTED_REGULAR", food="muesli-sweet"))
        self.assertIsNone(r["savingsProvenCents"])
        self.assertEqual(r["status"], "REVIEW")

    def test_offer_starts_after_shopping_day(self):
        r = evaluate(current=obs("LATER", 100, start="2026-11-01"))
        self.assertEqual(r["status"], "REVIEW")
        self.assertIsNone(r["packs"])

    def test_unconfirmed_store_scope_not_proven(self):
        r = evaluate(current=obs("CHAIN", 100, scope="CHAIN_WIDE_REPORTED",
                                 store=None))
        self.assertEqual(r["status"], "REVIEW")

    def test_bad_past_need_date_rejected(self):
        need = copy.deepcopy(NEED)
        need["dueDate"] = "2026-10-01"
        with self.assertRaises(DomainError):
            evaluate(need=need)


if __name__ == "__main__":
    unittest.main()
