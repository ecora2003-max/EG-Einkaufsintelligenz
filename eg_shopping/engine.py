"""Pure, deterministic shopping intelligence. No network, database, or I/O."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from fractions import Fraction
from math import ceil
from typing import Any

CONTRACT_VERSION = "1.0.0-draft"
SIGNALS = ("RED_SAME_BIO_CHEAPER", "ORANGE_DIFFERENT_BIO_CHEAPER", "GREY_MAY_BE_CHEAPER")
PRICE_KINDS = {"SALE", "CURRENT_DISPLAYED", "LISTED_REGULAR", "REFERENCE_OLD",
               "HISTORICAL_PAID", "ONLINE_LISTED", "UNKNOWN"}
CRITICAL = ("form", "sweetened", "species", "fatPercent", "state", "diet",
            "variety", "allergens", "processing", "cut")


class DomainError(ValueError):
    """Invalid or inconsistent snapshot; fail closed rather than invent values."""


def _integer(x: Any, name: str, minimum: int = 0) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or x < minimum:
        raise DomainError(f"{name}: integer >= {minimum} required")
    return x


def _day(x: str) -> date:
    try:
        if not isinstance(x, str) or len(x) != 10:
            raise ValueError()
        result = date.fromisoformat(x)
        if result.isoformat() != x:
            raise ValueError()
        return result
    except (ValueError, TypeError) as ex:
        raise DomainError("date: YYYY-MM-DD required") from ex


def _instant(x: str) -> datetime:
    try:
        dt = datetime.fromisoformat(x)
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError()
        return dt
    except (ValueError, TypeError) as ex:
        raise DomainError("observedAt/purchaseAt: ISO-8601 offset required") from ex


def _quantity(q: dict | None) -> tuple[int, str, str] | None:
    if not isinstance(q, dict) or q.get("confirmed") is not True or q.get("amount") is None:
        return None
    amount = _integer(q["amount"], "quantity.amount", 1)
    if q.get("packageCount", 1) is None:
        return None
    count = _integer(q.get("packageCount", 1), "packageCount", 1)
    unit, basis = q.get("unit"), q.get("basis")
    if unit not in ("g", "ml", "piece") or basis == "UNKNOWN":
        return None
    if unit == "piece" and basis != "PIECE":
        return None
    if unit != "piece" and basis not in ("NET", "DRAINED", "GROSS"):
        return None
    return amount * count, unit, basis


def _rate(obs: dict, online_shipping: bool = False) -> tuple[Fraction, str, tuple] | None:
    qty = _quantity(obs.get("article", {}).get("quantity"))
    price = obs.get("priceCents")
    if qty is None or price is None:
        return None
    _integer(price, "priceCents")
    if obs.get("currency") != "EUR":
        raise DomainError("only EUR supported")
    if online_shipping:
        shipping = obs.get("shippingCents")
        if shipping is None:
            return None
        price += _integer(shipping, "shippingCents")
    total, unit, basis = qty
    label = {"g": "kg", "ml": "l", "piece": "piece"}[unit]
    return Fraction(price * (1000 if unit != "piece" else 1), total), label, qty


def _scope_ok(obs: dict, allowed_stores: dict | None, strict: bool) -> tuple[bool, list[str]]:
    scope = obs.get("scope", {})
    retailer = scope.get("retailerId")
    typ = scope.get("scopeType")
    store = scope.get("storeId")
    if not retailer or typ not in ("STORE_CONFIRMED", "REGION_CONFIRMED",
                                   "CHAIN_WIDE_REPORTED", "ONLINE", "UNKNOWN"):
        return False, ["unknown store/region scope"]
    if typ == "STORE_CONFIRMED" and not store:
        return False, ["missing confirmed store ID"]
    if allowed_stores is not None:
        if retailer not in allowed_stores:
            return False, [f"retailer {retailer} not in accessible stores"]
        stores = allowed_stores[retailer]
        if typ == "STORE_CONFIRMED" and store not in stores:
            return False, [f"store {store} not accessible"]
    if strict and typ != "STORE_CONFIRMED":
        return False, ["historical alternative needs confirmed store"]
    cautions = []
    if typ != "STORE_CONFIRMED":
        cautions.append("chain/region scope is not a confirmed local shelf price")
    return True, cautions


def _valid(obs: dict, shopping_date: date, as_of: datetime, historical: bool = False,
           allow_online: bool = False, allowed_stores: dict | None = None) -> tuple[bool, list[str]]:
    kind = obs.get("priceKind")
    if kind not in PRICE_KINDS:
        return False, ["unrecognized price kind"]
    if kind in ("REFERENCE_OLD", "HISTORICAL_PAID", "UNKNOWN"):
        return False, ["reference/historical/unknown price cannot be a purchasable offer"]
    if obs.get("priceCents") is None:
        return False, ["price is unknown"]
    if obs.get("availability") == "OUT_OF_STOCK_REPORTED":
        return False, ["out of stock"]
    if obs.get("conditional"):
        return False, ["coupon/membership/multi-buy conditions unverified"]
    source = obs.get("source") or {}
    if source.get("dataQuality") not in ("CONFIRMED", "SOURCED"):
        return False, ["source quality unverified"]
    if source.get("rightsStatus") == "RESTRICTED":
        return False, ["source rights restricted"]
    if source.get("observedAt") is None:
        return False, ["observation timestamp unknown"]
    observed = _instant(source.get("observedAt"))
    if observed > as_of:
        return False, ["observed after decision time"]
    if kind == "ONLINE_LISTED" and not allow_online:
        return False, ["online channel excluded"]
    if kind == "ONLINE_LISTED" and obs.get("shippingCents") is None:
        return False, ["online shipping costs unknown"]
    if kind == "SALE":
        if obs.get("validFrom") is None or obs.get("validUntil") is None:
            return False, ["sale dates incomplete"]
    start = _day(obs["validFrom"]) if obs.get("validFrom") is not None else None
    end = _day(obs["validUntil"]) if obs.get("validUntil") is not None else None
    if start and end and start > end:
        raise DomainError("validFrom after validUntil")
    if start and shopping_date < start or end and shopping_date > end:
        return False, ["not valid on shopping date"]
    # Non-sale price observed for one day is not proof of a later/earlier day.
    if kind != "SALE" and (start is None or end is None):
        if observed.date() != shopping_date:
            return False, ["no dated validity proof for requested day"]
    if historical and kind == "ONLINE_LISTED":
        return False, ["online checkout not proven at past store"]
    ok, notes = _scope_ok(obs, allowed_stores, historical)
    if not ok:
        return False, notes
    return True, notes


def _comparability(target: dict, candidate: dict, matches: list[dict]) -> tuple[str, list[str]]:
    a, b = target["article"], candidate["article"]
    if a.get("foodTypeId") is None or b.get("foodTypeId") is None:
        return "UNKNOWN", ["food type not established"]
    evidence = []
    at, bt = a.get("attributes") or {}, b.get("attributes") or {}
    if a.get("foodTypeId") != b.get("foodTypeId"):
        explicit = next((m for m in matches if m.get("targetId") == target["observationId"]
                         and m.get("candidateId") == candidate["observationId"]
                         and m.get("status") == "CONFIRMED_BY_USER"
                         and m.get("matchLevel") == "FUNCTIONAL_SUBSTITUTE"), None)
        if explicit:
            return "FUNCTIONAL_SUBSTITUTE", ["explicitly confirmed substitution"] + explicit.get("evidence", [])
        return "UNKNOWN", ["different food types; no confirmed substitution"]
    for k in CRITICAL:
        if k in at or k in bt:
            if k not in at or k not in bt:
                return "UNKNOWN", [f"critical attribute {k} missing"]
            if at[k] != bt[k]:
                return "UNKNOWN", [f"incompatible {k}: {at[k]!r} vs {bt[k]!r}"]
    qty_a, qty_b = _quantity(a.get("quantity")), _quantity(b.get("quantity"))
    if qty_a is None or qty_b is None or qty_a[1:] != qty_b[1:]:
        return "UNKNOWN", ["quantity or unit/basis not comparable"]
    if a.get("gtin") and a.get("gtin") == b.get("gtin") and qty_a == qty_b:
        return "EXACT_SKU", ["same GTIN and package"]
    if a.get("brandKind") != b.get("brandKind") or a.get("brandName") != b.get("brandName"):
        evidence.append("brand/private-label difference")
    return "SAME_FOOD_VARIANT", ["same food type and critical attributes"] + evidence


def _coverage_gaps(coverage: dict | None) -> list[str]:
    if not isinstance(coverage, dict):
        return ["comparison coverage not supplied"]
    gaps = list(coverage.get("gaps") or [])
    if coverage.get("complete") is not True:
        gaps.append("comparison coverage incomplete")
    return sorted(set(gaps))


def compare_prices(target: dict, observations: list[dict], shopping_date: str, *,
                   as_of: str, coverage: dict | None = None, matches: list[dict] | None = None,
                   allowed_stores: dict | None = None, allow_online: bool = False,
                   historical: bool = False) -> dict:
    """Compare exact rational unit rates; emit v1 draft comparison.result payload.

    'as_of' is the evidence cutoff, not a wall-clock read. If coverage is not
    explicitly complete, GREY always accompanies other evidence-based signals.
    """
    day, cutoff = _day(shopping_date), _instant(as_of)
    if not isinstance(observations, list) or not isinstance(target, dict):
        raise DomainError("target and observations required")
    if not target.get("observationId"):
        raise DomainError("target.observationId required")
    target_rate = _rate(target)
    if target_rate is None:
        raise DomainError("target price and confirmed comparable quantity required")
    if not historical:
        target_ok, target_reasons = _valid(target, day, cutoff)
        if not target_ok:
            raise DomainError("target is not a proven price for shopping date: " +
                              "; ".join(target_reasons))
    alternative_rows, other_days, rejected = [], [], []
    used = {target["observationId"]}
    gaps = _coverage_gaps(coverage)
    for candidate in sorted(observations, key=lambda p: str(p.get("observationId", ""))):
        oid = candidate.get("observationId")
        if not oid:
            raise DomainError("observationId required")
        if oid in used:
            if oid == target["observationId"]:
                continue
            raise DomainError(f"duplicate observationId: {oid}")
        used.add(oid)
        valid, caveats = _valid(candidate, day, cutoff, historical, allow_online, allowed_stores)
        if not valid:
            reason = "; ".join(caveats)
            rejected.append({"observationId": oid, "reason": reason})
            if reason == "not valid on shopping date" and candidate.get("priceKind") == "SALE":
                other_days.append({"observationId": oid, "validFrom": candidate.get("validFrom"),
                                   "validUntil": candidate.get("validUntil")})
            if "unknown" in reason or "incomplete" in reason or "unverified" in reason or "proof" in reason:
                gaps.append(f"{oid}: {reason}")
            continue
        level, evidence = _comparability(target, candidate, matches or [])
        if level not in ("EXACT_SKU", "SAME_FOOD_VARIANT", "FUNCTIONAL_SUBSTITUTE"):
            rejected.append({"observationId": oid, "reason": "; ".join(evidence)})
            reason_text = "; ".join(evidence)
            if any(term in reason_text for term in (
                    "missing", "unknown", "not established", "quantity or unit")):
                gaps.append(f"{oid}: incomplete product comparability")
            continue
        rate_data = _rate(candidate, online_shipping=candidate.get("priceKind") == "ONLINE_LISTED")
        if rate_data is None or rate_data[1] != target_rate[1] or rate_data[2][2] != target_rate[2][2]:
            rejected.append({"observationId": oid, "reason": "incompatible base unit"})
            gaps.append(f"{oid}: base units not compatible")
            continue
        candidate_rate, basis, qty = rate_data
        if candidate_rate >= target_rate[0]:
            continue
        organic_a, organic_b = target["article"].get("organic"), candidate["article"].get("organic")
        if organic_a is None or organic_b is None:
            bio_difference = "UNKNOWN"
            gaps.append(f"{oid}: unknown organic status")
        else:
            bio_difference = "SAME" if organic_a == organic_b else "DIFFERENT"
        # Price difference is for equivalent TARGET quantity, not incomparable pack prices.
        target_basis_units = target_rate[2][0]
        scale = 1000 if basis in ("kg", "l") else 1
        price_delta = (candidate_rate - target_rate[0]) * target_basis_units / scale
        delta_int = int(price_delta) if price_delta.denominator == 1 else None
        milli = candidate_rate * 1000
        milli_int = (milli.numerator * 2 + milli.denominator) // (2 * milli.denominator)
        deposit = candidate.get("depositCents")
        if deposit is None:
            gaps.append(f"{oid}: deposit/checkout cost UNKNOWN")
        else:
            _integer(deposit, "depositCents")
        checkout_cents = (None if deposit is None else
                          candidate["priceCents"] + deposit +
                          (candidate.get("shippingCents") or 0))
        detail = {
            "observationId": oid, "pricePerBaseUnitMilliCents": milli_int,
            "basis": basis, "comparability": level, "bioDifference": bio_difference,
            "priceDifferenceCents": delta_int,
            "evidence": evidence + caveats + [f"exact rate: {candidate_rate} cents/{basis}",
                       f"target-equivalent price delta: {price_delta} cents"],
            "retailerId": candidate["scope"]["retailerId"],
            "storeId": candidate["scope"].get("storeId"),
            "scopeType": candidate["scope"]["scopeType"],
            "productLabel": candidate["article"]["label"],
            "brandKind": candidate["article"].get("brandKind"),
            "brandName": candidate["article"].get("brandName"),
            "organic": organic_b, "priceCents": candidate["priceCents"],
            "quantity": candidate["article"]["quantity"],
            "validFrom": candidate.get("validFrom"), "validUntil": candidate.get("validUntil"),
            "observedAt": candidate["source"]["observedAt"],
            "priceKind": candidate["priceKind"],
            "checkoutCents": checkout_cents,
            "depositCents": candidate.get("depositCents"),
            "shippingCents": candidate.get("shippingCents"),
            "exactUnitRateCents": {"numerator": candidate_rate.numerator,
                                   "denominator": candidate_rate.denominator},
        }
        alternative_rows.append(detail)
    alternative_rows.sort(key=lambda a: (Fraction(a["exactUnitRateCents"]["numerator"],
                                                 a["exactUnitRateCents"]["denominator"]),
                                         a["observationId"]))
    signals = []
    if any(a["bioDifference"] == "SAME" and a["comparability"] != "FUNCTIONAL_SUBSTITUTE"
           for a in alternative_rows):
        signals.append(SIGNALS[0])
    if any(a["bioDifference"] == "DIFFERENT" and a["comparability"] != "FUNCTIONAL_SUBSTITUTE"
           for a in alternative_rows):
        signals.append(SIGNALS[1])
    if gaps:
        signals.append(SIGNALS[2])
    return {"comparisonId": "comparison:" + target["observationId"] + ":" + shopping_date,
            "targetObservationId": target["observationId"], "shoppingDate": shopping_date,
            "alternatives": alternative_rows, "signals": signals,
            "incomplete": bool(gaps), "gaps": sorted(set(gaps)),
            "otherDayOffers": other_days, "rejected": rejected,
            "bestPriceClaim": "CHEAPEST_KNOWN_MATCHING_ONLY"}


def comparison_envelope(result: dict, *, created_at: str, trace_id: str) -> dict:
    """Schema-compatible message; extras within payload are optional."""
    _instant(created_at)
    if not trace_id:
        raise DomainError("traceId required")
    return {"contractVersion": CONTRACT_VERSION, "messageType": "comparison.result",
            "meta": {"producer": "eg-einkaufsintelligenz", "createdAt": created_at,
                     "traceId": trace_id}, "payload": result}


def _need_qty(row: dict) -> tuple[int, str, str] | None:
    q = row.get("quantity")
    return _quantity(q) if q is not None else None


def project_needs(snapshot: dict, horizons: tuple[int, ...] = (1, 7, 28, 56)) -> dict:
    """Allocate confirmed lots once chronologically and slice cumulative horizons.

    Inputs: asOf, stock (lotId, foodTypeId, quantity, usableUntil, safe),
    demands (eventId, foodTypeId, dueDate, quantity, kind, preparationId),
    consumptionHistory (actual eventId/foodTypeId/date/quantity), historyStart,
    historyUntil. 'PORTION_CONSUMPTION' is not raw food demand.
    """
    as_of = _day(snapshot["asOf"])
    if any(not isinstance(h, int) or h <= 0 for h in horizons):
        raise DomainError("positive integer horizons required")
    max_h = max(horizons)
    known = set()
    lots_by_type = defaultdict(list)
    warnings = []
    if snapshot.get("stock") is None:
        warnings.append("stock snapshot UNKNOWN")
    else:
        for lot in snapshot["stock"]:
            lid = lot.get("lotId")
            if not lid or lid in known:
                raise DomainError("duplicate/missing lotId")
            known.add(lid)
            qty = _need_qty(lot)
            if not lot.get("foodTypeId") or not qty:
                warnings.append(f"lot {lid}: quantity/type UNKNOWN")
                continue
            if lot.get("safe") is not True or lot.get("available") is not True:
                warnings.append(f"lot {lid}: not confirmed usable")
                continue
            until = lot.get("usableUntil")
            if until is None:
                warnings.append(f"lot {lid}: usableUntil UNKNOWN")
                continue
            lots_by_type[(lot["foodTypeId"], qty[1], qty[2])].append(
                {"id": lid, "until": _day(until), "remaining": qty[0]})
    for lots in lots_by_type.values():
        lots.sort(key=lambda x: (x["until"], x["id"]))
    tasks, used_ids, plan_days = [], set(), set()
    unknown_demands = []
    if snapshot.get("demands") is None:
        warnings.append("plan snapshot UNKNOWN")
    for row in snapshot.get("demands") or []:
        eid = row.get("eventId")
        if not eid:
            raise DomainError("eventId required")
        if eid in used_ids:
            # Same prepared meal appears in planning AND portion consumption:
            # duplicate event IDs only accepted when semantic event is identical.
            raise DomainError("duplicate demand eventId")
        used_ids.add(eid)
        if row.get("kind") in ("PORTION_CONSUMPTION", "COOKED_MEAL_CONSUMPTION"):
            continue
        qty = _need_qty(row)
        if qty is None or not row.get("foodTypeId"):
            warnings.append(f"demand {eid}: amount/type UNKNOWN")
            unknown_demands.append({"eventId": eid, "foodTypeId": row.get("foodTypeId"),
                                    "dueDate": row.get("dueDate"), "quantityToBuy": None,
                                    "reason": "confirmed comparable amount/type UNKNOWN"})
            continue
        due = _day(row["dueDate"])
        if as_of <= due < as_of + timedelta(days=max_h):
            tasks.append({"eventId": eid, "foodTypeId": row["foodTypeId"],
                          "dueDate": due, "quantity": qty, "origin": "PLAN"})
            plan_days.add((row["foodTypeId"], qty[1], qty[2], due))
    # Baseline is optional: measured daily actual consumption, not plan/recipe output.
    history = snapshot.get("consumptionHistory")
    if history:
        h_start, h_end = _day(snapshot["historyStart"]), _day(snapshot["historyUntil"])
        covered_days = (h_end - h_start).days + 1
        if covered_days < 7 or h_end >= as_of:
            warnings.append("consumption baseline insufficient observation period")
        else:
            aggregates, counts, hist_ids = defaultdict(int), defaultdict(int), set()
            for e in history:
                eid = e.get("eventId")
                if not eid or eid in hist_ids:
                    raise DomainError("duplicate/missing historical eventId")
                hist_ids.add(eid)
                d = _day(e["date"])
                if d < h_start or d > h_end:
                    raise DomainError("consumption event outside observation window")
                qty = _need_qty(e)
                if (qty and e.get("confirmed") is True and e.get("foodTypeId") and
                    e.get("kind") not in ("PORTION_CONSUMPTION",
                                          "COOKED_MEAL_CONSUMPTION")):
                    key = (e["foodTypeId"], qty[1], qty[2])
                    aggregates[key] += qty[0]
                    counts[key] += 1
            for key, total in sorted(aggregates.items()):
                if counts[key] < 3:
                    warnings.append(f"{key[0]}: baseline requires >= 3 actual events")
                    continue
                # Round up to integer base units to avoid systematically understating.
                daily = (total + covered_days - 1) // covered_days
                for offset in range(max_h):
                    d = as_of + timedelta(days=offset)
                    if (key[0], key[1], key[2], d) not in plan_days:
                        tasks.append({"eventId": f"baseline:{key[0]}:{d}:{key[1]}:{key[2]}",
                                      "foodTypeId": key[0], "dueDate": d,
                                      "quantity": (daily, key[1], key[2]), "origin": "BASELINE"})
    tasks.sort(key=lambda x: (x["dueDate"], x["eventId"]))
    needs = []
    for task in tasks:
        amount, unit, basis = task["quantity"]
        key = (task["foodTypeId"], unit, basis)
        remaining = amount
        for lot in lots_by_type.get(key, []):
            if lot["until"] < task["dueDate"]:
                continue
            take = min(remaining, lot["remaining"])
            lot["remaining"] -= take
            remaining -= take
            if remaining == 0:
                break
        needs.append({"eventId": task["eventId"], "foodTypeId": task["foodTypeId"],
                      "dueDate": task["dueDate"].isoformat(), "quantityRequired": amount,
                      "quantityToBuy": remaining, "unit": unit, "basis": basis,
                      "origin": task["origin"]})
    views = {}
    for h in sorted(set(horizons)):
        bound = as_of + timedelta(days=h)
        rows = [n for n in needs if _day(n["dueDate"]) < bound and n["quantityToBuy"] > 0]
        totals = defaultdict(int)
        for n in rows:
            totals[(n["foodTypeId"], n["unit"], n["basis"])] += n["quantityToBuy"]
        views[str(h)] = {"needs": rows,
                         "totals": [{"foodTypeId": k[0], "unit": k[1], "basis": k[2],
                                     "quantityToBuy": v}
                                    for k, v in sorted(totals.items())]}
    return {"asOf": snapshot["asOf"], "horizons": views, "allocations": needs,
            "unknownNeeds": sorted(unknown_demands, key=lambda x: x["eventId"]),
            "warnings": sorted(set(warnings)), "snapshotComplete": not warnings,
            "sideEffects": []}


def suggest_purchases(needs_view: dict, products: list[dict], *,
                      shopping_date: str, budget: dict | None = None,
                      capacity: dict | None = None, as_of: str | None = None) -> dict:
    """Suggest mixed packs without turning missing price/deposit evidence into certainty.

    CostCents is merchandise only; checkout includes known per-pack deposit.
    Budget remaining is UNKNOWN if any selected deposit is unknown.
    Source validity is checked against the same price-observation contract as
    compare_prices, if the host supplies a matching priceObservation and as_of.
    """
    from .pack_optimizer import PackSearchError, optimize_package_mix

    today = _day(shopping_date)
    cutoff = _instant(as_of) if as_of is not None else None
    budget_valid = (isinstance(budget, dict) and budget.get("amountCents") is not None
                    and _day(budget["periodStart"]) <= today <= _day(budget["periodEnd"]))
    funds = _integer(budget["amountCents"], "budget", 0) if budget_valid else None
    known_subtotal = 0
    known_checkout_subtotal = 0
    checkout_complete = True
    rows, issues = [], []
    free_capacity = dict(capacity) if isinstance(capacity, dict) else None
    for need in sorted(needs_view.get("totals", []),
                       key=lambda n: (n["foodTypeId"], n["unit"], n["basis"])):
        amount = _integer(need["quantityToBuy"], "need quantity", 1)
        due_dates = [_day(n["dueDate"]) for n in needs_view.get("needs", [])
                     if n["foodTypeId"] == need["foodTypeId"] and
                     n.get("unit", need["unit"]) == need["unit"] and
                     n.get("basis", need["basis"]) == need["basis"] and
                     n["quantityToBuy"] > 0]
        last_due = max(due_dates).isoformat() if due_dates else None
        offers = []
        source_issues = {}
        product_by_id = {}
        missing_product_prices = False
        for product in products:
            if product.get("foodTypeId") != need["foodTypeId"]:
                continue
            q = _quantity(product.get("quantity"))
            if not q or q[1:] != (need["unit"], need["basis"]):
                missing_product_prices = True
                continue
            if product.get("priceCents") is None:
                missing_product_prices = True
                continue
            _integer(product["priceCents"], "priceCents")
            pid = product["productId"]
            product_by_id[pid] = product
            evidence = product.get("priceObservation")
            problems = []
            if cutoff is None or not isinstance(evidence, dict):
                problems.append("price observation/asOf UNKNOWN")
            else:
                eligible, notes = _valid(evidence, today, cutoff)
                if not eligible:
                    problems.extend(notes)
                elif notes:
                    problems.extend(notes)
                art = evidence.get("article", {})
                if (evidence.get("priceCents") != product["priceCents"] or
                    _quantity(art.get("quantity")) != q or
                    art.get("foodTypeId") != product["foodTypeId"]):
                    problems.append("price observation does not match product/quantity")
                if art.get("productRef") not in (None, pid):
                    problems.append("product identity conflict")
                if evidence.get("depositCents") != product.get("depositCents"):
                    problems.append("deposit differs from source observation")
            if product.get("minPacks", 1) > 1 and product.get("termsVerified") is not True:
                problems.append("multibuy terms unverified")
            source_issues[pid] = problems
            offers.append({
                "productId": pid, "amount": q[0], "priceCents": product["priceCents"],
                "minPacks": product.get("minPacks", 1),
                "maxPacks": product.get("maxPacks"),
                "shelfLifeDays": product.get("shelfLifeDays"),
                "storageClass": product.get("storageClass"),
                "packageVolumeMl": product.get("packageVolumeMl"),
                "priceKind": product.get("priceKind"),
                "validFrom": product.get("validFrom"),
                "validUntil": product.get("validUntil"),
                "availability": product.get("availability"),
                "conditional": product.get("conditional") or [],
                "shippingCents": product.get("shippingCents"),
            })
        if not offers:
            rows.append({"foodTypeId": need["foodTypeId"], "status": "REVIEW",
                         "reason": "no comparable priced pack", "costCents": None,
                         "checkoutCents": None})
            issues.append("total cost UNKNOWN")
            checkout_complete = False
            continue
        try:
            plan = optimize_package_mix(amount, offers, shopping_date=shopping_date,
                          last_due_date=last_due, budget_cents=funds,
                          capacity_ml=free_capacity)
        except PackSearchError as ex:
            raise DomainError(str(ex)) from ex
        if plan["costCents"] is None:
            rows.append({"foodTypeId": need["foodTypeId"], "status": "REVIEW",
                         "reason": plan["status"], "costCents": None,
                         "checkoutCents": None, "warnings": plan["warnings"],
                         "rejected": plan["rejected"]})
            issues.append("total cost UNKNOWN")
            checkout_complete = False
            continue
        price = plan["costCents"]
        known_subtotal += price
        checkout = price
        reasons = list(plan["warnings"])
        for item in plan["items"]:
            product = product_by_id[item["productId"]]
            reasons.extend(source_issues[item["productId"]])
            deposit = product.get("depositCents")
            if deposit is None:
                checkout = None
                reasons.append("deposit/checkout cash UNKNOWN")
            else:
                _integer(deposit, "depositCents")
                if checkout is not None:
                    checkout += deposit * item["packs"]
        if checkout is None:
            checkout_complete = False
            funds = None
        else:
            known_checkout_subtotal += checkout
            if funds is not None:
                if checkout > funds:
                    reasons.append("checkout cash budget exceeded")
                funds -= checkout
        if free_capacity is not None:
            for storage, used in plan.get("usedCapacityMl", {}).items():
                if free_capacity.get(storage) is not None:
                    free_capacity[storage] = max(0, free_capacity[storage] - used)
        if missing_product_prices:
            reasons.append("incomplete priced products for food type")
        if budget_valid and last_due is not None and _day(last_due) > _day(budget["periodEnd"]):
            reasons.append("budget period does not cover last demand")
        mix = plan["items"]
        rows.append({
            "foodTypeId": need["foodTypeId"],
            "productId": mix[0]["productId"] if len(mix) == 1 else None,
            "packs": sum(item["packs"] for item in mix),
            "mix": mix, "quantityBought": plan["quantityBought"],
            "costCents": price, "checkoutCents": checkout,
            "status": ("FEASIBLE_NOT_PURCHASED" if plan["status"] ==
                       "FEASIBLE_NOT_PURCHASED" and not reasons else "REVIEW"),
            "reasons": sorted(set(reasons)),
            "optimalityProven": plan["optimalityProven"],
            "optimizationScope": plan["scope"],
            "rejectedCandidates": plan["rejected"],
        })
    return {"items": rows, "knownSubtotalCents": known_subtotal,
            "totalCostCents": (known_subtotal if all(r.get("costCents") is not None for r in rows)
                               else None),
            "knownCheckoutSubtotalCents": known_checkout_subtotal,
            "totalCheckoutCents": (known_checkout_subtotal if checkout_complete else None),
            "budgetRemainingCents": funds, "issues": sorted(set(issues)),
            "optimizationScope": "PER_FOODTYPE_SEQUENTIAL",
            "sideEffects": []}

ACTIONS = {"INTERESTED", "UNDECIDED", "NOT_TODAY", "HIDE_PRODUCT", "HIDE_FOOD_TYPE",
           "ADD_TO_SHOPPING_LIST"}


def evaluate_offer_interest(state: dict, action: dict) -> dict:
    """Return proposed state only. UI/host must confirm persistence explicitly."""
    if action.get("action") not in ACTIONS or not action.get("productId"):
        raise DomainError("invalid interest action/product")
    new = {"interests": dict(state.get("interests", {})),
           "hiddenProducts": list(state.get("hiddenProducts", [])),
           "hiddenFoodTypes": list(state.get("hiddenFoodTypes", [])),
           "shoppingListProposals": list(state.get("shoppingListProposals", []))}
    product = action["productId"]
    a = action["action"]
    if a == "HIDE_PRODUCT":
        new["hiddenProducts"] = sorted(set(new["hiddenProducts"]) | {product})
    elif a == "HIDE_FOOD_TYPE":
        if not action.get("foodTypeId"):
            raise DomainError("foodTypeId required")
        new["hiddenFoodTypes"] = sorted(set(new["hiddenFoodTypes"]) | {action["foodTypeId"]})
    elif a == "ADD_TO_SHOPPING_LIST":
        if product not in new["shoppingListProposals"]:
            new["shoppingListProposals"].append(product)
    else:
        new["interests"][product] = a
    return {"proposedState": new, "events": [{"action": a, "productId": product}],
            "purchaseRecorded": False, "stockChanged": False}


def list_offer_interests(observations: list[dict], state: dict, shopping_date: str, *,
                         as_of: str, preferred_retailers: list[str] | None = None) -> list[dict]:
    """Deduplicate same product across retailers, retaining alternate retailer IDs."""
    day, cutoff = _day(shopping_date), _instant(as_of)
    groups = defaultdict(list)
    for obs in observations:
        a = obs.get("article", {})
        product = a.get("gtin") or a.get("productId")
        if not product or product in state.get("hiddenProducts", []):
            continue
        if a.get("foodTypeId") in state.get("hiddenFoodTypes", []):
            continue
        if preferred_retailers is not None and obs.get("scope", {}).get("retailerId") not in preferred_retailers:
            continue
        ok, _ = _valid(obs, day, cutoff)
        if ok and obs["priceKind"] == "SALE":
            priced = _rate(obs)
            if priced:
                groups[product].append((priced[0], obs["observationId"], obs))
    results = []
    for product, arr in sorted(groups.items()):
        arr.sort(key=lambda x: (x[0], x[1]))
        results.append({"productId": product, "bestKnownObservationId": arr[0][1],
                        "otherObservationIds": [x[1] for x in arr[1:]],
                        "status": state.get("interests", {}).get(product, "UNDECIDED")})
    return results


def evaluate_past_purchase(purchase: dict, historical_prices: list[dict], *,
                           accessible_stores: dict, coverage: dict | None = None) -> dict:
    """No hindsight: cutoff at actual purchase instant and require store evidence."""
    if purchase.get("confirmed") is not True or not purchase.get("purchaseAt"):
        return {"status": "UNKNOWN", "reason": "confirmed purchase timestamp missing",
                "comparison": None}
    when = _instant(purchase["purchaseAt"])
    if purchase.get("priceKind") != "HISTORICAL_PAID":
        raise DomainError("purchase must carry HISTORICAL_PAID priceKind")
    result = compare_prices(purchase, historical_prices, when.date().isoformat(),
                            as_of=purchase["purchaseAt"], coverage=coverage,
                            allowed_stores=accessible_stores, historical=True)
    return {"status": "EVIDENCED_ALTERNATIVES" if result["alternatives"] else "NOT_PROVEN",
            "comparison": result, "noHindsight": True}


def compare_catalog(observations: list[dict], shopping_date: str, *,
                    as_of: str, coverage: dict | None = None,
                    allowed_stores: dict | None = None) -> dict:
    """Every eligible priced item is compared against every other snapshot item.

    Noncomparable/unknown-price observations are reported as omitted targets,
    never silently treated as zero. O(n^2), suitable for bounded app snapshots.
    """
    results, omitted = [], []
    for target in sorted(observations, key=lambda o: o.get("observationId", "")):
        if _rate(target) is None:
            omitted.append({"observationId": target.get("observationId"),
                            "reason": "unknown price or confirmed quantity"})
            continue
        accepted, reason = _valid(target, _day(shopping_date), _instant(as_of),
                                  allowed_stores=allowed_stores)
        if not accepted:
            omitted.append({"observationId": target["observationId"],
                            "reason": "; ".join(reason)})
            continue
        results.append(compare_prices(target, observations, shopping_date, as_of=as_of,
                                      coverage=coverage, allowed_stores=allowed_stores))
    return {"shoppingDate": shopping_date, "comparisons": results,
            "omittedTargets": omitted, "sideEffects": []}
