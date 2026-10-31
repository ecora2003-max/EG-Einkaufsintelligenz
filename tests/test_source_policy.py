"""Synthetic ADR-014/016 regression and negative tests (no network/real receipts)."""
import copy
import unittest
from test_engine import observation, quantity, DATE, NOW
from eg_shopping.cli import dispatch
from eg_shopping.engine import (DomainError, compare_prices, compare_catalog,
                                evaluate_past_purchase, suggest_purchases,
                                list_offer_interests)
from eg_shopping.source_policy import (CAPABILITIES, retailer_capability,
                                       gate_observation, private_receipt_verified)


def permitted(obs, operation="PUBLISHED_OFFER_COLLECTION"):
    obs = copy.deepcopy(obs)
    obs["source"].update({
        "origin": "SYNTHETIC_PERMISSION_FIXTURE", "evidenceKind": "OFFICIAL_WEB",
        "operation": operation, "rightsStatus": "PERMITTED",
        "displayPermission": {
            "verified": True, "reference": "FAKE-TEST-ONLY",
            "sourceOrigin": "SYNTHETIC_PERMISSION_FIXTURE",
            "allowedUses": ["APP_DISPLAY"]}})
    return obs


def receipt(confirmed=True):
    p = observation("RECEIPT", 199, retailer="PENNY", kind="HISTORICAL_PAID")
    p.update({"confirmed": confirmed, "purchaseAt": NOW,
              "receiptId": "FAKE-R1", "receiptLineId": "FAKE-L1"})
    p["source"].update({"origin": "USER_LOCAL_RECEIPT",
                        "evidenceKind": "USER_CONFIRMED_RECEIPT",
                        "localOnly": True})
    return p


class SourceScope(unittest.TestCase):
    def test_capability_matrix_eight_retailers(self):
        self.assertEqual(len(CAPABILITIES), 8)
        for retailer in ("ALDI_NORD", "ALDI_SUED", "REWE", "LIDL"):
            self.assertTrue(retailer_capability(retailer, "TARGETED_PRODUCT_PRICE_QUERY"))
            self.assertTrue(retailer_capability(retailer, "PUBLISHED_OFFER_COLLECTION"))
        for retailer in ("PENNY", "KAUFLAND", "EDEKA", "NETTO_MD"):
            self.assertFalse(retailer_capability(retailer, "TARGETED_PRODUCT_PRICE_QUERY"))
            self.assertTrue(retailer_capability(retailer, "PUBLISHED_OFFER_COLLECTION"))
        self.assertFalse(retailer_capability("NETTO", "TARGETED_PRODUCT_PRICE_QUERY"))
        self.assertFalse(retailer_capability("REWE", "BULK_CATALOG"))

    def test_research_is_separate_from_display(self):
        obs = observation("O", 99, retailer="PENNY")
        self.assertTrue(gate_observation(obs, "RESEARCH_ONLY")[0])
        self.assertFalse(gate_observation(obs, "APP_DISPLAY")[0])
        self.assertTrue(gate_observation(permitted(obs), "APP_DISPLAY")[0])

    def test_unverified_restricted_and_missing_permission_never_visible(self):
        target = permitted(observation("T", 199, retailer="LIDL"))
        for status in ("UNVERIFIED", "RESTRICTED"):
            alt = permitted(observation("A", 99, retailer="REWE"))
            alt["source"]["rightsStatus"] = status
            result = compare_prices(target, [alt], DATE, as_of=NOW,
                                    coverage={"complete": True},
                                    usage_context="APP_DISPLAY")
            self.assertEqual(result["alternatives"], [])
            self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])
            self.assertTrue(result["incomplete"])
            self.assertNotIn("99", str(result["rejected"]))
        for patch in ({"verified": False}, {"reference": ""},
                      {"sourceOrigin": "OTHER"}, {"allowedUses": ["RESEARCH_ONLY"]}):
            alt = permitted(observation("B", 99, retailer="REWE"))
            alt["source"]["displayPermission"].update(patch)
            self.assertFalse(gate_observation(alt, "APP_DISPLAY")[0])
        alt = permitted(observation("C", 99, retailer="REWE"))
        del alt["source"]["displayPermission"]
        self.assertFalse(gate_observation(alt, "APP_DISPLAY")[0])

    def test_restricted_retailer_regular_snapshot_not_relabelled(self):
        target = permitted(observation("T", 199, retailer="LIDL"))
        for retailer in ("PENNY", "KAUFLAND", "EDEKA", "NETTO_MD"):
            alt = permitted(observation(retailer, 99, retailer=retailer,
                                        kind="LISTED_REGULAR"),
                            "TARGETED_PRODUCT_PRICE_QUERY")
            result = compare_prices(target, [alt], DATE, as_of=NOW,
                                    coverage={"complete": True},
                                    usage_context="APP_DISPLAY")
            self.assertEqual(result["alternatives"], [])
            self.assertTrue(result["incomplete"])
            self.assertIn("GREY_MAY_BE_CHEAPER", result["signals"])
            self.assertNotIn("priceCents", str(result["rejected"]))
            alt["source"]["operation"] = "PUBLISHED_OFFER_COLLECTION"
            self.assertFalse(gate_observation(alt, "APP_DISPLAY")[0])

    def test_positive_regular_four_and_offers_eight(self):
        target = permitted(observation("T", 199, retailer="LIDL"))
        for retailer in ("ALDI_NORD", "ALDI_SUED", "REWE", "LIDL"):
            alt = permitted(observation(retailer, 99, retailer=retailer,
                                        kind="LISTED_REGULAR"),
                            "TARGETED_PRODUCT_PRICE_QUERY")
            self.assertEqual(len(compare_prices(target, [alt], DATE, as_of=NOW,
                coverage={"complete": True}, usage_context="APP_DISPLAY")["alternatives"]), 1)
        for retailer in CAPABILITIES:
            alt = permitted(observation(retailer, 99, retailer=retailer))
            self.assertEqual(len(compare_prices(target, [alt], DATE, as_of=NOW,
                coverage={"complete": True}, usage_context="APP_DISPLAY")["alternatives"]), 1)

    def test_target_and_catalog_exclusion_no_price_leak(self):
        with self.assertRaises(DomainError):
            compare_prices(observation("T", 199, retailer="LIDL"), [], DATE,
                           as_of=NOW, usage_context="APP_DISPLAY")
        result = compare_catalog([observation("T", 199, retailer="LIDL")],
                                 DATE, as_of=NOW, coverage={"complete": True},
                                 usage_context="APP_DISPLAY")
        self.assertEqual(result["comparisons"], [])
        self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])
        self.assertTrue(result["incomplete"])
        self.assertNotIn("priceCents", str(result))

    def test_cli_opt_in_and_backward_compatibility(self):
        target = permitted(observation("T", 199, retailer="LIDL"))
        msg = {"operation": "comparePrices", "target": target,
               "observations": [observation("BAD", 99, retailer="REWE")],
               "shoppingDate": DATE, "asOf": NOW,
               "coverage": {"complete": True}, "usageContext": "APP_DISPLAY"}
        self.assertEqual(dispatch(msg)["signals"], ["GREY_MAY_BE_CHEAPER"])
        msg.pop("usageContext")
        self.assertEqual(len(dispatch(msg)["alternatives"]), 1)
        msg["usageContext"] = "INVALID"
        with self.assertRaises(DomainError):
            dispatch(msg)

    def test_offer_interest_excludes_unlicensed_source(self):
        good = permitted(observation("GOOD", 99, retailer="PENNY"))
        bad = observation("BAD", 50, retailer="LIDL")
        good["article"]["productId"] = "P-GOOD"
        bad["article"]["productId"] = "P-BAD"
        result = list_offer_interests([good, bad], {}, DATE, as_of=NOW,
                                      usage_context="APP_DISPLAY")
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])

    def test_purchase_proposal_cannot_use_unverified_snapshot(self):
        product = {"productId": "OATS", "foodTypeId": "oats-fine",
                   "quantity": quantity(), "priceCents": 99, "depositCents": 0,
                   "shelfLifeDays": 40, "storageClass": "DRY",
                   "packageVolumeMl": 800,
                   "priceObservation": observation("BAD", 99, retailer="PENNY",
                                                    kind="LISTED_REGULAR")}
        needs = {"totals": [{"foodTypeId": "oats-fine", "unit": "g",
                             "basis": "NET", "quantityToBuy": 500}],
                 "needs": [{"foodTypeId": "oats-fine", "unit": "g",
                            "basis": "NET", "quantityToBuy": 500, "dueDate": DATE}]}
        result = suggest_purchases(needs, [product], shopping_date=DATE,
                                   as_of=NOW, usage_context="APP_DISPLAY")
        self.assertIsNone(result["items"][0]["costCents"])
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])
        self.assertNotIn("99", str(result))


    def test_early_purchase_rejects_unlicensed_offer_and_future_quote(self):
        need = {"foodTypeId": "oats-fine", "dueDate": "2026-11-02",
                "quantityToBuy": 500, "unit": "g", "basis": "NET"}
        offer = observation("S", 199, retailer="LIDL")
        request = {"operation": "evaluateEarlyPurchase", "need": need,
                   "offer": offer, "shoppingDate": DATE, "asOf": NOW,
                   "usageContext": "APP_DISPLAY"}
        blocked = dispatch(request)
        self.assertEqual(blocked["status"], "REVIEW")
        self.assertIsNone(blocked["merchandiseCents"])
        self.assertIsNone(blocked["savingsProvenCents"])
        request.update({
            "offer": permitted(offer),
            "futurePrice": observation("F", 250, retailer="REWE",
                                       kind="LISTED_REGULAR",
                                       start="2026-11-02", until="2026-11-02"),
            "budget": {"amountCents": 1000, "periodStart": DATE,
                       "periodEnd": "2026-11-07"},
            "capacity": {"DRY": 10000}, "storageClass": "DRY",
            "shelfLifeDays": 30, "packageVolumeMl": 500})
        blocked_future = dispatch(request)
        self.assertEqual(blocked_future["status"], "REVIEW")
        self.assertIsNone(blocked_future["futureComparableCents"])
        self.assertIsNone(blocked_future["savingsProvenCents"])

    def test_mixed_catalog_excludes_unauthorized_target_and_alternative(self):
        good = permitted(observation("GOOD", 199, retailer="LIDL"))
        bad = observation("BAD", 50, retailer="PENNY")
        result = compare_catalog([good, bad], DATE, as_of=NOW,
                                 coverage={"complete": True},
                                 usage_context="APP_DISPLAY")
        self.assertEqual(len(result["comparisons"]), 1)
        self.assertEqual(len(result["omittedTargets"]), 1)
        self.assertEqual(result["comparisons"][0]["alternatives"], [])
        self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])
        self.assertTrue(result["incomplete"])
        self.assertNotIn("50", str(result))


class PrivateHistory(unittest.TestCase):
    def test_ocr_draft_or_missing_identity_no_price_or_booking(self):
        for changes in ({"confirmed": False}, {"receiptId": ""},
                        {"receiptLineId": ""}):
            p = receipt()
            p.update(changes)
            result = evaluate_past_purchase(p, [], accessible_stores={},
                                             usage_context="PRIVATE_USER_HISTORY")
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertIsNone(result["comparison"])
            self.assertEqual(result["sideEffects"], [])
            self.assertNotIn("199", str(result))
        p = receipt()
        p["source"]["localOnly"] = False
        self.assertFalse(private_receipt_verified(p))

    def test_confirmed_local_receipt_dated_idempotent_and_not_current(self):
        p = receipt()
        a = evaluate_past_purchase(p, [], accessible_stores={},
                                   usage_context="PRIVATE_USER_HISTORY")
        b = evaluate_past_purchase(copy.deepcopy(p), [], accessible_stores={},
                                   usage_context="PRIVATE_USER_HISTORY")
        self.assertEqual(a, b)
        self.assertEqual(a["historicalPaid"]["priceCents"], 199)
        self.assertEqual(a["historicalPaid"]["priceKind"], "HISTORICAL_PAID")
        self.assertEqual(a["historicalPaid"]["retailerId"], "PENNY")
        self.assertEqual(a["historicalPaid"]["purchaseAt"], NOW)
        self.assertEqual(a["sideEffects"], [])
        self.assertNotIn("CURRENT_DISPLAYED", str(a))

    def test_private_receipt_cannot_legalize_external_price(self):
        p = receipt()
        alt = observation("ALT", 50, retailer="REWE")
        result = evaluate_past_purchase(p, [alt],
                  accessible_stores={"REWE": ["STORE_ALT"]},
                  coverage={"complete": True},
                  usage_context="PRIVATE_USER_HISTORY")
        self.assertEqual(result["comparison"]["alternatives"], [])
        self.assertTrue(result["comparison"]["incomplete"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["comparison"]["signals"])
