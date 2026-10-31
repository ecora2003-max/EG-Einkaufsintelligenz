"""EXPERIMENTAL, explicitly opted-in v1.1.0-draft envelope adapters.

Not a production contract upgrade. The canonical CLI continues to publish
1.0.0-draft messages until architecture and Codex approve v1.1.
All IDs, timestamps and evidence references must come from the host:
this adapter never fabricates market coverage, purchases, or stock movements.
"""
from __future__ import annotations

from datetime import timedelta

from .engine import DomainError, _day, _instant

DRAFT_VERSION = "1.1.0-draft"
ALLOWED_KINDS = frozenset((
    "shopping.need.projection", "shopping.purchase.suggestion",
    "shopping.offer.interest", "shopping.past.comparison",
))


def _identifier(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(f"{label}: nonempty identifier required")
    return value


def _references(values, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(values, (list, tuple)):
        raise DomainError(f"{label}: array required")
    result = [_identifier(v, label) for v in values]
    if len(set(result)) != len(result) or (nonempty and not result):
        raise DomainError(f"{label}: duplicate or missing reference")
    return result


def _envelope(kind: str, payload: dict, *, created_at: str,
              trace_id: str, snapshot_at: str | None = None) -> dict:
    if kind not in ALLOWED_KINDS:
        raise DomainError("unknown experimental message type")
    created = _instant(created_at)
    _identifier(trace_id, "traceId")
    if snapshot_at is not None and _instant(snapshot_at) > created:
        raise DomainError("input snapshot may not be later than message")
    meta = {"producer": "eg-einkaufsintelligenz-draft-adapter",
            "createdAt": created_at, "traceId": trace_id,
            "usageContext": "RESEARCH_ONLY"}
    if snapshot_at is not None:
        meta["inputsSnapshotAt"] = snapshot_at
    return {"contractVersion": DRAFT_VERSION, "messageType": kind,
            "meta": meta, "payload": payload}


def need_projection_envelope(projection: dict, *, horizon_days: int,
                             snapshot_at: str, as_of: str, trace_id: str,
                             source_snapshot_refs: list[str],
                             stock_refs_by_event: dict[str, list[str]] | None = None) -> dict:
    """Serialize ONE cumulative horizon without duplicating stock allocations.

    The original engine projection is not mutated. Unknown demand remains a
    nullable unconfirmed quantity; it must not become a zero.
    """
    _instant(snapshot_at)
    cutoff = _instant(as_of)
    if _instant(snapshot_at) > cutoff:
        raise DomainError("snapshot newer than evidence cutoff")
    if type(horizon_days) is not int or not 1 <= horizon_days <= 365:
        raise DomainError("horizonDays out of range")
    if not isinstance(projection, dict) or str(horizon_days) not in projection.get("horizons", {}):
        raise DomainError("requested horizon not projected")
    if _day(projection["asOf"]) != cutoff.date():
        # Host must align date-view and local snapshot calendar before export.
        raise DomainError("projection date does not match asOf")
    origin_day = _day(projection["asOf"])
    bound = origin_day + timedelta(days=horizon_days)
    warnings = list(projection.get("warnings") or [])
    refs = stock_refs_by_event or {}
    needs = []
    used_ids = set()
    view = projection["horizons"][str(horizon_days)]
    for row in view.get("needs", []):
        due = _day(row["dueDate"])
        if not origin_day <= due < bound:
            raise DomainError("need outside declared cumulative horizon")
        eid = _identifier(row.get("eventId"), "need eventId")
        if eid in used_ids:
            raise DomainError("duplicate need identifier")
        used_ids.add(eid)
        amount = row.get("quantityToBuy")
        if type(amount) is not int or amount <= 0:
            raise DomainError("positive known purchase quantity required")
        item = {"needId": eid, "foodTypeId": _identifier(row.get("foodTypeId"), "foodTypeId"),
                "dueDate": row["dueDate"],
                "quantity": {"amount": amount, "unit": row["unit"],
                             "basis": row["basis"], "confirmed": True},
                "stockEvidenceRefs": _references(refs.get(eid, []), "stock evidence"),
                "planRefs": [eid] if row.get("origin") == "PLAN" else [],
                "completeness": "COMPLETE" if projection.get("snapshotComplete") is True
                                else "PARTIAL",
                "warnings": []}
        needs.append(item)
    for unknown in projection.get("unknownNeeds") or []:
        eid = _identifier(unknown.get("eventId"), "unknown demand eventId")
        if eid in used_ids:
            raise DomainError("duplicate known and unknown need")
        due_str = unknown.get("dueDate")
        food = unknown.get("foodTypeId")
        if not due_str or not food:
            warnings.append(f"unknown demand {eid}: due date or foodTypeId missing")
            continue
        due = _day(due_str)
        if not origin_day <= due < bound:
            continue
        used_ids.add(eid)
        needs.append({
            "needId": eid, "foodTypeId": _identifier(food, "foodTypeId"),
            "dueDate": due_str,
            "quantity": {"amount": None, "unit": "g", "basis": "UNKNOWN",
                         "confirmed": False},
            "stockEvidenceRefs": [], "planRefs": [eid],
            "completeness": "UNKNOWN",
            "warnings": [unknown.get("reason") or "quantity UNKNOWN",
                         "quantity.unit unresolved; g is schema placeholder only"]})
        warnings.append(f"unknown demand {eid}: quantity and unit unresolved")
    needs.sort(key=lambda row: (row["dueDate"], row["needId"]))
    complete = projection.get("snapshotComplete") is True and not warnings
    payload = {"snapshotAt": snapshot_at, "asOf": as_of,
               "horizonDays": horizon_days,
               "horizonMode": "CUMULATIVE_FROM_SNAPSHOT", "needs": needs,
               "completeness": "COMPLETE" if complete else "PARTIAL",
               "warnings": sorted(set(warnings)),
               "sourceSnapshotRefs": _references(source_snapshot_refs, "sourceSnapshotRefs", nonempty=True)}
    return _envelope("shopping.need.projection", payload, created_at=as_of,
                     trace_id=trace_id, snapshot_at=snapshot_at)


def purchase_suggestion_envelope(item: dict, *,
                                 need_ids: list[str], unit: str, basis: str,
                                 created_at: str, trace_id: str,
                                 suggestion_id: str, budget_period: dict | None = None,
                                 capacity_evidence: dict | None = None) -> dict:
    """One price-evidence-aware purchase proposal, never a purchase command."""
    ids = _references(need_ids, "needIds", nonempty=True)
    _identifier(suggestion_id, "suggestionId")
    if item.get("status") not in ("REVIEW", "FEASIBLE_NOT_PURCHASED"):
        status = "UNKNOWN"
    else:
        status = item["status"]
    mix = item.get("mix") or []
    refs = _references([x["observationId"] for x in mix
                       if x.get("observationId") is not None], "observationRefs")
    verified = item.get("priceEvidenceVerified") is True
    if not verified or not refs:
        status = "REVIEW" if mix else "UNKNOWN"
    pids = {x.get("productId") for x in mix}
    single = len(mix) == 1 and len(pids) == 1
    total = item.get("quantityBought") if mix else None
    if total is not None and (type(total) is not int or total <= 0):
        raise DomainError("invalid quantityBought")
    packs = mix[0]["packs"] if single else None
    if packs is not None and (type(packs) is not int or packs <= 0):
        raise DomainError("invalid package count")
    if budget_period is not None:
        if set(budget_period) != {"from", "until"} or _day(budget_period["from"]) > _day(budget_period["until"]):
            raise DomainError("invalid budgetPeriod")
    if capacity_evidence is not None and "snapshotAt" in capacity_evidence:
        _instant(capacity_evidence["snapshotAt"])
    warnings = list(item.get("reasons") or item.get("warnings") or [])
    if not verified:
        warnings.append("price observation not verified")
    if not single and mix:
        warnings.append("mixed packages: packageCount is intentionally unknown")
    payload = {
        "suggestionId": suggestion_id, "needIds": ids,
        "productId": next(iter(pids)) if single else None,
        "observationRefs": refs,
        "quantity": {"amount": total, "unit": unit, "basis": basis,
                     "confirmed": total is not None},
        "packageCount": packs,
        "expectedCents": item.get("costCents") if verified else None,
        "checkoutCents": item.get("checkoutCents") if verified else None,
        "budgetPeriod": budget_period,
        "capacityEvidence": capacity_evidence,
        "status": status, "warnings": sorted(set(warnings)),
        "termsVerified": None,
        "mix": [dict(x) for x in mix],
        "hasSideEffects": False
    }
    return _envelope("shopping.purchase.suggestion", payload,
                     created_at=created_at, trace_id=trace_id)


def offer_interest_envelope(result: dict, action: dict, *,
                            interest_id: str, effective_at: str,
                            trace_id: str, source_offer_ids: list[str]) -> dict:
    """Emit proposed interest only: no confirmation, no checkout, no stock."""
    if result.get("purchaseRecorded") is not False or result.get("stockChanged") is not False:
        raise DomainError("interest event must not have side effects")
    a = action.get("action")
    if a not in ("INTERESTED", "UNDECIDED", "NOT_TODAY", "HIDE_PRODUCT",
                 "HIDE_FOOD_TYPE", "ADD_TO_SHOPPING_LIST"):
        raise DomainError("invalid offer action")
    product, food = action.get("productId"), action.get("foodTypeId")
    if not product and not food:
        raise DomainError("productId or foodTypeId required")
    if result.get("events") != [{"action": a, "productId": product}]:
        raise DomainError("state proposal and action conflict")
    payload = {"interestId": _identifier(interest_id, "interestId"),
               "productId": product or None, "foodTypeId": food or None,
               "action": a, "effectiveAt": effective_at,
               "sourceOfferIds": _references(source_offer_ids, "sourceOfferIds"),
               "proposedState": dict(result["proposedState"]),
               "confirmed": False}
    return _envelope("shopping.offer.interest", payload,
                     created_at=effective_at, trace_id=trace_id)


def past_comparison_envelope(report: dict, *, purchase_ref: str, purchase_at: str,
                             store_scope: dict, created_at: str,
                             trace_id: str) -> dict:
    """Use only evidence from the actual confirmed historical purchase cutoff."""
    cutoff = _instant(purchase_at)
    if cutoff > _instant(created_at):
        raise DomainError("past purchase later than report")
    if report.get("noHindsight") is not True:
        raise DomainError("historical comparison lacks no-hindsight proof")
    if not isinstance(store_scope, dict) or store_scope.get("scopeType") != "STORE_CONFIRMED" or not store_scope.get("storeId"):
        raise DomainError("historical scope must be store confirmed")
    c = report.get("comparison")
    if not isinstance(c, dict):
        raise DomainError("no comparison data")
    alternatives = c.get("alternatives") or []
    refs = _references([x["observationId"] for x in alternatives], "matchedHistoricalOfferIds")
    unit_only = _references([x["observationId"] for x in c.get("unitOnlyAlternatives", [])],
                            "unitOnlyAlternatives")
    warnings = sorted(set(c.get("gaps") or []))
    if alternatives:
        status = "PROVEN"
    elif warnings:
        status = "INCOMPLETE"
    else:
        status = "NO_COMPARABLE_OFFER"
    saving = c.get("bestProvenMerchandiseSavingCents") if alternatives else None
    if saving is not None and (type(saving) is not int or saving <= 0):
        raise DomainError("historical savings must be positive known integer")
    payload = {"confirmedPurchaseRef": _identifier(purchase_ref, "confirmedPurchaseRef"),
               "purchaseAt": purchase_at, "evidenceCutoff": purchase_at,
               "storeScope": dict(store_scope),
               "matchedHistoricalOfferIds": refs,
               "rejectedReasons": [x.get("reason", "unknown") for x in c.get("rejected", [])],
               "savingsProvenCents": saving, "warnings": warnings,
               "unitOnlyAlternatives": unit_only, "status": status,
               "savingsBasis": "MERCHANDISE_ONLY",
               "hasSideEffects": False}
    return _envelope("shopping.past.comparison", payload,
                     created_at=created_at, trace_id=trace_id)
