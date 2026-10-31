"""Evidence-gated early-purchase recommendations from immutable snapshots."""
from __future__ import annotations

from .engine import (_day, _instant, _integer, _quantity, _valid,
                     _comparability, DomainError)


def evaluate_early_purchase(need: dict, offer: dict, *,
                            shopping_date: str, as_of: str,
                            budget: dict | None, capacity: dict | None,
                            shelf_life_days: int | None,
                            storage_class: str | None,
                            package_volume_ml: int | None,
                            future_price: dict | None = None,
                            accessible_stores: dict | None = None) -> dict:
    """A non-booking proposal. Only prove savings from a published future price.

    - Need: foodTypeId, dueDate, quantityToBuy, unit, basis.
    - Offer/future_price: v1-draft PriceObservation payload.
    - Budget and capacity: confirmed cash budget for shopping day and known
      remaining storage volume; missing values are unknown, not zero.
    """
    today, cutoff, due = _day(shopping_date), _instant(as_of), _day(need["dueDate"])
    if due < today:
        raise DomainError("need due before shopping date")
    requested = _integer(need.get("quantityToBuy"), "quantityToBuy", 1)
    oid = offer.get("observationId")
    out = {"needDate": need["dueDate"], "shoppingDate": shopping_date,
           "offerObservationId": oid, "status": "REVIEW", "reasons": [],
           "quantityNeeded": requested, "packs": None,
           "merchandiseCents": None, "checkoutCents": None,
           "futureComparableCents": None, "savingsProvenCents": None,
           "sideEffects": []}
    reasons = out["reasons"]
    valid, notes = _valid(offer, today, cutoff, allowed_stores=accessible_stores)
    if not valid:
        reasons.extend(notes)
        return out
    reasons.extend(notes)
    q = _quantity(offer.get("article", {}).get("quantity"))
    if q is None or (q[1], q[2]) != (need.get("unit"), need.get("basis")):
        reasons.append("offer quantity or basis not comparable")
        return out
    if offer["article"].get("foodTypeId") != need.get("foodTypeId"):
        reasons.append("offer foodType not comparable")
        return out
    packs = (requested + q[0] - 1) // q[0]
    out["packs"] = packs
    out["merchandiseCents"] = packs * _integer(offer["priceCents"], "offer.priceCents")
    deposit = offer.get("depositCents")
    if deposit is None:
        reasons.append("checkout/deposit UNKNOWN")
    else:
        out["checkoutCents"] = out["merchandiseCents"] + packs * _integer(deposit, "depositCents")
    if shelf_life_days is None:
        reasons.append("verified shelf life UNKNOWN")
    elif _integer(shelf_life_days, "shelfLifeDays") < (due - today).days:
        reasons.append("shelf life insufficient")
    if capacity is None or storage_class is None or package_volume_ml is None or \
       storage_class not in capacity or capacity[storage_class] is None:
        reasons.append("physical storage capacity UNKNOWN")
    else:
        available = _integer(capacity[storage_class], "capacity")
        required_space = packs * _integer(package_volume_ml, "packageVolumeMl", 1)
        if required_space > available:
            reasons.append("insufficient physical storage capacity")
    if (not isinstance(budget, dict) or budget.get("amountCents") is None or
        _day(budget["periodStart"]) > today or _day(budget["periodEnd"]) < today):
        reasons.append("budget for shopping day UNKNOWN")
    else:
        budget_cents = _integer(budget["amountCents"], "budget.amountCents")
        if out["checkoutCents"] is None:
            reasons.append("cannot certify cash budget with unknown checkout")
        elif out["checkoutCents"] > budget_cents:
            reasons.append("cash budget exceeded")
    if future_price is None:
        reasons.append("future comparable price UNKNOWN; saving not proven")
    else:
        ok, future_notes = _valid(future_price, due, cutoff,
                                  allowed_stores=accessible_stores)
        if not ok:
            reasons.extend(["future price: " + note for note in future_notes])
        else:
            reasons.extend(["future price: " + note for note in future_notes])
            level, _ = _comparability(offer, future_price, [])
            q_future = _quantity(future_price.get("article", {}).get("quantity"))
            if level not in ("EXACT_SKU", "SAME_FOOD_VARIANT") or q_future is None or \
               q_future[1:] != q[1:]:
                reasons.append("future price product not proven comparable")
            elif future_price.get("depositCents") is None:
                reasons.append("future checkout deposit UNKNOWN")
            else:
                future_packs = (requested + q_future[0] - 1) // q_future[0]
                future_cost = future_packs * _integer(future_price["priceCents"],
                                                     "futurePrice.priceCents")
                out["futureComparableCents"] = future_cost
                savings = future_cost - out["merchandiseCents"]
                if savings <= 0:
                    reasons.append("no cheaper early purchase proven")
                else:
                    out["savingsProvenCents"] = savings
    if not reasons and out["savingsProvenCents"] is not None:
        out["status"] = "ADVANCE_FEASIBLE_NOT_PURCHASED"
    return out
