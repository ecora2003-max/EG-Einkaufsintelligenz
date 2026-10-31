"""Offline source-rights and retailer-capability acceptance (ADR-014/016)."""
import copy
import unittest

from eg_shopping.engine import (DomainError, compare_prices, compare_catalog,
                                suggest_purchases, list_offer_interests, evaluate_past_purchase)
from eg_shopping.stockup import evaluate_early_purchase
from eg_shopping.cli import dispatch
from eg_shopping.source_policy import (
    POLICY, source_gate, PRICE_QUERY, PUBLISHED_OFFER
)

DATE = "2026-10-31"
NOW = "2026-10-31T15:00:00+01:00"


def obs(ref="A", retailer="REWE", price=100, *, kind="SALE",
        rights="PERMITTED", evidence="E1"):
    return {
        "observationId": ref,
        "article": {"label": "synthetic oats", "foodTypeId": "oats",
                    "organic": True, "brandKind": "PRIVATE_LABEL",
                    "productId": "OATS", "gtin": "12345678",
                    "attributes": {"form": "fine"},
                    "quantity": {"amount": 500, "unit": "g",
                                 "basis": "NET", "confirmed": True}},
        "scope": {"retailerId": retailer, "storeId": "SHOP1",
                  "scopeType": "STORE_CONFIRMED"},
        "priceCents": price, "currency": "EUR", "priceKind": kind,
        "acquisitionMode": PUBLISHED_OFFER if kind == "SALE" else PRICE_QUERY,
        "validFrom": DATE, "validUntil": "2026-11-06",
        "depositCents": 0, "conditional": [],
        "availability": "IN_STOCK_REPORTED",
        "source": {"origin": "official-synthetic-rewe", "rightsStatus": rights,
                   "rightsEvidenceRef": evidence, "observedAt": NOW,
                   "dataQuality": "CONFIRMED", "evidenceKind": "OFFICIAL_WEB"}
    }


def grant(retailer="REWE", mode=PUBLISHED_OFFER, evidence="E1"):
    return {"official-synthetic-rewe": {
        "rightsEvidenceRef": evidence, "usageContext": "APP_DISPLAY",
        "retailerId": retailer, "acquisitionModes": [mode],
        "hostVerified": True}}


class RetailerAndRightsGates(unittest.TestCase):
    def test_eight_retailer_policy_is_complete_and_not_a_license(self):
        matrix = POLICY["retailerCapabilities"]
        self.assertEqual(set(matrix), {
            "ALDI_NORD", "ALDI_SUED", "REWE", "LIDL",
            "PENNY", "KAUFLAND", "EDEKA", "NETTO_MD"})
        self.assertEqual(POLICY["category"],
                         "PROJECT_FUNCTIONAL_CAPABILITY_NOT_LEGAL_PERMISSION")
        for retailer in matrix:
            with self.subTest(retailer=retailer):
                sale = obs(retailer=retailer)
                self.assertTrue(source_gate(sale)[0])
                targeted = obs(retailer=retailer, kind="LISTED_REGULAR")
                self.assertEqual(source_gate(targeted)[0],
                                 matrix[retailer]["targetedProductPriceQuery"])

    def test_netto_md_disallows_targeted_even_when_rights_look_permitted(self):
        p = obs(retailer="NETTO_MD", kind="LISTED_REGULAR")
        self.assertFalse(source_gate(p, usage_context="APP_DISPLAY",
                                     rights_grants=grant(retailer="NETTO_MD",
                                                         mode=PRICE_QUERY))[0])
        self.assertTrue(source_gate(obs(retailer="NETTO_MD"))[0])

    def test_display_requires_acquisition_provenance_even_for_sale(self):
        # A targeted query may return an advertised SALE; priceKind alone
        # cannot prove that the data came from a published-offer feed.
        sale = obs(retailer="PENNY")
        sale.pop("acquisitionMode")
        original = copy.deepcopy(sale)
        penny_grant = grant(retailer="PENNY")
        self.assertFalse(source_gate(sale, usage_context="APP_DISPLAY",
                                     rights_grants=penny_grant)[0])
        self.assertTrue(source_gate(sale, usage_context="RESEARCH_ONLY")[0])
        self.assertEqual(sale, original)
        sale["acquisitionMode"] = PRICE_QUERY
        self.assertFalse(source_gate(sale, usage_context="APP_DISPLAY",
                                     rights_grants=penny_grant)[0])
        sale["acquisitionMode"] = PUBLISHED_OFFER
        self.assertTrue(source_gate(sale, usage_context="APP_DISPLAY",
                                    rights_grants=penny_grant)[0])

    def test_conflicting_observation_and_source_mode_rejected(self):
        sale = obs(retailer="PENNY")
        sale["source"]["acquisitionMode"] = PRICE_QUERY
        before = copy.deepcopy(sale)
        for context in ("APP_DISPLAY", "RESEARCH_ONLY"):
            with self.subTest(context=context):
                self.assertFalse(source_gate(sale, usage_context=context,
                                             rights_grants=grant(retailer="PENNY"))[0])
        self.assertEqual(sale, before)

    def test_unproven_sale_mode_does_not_leak_through_comparison(self):
        target = obs("TARGET", retailer="REWE", price=200)
        cheaper = obs("ALT", retailer="PENNY", price=100)
        cheaper.pop("acquisitionMode")
        cheaper["source"]["origin"] = "penny-synthetic"
        rights = grant()
        rights["penny-synthetic"] = {
            "rightsEvidenceRef": "E1", "usageContext": "APP_DISPLAY",
            "retailerId": "PENNY", "acquisitionModes": [PUBLISHED_OFFER],
            "hostVerified": True}
        originals = copy.deepcopy([target, cheaper, rights])
        result = compare_prices(target, [cheaper], DATE, as_of=NOW,
                                coverage={"complete": True},
                                usage_context="APP_DISPLAY", rights_grants=rights)
        self.assertEqual(result["alternatives"], [])
        self.assertTrue(result["incomplete"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["signals"])
        self.assertNotIn("100", str(result))
        self.assertEqual([target, cheaper, rights], originals)

    def test_non_sale_cannot_disguise_targeted_query_as_published_offer(self):
        regular = obs(kind="LISTED_REGULAR", retailer="PENNY")
        regular["acquisitionMode"] = PUBLISHED_OFFER
        self.assertFalse(source_gate(regular)[0])

    def test_research_mode_never_implies_display_permission(self):
        unverified = obs(rights="UNVERIFIED")
        self.assertTrue(source_gate(unverified, usage_context="RESEARCH_ONLY")[0])
        ok, message = source_gate(unverified, usage_context="APP_DISPLAY",
                                  rights_grants=grant())
        self.assertFalse(ok)
        self.assertIn("rights", message)

    def test_app_display_requires_explicit_matching_source_grant(self):
        permitted = obs()
        self.assertFalse(source_gate(permitted, usage_context="APP_DISPLAY")[0])
        self.assertTrue(source_gate(permitted, usage_context="APP_DISPLAY",
                                    rights_grants=grant())[0])
        self.assertFalse(source_gate(permitted, usage_context="APP_DISPLAY",
                                     rights_grants=grant(evidence="WRONG"))[0])
        self.assertFalse(source_gate(permitted, usage_context="APP_DISPLAY",
                                     rights_grants=grant(mode=PRICE_QUERY))[0])
        forged = grant()
        forged["official-synthetic-rewe"]["hostVerified"] = False
        self.assertFalse(source_gate(permitted, usage_context="APP_DISPLAY",
                                     rights_grants=forged)[0])
        self.assertFalse(source_gate(obs(rights="RESTRICTED"),
                                     usage_context="APP_DISPLAY",
                                     rights_grants=grant())[0])

    def test_app_display_redacts_rejected_alternative_and_signals_grey(self):
        target = obs("TARGET", price=200)
        alternative = obs("CHEAPER", price=100, rights="UNVERIFIED")
        out = compare_prices(target, [alternative], DATE, as_of=NOW,
                             coverage={"complete": True},
                             usage_context="APP_DISPLAY",
                             rights_grants=grant())
        self.assertEqual(out["alternatives"], [])
        self.assertIn("GREY_MAY_BE_CHEAPER", out["signals"])
        self.assertTrue(out["incomplete"])
        self.assertNotIn("100", str(out))
        self.assertIn("CHEAPER", out["rejected"][0]["observationId"])

    def test_target_with_unverified_rights_cannot_be_exposed(self):
        with self.assertRaises(DomainError):
            compare_prices(obs("TARGET", rights="UNVERIFIED"), [], DATE,
                           as_of=NOW, coverage={"complete": True},
                           usage_context="APP_DISPLAY", rights_grants=grant())
        result = compare_catalog([obs("TARGET", rights="UNVERIFIED")],
                                 DATE, as_of=NOW, usage_context="APP_DISPLAY",
                                 rights_grants=grant(), coverage={"complete": True})
        self.assertEqual(result["comparisons"], [])
        self.assertEqual(len(result["omittedTargets"]), 1)

    def test_approved_source_remains_visible_only_with_correct_rights(self):
        target = obs("TARGET", price=200)
        other = obs("CHEAPER", price=100)
        result = compare_prices(target, [other], DATE, as_of=NOW,
                                coverage={"complete": True},
                                usage_context="APP_DISPLAY", rights_grants=grant())
        self.assertEqual(len(result["alternatives"]), 1)
        self.assertEqual(result["alternatives"][0]["priceCents"], 100)

    def test_offer_interest_is_redacted_when_rights_missing(self):
        item = obs("SALE", rights="UNVERIFIED")
        self.assertEqual(list_offer_interests([item], {}, DATE, as_of=NOW,
                         usage_context="APP_DISPLAY", rights_grants=grant()), [])
        self.assertEqual(len(list_offer_interests([item], {}, DATE,
                             as_of=NOW, usage_context="RESEARCH_ONLY")), 1)

    def test_purchase_suggestion_without_grant_has_no_display_prices(self):
        price = obs("PRICE", price=90, rights="UNVERIFIED")
        product = {"productId": "OATS", "foodTypeId": "oats",
                   "priceCents": 90, "quantity": price["article"]["quantity"],
                   "depositCents": 0, "shelfLifeDays": 30,
                   "storageClass": "DRY", "packageVolumeMl": 500,
                   "priceObservation": price}
        needs = {"totals": [{"foodTypeId": "oats", "quantityToBuy": 500,
                             "unit": "g", "basis": "NET"}],
                 "needs": [{"foodTypeId": "oats", "quantityToBuy": 500,
                            "dueDate": DATE}]}
        result = suggest_purchases(needs, [product], shopping_date=DATE, as_of=NOW,
                                    budget={"amountCents": 200, "periodStart": DATE,
                                            "periodEnd": DATE},
                                    capacity={"DRY": 1000},
                                    usage_context="APP_DISPLAY",
                                    rights_grants=grant())
        self.assertIsNone(result["totalCostCents"])
        self.assertIsNone(result["totalCheckoutCents"])
        self.assertEqual(result["items"][0]["mix"], [])
        self.assertNotIn("90", str(result))
        price["source"]["rightsStatus"] = "PERMITTED"
        result = suggest_purchases(needs, [product], shopping_date=DATE, as_of=NOW,
                                    budget={"amountCents": 200, "periodStart": DATE,
                                            "periodEnd": DATE},
                                    capacity={"DRY": 1000},
                                    usage_context="APP_DISPLAY",
                                    rights_grants=grant())
        self.assertEqual(result["totalCheckoutCents"], 90)

    def test_own_receipt_is_private_history_not_current_price(self):
        purchase = obs(kind="HISTORICAL_PAID", retailer="PENNY")
        purchase["confirmed"] = True
        purchase["purchaseAt"] = NOW
        purchase["source"]["evidenceKind"] = "USER_CONFIRMED_RECEIPT"
        self.assertTrue(source_gate(purchase,
                                    usage_context="PRIVATE_USER_HISTORY")[0])
        self.assertFalse(source_gate(purchase, usage_context="APP_DISPLAY",
                                     rights_grants=grant(retailer="PENNY"))[0])
        self.assertFalse(source_gate(dict(purchase, confirmed=False),
                                     usage_context="PRIVATE_USER_HISTORY")[0])
        self.assertFalse(source_gate(dict(purchase, purchaseAt=None),
                                     usage_context="PRIVATE_USER_HISTORY")[0])
        self.assertFalse(source_gate(dict(purchase, purchaseAt="not-a-date"),
                                     usage_context="PRIVATE_USER_HISTORY")[0])

    def test_historical_alternatives_respect_display_rights(self):
        bought = obs("PURCHASED", price=200, kind="HISTORICAL_PAID")
        bought["confirmed"] = True
        bought["purchaseAt"] = NOW
        bought["source"]["evidenceKind"] = "USER_CONFIRMED_RECEIPT"
        old_alt = obs("OLD_ALT", price=100, kind="LISTED_REGULAR",
                      rights="UNVERIFIED")
        result = evaluate_past_purchase(
            bought, [old_alt], accessible_stores={"REWE": ["SHOP1"]},
            coverage={"complete": True}, usage_context="APP_DISPLAY",
            rights_grants=grant(mode=PRICE_QUERY))
        self.assertEqual(result["comparison"]["alternatives"], [])
        self.assertIsNone(result["comparison"]["bestProvenMerchandiseSavingCents"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["comparison"]["signals"])
        old_alt["source"]["rightsStatus"] = "PERMITTED"
        result = evaluate_past_purchase(
            bought, [old_alt], accessible_stores={"REWE": ["SHOP1"]},
            coverage={"complete": True}, usage_context="APP_DISPLAY",
            rights_grants=grant(mode=PRICE_QUERY))
        self.assertEqual(result["comparison"]["bestProvenMerchandiseSavingCents"], 100)

    def test_early_purchase_evidence_rights_are_independent(self):
        need = {"foodTypeId": "oats", "dueDate": "2026-11-03",
                "quantityToBuy": 500, "unit": "g", "basis": "NET"}
        offer = obs("NOW", price=100)
        future = obs("NEXT", price=130, kind="LISTED_REGULAR")
        future["validFrom"] = "2026-11-03"
        grants = grant()
        grants["official-synthetic-rewe"]["acquisitionModes"] = [
            PUBLISHED_OFFER, PRICE_QUERY]
        common = {"shopping_date": DATE, "as_of": NOW,
                  "budget": {"amountCents": 200, "periodStart": DATE,
                             "periodEnd": DATE},
                  "capacity": {"DRY": 1000},
                  "shelf_life_days": 7, "storage_class": "DRY",
                  "package_volume_ml": 500, "future_price": future,
                  "usage_context": "APP_DISPLAY", "rights_grants": grants}
        offer["source"]["rightsStatus"] = "UNVERIFIED"
        blocked = evaluate_early_purchase(need, offer, **common)
        self.assertIsNone(blocked["merchandiseCents"])
        self.assertIsNone(blocked["savingsProvenCents"])
        offer["source"]["rightsStatus"] = "PERMITTED"
        future["source"]["rightsStatus"] = "UNVERIFIED"
        blocked = evaluate_early_purchase(need, offer, **common)
        self.assertIsNone(blocked["futureComparableCents"])
        self.assertIsNone(blocked["savingsProvenCents"])
        future["source"]["rightsStatus"] = "PERMITTED"
        valid = evaluate_early_purchase(need, offer, **common)
        self.assertEqual(valid["status"], "ADVANCE_FEASIBLE_NOT_PURCHASED")
        self.assertEqual(valid["savingsProvenCents"], 30)

    def test_cli_refuses_caller_forged_grants(self):
        with self.assertRaises(DomainError):
            dispatch({"operation": "comparePrices", "usageContext": "APP_DISPLAY",
                      "rightsGrants": grant()})
        with self.assertRaises(DomainError):
            dispatch({"operation": "comparePrices", "rightsGrants": grant()})

    def test_host_grant_mode_must_be_typed_list_not_substring(self):
        misformed = grant()
        misformed["official-synthetic-rewe"]["acquisitionModes"] = (
            "PUBLISHED_OFFER_COLLECTION")
        self.assertFalse(source_gate(obs(), usage_context="APP_DISPLAY",
                                     rights_grants=misformed)[0])

    def test_all_restricted_catalog_has_aggregate_grey_coverage(self):
        # No comparison row exists, but rights filtering still loses coverage.
        blocked = obs("BLOCKED", rights="RESTRICTED", price=73)
        before = copy.deepcopy(blocked)
        result = compare_catalog(
            [blocked], DATE, as_of=NOW, coverage={"complete": True},
            usage_context="APP_DISPLAY", rights_grants=grant())
        self.assertEqual(result["comparisons"], [])
        self.assertEqual(len(result["omittedTargets"]), 1)
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["signals"], ["GREY_MAY_BE_CHEAPER"])
        self.assertTrue(result["gaps"])
        self.assertNotIn("73", str(result))
        self.assertEqual(blocked, before)

    def test_catalog_aggregate_coverage_propagates_child_rights_gap(self):
        visible = obs("VISIBLE", price=200)
        blocked = obs("BLOCKED", rights="UNVERIFIED", price=73)
        result = compare_catalog(
            [visible, blocked], DATE, as_of=NOW, coverage={"complete": True},
            usage_context="APP_DISPLAY", rights_grants=grant())
        self.assertEqual(len(result["comparisons"]), 1)
        self.assertTrue(result["incomplete"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["signals"])
        self.assertNotIn("73", str(result))

    def test_historical_display_rejects_unverified_receipt_origin(self):
        bought = obs("PURCHASED", price=200, kind="HISTORICAL_PAID")
        bought["confirmed"] = True
        bought["purchaseAt"] = NOW
        alternative = obs("ALT", price=100, kind="LISTED_REGULAR")
        options = dict(accessible_stores={"REWE": ["SHOP1"]},
                       coverage={"complete": True},
                       usage_context="APP_DISPLAY",
                       rights_grants=grant(mode=PRICE_QUERY))
        before = copy.deepcopy(bought)
        rejected = evaluate_past_purchase(bought, [alternative], **options)
        self.assertEqual(rejected["status"], "UNKNOWN")
        self.assertIsNone(rejected["comparison"])
        self.assertIn("receipt", rejected["reason"])
        self.assertNotIn("100", str(rejected))
        self.assertEqual(bought, before)
        bought["source"]["evidenceKind"] = "USER_CONFIRMED_RECEIPT"
        accepted = evaluate_past_purchase(bought, [alternative], **options)
        self.assertEqual(
            accepted["comparison"]["bestProvenMerchandiseSavingCents"], 100)

    def test_unknown_usage_context_is_rejected(self):
        with self.assertRaises(DomainError):
            source_gate(obs(), usage_context="NOT_A_CONTEXT")


if __name__ == "__main__":
    unittest.main()
