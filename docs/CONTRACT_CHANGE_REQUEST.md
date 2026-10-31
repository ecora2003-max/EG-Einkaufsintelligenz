# Vertragsänderungsvorschlag — Einkaufs-DTOs (nicht freigegeben)

**Status:** REQUESTED, nicht Bestandteil des freigegebenen `1.0.0-draft`-Schemas. Nur dieses Modulrepository schreiben.

## Problem

Der gemeinsame Vertrag definiert `comparison.result`, aber nicht die Input-/Output-Formen für `ShoppingNeed`, `OfferInterest`, `PurchaseSuggestion` und `HistoricalComparison`. Ohne gemeinsame IDs und Snapshot-/Zeit-/Qualitätsgarantien kann der Haupt-App-Adapter Listen- und Vorschlagszustände nur proprietär zuordnen.

## Gewünschte kompatible Erweiterung

Optional neue Nachrichten in einem später freigegebenen Minor-/Major-Kontrakt (je nach Art):

- `shopping.need.projection`: `snapshotAt`, `asOf`, `horizonDays`, `needs[]` mit stabiler `needId`, `foodTypeId`, `dueDate`, `quantity`, `stockEvidenceRefs`, `completeness`, `warnings`. Kumulative Horizonte aus identischem Snapshot.
- `shopping.purchase.suggestion`: `needIds[]`, `productId`, `observationRefs[]`, `quantity`, `packageCount`, `expectedCents|null`, `budgetPeriod`, `capacityEvidence`, `status`, `warnings`. Kein Buchungsbefehl.
- `shopping.offer.interest`: `productId`, `foodTypeId`, `action`, `effectiveAt`, `sourceOfferIds[]`, `proposedState`. Persistenz ausschließlich Host.
- `shopping.past.comparison`: `confirmedPurchaseRef`, `purchaseAt`, `evidenceCutoff`, `storeScope`, `matchedHistoricalOfferIds[]`, `rejectedReasons`, `savingsProvenCents|null`.

Pro Eintrag: Verknüpfung zur Ursprungsbeobachtung, Offset-Zeitpunkt, Datenqualität und reproduzierbare Mengenbasis. `null` ausdrücklich unbekannt; nicht Nullwert. Optional `availabilityEvidence`, `conditionsFulfilled`, `unitRateRational`.

## Risiken / Migration

Neue Nachrichtentypen ändern die `messageType`-Enum und benötigen Entscheidung der Architektursteuerung, aktualisierte `contracts/v1` bzw. neue Version, Schema, Positiv-/Negativ-Fixtures, Abnehmerabstimmung und Kotlin-Adapter. Bis dahin bleiben die DTOs **modulintern**, `comparison.result` kann vertragskonform separat serialisiert werden.

## Testforderungen

Abwärtskompatibilität des existierenden `comparison.result`; fehlende Beträge/Zeiten ungleich Null; klare Abweisung unbestätigter Buchungszustände; Validierung kumulativer Horizonte ohne Doppelzählung; Schema-Validierung aller neuen Nachrichten und falscher Nachrichtentypen.
