# Integration: Einkaufsintelligenz (Arbeitsstand 31.10.2026)

## Verantwortung und Version

Vertragsversion **1.0.0-draft** aus EG-Architecture. Letztgelesener Architektur-Commit: `d22862739bd0e3ef8451ce029e54f7c33ee53e40`. In `contracts/v1/` liegen eine Schema- und Beispielkopie, **keine** Änderung am Architekturrepository. Einziges Schreibrepository ist `EG-Einkaufsintelligenz`; Room, Haupt-App, externe Quellen und produktives Sheet werden **nicht** geschrieben.

Der Fachkern ist eine reine Python-Referenz (CPython >=3.10, nur Standardbibliothek), ohne Netzwerk, Cloud, Datenbank, Uhrzeitabfrage oder Seiteneffekte. Zielintegration in Android: Codex bildet DTOs in Kotlin ab; exakte Arithmetik als `BigInteger`-Brüche, `LocalDate` und `OffsetDateTime`, vorgeschaltete Schema- und Quellenprüfung. Keine verpflichtende Python-Runtime in Android beabsichtigt.

## Schnittstellen

| CLI operation | Python-Port | Input | Rückgabe |
|---|---|---|---|
| `comparePrices` | `compare_prices` | target; observations; shoppingDate; asOf; coverage; optional matches, allowedStores, allowOnline | Vergleich/Signal-Liste, datenqualitätsbewusste Alternative |
| `compareCatalog` | `compare_catalog` | observations; shoppingDate; asOf; coverage | Preisvergleich für alle zum Datum zugelassenen Zielbeobachtungen |
| `projectNeeds` | `project_needs` | snapshot mit asOf, stock, demands, optional consumptionHistory/historyStart/historyUntil; horizons | kumulative Bedarfssichten und einmalige FEFO-Allokation |
| `suggestPurchases` | `suggest_purchases` | needsView, products, shoppingDate, budget, capacity | überprüfbare **Vorschläge**, keine Käufe |
| `evaluatePastPurchase` | `evaluate_past_purchase` | purchase, historicalPrices, accessibleStores, coverage | zum Kaufzeitpunkt belegte Alternativen |
| `evaluateOfferInterest` | `evaluate_offer_interest` | state, action | Zustand/Events **nur als Vorschlag** |
| `listOfferInterests` | `list_offer_interests` | observations, state, shoppingDate, asOf, preferredRetailers | deduplizierte Angebotsinteressen, getrennt vom Bedarf |

Aufruf: `python -m eg_shopping < examples/compare_request.json`. Die CLI erwartet ein JSON-Objekt und schreibt genau ein Ausgabe-JSON nach stdout, im Fehlerfall `{"error":{"code":"INVALID_SNAPSHOT","message":"..."}}` nach stderr, Exit-Code 2. Optional `envelope: true` mit `traceId` erzeugt die kanonische `comparison.result`-Nachricht (Schema im Repository).

## Format und Semantik

Geld = ganzzahlige Euro-Cents. `article.quantity.amount` ist die Menge **pro Packung**; `packageCount` multipliziert sie. Nur bestätigte g/ml-Stückmengen mit gleicher `basis` dürfen verglichen werden. Für g/ml wird der Nenner exakt auf 1000 g/ml normalisiert; Stück erfordert `basis=PIECE`. Keine Schätzung von Stückgewicht, Abtropfgewicht, Dichte oder Portionsmenge.

Intern `fractions.Fraction`, `exactUnitRateCents` als `numerator/denominator` für Cents/kg, Cents/l oder Cents/Stück; `pricePerBaseUnitMilliCents` ist nur ein gerundeter Anzeigewert in 1/1000 Cent. `priceDifferenceCents` ist die **auf die Zielmenge umgerechnete** ganzzahlige Differenz oder `null`, wenn nicht ganzzahlig. `checkoutCents` führt dokumentierten Versand und Pfand separat, keine angenommenen Coupons. Online nur opt-in und bei belegtem Versandbetrag.

Gleiche FoodType-ID und alle beidseitig vorhandenen kritischen Attribute müssen übereinstimmen; unbekannte kritische Attribute blockieren den sicheren Vergleich. Explizit bestätigte `FUNCTIONAL_SUBSTITUTE`-Beziehungen können separat ausgegeben werden, aber lösen kein automatisches Rot aus. Marken-/Eigenmarkenunterschiede blockieren den sachlich vergleichbaren FoodType nicht. Bio `true`/`false`/`null` werden getrennt: Rot gleiche **bekannte** Bio-Eigenschaft, Orange abweichende **bekannte**, Grau bei Lücke. Kein absoluter Marktbestpreis, auch nicht ohne Warnsignal.

`shoppingDate` ist ein ISO-Datum; `asOf` ist ISO-Zeitpunkt mit Zeitzonen-Offset. `SALE` nur während `validFrom..validUntil` (einschließlich). Ohne belegte Datumsintervalle werden reguläre/angezeigte Preise konservativ nur auf ihren Beobachtungstag bezogen. `REFERENCE_OLD`, `HISTORICAL_PAID`, `UNKNOWN`, konditionale Rabatte ohne Bedingungsnachweis und unbekannte/geschätzte Quellen sind keine garantierten aktuellen Kaufalternativen. Vergriffene Artikel werden ausgeschlossen. Bei `STORE_CONFIRMED` benötigt historische Analyse einen explizit erreichbaren Markt in `accessibleStores` und eine bereits beim Kauf existierende Beobachtung.

## Bedarfs- und Listenport

Stock: `{lotId,foodTypeId,quantity,usableUntil,safe,available}`; nur ausdrücklich `safe=true` und `available=true` mit bis zum Bedarfsdatum gültigem `usableUntil` wird FEFO-verbraucht. Demands: `{eventId,foodTypeId,dueDate,quantity,kind}`; zubereitete Mahlzeit und späterer Portionsverzehr werden nicht nochmals als rohe Zutaten gerechnet. Ungültige IDs/Daten ergeben Fehler; unbekannte Mengen, Chargen und Pläne bleiben sichtbar unvollständig.

`horizons` (Standard 1/7/28/56 Tage) sind **kumulativ aus demselben Lauf**, nicht addierbar. Für den optionalen historischen Baseline-Verbrauch sind mindestens sieben beobachtete Tage und drei bestätigte tatsächliche Events je Produktvariante erforderlich; ein Tag mit explizitem Plan ersetzt die Baseline desselben FoodTypes und Mengentyps.

`suggestPurchases` rundet die benötigte Packungsanzahl auf, rechnet bekannte Paketpreise und überschreitet keine stillschweigend unterstellten Budgets/Kapazitäten. Ein Budget benötigt bestätigten Betrag und Zeitraum; Lagerplatz `capacity[storageClass]` und `packageVolumeMl` müssen explizit sein. Lagerkapazität wird **über alle Vorschläge** fortlaufend angerechnet. Haltbarkeit anhand dokumentiertem `shelfLifeDays` bis zum letzten Bedarfstag; keine automatisierte lebensmittelrechtliche Freigabe. `FEASIBLE_NOT_PURCHASED` ist nur ein Rechnungs-/Planvorschlag, `REVIEW` erfordert Host-/Nutzerprüfung. Bei unbekanntem Einzelpreis bleiben `totalCostCents=null` und bekannte Teilsumme separat.

Zulässige Interessenaktionen: `INTERESTED`, `UNDECIDED`, `NOT_TODAY`, `HIDE_PRODUCT`, `HIDE_FOOD_TYPE`, `ADD_TO_SHOPPING_LIST`. Keine Aktion schreibt Bestände oder bestätigt einen Kauf. Listen- und Preisvergleiche sind getrennte DTOs. Der Host übernimmt nach Nutzerentscheidung allein die Persistenz.

## Erweiterung: gemischte Packungsoptimierung (aktuelle Referenz)

`eg_shopping/pack_optimizer.py:optimize_package_mix` durchsucht für **einen** bestätigten FoodType mit gleicher Mengenbasis alle Kandidatenmischungen exakt bis zur begrenzten Suchgröße (`max_nodes` standardmäßig 250000, höchstens acht Preisvarianten). Der Output gibt `items[]` mit `productId`, `packs`, `quantityBought`, `costCents`, `optimalityProven`, `warnings` und `scope=EXACT_PER_FOODTYPE_ONLY` aus. Bei Überschreiten von Suchgrenzen: `SEARCH_LIMIT` und keine erfundene optimale Kaufempfehlung.

`suggest_purchases` nutzt den Optimierer **pro Lebensmitteltyp** und rechnet nach jeder Zuteilung Budget und Lagerkapazität fort. Die Reihenfolge nach FoodType ist deterministisch, aber **nicht global budgetoptimal über unterschiedliche Lebensmittel**. Bei mehreren Gebinden ist `productId=null`, `mix[]` beschreibt die Einzelgebinde. `FEASIBLE_NOT_PURCHASED` bedeutet ausschließlich *rechnerisch anhand bekannter Inputannahmen ausführbar*, weder verfügbare Ware garantiert noch reserviert. Keine Buchung.

Multibuy-Schwellen mit `minPacks` werden nur berücksichtigt, wenn die vorgeschlagene Bestellanzahl den Mindestwert tatsächlich erreicht; die entsprechende Preis-/Aktionsgültigkeit muss der Host belegen. Beliebige `conditional[]`-Texte (App-Mitgliedschaft/Coupon) gelten **nicht** als erfüllt und schließen die rabattierte Option aus. `ONLINE_LISTED` bleibt in diesem Packungsoptimierer ausgeschlossen, weil eine verlässliche Zuordnung einmaliger Versandkosten zum gesamten Warenkorb nicht modelliert ist. Berücksichtigte Mengenbereiche: bestätigte `quantity.amount`, `unit`, `basis`; `packageCount` wird exakt multipliziert.

Bei unbekanntem Rohbedarf enthält `project_needs` zusätzlich `unknownNeeds[]` mit `quantityToBuy=null`; die kumulative Bedarfssumme behauptet dadurch keine bekannte Null. Historische Portionen konsumierter Fertiggerichte (`kind=PORTION_CONSUMPTION` bzw. `COOKED_MEAL_CONSUMPTION`) fließen nicht als Rohzutaten-Verbrauchsbaseline ein.

## Nachweis und offene Integration

Installieren für Tests: `python -m pip install 'jsonschema[format]==4.23.0'` und `python -m unittest discover -s tests -v`. GitHub Actions prüft dieses Kommando bei Push/PR. Der formale Contract-Validator läuft gegen alle vorhandenen `contracts/v1/examples.json` und einen erzeugten `comparison.result`-Envelope.

**Noch nicht integriert:** Kotlin-Produktivport, Room-Adapter, UI und Geräte-/Kühlkettenprüfung. Weitere konservative Einschränkungen, insbesondere Packungsoptimierung und bestätigte komplexe Couponbedingungen, sind in `docs/STATUS.md` notiert. Die Python-Referenz darf nicht als fertig integrierte Android-Funktion bezeichnet werden.


## Belegte Preis-/Kaufkosten für Nachkaufvorschläge (31.10.2026)

Der Port `suggest_purchases(..., as_of="2026-10-31T15:00:00+01:00")` akzeptiert pro internem Produkt-Snapshot zusätzlich ein originalgetreues `priceObservation` im Format von `contracts/v1/contract.schema.json` sowie `depositCents` als **bekannte ganze Centzahl oder null**. Eine rechnerische Packungsoptimierung ohne diese Angaben bleibt möglich, darf aber nur `REVIEW` liefern. Für eine als `FEASIBLE_NOT_PURCHASED` markierte Planrechnung muss die Preisbeobachtung zum Einkaufstag gültig, mit passender Ware/Mengenbasis/Preis verknüpft, qualitativ `CONFIRMED` oder `SOURCED` und spätestens zu `as_of` bekannt sein. Ketten-/Regionalscope erhält Warnhinweise statt Filialgarantie.

`costCents` und `totalCostCents`: Warenpreise, ohne rückerstattbares Pfand. `checkoutCents` und `totalCheckoutCents`: beim Kauf zu zahlende bekannte Warenpreise **plus explizit belegtes Pfand**. Bei unbekanntem Pfand ist die Checkout-Summe `null`, nicht Warenpreis+0; dadurch auch `budgetRemainingCents=null`, weil die Liquidität nicht sicher berechnet werden kann. `knownCheckoutSubtotalCents` ist ausdrücklich nur die belegte Teilsumme. Shop-weite Versandkosten, Coupon-Kombinationen, einlösbare Rückgaben und Filialrouting sind nicht modelliert und werden nicht als optimiert dargestellt.

Erforderliche minimal-normalisierte Produktdaten: `productId`, `foodTypeId`, `quantity`, `priceCents`, `priceObservation`, `depositCents`, `shelfLifeDays`, `storageClass`, `packageVolumeMl`; optional `minPacks` nur mit `termsVerified=true` aus verifizierten Promotionsbedingungen. Fehlt der Beleg, gibt die Engine `REVIEW` und eine dokumentierte Ursache zurück. Zusätzliche Präferenzfelder und Kombinationen ohne explizite Quellbasis gelten nicht automatisch als verbindliche Kaufentscheidung.
