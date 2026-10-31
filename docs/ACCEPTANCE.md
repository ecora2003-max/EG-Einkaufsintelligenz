# Testpflicht und Abnahme – Einkaufsintelligenz
Jede Codeänderung mit veränderter Fachlogik: betroffene Unit-/Vertrags-/Regressionstests **ausführen** und in `docs/STATUS.md` Datum, SHA, Befehl, Anzahl grün/rot/skipped sowie bekannte Datenlücken festhalten. Ohne solche Testnachweise keine Abschlussmeldung.

## Deterministische Pflichtfälle
| Szenario | Erwartung |
| --- | --- |
| Bio-Haferflocken 500 g 1,99 €; Bio-Alternative 500 g 1,79 € | **Rot**, 20 Cent Packungsersparnis, €/kg korrekt |
| Bio-Angebot 500 g 1,99 €; Nicht-Bio 500 g 0,99 € | **Orange** zusätzlich, niemals still als gleichwertiges Bio |
| Fehlende Preise in Penny/EDEKA/Netto | **Grau** „Könnte es günstiger geben“, ohne unbelegte Bestpreisbehauptung |
| Bio unbekannt | nicht als `false` einordnen; keine falsche Rot-/Orange-Sicherheit |
| Marken- gegen Eigenmarke, gleiche funktionale Variante | Vergleich möglich, Markenunterschied sichtbar |
| Süßes Müsli vs. Haferflocken | ohne fachliche Substitutionsregel kein gleicher-FoodType-Preisvergleich |
| 2×500 g 2,30 € vs. 500 g 1,20 € | korrekter €/kg-Vergleich ohne nur Packungspreis zu vergleichen |
| Ananas 1 Stück ohne Gewicht | **kein** geratener €/kg |
| 1 l vs. 500 ml; fehlendes Abtropfgewicht | Liter-Umrechnung korrekt; unklare Basis blockiert |
| Aktionspreis beginnt morgen | heute nicht als verfügbare Alternative; Zukunft separat |
| Onlinepreis + Versand/App-Coupon/Pfand | Bedingungen und Endkosten getrennt, kein irreführender Vergleich |
| Kauf rückwirkend vergleichen | ausschließlich damals belegte alternative Preise |
| Alte Beobachtung vs. heutiger Preis | historischer Wert nie als aktueller Preis |
| Zwei Pläne/mehrere Portionsverzehre aus einer Zubereitung | keine Rohwaren-/Bestandsdoppelzählung |
| Fehlendes Budget/Bestand/Lagerkapazität | `UNKNOWN` und Warnung, niemals 0 |
| Rabattaktionen/Mehrfachkauf | günstigere Kosten nur bei tatsächlich erfüllbaren Bedingungen |
| Inkompatible/gesperrte Chargen | nicht als uneingeschränkt verwendbarer Bestand |
| Nutzer markiert Angebot „Interessiert mich“ | nur Zustandsvorschlag, keine tatsächliche Buchung |

## Status READY_FOR_INTEGRATION
Nur wenn ein **ausführbares, getestetes** Vergleichssystem alle oben beschriebenen Kosten-, Einheiten-, Geltungs-, Bio- und Coverage-Fälle besteht; offene Unterschiede/Alternativen korrekt ausgegeben; kontraktkonforme Beispielpayloads existieren; deterministische Nachkaufberechnung ohne Doppelzählung für mindestens drei realistische fiktive Zeithorizonte getestet ist; die Interessen-/Listenmodelle dokumentiert sind; Offline-, Fehler- und Teilwissenpfade funktionieren; keine App-/Sheets-/Datenbankänderung stattgefunden hat. Fehlende Teilfunktion = `PARTIAL_READY` mit genauem Funktionsumfang. `INTEGRATED` nur Codex.

## Darf nicht als bestanden gelten
Ein einziges „bestes Angebot“ aus unvollständigen Katalogen; aus `oldPrice` erfundener Normalpreis; Bewertung ohne Grundpreis-/Variante-Prüfung; Preis für falschen Einkaufstag; direkter Bestandsabzug durch eine Empfehlung; Geld mit unkontrollierten Float-Rundungen.

## Zusätzliche verbindliche Architekturabnahme 31.10.2026 (ADR-014/016/017)

Der alte Pflichtumfang bleibt unverändert. Als weitere *Offline*-Abnahme gelten nun:
- Anzeige-/Nutzungs-Gate: RESEARCH_ONLY strikt von APP_DISPLAY und PRIVATE_USER_HISTORY unterscheiden; externer Preis in APP_DISPLAY nur mit Host-geprüfter, auf Source-Origin, RightsEvidenceRef, Retailer, Erhebungsmodus und Verwendungszweck bezogener Berechtigung. UNVERIFIED und RESTRICTED aus externen Preisalternativen, Angeboten, Kaufvorschlägen sowie historischen/future Sparbehauptungen ausschließen; bei Coverage-Lücke Grau und keine Bestpreisgarantie.
- Funktions-Gate: acht exakte Händler-IDs; gezielte reguläre Preisabfrage nur ALDI_NORD/ALDI_SUED/REWE/LIDL, veröffentlichte Angebote für diese und PENNY/KAUFLAND/EDEKA/NETTO_MD. Händlername allein keine Rechtsfreigabe. Netto-Varianten dürfen nicht verwechselt werden.
- Private Preisgeschichte: eigene, datierte und bestätigte HISTORICAL_PAID-Bons getrennt von fremden aktuellen Quellen; keine zweite Buchungswahrheit. Anonyme/unbestätigte OCR-Ergebnisse sind nicht automatisch bestätigte Käufe.
- Experimentelle v1.1-Interop: typed unknownNeeds[] ohne Mengen-/Einheitenerfindung, typed packageLines[] mit verifizierbaren Summen und Originalbelegen; Checkout bei unklarem Pfand null; verpflichtendes savingsBasis=MERCHANDISE_ONLY und positives belegtes historisches Sparen für PROVEN. Neue Draft-Nachrichten nicht ungefragt als stabile Integration bezeichnen. Unveränderte v1.0-Regressionen weiterhin grün.

Reproduzierbarer Nachweis: GitHub Actions https://github.com/ecora2003-max/EG-Einkaufsintelligenz/actions/runs/41228078142, python -m unittest discover -s tests -v nach jsonschema[format]==4.23.0: 127/127 bestanden, keine Fehler/Skips. Abgedeckt sind nur reine Offline- und Vertragsprüfungen; keine behauptete Live-Quelllizenz, sichere Host-Rechteauthentifizierung, Android-Port- oder Gerätetests.
