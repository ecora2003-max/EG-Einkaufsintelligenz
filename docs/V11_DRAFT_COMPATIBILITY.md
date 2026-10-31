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

1. **Unbekannte Menge und Einheit:** Der Engine-Output kann `quantityToBuy=null` zusammen mit nicht bekannter `unit`/`basis` enthalten. `ShoppingNeed.quantity.unit` erlaubt in `1.1.0-draft` jedoch ausschließlich `g/ml/portion/piece`. Der Adapter **erfindet keinen Einheitstyp**: solche Bedarfe werden unter Erhalt ihrer Ereignis-ID in `warnings` ausgewiesen, bei `completeness=PARTIAL`; sie dürfen noch nicht als typisierte Einkaufsposition angezeigt werden. Gewünschte v1.1-Erweiterung: `unit=null` oder explizite separate `unknownNeeds[]` mit Identifier.
2. **Gemischte Gebinde:** `productId=null` und `packageCount=null` bei mehreren Artikeln; genaue Zusammensetzung verbleibt als optionale `mix[]`-Extension. Für den finalen Android-Adapter wären versionierte `packageLines[]` statt einer mehrdeutigen Einzelzeile sinnvoll.
3. **Historisches Sparen:** `savingsProvenCents` repräsentiert nachgewiesene **Warenpreis**-Ersparnis. Pfand-/Retoure- und vollständige Checkout-Ersparnis dürfen ohne eigene Belege nicht behauptet werden. Die Extension `savingsBasis=MERCHANDISE_ONLY` legt die Semantik offen.
4. **Rechte und Quelle:** Offizielle Schema-Validität belegt keine Live-Lizenz, kein Geschäftslokal und keine Lagerverfügbarkeit. `meta.usageContext` ist bewusst stets `RESEARCH_ONLY`.

## Nachweis / reproduzierbare Prüfung

CI: [Offline acceptance, Run 41224489521](https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41224489521), PR-Merge-Checkout `6d2ff53` gegen Fachcode-SHA `2c25588dd183e2c6d8c73ba318d47bb54f0981d1`. Python 3.12, Befehl:

```bash
python -m pip install 'jsonschema[format]==4.23.0'
python -m unittest discover -s tests -v
```

Ergebnis: **106 bestanden / 0 fehlgeschlagen / 0 übersprungen**. In `tests/test_draft_v11.py` werden alle neun Architektur-Beispielnachrichten durch `Draft202012Validator` und den Formatchecker validiert sowie eigene positive und negative Adapter-Fälle geprüft. Die unveränderte `v1.0`-Validierung wird parallel fortgeführt. Diese CI belegt eine **experimentelle Formatkompatibilität**, keine Freigabe der neuen Vertragsversion oder Geräteintegration.

**Wiederaufnahme:** Auf formale Freigabe durch Architektursteuerung und Entscheidung über unbekannte Einheiten/Mischgebinde warten. Erst nach Freigabe anbieterkompatiblen CLI-/Kotlin-Adapter erstellen und mit Codex auf der Haupt-App-Seite integrieren. Haupt-App, Architektur und andere Modulrepositorien wurden nicht verändert.
