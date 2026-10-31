# V1.1 Shopping-Vertrag: isolierter experimenteller Adapter

**Stand 31.10.2026, Status: EXPERIMENTAL / SCHEMA_TESTED; keine Freigabe zur produktiven Nutzung.**

**Quellvertrag:** EG-Architecture `contracts/v1.1/contract.schema.json` (`1.1.0-draft`, ursprüngliche Quell-Blob-SHA `f4755a0a2dfbd8c4f58f2778fa21800b9e3ffbdc`; Architektur-Head beim Abschluss `ecd26097eb5678296a14de9d9b5db79ccea9be64`). Unveränderte Testkopien: `contracts/v1.1/contract.schema.json` und `contracts/v1.1/examples.json`. Beide liegen ausschließlich im eigenen Modulrepo.

## Laufender v1-Vertrag bleibt unverändert

`eg_shopping/cli.py`, `comparison_envelope` und alle bisherigen Aufrufe verwenden weiterhin **`1.0.0-draft`**. Die vier Funktionen in `eg_shopping/draft_v11.py` sind **nur bei ausdrücklich direktem Import** verfügbar. Sie sind **nicht** in `__init__.py` und **nicht** als CLI-Operation freigeschaltet. Die Architekturfreigabe und die Kotlin-Integration durch Codex sind ausstehend.

## Abgebildete Nachrichten

| Neue Draft-Nachricht | Experimenteller Adapter | Evidenz und Begrenzung |
| --- | --- | --- |
| `shopping.need.projection` | `need_projection_envelope` | Expliziter Snapshot- und Cutoff-Zeitpunkt, ein kumulativer Horizont, stabile `eventId` als `needId`, übergebene Snapshot-/Chargenbeleg-IDs. Unbekannte Mengen werden **nicht zu 0**. |
| `shopping.purchase.suggestion` | `purchase_suggestion_envelope` | Ein Vorschlag, Bedarf-IDs, einzelne Angebotsbeleg-IDs, gebundene Cents, gemischte Gebinde als Extension `mix`; unbewiesene Preise niemals als gesicherte `expectedCents`/`checkoutCents`. Kein Kaufbefehl. |
| `shopping.offer.interest` | `offer_interest_envelope` | Alle sechs erlaubten Aktionen; prüft, dass der interne Vorschlag keine Bestands- oder Kaufänderung enthält, `confirmed=false`. |
| `shopping.past.comparison` | `past_comparison_envelope` | Bestätigte Kaufreferenz vom Host, Filial-Scope, `evidenceCutoff=purchaseAt`, alternative Beleg-IDs, Warnungen, historisch beweisbare **Warenpreis**- statt hypothetischer Checkout-Ersparnis. |

## Nicht verlustfrei abbildbare Fälle / notwendige Architekturentscheidung

1. **Unbekannte Menge und Einheit:** Der Engine-Output kann `quantityToBuy=null` zusammen mit nicht bekannter `unit`/`basis` enthalten. `ShoppingNeed.quantity.unit` erlaubt in `1.1.0-draft` jedoch ausschließlich `g/ml/portion/piece`. Der Adapter **erfindet keinen Einheitstyp**: solche Bedarfe werden im zusätzlichen, schema-zulässigen `unknownNeeds[]`-Objekt mit unverändertem `needId`, `foodTypeId`, `dueDate`, `quantityToBuy=null` und Grund gesondert erhalten und zugleich in `warnings` markiert (`completeness=PARTIAL`); sie dürfen nicht als typisierte Einkaufsposition mit fingierter Einheit ausgegeben werden. Gewünschte v1.1-Erweiterung: `unit=null` oder explizite separate `unknownNeeds[]` mit Identifier.
2. **Gemischte Gebinde:** `productId=null` und `packageCount=null` bei mehreren Artikeln; genaue Zusammensetzung verbleibt als optionale `mix[]`-Extension. Für den finalen Android-Adapter wären versionierte `packageLines[]` statt einer mehrdeutigen Einzelzeile sinnvoll.
3. **Historisches Sparen:** `savingsProvenCents` repräsentiert nachgewiesene **Warenpreis**-Ersparnis. Pfand-/Retoure- und vollständige Checkout-Ersparnis dürfen ohne eigene Belege nicht behauptet werden. Die Extension `savingsBasis=MERCHANDISE_ONLY` legt die Semantik offen.
4. **Rechte und Quelle:** Offizielle Schema-Validität belegt keine Live-Lizenz, kein Geschäftslokal und keine Lagerverfügbarkeit. `meta.usageContext` ist bewusst stets `RESEARCH_ONLY`.

## Nachweis / reproduzierbare Prüfung

CI: [Offline acceptance, Run 41224765046](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224765046), PR-Merge-Checkout `67084be` gegen Fachcode-SHA `f56ade91d2192d41cb21ac780d6f9937d6722702`. Python 3.12, Befehl:

```bash
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

Ergebnis: **107 bestanden / 0 fehlgeschlagen / 0 übersprungen**. In `tests/test_draft_v11.py` werden alle neun Architektur-Beispielnachrichten durch `Draft202012Validator` und den Formatchecker validiert sowie eigene positive und negative Adapter-Fälle geprüft. Die unveränderte `v1.0`-Validierung wird parallel fortgeführt. Diese CI belegt eine **experimentelle Formatkompatibilität**, keine Freigabe der neuen Vertragsversion oder Geräteintegration.

**Wiederaufnahme:** Auf formale Freigabe durch Architektursteuerung und Entscheidung über unbekannte Einheiten/Mischgebinde warten. Erst nach Freigabe anbieterkompatiblen CLI-/Kotlin-Adapter erstellen und mit Codex auf der Haupt-App-Seite integrieren. Haupt-App, Architektur und andere Modulrepositorien wurden nicht verändert.

**Hinweis:** Die erfolgreiche PR-Prüfung wurde unter https://github.com/ecora2003-max/EG-Einkaufsintelligenz/pull/4 ins eigene Repository integriert (Merge `63c7f22401cd7b7765f81b4b92b9938952f883cf`). Änderungen an der Haupt-App, Architektur oder anderen Zuliefererprojekten wurden nicht vorgenommen.

**Zusätzlicher Negativtest:** Auch wenn ein Host intern `priceEvidenceVerified=true` behauptet, blockiert der Adapter die Ausgabe als nachgewiesene Kosten, wenn **eine** Zeile der gemischten Gebindeauswahl ohne `observationId` vorliegt. Test: `test_purchase_adapter_missing_one_mix_observation_cannot_prove_costs`; CI 41224765046, 107/107 grün. Die zusätzliche testauslösende PR #5 wurde ausschließlich im eigenen Repository gemergt (`da08f07122a4924f1437b0bb2a1a6e9c524762c7`).

## Aktualisierung nach ADR-017, ADR-014 und ADR-016 – 31.10.2026

Die früheren Vorschläge zu unbekannten Einheiten, Mischgebinden und Ersparnis-Basis wurden durch die Architektursteuerung als ADR-017 **im neuen 1.1.0-draft** umgesetzt. Dieser Entwurfsstand ist noch **nicht** stabil oder für Codex produktiv freigegeben. Gegen die neue Schema-Blob-SHA dca777d219307a90bf3d4dff6189fbf12476c508 ist der isolierte opt-in-Adapter erneut implementiert und getestet:

- unknownNeeds[] enthält den ursprünglichen needId/foodTypeId, dueDate als echtes ISO-Datum oder null, quantityToBuy=null und die Ursache. Keine erfundene physikalische Einheit; COMPLETE wird bei unbekannten Bedarfen nicht ausgegeben.
- packageLines[] enthält pro ausgewählter Packungsvariante die Produkt-/Quell-ID, Anzahl, genaue Menge, Waren-, Pfand- und Checkout-Cents sowie Händler/Filiale. Fehlende Einzelbelege oder unbekannte Pfandwerte verhindern die Behauptung belegter Endkosten. Waren-/Pfand-/Checkout-Summen und die gesamte Einkaufsmenge werden geprüft.
- Historische Vergleichsergebnisse tragen verpflichtend savingsBasis=MERCHANDISE_ONLY; PROVEN setzt positive nachgewiesene Warenpreisersparnis voraus. Kein rückwirkendes heutiges Angebot und keine automatische Buchung.

ADR-014/016 sind durch source_policy.py und die unveränderte Capability-Policy-Kopie umgesetzt. Erlaubte targeted price queries nur ALDI_NORD/ALDI_SUED/REWE/LIDL; alle acht Händler nur veröffentlichte Angebote. APP_DISPLAY fremder Preise ausschließlich mit hostgeprüften quell-, handels-, verwendungs- und verfahrensbezogenen Rechtsbelegen; sonst nicht in sichtbare Alternativen/Vorschläge übernehmen und Preisvergleich als unvollständig kennzeichnen. Der öffentlich aufrufbare JSON-CLI-Adapter lässt kein APP_DISPLAY und keine ungeprüften Rechtezuweisungen zu.

Echter Regressionstest: GitHub Actions 41228078142, Job 124616327776, geprüft main-Basis 05ec7fdeed29fc80392e35478fcfd4e923268ecf im PR-Merge d97624e: 127/127 bestanden, 0 fehlgeschlagen, 0 übersprungen. PR #8 erfolgreich ins eigene Repository gemergt (Commit a3d14e76867ed0b2f576a8eb7d11c34db1362f26). Die beiden Architektur-Schema-/Policy-Blobs wurden auf Architektur-HEAD d7aa7dda1f0a34b52102b35785195e7ade26ceb4 erneut unverändert verifiziert.

**Freigabegrenze:** geprüfter Offline-Referenzkern weiterhin READY_FOR_INTEGRATION, zusätzliche v1.1-Nachrichten nur EXPERIMENTAL/SCHEMA_TESTED, keine live erprobten oder rechtlich freigegebenen externen Quelladapter, keine bestätigte Android-App-Anbindung. Abschluss des Gesamt-App-Integrationsgates bleibt ausschließlich Codex vorbehalten.
