"""Fail-closed, offline ADR-014/016 gates. Functional scope is not legal permission."""
CAPABILITIES = {
    "ALDI_NORD": (True, True), "ALDI_SUED": (True, True),
    "REWE": (True, True), "LIDL": (True, True),
    "PENNY": (False, True), "KAUFLAND": (False, True),
    "EDEKA": (False, True), "NETTO_MD": (False, True),
}
CONTEXTS = {"RESEARCH_ONLY", "APP_DISPLAY", "PRIVATE_USER_HISTORY"}
OPERATIONS = {"TARGETED_PRODUCT_PRICE_QUERY", "PUBLISHED_OFFER_COLLECTION"}


def retailer_capability(retailer_id, operation):
    """Scope only: true never implies source rights or a live price endpoint."""
    capabilities = CAPABILITIES.get(retailer_id)
    if operation not in OPERATIONS or capabilities is None:
        return False
    return capabilities[0 if operation == "TARGETED_PRODUCT_PRICE_QUERY" else 1]


def gate_observation(obs, usage_context):
    if usage_context not in CONTEXTS:
        return False, ["unknown usage context"]
    if usage_context == "RESEARCH_ONLY":
        return True, []
    if not isinstance(obs, dict):
        return False, ["APP_DISPLAY source missing"]
    source = obs.get("source") or {}
    if obs.get("priceKind") == "HISTORICAL_PAID" or source.get("evidenceKind") == "USER_CONFIRMED_RECEIPT":
        return False, ["private historical receipt is not a current external price"]
    if source.get("rightsStatus") != "PERMITTED":
        return False, ["APP_DISPLAY rights unverified or restricted"]
    permission = source.get("displayPermission")
    if not (isinstance(permission, dict) and permission.get("verified") is True
            and isinstance(permission.get("reference"), str)
            and permission["reference"].strip()
            and permission.get("sourceOrigin") == source.get("origin")
            and isinstance(permission.get("allowedUses"), list)
            and "APP_DISPLAY" in permission["allowedUses"]):
        return False, ["APP_DISPLAY permission scope/evidence missing"]
    operation = source.get("operation")
    retailer = (obs.get("scope") or {}).get("retailerId")
    if not retailer_capability(retailer, operation):
        return False, ["retailer operation disallowed by ADR-016"]
    kind = obs.get("priceKind")
    if operation == "PUBLISHED_OFFER_COLLECTION" and kind != "SALE":
        return False, ["published offer cannot establish a regular price"]
    if operation == "TARGETED_PRODUCT_PRICE_QUERY" and kind not in (
            "CURRENT_DISPLAYED", "LISTED_REGULAR", "ONLINE_LISTED"):
        return False, ["targeted operation inconsistent with price kind"]
    return True, []


def private_receipt_verified(purchase):
    if not isinstance(purchase, dict):
        return False
    source = purchase.get("source") or {}
    return (purchase.get("confirmed") is True
            and purchase.get("priceKind") == "HISTORICAL_PAID"
            and bool(purchase.get("purchaseAt"))
            and isinstance(purchase.get("receiptId"), str)
            and bool(purchase["receiptId"].strip())
            and isinstance(purchase.get("receiptLineId"), str)
            and bool(purchase["receiptLineId"].strip())
            and source.get("origin") == "USER_LOCAL_RECEIPT"
            and source.get("evidenceKind") == "USER_CONFIRMED_RECEIPT"
            and source.get("localOnly") is True)
