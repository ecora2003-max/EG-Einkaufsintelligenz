"""Source-rights and retailer-capability gates.

Retailer policy is a *functional* scope, never a legal license. Calls to this
module are pure: an upstream host must authenticate any rights grants.
"""
from __future__ import annotations

import json
from pathlib import Path

from .engine import DomainError, _instant

POLICY = json.loads((Path(__file__).resolve().parents[1] /
                     "policies/retailer-source-capabilities.v1.json").read_text())
RETAILERS = POLICY["retailerCapabilities"]
USAGE_CONTEXTS = frozenset(("RESEARCH_ONLY", "APP_DISPLAY", "PRIVATE_USER_HISTORY"))
PRICE_QUERY = "TARGETED_PRODUCT_PRICE_QUERY"
PUBLISHED_OFFER = "PUBLISHED_OFFER_COLLECTION"


def source_gate(obs: dict, *, usage_context: str = "RESEARCH_ONLY",
                rights_grants: dict | None = None) -> tuple[bool, str]:
    """Validate one externally sourced price observation without changing it.

    In APP_DISPLAY mode a host-authenticated, purpose- and source-specific
    grant AND source rightsStatus=PERMITTED are mandatory. Claimed permission
    alone, or the ability to read an endpoint, is not sufficient. Rejected
    observations must be redacted by all consumer output functions.
    """
    if usage_context not in USAGE_CONTEXTS:
        raise DomainError("unrecognized price usage context")
    if not isinstance(obs, dict):
        return False, "invalid observation"
    scope = obs.get("scope") or {}
    src = obs.get("source") or {}
    if usage_context == "PRIVATE_USER_HISTORY":
        if (obs.get("priceKind") != "HISTORICAL_PAID" or
            obs.get("confirmed") is not True or
            src.get("evidenceKind") != "USER_CONFIRMED_RECEIPT" or
            not (scope.get("retailerId") and obs.get("purchaseAt"))):
            return False, "private history requires confirmed dated own receipt and retailer"
        try:
            _instant(obs["purchaseAt"])
        except (DomainError, TypeError, ValueError):
            return False, "private history purchase timestamp invalid"
        return True, "private history only, never current store price"
    retailer = scope.get("retailerId")
    # Price kind is not evidence of how the observation was acquired.  A
    # targeted product query may itself return a SALE price.  Do not allow
    # absent or conflicting provenance to turn that query into an offer feed.
    observation_mode = obs.get("acquisitionMode")
    source_mode = src.get("acquisitionMode")
    if (observation_mode is not None and source_mode is not None
            and observation_mode != source_mode):
        return False, "conflicting observation/source acquisition modes"
    mode = observation_mode if observation_mode is not None else source_mode
    if mode is None:
        if usage_context == "APP_DISPLAY":
            return False, "explicit acquisition mode provenance required for display"
        # Legacy synthetic/research fixtures can still infer a test-only mode.
        mode = PUBLISHED_OFFER if obs.get("priceKind") == "SALE" else PRICE_QUERY
    if mode not in (PRICE_QUERY, PUBLISHED_OFFER):
        return False, "acquisition mode not recognized"
    if mode == PUBLISHED_OFFER and obs.get("priceKind") != "SALE":
        return False, "non-sale price cannot be relabelled as a published offer"
    capability = RETAILERS.get(retailer)
    if capability is not None:
        field = ("targetedProductPriceQuery" if mode == PRICE_QUERY
                 else "publishedOfferCollection")
        if capability[field] is not True:
            return False, f"retailer {retailer}: {mode} disallowed by policy"
    elif usage_context == "APP_DISPLAY":
        return False, "retailer capability not verified"
    if usage_context == "RESEARCH_ONLY":
        return True, "synthetic/research evidence only; no display permission"
    if obs.get("priceKind") == "HISTORICAL_PAID":
        return False, "historical user receipt is not external current price"
    if src.get("rightsStatus") != "PERMITTED":
        return False, "external rights not cleared for APP_DISPLAY"
    origin = src.get("origin")
    evidence_ref = src.get("rightsEvidenceRef")
    grant = (rights_grants or {}).get(origin) if isinstance(rights_grants, dict) else None
    if not origin or not evidence_ref or not isinstance(grant, dict):
        return False, "documented source-specific display permission missing"
    modes = grant.get("acquisitionModes")
    if (grant.get("rightsEvidenceRef") != evidence_ref or
        grant.get("usageContext") != "APP_DISPLAY" or
        grant.get("retailerId") != retailer or
        not isinstance(modes, (list, tuple)) or
        mode not in modes or
        grant.get("hostVerified") is not True):
        return False, "rights grant does not match origin/retailer/purpose"
    return True, "APP_DISPLAY rights verified for source and use"
