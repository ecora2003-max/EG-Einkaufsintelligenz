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

## Nachprüfung gegen neuen Architekturentwurf 1.1.0-draft (31.10.2026)

Die vier zuvor vorgeschlagenen Shopping-Nachrichten sind inzwischen im **noch nicht freigegebenen** Architektur-Schema `contracts/v1.1/contract.schema.json` vorhanden. Ein experimenteller, ausschließlich explizit importierbarer Adapter im eigenen Modul liegt unter `eg_shopping/draft_v11.py`; die produktive CLI bleibt auf `1.0.0-draft`. Die internen Payloads ersetzen nicht die später von Codex abzunehmende App-Integration.

**Offener Vertragsänderungsbedarf CR-20261031-unknown-shopping-units:** `ShoppingNeed.quantity.unit` erlaubt nur `g`, `ml`, `portion`, `piece`, selbst wenn `amount=null`, `confirmed=false` und `basis=UNKNOWN`. Dadurch ist ein Bedarf mit **noch nicht bekannter Mengenart** nicht typwahr abbildbar. Vorgeschlagen: ausdrücklich `unit=null` bzw. `unit=UNKNOWN` für unbestätigte Mengen erlauben **oder** `ShoppingNeedProjection.unknownNeeds[]` als eigenes Belegmodell mit `needId`, `foodTypeId`, `dueDate|null`, `reason` spezifizieren. Bis zur Entscheidung darf der experimentelle Adapter nur die separat als Extension transportierten unbekannten Bedarfe anzeigen, nicht `g` oder Nullmengen erfinden. Negativ-/Schema-Test nach Versionsentscheidung erforderlich.

**Offener Vertragsänderungsbedarf CR-20261031-mixed-packs:** `ShoppingPurchaseSuggestion.productId` und `packageCount` können null sein, bieten aber keinen typisierten Platz für gleichzeitig gewählte SKU-/Packungszeilen. Vorgeschlagen: optionale `packageLines[]` mit `productId`, `observationId`, `packageCount`, `quantity`, `merchandiseCents`, `depositCents|null`, `checkoutCents|null`, `retailerId/storeId`. Bis zur Entscheidung wird die exakte Mischung nur als optionale `mix[]`-Extension transportiert, `packageCount=null` bei Mischgebinden.

**Semantikpunkt CR-20261031-historical-savings-basis:** `savingsProvenCents` muss als reine **Warenpreisersparnis** oder als **Cash-/Checkout-Differenz** definiert werden. Der experimentelle Adapter setzt derzeit `savingsBasis=MERCHANDISE_ONLY`; unbekanntes Pfand bleibt ausdrücklich ungeklärt. Historische Filial-/Quellbeobachtung muss vor `purchaseAt` vorgelegen haben.

Keine Änderungen am Architekturrepository. Der Vertrag v1.1 bleibt ausdrücklich Draft, kein Runtime-Upgrade ohne Freigabe.

## Stand nach Architekturentscheidung ADR-017, 31.10.2026

Die drei dokumentierten Sachprobleme wurden für den separaten Draft 1.1.0 durch die Architektursteuerung formal aufgegriffen:
(1) unknownNeeds[] als eigener typisierter Nullable-Bedarf ohne fingierte Einheit;
(2) packageLines[] für belegte Mischgebinde mit Waren-/Pfand-/Checkout-Komponenten und Originalpreisreferenzen;
(3) savingsBasis=MERCHANDISE_ONLY als Pflichtangabe historischer Ersparnis.

**Umsetzungsstand:** Lokale experimentelle Python-Adapter in eg_shopping/draft_v11.py wurden gegen Architektur-Schema-Blob dca777d219307a90bf3d4dff6189fbf12476c508 mit 127 erfolgreichen synthetischen Offline-Tests (CI 41228078142) verifiziert. Der alte v1.0-Vertrag bleibt unverändert. Die Anträge sind auf Ebene des 1.1-Draft berücksichtigt, **aber nicht endgültig produktiv freigegeben**. Offen bleiben Freigabe durch Architektursteuerung/Abnehmer, Kotlin-/App-Integration durch Codex und externer Quellenrechtsnachweis. Es erfolgt keine Änderung an Fremdrepositories.
