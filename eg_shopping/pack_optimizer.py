"""Bounded exact package-mix search for a single confirmed food/quantity basis.

No input mutations, no guessed conditional discount, no network. A search limit
is explicitly surfaced, never mislabeled as an optimal recommendation.
"""
from __future__ import annotations

from datetime import date
from typing import Any


class PackSearchError(ValueError):
    pass


def _pos(x: Any, label: str, minimum: int = 0) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or x < minimum:
        raise PackSearchError(f"{label}: integer >= {minimum} required")
    return x


def optimize_package_mix(
    target_amount: int,
    candidates: list[dict],
    *,
    shopping_date: str,
    last_due_date: str | None = None,
    budget_cents: int | None = None,
    capacity_ml: dict[str, int | None] | None = None,
    max_nodes: int = 250000,
) -> dict:
    """Exact enumeration for bounded candidate set (max 8 variants).

    Candidate fields: productId, amount (units per saleable pack), priceCents,
    minPacks (verified structured multibuy threshold), shelfLifeDays,
    storageClass, packageVolumeMl, optional validFrom/validUntil, priceKind,
    conditional (unverified text conditions: excluded), availability, maxPacks.

    Searches all combinations within a provably sufficient count limit:
    max(ceil(target/size), minPacks) per candidate. Returns the cheapest
    *feasible* combination for confirmed constraints, otherwise the cheapest
    known combination flagged REVIEW. All known storage is accounted across
    variants; unknown capacity or shelf-life prevents FEASIBLE classification.
    """
    amount = _pos(target_amount, "target_amount", 1)
    max_nodes = _pos(max_nodes, "max_nodes", 1)
    try:
        today = date.fromisoformat(shopping_date)
        if today.isoformat() != shopping_date:
            raise ValueError()
        due = date.fromisoformat(last_due_date) if last_due_date else None
    except (ValueError, TypeError) as ex:
        raise PackSearchError("ISO shopping_date / last_due_date required") from ex
    if budget_cents is not None:
        budget_cents = _pos(budget_cents, "budget_cents")
    if capacity_ml is not None:
        for key, value in capacity_ml.items():
            if value is not None:
                _pos(value, f"capacity[{key}]")

    entries, rejected = [], []
    seen = set()
    for c in candidates:
        pid = c.get("productId")
        if not isinstance(pid, str) or not pid:
            raise PackSearchError("productId required")
        if pid in seen:
            raise PackSearchError(f"duplicate productId: {pid}")
        seen.add(pid)
        q, price = _pos(c.get("amount"), "amount", 1), _pos(c.get("priceCents"), "priceCents")
        minimum = _pos(c.get("minPacks", 1), "minPacks", 1)
        if c.get("conditional"):
            rejected.append({"productId": pid, "reason": "unverified coupon or access condition"})
            continue
        if c.get("priceKind") in ("REFERENCE_OLD", "HISTORICAL_PAID", "UNKNOWN"):
            rejected.append({"productId": pid, "reason": "non-purchasable price kind"})
            continue
        if c.get("availability") == "OUT_OF_STOCK_REPORTED":
            rejected.append({"productId": pid, "reason": "out of stock"})
            continue
        start, end = c.get("validFrom"), c.get("validUntil")
        if c.get("priceKind") == "SALE" and (not start or not end):
            rejected.append({"productId": pid, "reason": "sale validity unknown"})
            continue
        if start is not None and end is not None and start > end:
            raise PackSearchError("validFrom after validUntil")
        if start and today < date.fromisoformat(start) or end and today > date.fromisoformat(end):
            rejected.append({"productId": pid, "reason": "price not valid on shopping date"})
            continue
        if c.get("priceKind") == "ONLINE_LISTED" and c.get("shippingCents") is None:
            rejected.append({"productId": pid, "reason": "shipping unknown"})
            continue
        if c.get("priceKind") == "ONLINE_LISTED":
            # Shipping is order-level, cannot safely treat as per-pack unless
            # its allocation or full checkout fee is explicitly modeled.
            rejected.append({"productId": pid, "reason": "online order-level shipping not modeled"})
            continue
        cap = c.get("maxPacks")
        if cap is not None:
            cap = _pos(cap, "maxPacks")
        shelf = c.get("shelfLifeDays")
        if shelf is not None:
            _pos(shelf, "shelfLifeDays")
        storage, vol = c.get("storageClass"), c.get("packageVolumeMl")
        if vol is not None:
            _pos(vol, "packageVolumeMl", 1)
        hi = max((amount + q - 1) // q, minimum)
        if cap is not None:
            hi = min(hi, cap)
        # Each product's availability is not implicitly unlimited if supplied.
        entries.append({"id": pid, "q": q, "price": price,
                        "min": minimum, "max": hi, "shelf": shelf,
                        "storage": storage, "volume": vol})
    entries.sort(key=lambda c: c["id"])
    if not entries:
        return {"status": "NO_ELIGIBLE_PRICE", "items": [], "costCents": None,
                "quantityBought": 0, "optimalityProven": False, "rejected": rejected,
                "warnings": ["no eligible priced packages"]}
    if len(entries) > 8:
        return {"status": "SEARCH_LIMIT", "items": [], "costCents": None,
                "quantityBought": 0, "optimalityProven": False, "rejected": rejected,
                "warnings": ["more than eight variants; exact search declined"]}

    strict_best = None
    fallback_best = None
    nodes = 0
    exceeded = False
    quantities = [0] * len(entries)

    def _consider(total_units: int, total_cost: int, used: dict[str, int],
                  missing: set[str], shelf_issue: bool) -> None:
        nonlocal strict_best, fallback_best
        if total_units < amount:
            return
        count = sum(quantities)
        key = (total_cost, total_units - amount, count, tuple(quantities))
        plan = (key, tuple(quantities), dict(used), sorted(missing), shelf_issue)
        if fallback_best is None or key < fallback_best[0]:
            fallback_best = plan
        budget_ok = budget_cents is None or total_cost <= budget_cents
        capacity_ok = (capacity_ml is not None and not missing and
                       all(v <= capacity_ml[k] for k, v in used.items()))
        shelf_ok = (due is not None and not shelf_issue)
        if budget_ok and capacity_ok and shelf_ok:
            if strict_best is None or key < strict_best[0]:
                strict_best = plan

    def visit(i: int, units: int, cost: int, used: dict[str, int],
              missing: set[str], shelf_issue: bool) -> None:
        nonlocal nodes, exceeded
        nodes += 1
        if nodes > max_nodes:
            exceeded = True
            return
        # Lower-bound prune, valid since prices are nonnegative.
        if strict_best is not None and cost > strict_best[0][0] and \
           (fallback_best is not None and cost > fallback_best[0][0]):
            return
        if i == len(entries):
            _consider(units, cost, used, missing, shelf_issue)
            return
        p = entries[i]
        options = [0] + list(range(p["min"], p["max"] + 1))
        for n in options:
            if exceeded:
                return
            new_used = dict(used)
            new_missing = set(missing)
            bad = shelf_issue
            if n:
                storage, vol = p["storage"], p["volume"]
                if storage is None or vol is None or capacity_ml is None or \
                   storage not in capacity_ml or capacity_ml[storage] is None:
                    new_missing.add(p["id"])
                else:
                    new_used[storage] = new_used.get(storage, 0) + vol * n
                if due is None or p["shelf"] is None or \
                   p["shelf"] < (due - today).days:
                    bad = True
            visit(i + 1, units + n * p["q"], cost + n * p["price"],
                  new_used, new_missing, bad)

    visit(0, 0, 0, {}, set(), False)
    chosen = strict_best if strict_best is not None else fallback_best
    if chosen is None:
        return {"status": "SEARCH_LIMIT" if exceeded else "NO_FEASIBLE_MIX",
                "items": [], "costCents": None, "quantityBought": 0,
                "optimalityProven": not exceeded, "rejected": rejected,
                "warnings": ["no bounded package combination proven"]}
    key, nums, used, missing, shelf_issue = chosen
    warnings = []
    if exceeded:
        warnings.append("exact search limit reached; optimality not proven")
    if missing:
        warnings.append("available storage volume UNKNOWN")
    if capacity_ml is None:
        warnings.append("available storage volume UNKNOWN")
    elif any(used[k] > capacity_ml[k] for k in used):
        warnings.append("insufficient confirmed storage volume")
    if due is None or shelf_issue:
        warnings.append("shelf life or due date UNKNOWN/insufficient")
    if budget_cents is None:
        warnings.append("budget UNKNOWN")
    elif key[0] > budget_cents:
        warnings.append("budget exceeded")
    items = [{"productId": c["id"], "packs": n, "quantityBought": c["q"] * n,
              "costCents": c["price"] * n}
             for c, n in zip(entries, nums) if n]
    return {"status": ("FEASIBLE_NOT_PURCHASED" if strict_best is not None and
                        not exceeded and budget_cents is not None else "REVIEW"),
            "items": items, "costCents": key[0], "quantityBought": sum(x["quantityBought"] for x in items),
            "optimalityProven": not exceeded, "usedCapacityMl": used,
            "warnings": sorted(set(warnings)), "rejected": rejected,
            "scope": "EXACT_PER_FOODTYPE_ONLY"}
