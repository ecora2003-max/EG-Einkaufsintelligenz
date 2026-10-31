"""JSON-in/JSON-out offline CLI. Run: python -m eg_shopping < input.json."""
import json
import sys

from .stockup import evaluate_early_purchase
from .engine import (DomainError, compare_catalog, compare_prices, comparison_envelope,
                     evaluate_offer_interest, evaluate_past_purchase,
                     list_offer_interests, project_needs, suggest_purchases)


def dispatch(message: dict) -> dict | list:
    # A caller-controlled JSON body cannot authenticate rights grants. The
    # Android/host adapter must verify provenance and purpose outside this CLI.
    if message.get("usageContext", "RESEARCH_ONLY") != "RESEARCH_ONLY":
        raise DomainError("APP_DISPLAY and private history require trusted host adapter")
    if message.get("rightsGrants") is not None:
        raise DomainError("untrusted JSON rights grants are not accepted")
    op = message.get("operation")
    if op == "comparePrices":
        result = compare_prices(message["target"], message["observations"],
                   message["shoppingDate"], as_of=message["asOf"],
                   coverage=message.get("coverage"), matches=message.get("matches"),
                   allowed_stores=message.get("allowedStores"),
                   allow_online=message.get("allowOnline", False),
                   usage_context=message.get("usageContext", "RESEARCH_ONLY"),
                   rights_grants=message.get("rightsGrants"))
        if message.get("envelope"):
            return comparison_envelope(result, created_at=message["asOf"],
                                       trace_id=message["traceId"])
        return result
    if op == "compareCatalog":
        return compare_catalog(message["observations"], message["shoppingDate"],
                   as_of=message["asOf"], coverage=message.get("coverage"),
                   allowed_stores=message.get("allowedStores"),
                   usage_context=message.get("usageContext", "RESEARCH_ONLY"),
                   rights_grants=message.get("rightsGrants"))
    if op == "evaluateEarlyPurchase":
        return evaluate_early_purchase(message["need"], message["offer"],
            shopping_date=message["shoppingDate"], as_of=message["asOf"],
            budget=message.get("budget"), capacity=message.get("capacity"),
            shelf_life_days=message.get("shelfLifeDays"),
            storage_class=message.get("storageClass"),
            package_volume_ml=message.get("packageVolumeMl"),
            future_price=message.get("futurePrice"),
            accessible_stores=message.get("accessibleStores"))
    if op == "projectNeeds":
        return project_needs(message["snapshot"], tuple(message.get("horizons", (1, 7, 28, 56))))
    if op == "suggestPurchases":
        return suggest_purchases(message["needsView"], message["products"],
                   shopping_date=message["shoppingDate"], budget=message.get("budget"),
                   capacity=message.get("capacity"), as_of=message.get("asOf"),
                   usage_context=message.get("usageContext", "RESEARCH_ONLY"),
                   rights_grants=message.get("rightsGrants"))
    if op == "evaluatePastPurchase":
        return evaluate_past_purchase(message["purchase"], message["historicalPrices"],
                   accessible_stores=message["accessibleStores"],
                   coverage=message.get("coverage"))
    if op == "evaluateOfferInterest":
        return evaluate_offer_interest(message["state"], message["action"])
    if op == "listOfferInterests":
        return list_offer_interests(message["observations"], message["state"],
                   message["shoppingDate"], as_of=message["asOf"],
                   preferred_retailers=message.get("preferredRetailers"),
                   preferred_food_types=message.get("preferredFoodTypes"),
                   walking_distance_by_store_m=message.get("walkingDistanceByStoreM"),
                   max_walking_distance_m=message.get("maxWalkingDistanceM"),
                   usage_context=message.get("usageContext", "RESEARCH_ONLY"),
                   rights_grants=message.get("rightsGrants"))
    raise DomainError("unrecognized operation")


def main() -> int:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise DomainError("JSON object expected")
        response = dispatch(request)
    except (DomainError, KeyError, TypeError, ValueError, json.JSONDecodeError) as ex:
        json.dump({"error": {"code": "INVALID_SNAPSHOT", "message": str(ex)}}, sys.stderr)
        sys.stderr.write("\n")
        return 2
    json.dump(response, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
