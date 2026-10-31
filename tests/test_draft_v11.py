"""Architecture v1.1.0-draft opt-in mapping: real JSON Schema validation.

Draft adapters have NO production CLI registration. They do not change the
approved v1.0.0-draft interchange behavior. All examples are synthetic.
"""
import copy
import json
from pathlib import Path
import unittest

import jsonschema

from eg_shopping.engine import DomainError, project_needs, evaluate_offer_interest
from eg_shopping.draft_v11 import (
    need_projection_envelope, purchase_suggestion_envelope,
    offer_interest_envelope, past_comparison_envelope
)

ROOT = Path(__file__).resolve().parents[1]
DRAFT_SCHEMA = json.loads((ROOT / "contracts/v1.1/contract.schema.json").read_text())
DRAFT_EXAMPLES = json.loads((ROOT / "contracts/v1.1/examples.json").read_text())
STABLE_SCHEMA = json.loads((ROOT / "contracts/v1/contract.schema.json").read_text())
STAMP = "2026-10-31T11:00:00+01:00"
SNAPSHOT = "2026-10-31T10:00:00+01:00"


def check(message):
    jsonschema.Draft202012Validator(
        DRAFT_SCHEMA, format_checker=jsonschema.FormatChecker()
    ).validate(message)
    return message


class DraftInterchange(unittest.TestCase):
    def test_all_canonical_draft_examples_are_schema_valid(self):
        jsonschema.Draft202012Validator.check_schema(DRAFT_SCHEMA)
        self.assertEqual(len(DRAFT_EXAMPLES), 9)
        for m in DRAFT_EXAMPLES:
            with self.subTest(kind=m["messageType"]):
                check(m)

    def test_legacy_version_does_not_implicitly_change(self):
        assert DRAFT_EXAMPLES[0]["contractVersion"] == "1.1.0-draft"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(
                STABLE_SCHEMA, format_checker=jsonschema.FormatChecker()
            ).validate(DRAFT_EXAMPLES[0])

    def test_need_projection_single_and_cumulative_horizons(self):
        p = project_needs({
            "asOf": "2026-10-31", "stock": [], "demands": [
                {"eventId": "PLAN1", "foodTypeId": "oats-fine",
                 "dueDate": "2026-11-01",
                 "quantity": {"amount": 500, "unit": "g", "basis": "NET",
                              "confirmed": True}, "kind": "PREPARATION_RAW"},
                {"eventId": "PLAN2", "foodTypeId": "oats-fine",
                 "dueDate": "2026-11-04",
                 "quantity": {"amount": 300, "unit": "g", "basis": "NET",
                              "confirmed": True}, "kind": "PREPARATION_RAW"}]},
            horizons=(1, 7, 28))
        seven = check(need_projection_envelope(
            p, horizon_days=7, snapshot_at=SNAPSHOT, as_of=STAMP,
            trace_id="draft-need7", source_snapshot_refs=["SYNTHETIC-SNAP"],
            stock_refs_by_event={"PLAN1": ["SYNTH-LOT-01"]}))
        one = check(need_projection_envelope(
            p, horizon_days=1, snapshot_at=SNAPSHOT, as_of=STAMP,
            trace_id="draft-need1", source_snapshot_refs=["SYNTHETIC-SNAP"]))
        self.assertEqual(len(seven["payload"]["needs"]), 2)
        self.assertEqual(one["payload"]["needs"], [])
        self.assertEqual(seven["payload"]["needs"][0]["quantity"]["amount"], 500)
        self.assertEqual(seven["payload"]["needs"][0]["stockEvidenceRefs"], ["SYNTH-LOT-01"])
        self.assertEqual(seven["payload"]["horizonMode"], "CUMULATIVE_FROM_SNAPSHOT")
        self.assertEqual(p["horizons"]["7"]["totals"][0]["quantityToBuy"], 800)
        self.assertEqual(seven["meta"]["usageContext"], "RESEARCH_ONLY")
        self.assertEqual(p["sideEffects"], [])

    def test_unknown_demand_not_falsely_typed_or_zero(self):
        p = project_needs({
            "asOf": "2026-10-31", "stock": [], "demands": [
                {"eventId": "UNKNOWN1", "foodTypeId": "oats-fine",
                 "dueDate": "2026-11-01", "quantity": None}]}, horizons=(7,))
        out = check(need_projection_envelope(
            p, horizon_days=7, snapshot_at=SNAPSHOT, as_of=STAMP,
            trace_id="draft-unknown", source_snapshot_refs=["SNAP"]))
        self.assertEqual(out["payload"]["needs"], [])
        self.assertEqual(out["payload"]["completeness"], "PARTIAL")
        self.assertIn("UNKNOWN1", " ".join(out["payload"]["warnings"]))
        self.assertEqual(out["payload"]["unknownNeeds"][0]["needId"], "UNKNOWN1")
        self.assertIsNone(out["payload"]["unknownNeeds"][0]["quantityToBuy"])
        self.assertNotIn("unit", out["payload"]["unknownNeeds"][0])
        self.assertNotIn('"amount": 0', json.dumps(out))

    def test_need_projection_rejects_unprovable_time_or_refs(self):
        p = project_needs({"asOf": "2026-10-31", "stock": [], "demands": []},
                          horizons=(7,))
        kwargs = {"projection": p, "horizon_days": 7,
                  "snapshot_at": SNAPSHOT, "as_of": STAMP,
                  "trace_id": "S", "source_snapshot_refs": ["SNAP"]}
        for changes in [
            {"snapshot_at": "2026-11-01T11:00:00+01:00"},
            {"source_snapshot_refs": []},
            {"horizon_days": 365},
            {"source_snapshot_refs": ["SNAP", "SNAP"]},
            {"trace_id": ""}
        ]:
            with self.subTest(changes=changes), self.assertRaises(DomainError):
                need_projection_envelope(**dict(kwargs, **changes))

    def test_purchase_adapter_verified_single_pack_is_draft_valid(self):
        item = {"foodTypeId": "oats-fine", "status": "FEASIBLE_NOT_PURCHASED",
                "priceEvidenceVerified": True, "costCents": 199,
                "checkoutCents": 224, "quantityBought": 500,
                "mix": [{"productId": "OATS-500", "packs": 1,
                         "quantityBought": 500, "costCents": 199,
                         "depositCents": 25, "checkoutCents": 224,
                         "observationId": "OFFER-1", "retailerId": "REWE",
                         "storeId": "R1"}], "reasons": []}
        out = check(purchase_suggestion_envelope(
            item, need_ids=["N-1"], unit="g", basis="NET",
            created_at=STAMP, trace_id="draft-purch",
            suggestion_id="S-1", budget_period={"from": "2026-10-31",
                                                 "until": "2026-11-07"},
            capacity_evidence={"snapshotAt": SNAPSHOT, "scope": "DRY"}))
        self.assertEqual(out["payload"]["productId"], "OATS-500")
        self.assertEqual(out["payload"]["observationRefs"], ["OFFER-1"])
        self.assertEqual(out["payload"]["checkoutCents"], 224)
        self.assertFalse(out["payload"]["hasSideEffects"])
        self.assertEqual(out["payload"]["packageLines"][0]["checkoutCents"], 224)
        self.assertEqual(out["payload"]["packageLines"][0]["depositCents"], 25)

    def test_purchase_adapter_unverified_is_not_confirmed_cost(self):
        item = {"foodTypeId": "oats-fine", "status": "REVIEW",
                "priceEvidenceVerified": False, "costCents": 100,
                "checkoutCents": None, "quantityBought": 500,
                "mix": [{"productId": "P", "packs": 1, "quantityBought": 500,
                         "costCents": 100}], "reasons": ["source missing"]}
        out = check(purchase_suggestion_envelope(
            item, need_ids=["N-1"], unit="g", basis="NET",
            created_at=STAMP, trace_id="draft-uncertain",
            suggestion_id="S-2"))
        self.assertEqual(out["payload"]["status"], "REVIEW")
        self.assertIsNone(out["payload"]["expectedCents"])
        self.assertIsNone(out["payload"]["checkoutCents"])
        self.assertEqual(out["payload"]["observationRefs"], [])

    def test_purchase_adapter_mixed_packages_retain_exact_refs(self):
        item = {"status": "FEASIBLE_NOT_PURCHASED", "priceEvidenceVerified": True,
                "costCents": 330, "checkoutCents": 330, "quantityBought": 1500,
                "mix": [{"productId": "A", "packs": 1, "quantityBought": 1000,
                         "costCents": 210, "depositCents": 0, "checkoutCents": 210,
                         "observationId": "OA"},
                        {"productId": "B", "packs": 1, "quantityBought": 500,
                         "costCents": 120, "depositCents": 0, "checkoutCents": 120,
                         "observationId": "OB"}], "reasons": []}
        out = check(purchase_suggestion_envelope(
            item, need_ids=["N-1", "N-2"], unit="g", basis="NET",
            created_at=STAMP, trace_id="mixed", suggestion_id="M-1"))
        self.assertIsNone(out["payload"]["productId"])
        self.assertIsNone(out["payload"]["packageCount"])
        self.assertEqual(out["payload"]["observationRefs"], ["OA", "OB"])
        self.assertEqual(out["payload"]["packageLines"][0]["merchandiseCents"], 210)
        self.assertEqual(out["payload"]["checkoutCents"], 330)

    def test_purchase_adapter_missing_one_mix_observation_cannot_prove_costs(self):
        item = {"status": "FEASIBLE_NOT_PURCHASED", "priceEvidenceVerified": True,
                "costCents": 330, "checkoutCents": 330, "quantityBought": 1500,
                "mix": [
                    {"productId": "A", "packs": 1, "quantityBought": 1000,
                     "costCents": 210, "observationId": "OA"},
                    {"productId": "B", "packs": 1, "quantityBought": 500,
                     "costCents": 120}
                ], "reasons": []}
        out = check(purchase_suggestion_envelope(
            item, need_ids=["N1"], unit="g", basis="NET", created_at=STAMP,
            trace_id="missing-line-proof", suggestion_id="S3"))
        self.assertEqual(out["payload"]["status"], "REVIEW")
        self.assertEqual(out["payload"]["observationRefs"], ["OA"])
        self.assertIsNone(out["payload"]["expectedCents"])
        self.assertIsNone(out["payload"]["checkoutCents"])
        self.assertIn("price observation not verified", out["payload"]["warnings"])

    def test_ad017_unconfirmed_cash_is_null_for_unknown_deposit(self):
        item = {"status": "FEASIBLE_NOT_PURCHASED", "priceEvidenceVerified": True,
                "costCents": 100, "checkoutCents": None, "quantityBought": 500,
                "mix": [{"productId": "P", "packs": 1, "quantityBought": 500,
                         "costCents": 100, "observationId": "O",
                         "depositCents": None, "checkoutCents": None}]}
        result = check(purchase_suggestion_envelope(
            item, need_ids=["N"], unit="g", basis="NET",
            created_at=STAMP, trace_id="no-deposit", suggestion_id="NO-DEPOSIT"))
        self.assertEqual(result["payload"]["expectedCents"], 100)
        self.assertIsNone(result["payload"]["checkoutCents"])
        self.assertIsNone(result["payload"]["packageLines"][0]["depositCents"])

    def test_ad017_rejects_line_cash_arithmetic_mismatch(self):
        item = {"status": "FEASIBLE_NOT_PURCHASED", "priceEvidenceVerified": True,
                "costCents": 100, "checkoutCents": 150, "quantityBought": 500,
                "mix": [{"productId": "P", "packs": 1, "quantityBought": 500,
                         "costCents": 100, "depositCents": 25,
                         "checkoutCents": 150, "observationId": "O"}]}
        with self.assertRaises(DomainError):
            purchase_suggestion_envelope(item, need_ids=["N"], unit="g",
                basis="NET", created_at=STAMP, trace_id="bad-cash",
                suggestion_id="BAD-CASH")

    def test_ad017_unknown_without_due_date_remains_unresolved(self):
        p = project_needs({"asOf": "2026-10-31", "stock": [], "demands": [
            {"eventId": "UNK_DATE", "foodTypeId": "oats-fine",
             "quantity": None}]}, horizons=(7,))
        v = check(need_projection_envelope(p, horizon_days=7,
            snapshot_at=SNAPSHOT, as_of=STAMP, trace_id="unk-date",
            source_snapshot_refs=["S"]))
        self.assertIsNone(v["payload"]["unknownNeeds"][0]["dueDate"])
        self.assertEqual(v["payload"]["completeness"], "PARTIAL")

    def test_ad017_savings_status_requires_positive_merchandise_delta(self):
        report = {"noHindsight": True, "comparison": {
            "alternatives": [{"observationId": "A"}],
            "bestProvenMerchandiseSavingCents": None, "gaps": [],
            "rejected": []}}
        v = check(past_comparison_envelope(report,
            purchase_ref="P", purchase_at="2026-10-31T09:00:00+01:00",
            store_scope={"retailerId": "REWE", "storeId": "1",
                         "scopeType": "STORE_CONFIRMED"},
            created_at=STAMP, trace_id="no-save"))
        self.assertNotEqual(v["payload"]["status"], "PROVEN")
        self.assertIsNone(v["payload"]["savingsProvenCents"])

    def test_purchase_adapter_rejects_duplicate_need_ids(self):
        with self.assertRaises(DomainError):
            purchase_suggestion_envelope(
                {}, need_ids=["N", "N"], unit="g", basis="NET",
                created_at=STAMP, trace_id="bad", suggestion_id="S")

    def test_interest_adapter_proposes_without_persistence(self):
        state = {"interests": {}, "hiddenProducts": []}
        old = copy.deepcopy(state)
        action = {"action": "INTERESTED", "productId": "P", "foodTypeId": "oats-fine"}
        result = evaluate_offer_interest(state, action)
        out = check(offer_interest_envelope(
            result, action, interest_id="INT-1", effective_at=STAMP,
            trace_id="draft-interest", source_offer_ids=["OBS-1"]))
        self.assertFalse(out["payload"]["confirmed"])
        self.assertEqual(out["payload"]["proposedState"]["interests"]["P"], "INTERESTED")
        self.assertEqual(state, old)
        self.assertFalse(result["purchaseRecorded"])

    def test_interest_adapter_rejects_confirmed_purchase_state(self):
        action = {"action": "INTERESTED", "productId": "P"}
        result = evaluate_offer_interest({}, action)
        with self.assertRaises(DomainError):
            offer_interest_envelope(dict(result, stockChanged=True), action,
                interest_id="INT-1", effective_at=STAMP, trace_id="bad",
                source_offer_ids=[])

    def test_past_adapter_marks_actual_savings_only(self):
        report = {"noHindsight": True, "comparison": {
            "alternatives": [{"observationId": "ALT-1"}],
            "bestProvenMerchandiseSavingCents": 19,
            "gaps": ["Other stores unknown"], "rejected": [
                {"reason": "unverifiable coupon"}], "unitOnlyAlternatives": [
                {"observationId": "ALT-UNIT"}]}}
        out = check(past_comparison_envelope(
            report, purchase_ref="PUR-1", purchase_at="2026-10-31T09:00:00+01:00",
            store_scope={"retailerId": "REWE", "storeId": "R1",
                         "scopeType": "STORE_CONFIRMED"},
            created_at=STAMP, trace_id="hist"))
        self.assertEqual(out["payload"]["status"], "PROVEN")
        self.assertEqual(out["payload"]["savingsProvenCents"], 19)
        self.assertEqual(out["payload"]["evidenceCutoff"], "2026-10-31T09:00:00+01:00")
        self.assertEqual(out["payload"]["unitOnlyAlternatives"], ["ALT-UNIT"])

    def test_past_adapter_rejects_future_and_unconfirmed_scope(self):
        args = {"report": {"noHindsight": True, "comparison": {
                    "alternatives": [], "gaps": [], "rejected": []}},
                "purchase_ref": "PUR", "purchase_at": STAMP,
                "store_scope": {"retailerId": "REWE",
                                "scopeType": "CHAIN_WIDE_REPORTED"},
                "created_at": STAMP, "trace_id": "hist"}
        with self.assertRaises(DomainError):
            past_comparison_envelope(**args)
        args["store_scope"] = {"retailerId": "REWE", "storeId": "R1",
                               "scopeType": "STORE_CONFIRMED"}
        args["created_at"] = "2026-10-30T09:00:00+01:00"
        with self.assertRaises(DomainError):
            past_comparison_envelope(**args)

    def test_schema_rejects_mutated_emissions(self):
        report = {"noHindsight": True, "comparison": {
            "alternatives": [], "gaps": [], "rejected": []}}
        valid = past_comparison_envelope(
            report, purchase_ref="PUR", purchase_at="2026-10-31T09:00:00+01:00",
            store_scope={"retailerId": "REWE", "storeId": "R1",
                         "scopeType": "STORE_CONFIRMED"},
            created_at=STAMP, trace_id="hist")
        check(valid)
        mutations = [
            ("contractVersion", "1.0.0-draft"),
            ("messageType", "shopping.nonexistent"),
        ]
        validator = jsonschema.Draft202012Validator(
            DRAFT_SCHEMA, format_checker=jsonschema.FormatChecker())
        for key, val in mutations:
            msg = copy.deepcopy(valid)
            msg[key] = val
            self.assertFalse(validator.is_valid(msg))
        for key, val in [("savingsProvenCents", -2),
                         ("purchaseAt", "bad-date")]:
            msg = copy.deepcopy(valid)
            msg["payload"][key] = val
            self.assertFalse(validator.is_valid(msg))
        msg = copy.deepcopy(valid)
        msg["payload"]["storeScope"]["storeId"] = None
        self.assertFalse(validator.is_valid(msg))


if __name__ == "__main__":
    unittest.main()
