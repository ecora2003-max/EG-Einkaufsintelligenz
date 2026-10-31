# Integrations-Ports – Einkaufsintelligenz
Beispielsignaturen für einen rein deterministischen Kern:
- `comparePrices(target, observationsSnapshot, matchSnapshot, shoppingDate, preferences) -> ComparisonResult`
- `projectNeeds(stockSnapshot, planSnapshot, consumptionSnapshot, horizon) -> NeedsProjection`
- `suggestPurchases(needs, priceSnapshot, budgetSnapshot, capacitySnapshot) -> PurchaseSuggestions`
- `evaluatePastPurchase(confirmedPurchase, historicalPricesAtPurchaseDate) -> HistoricalComparison`
- `evaluateOfferInterest(interestState, action) -> ProposedInterestState`

Der eigentliche Code muss ohne Netzwerk, ohne Room-DAO und mit Mock-Snapshots ausführbar sein. Preise/Cents und Mengen exakt mit rationaler/integer Arithmetik, historische Datumsgeltung und Quellenqualität prüfbar. Mindestens `comparison.result` wird gemäß `EG-Architecture/contracts/v1` exportiert. Für neue DTOs Änderungsantrag im eigenen Repo stellen; im Entwurf bereits dokumentieren.

Codex stellt bestätigte, transaktional konsistente Snapshots bereit, kümmert sich um dauerhafte Speicherung von Einstellungen und validierte Ausführung über `FoodStore`. Engine darf **keinen** tatsächlichen Kauf, keine Reservierung, keinen Lagerzugang und keinen Verzehr auslösen.
