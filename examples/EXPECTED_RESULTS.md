# Synthetic compare example

Run `python -m eg_shopping < examples/compare_request.json`.

Expected essentials: target T: 500 g organic oats at 199 cents = 3.98 EUR/kg. Alternative B: 500 g organic oats at 179 cents = 3.58 EUR/kg, 20 cents less. Signals include RED_SAME_BIO_CHEAPER and GREY_MAY_BE_CHEAPER (coverage incomplete). `priceDifferenceCents=-20`; `pricePerBaseUnitMilliCents=358000`. `checkoutCents=null` because no evidence for zero deposit was supplied. No absolute market-best claim.

Invalid date causes error code INVALID_SNAPSHOT, exit code 2. Unknown quantity/basis/source timestamp yields no invented rate; unverified coupon is excluded. A historical cheaper unit rate is not confirmed savings unless the actual required saleable pack quantity costs less.
