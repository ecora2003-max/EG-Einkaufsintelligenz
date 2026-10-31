# Entwicklungsmandat – Preisvergleich, Einkaufsprognose und Empfehlungen
**Fachprodukt:** Preisvergleichs- und Einkaufsintelligenz als eigenständige, reine Engine ohne externe Datenbeschaffung.

## 1. Auftrag und Datenabhängigkeit
Die Engine konsumiert **explizit gelieferte** Preis-Snapshots, Produktzuordnungen und optional freigegebene Bestands-/Planungs-Snapshots. Sie importiert niemals direkt den Code von Händleradaptern oder Android-Room. Ergebnis: begründete und prüfbare Vergleiche, Warnsignale und Vorschläge für Einkaufslisten.

## 2. Erste Kernfunktion: der Preisvergleich
Vergleiche (a) **alle aktuellen und für den Einkaufstag veröffentlichten Aktionen der acht Händler miteinander**, (b) alle gefundenen regulären/stationären Produktpreise aus verfügbaren Katalogen/Suchen (besonders Lidl, ALDI Nord/Süd, REWE, ohne Vollständigkeitsgarantie), (c) passend datierte historische Beobachtungen aus bestätigten Käufen **nur als historische Referenz**. Onlinepreise nur als gesonderte Alternativen mit anderem Kanal; Versandkosten und Gebinde beachten.

Automatisch vergleichbar nur bei belegter Menge, passender Einheit und ausreichender Produktähnlichkeit. Basis-Preis je kg/l; Stück bei unbekanntem Stückgewicht nur als Stückpreis unter passenden Identitäten/Einheiten. Gleiche/ähnliche Markenprodukte, Eigenmarken und Bio-Vergleich in separaten Dimensionen; nicht nur exakte GTIN und nicht nur gleiches Wort vergleichen.

### Qualitäts- und Bio-Warnungen
- **Rot:** funktional vergleichbare Alternative mit **demselben bekannten Bio-Status** und nachweislich niedrigeren kompatiblen Grund-/Kaufkosten gefunden; Marke/Eigenmarke darf unterschiedlich sein und wird angezeigt.
- **Orange:** funktional vergleichbare billigere Alternative mit **anderem bekannten Bio-Status**; Unterschiede explizit nennen, z. B. Bio vs. nicht Bio.
- **Grau:** `Könnte es günstiger geben` bei fehlenden/alten/nicht kompatiblen Daten oder unvollständigem Suchraum; nicht behaupten, eine günstigere Alternative existiere. Grau kann mit Rot/Orange zusammen erscheinen.
- Bio `unknown` darf nicht als „nicht Bio“ gelten. Weitere Merkmale (zart/kernig, Fettanteil, gesüßt, tierisch/vegan, tiefgekühlt/frisch, Sorte, Allergene) können Vergleich blockieren oder als `FUNCTIONAL_SUBSTITUTE` qualifizieren.
- „Kein günstigeres **gefunden**“ != „es gibt kein günstigeres“. Kein Gewinn-Signal allein aufgrund von Rabattschild/UVP/OldPrice.
- Mindestens eine Anzeige-Alternative soll zeigen: Händler, Produktname, Menge, €/kg oder €/l, absoluter Kaufpreis, gültiger Tag, Bio/Marke-Unterschied, Einschränkungen und Quellenalter.

### Preisarten und Vergleichsdatum
`SALE`, `CURRENT_DISPLAYED`, `LISTED_REGULAR`, `REFERENCE_OLD`, `HISTORICAL_PAID`, `ONLINE_LISTED` nicht vermischen. Referenz/UVP nicht ohne Beleg als tatsächlichen Normalpreis behandeln. Angebote nur innerhalb bestätigtem Gültigkeitsfenster für `shoppingDate` vergleichen; zeitlich abweichende Angebote als Option **für anderen Einkaufstag** hervorheben. Historische Einkaufsauswertung nur mit zum Kaufdatum belegten Alternativen – nicht rückwirkend mit heutigen Preisen. Pfand, Coupons, App-Mitgliedschaft und Mengenschwellen separat, ohne stillen Rabattabzug. Nicht verfügbare Waren/Filialen nicht als garantiert kaufbar bezeichnen.

## 3. Zweite Kernfunktion: Einkaufsbedarf
Ein reiner `NeedProjectionEngine`-Kern berechnet aus vom Host bereitgestelltem **zeitlich konsistentem** Bestand/Chargen, bestätigten offenen Bedarfspositionen, Verbrauchshistorie und geplanten Kochvorgängen optional einen Nachkaufvorschlag.
- Frühester Bedarfstermin, sichere Charge, FEFO, physisch belegter Lagerplatz und Haltbarkeit beachten.
- Rollierender Horizont Tag, sieben Tage, vier bis acht Wochen **aus denselben Input-Plänen**; keine doppelte Menge bei Tag/Woche/56 Tagen.
- Derselbe vorhandene Bestand wird innerhalb eines Snapshots nur einmalig angerechnet. Gekochte Zutaten und später verzehrte Portionen werden nicht nochmals als Roheinkauf verlangt. Geplantes Kochen verändert noch keinen realen Lagerbestand.
- Baseline-Verbrauch aus historischen **tatsächlichen** Ereignissen nur bei ausreichender Datenqualität, ohne doppelte Berücksichtigung geplanter Rezeptmengen. `UNKNOWN`-Mengen dürfen keinen Nullbedarf erzeugen.
- Budget als bestätigter Zeitraum und bekannte Zahl; unvollständige Preise machen **Gesamtkosten offen**, ggf. bekannte Teilsumme getrennt. Lagerkapazität, Verpackungsvolumen, Kühlsituation und Verderb prüfen, keine automatische Sicherheitsfreigabe.
- Zeitliche Vorverlegung bei günstigem Angebot nur wenn benötigte Menge, Haltbarkeit, Finanzierung und Lagerkapazität belegbar passen; sonst nur als Unsicherheitsvorschlag.

## 4. Einkaufsliste und Angebotsliste getrennt
`ShoppingNeed` = Bedarf aus Plan/Verbrauch. `OfferInterest` = interessante Aktionen, **auch ohne akuten Bedarf**. Eigene UI-/Host-Aktionen: Interessiert mich, Weiß ich noch nicht, Heute nicht, Nicht mehr anzeigen (per Produkt/Typ), Zur Einkaufsliste; diese ändern Interesse/Ansicht, nicht physische Käufe/Bestände. Statusvorschläge als DTO/Events liefern, Speicherung später Codex. Nicht zu viele gleichartige Angebote mit anderem Filialnamen doppelt listen; Filter für präferierte Märkte, FoodTypes, Laufwege.

## 5. Drittes Ergebnis: Kaufnachbetrachtung
Aus **bestätigtem historischen Kauf** und zum Kaufdatum passendem Preissnapshot eine vergleichende Auswertung erzeugen: „Bei Händler X wäre diese nachweislich vergleichbare Menge damals günstiger gewesen“ – aber nur wenn Gültigkeit/Standort/Konditionen belegt sind. Ist-Datum unbekannt oder kein anderer damaliger Preis vorhanden: **keine erfundene Ersparnis**. Bei nicht vergleichbarer Ware Option separat als Substitut ausweisen.

## 6. Grenzen der Engine
Kein tatsächliches Einkaufsergebnis buchen, keine Zahlungsbuchung, keine Preis-API-Calls, keine Bon-OCR, kein eigenständiges Rezept-KI-Modell, keine medizinische Ernährungskontrolle. Der Host liefert validierte Snapshots. Alle Vorschläge sind revisionsfähige Entscheidungen, keine automatischen Bestandsbewegungen.

## 7. Ausgaben und Adapter
Die Engine liefert `comparison.result` mit **Liste** günstigerer Alternativen plus `signals` (Rot/Orange/Grau), `incomplete`, `gaps`, Quellreferenzen; weitere modulinterne DTOs `ShoppingNeedCandidate`, `OfferInterestCandidate`, `ShoppingDecisionReport` sind separat zu dokumentieren und später über Änderungsvorschlag im Architekturvertrag zu harmonisieren. Tests liefern exakte Zahlenbeispiele mit integer Cents, nachvollziehbarer Grundpreisrechnung und zeitlicher Gültigkeit.

## 8. Lieferpaket
Reiner Kern, reproduzierbare synthetische Fixtures, Vertragsexport, Error-Modell, gründliche Tests, bewusst fehlende Werte, präzise Abdeckungs-/Quellenhinweise, Android-Adapter-Skizze. Nicht implementierte Optimierungsschritte und konservative Vereinfachungen klar markieren.
