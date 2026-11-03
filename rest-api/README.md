# Mock REST API für Retourenmeldungen

<!-- Hinweis: Dieses Dokument wurde mithilfe von KI anhand des vorhandenen Programmcodes aktualisiert. -->

Eigenständige Komponente für Sprint 2 des DvG-Projekts. Die FastAPI-Anwendung
simuliert eine Marktplatz-API: ShopEasy kann Retouren von Amazon und Zalando
abrufen, Bestelldaten abfragen und den Retourenstatus aktualisieren.
`examples/demo.py` ist der aufrufende ShopEasy-Client. Er legt zur Vorbereitung
zwei Mock-Retouren an und demonstriert anschließend die Abfragen und Statuswechsel.
Die echten API-Formate von Amazon und Zalando werden nicht nachgebildet.

## Rolle der Schnittstelle

Die API stellt lokal gespeicherte Mock-Daten bereit. ShopEasy ruft diese über
HTTP ab; die API selbst ruft keine Daten bei echten Marketplaces ab.

```text
ShopEasy-Client  -- GET: Retouren / Bestellungen -->  Mock-Marktplatz-API
                <-- JSON-Antworten ---------------
                -- PATCH: Retourenstatus -------->
```

`POST /api/v1/returns` dient zum Vorbereiten der Demonstration: Der Client legt
damit eine Meldung an, die einen beim Marketplace eingegangenen Retourenwunsch
darstellt. Anschließend liest und bearbeitet er sie in der Rolle von ShopEasy.
Beim Start einer neuen Datenbank sind die beiden Mock-Bestellungen verfügbar;
die Retourenliste bleibt leer, bis Meldungen per POST angelegt werden.

## Schnellstart unter Windows / PowerShell

Zu Beginn jedes Terminals vom Stammordner des geklonten Repositorys
`digitalisierung-von-geschaeftsprozessen` in die Komponente wechseln:

```powershell
cd rest-api
```

Alle weiteren Befehle werden in diesem Komponentenordner ausgeführt.
Die vorhandene lokale Umgebung nutzt Python 3.15.2; die Projektmetadaten verlangen
Python >=3.15.2 und <3.16. Eine Aktivierung der virtuellen Umgebung ist nicht nötig.

Falls die Umgebung noch nicht existiert:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Die Version muss mindestens 3.15.2 und kleiner als 3.16 sein. Falls `py` nicht
verfügbar ist, den Pfad zu einer passenden Python-Installation verwenden.
Eine virtuelle Umgebung auf jedem Rechner neu erstellen; `.venv` wird nicht
mit Git übertragen.

In Terminal 1 den Server starten. Der eigene Datenbankpfad hält die Demo vom
bisherigen Datenbestand getrennt:

```powershell
$env:REST_API_DB_PATH = 'data/demo.sqlite3'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In Terminal 2 den Client ausführen:

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/demo.py
```

Der Client gibt Requests, Antwortdaten und HTTP-Statuscodes aus. Er endet bei
unerwarteten Statuscodes oder fehlgeschlagenen Inhaltsprüfungen mit Exitcode 1.
Jeder Durchlauf legt zwei neue Retouren an und setzt sie auf `REFUNDED` und
`REJECTED`. UUIDs und Zeitpunkte ändern sich. Ein abweichender Server ist mit
`--base-url http://127.0.0.1:8001` einstellbar. Mit `Strg+C` den Server beenden.
Für einen leeren Retourenbestand einen bisher unbenutzten Datenbankpfad wählen.

Die Demo führt folgende fachliche Schritte aus:

1. Erreichbarkeit und die unabhängigen Amazon-/Zalando-Bestelldaten abfragen.
2. Zwei Retouren mit Initialstatus `NEW` anlegen und einzeln abrufen.
3. Retouren nach Marktplatz filtern.
4. Die Amazon-Retoure über `RECEIVED`, `IN_REVIEW` und `APPROVED` auf `REFUNDED`
   setzen und jeden neuen Status erneut über GET prüfen.
5. Nach Marktplatz, Bestellnummer und Status kombiniert filtern.
6. Die Zalando-Retoure über `RECEIVED` auf `REJECTED` setzen.
7. Erwartete Fehler `404`, `409` und `422` demonstrieren.

Unter Linux/macOS entsprechend `python3.15 -m venv .venv`,
`.venv/bin/python -m pip install -r requirements.txt`,
`.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` und
`.venv/bin/python -X utf8 examples/demo.py` verwenden.

## VSCode einrichten

Den Stammordner des geklonten Repositorys in VSCode öffnen. Die Datei
[`../.vscode/settings.json`](../.vscode/settings.json) hinterlegt die Umgebung
unter `rest-api/.venv`, den Suchpfad für `app` und die unittest-Erkennung.

Wenn VSCode bereits einen anderen Interpreter gespeichert hat, wird dieser
durch den neuen Standardpfad nicht automatisch ersetzt. Deshalb einmal:

1. `Strg+Shift+P` öffnen und **Python: Select Interpreter** auswählen.
2. **Enter interpreter path** wählen und im geklonten Repository
   `rest-api/.venv/Scripts/python.exe` auswählen.
3. **Developer: Reload Window** ausführen.

Unter Linux/macOS ist der Interpreter `rest-api/.venv/bin/python`.
Bei Meldungen über fehlende `fastapi`- oder `uvicorn`-Imports zuerst prüfen,
ob die Projektumgebung ausgewählt und `requirements.txt` dort installiert ist.
Ein im Terminal aktiviertes `.venv` allein ändert die gespeicherte
Interpreter-Auswahl des Editors nicht.

## Interaktiv vorführen

Bei laufendem Server <http://127.0.0.1:8000/docs> öffnen. Über **Try it out** und
**Execute** lassen sich alle Operationen ohne zusätzlichen Client aufrufen:

1. `GET /api/v1/orders/AMZ-2026-10001`: vorbereitete Bestellung mit zwei Positionen.
2. `POST /api/v1/returns`: Inhalt von `mock-data/amazon-return.json` verwenden.
3. Die zurückgegebene `id` für `GET /api/v1/returns/{return_id}` übernehmen.
4. `PATCH /api/v1/returns/{return_id}/status` mit `{"status":"RECEIVED"}` ausführen.
5. `GET /api/v1/returns` mit `marketplace=amazon` und `status=RECEIVED` aufrufen.
6. Status auf `APPROVED`, anschließend auf `REFUNDED` setzen.
7. Erneutes Setzen auf `NEW` zeigt den Fehler `409 Conflict`.

Zusätzlich erreichbar: `/redoc`, `/openapi.json` und `/health`.
Ein vollständiger tatsächlich ausgeführter Clientlauf ist in
[examples/demo-output.txt](examples/demo-output.txt) protokolliert.

## Automatisiert testen

Kein manuell gestarteter Server und keine zusätzlichen Testpakete erforderlich:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -v
```

Linux/macOS:

```bash
.venv/bin/python -B -X utf8 -m unittest discover -s tests -v
```

Die 15 Tests starten eigene HTTP-Server auf freien Ports an `127.0.0.1` und
verwenden temporäre SQLite-Datenbanken. Geprüft werden Bestelldaten unabhängig von
Retouren, Anlegen/Einzelabruf, kombinierte Filter und Pagination, Statuspfade,
Wiederholungen, Fehlerfälle, Schutz vor konkurrierendem Überschreiben,
Persistenz nach Neustart, Migration des bisherigen Schemas und der Demo-Client.
Die normale Datenbank wird dabei nicht verändert.

## Endpunkte

| Methode | Pfad | Funktion | Erfolg |
| --- | --- | --- | --- |
| `POST` | `/api/v1/returns` | Mock-Retoure anlegen | `201 Created` |
| `GET` | `/api/v1/returns` | Retouren auflisten und filtern | `200 OK` |
| `GET` | `/api/v1/returns/{return_id}` | Retoure über UUID abrufen | `200 OK` |
| `PATCH` | `/api/v1/returns/{return_id}/status` | Status aktualisieren | `200 OK` |
| `GET` | `/api/v1/orders/{order_id}` | Eigenständige Mock-Bestelldaten abrufen | `200 OK` |
| `GET` | `/health` | Erreichbarkeit prüfen | `200 OK` |

### Liste und Filter

`GET /api/v1/returns` liefert `items`, `total`, `limit` und `offset`.
`total` zählt alle Treffer vor der Pagination. Sortierung: Eingangszeitpunkt
absteigend, bei gleichem Zeitpunkt zusätzlich UUID absteigend.

| Query-Parameter | Bedeutung | Standard / Grenzen |
| --- | --- | --- |
| `marketplace` | `amazon` oder `zalando` | Optional, kleingeschrieben |
| `status` | Einer der unten genannten Statuswerte | Optional, großgeschrieben |
| `order_id` | Exakte Bestellnummer | Optional, 1-100 Zeichen |
| `limit` | Maximale Anzahl pro Seite | 20; erlaubt: 1-100 |
| `offset` | Zu überspringende Treffer | 0; mindestens 0 |

Alle Filter sind kombinierbar, etwa
`GET /api/v1/returns?marketplace=amazon&status=RECEIVED&limit=5`.
Der `order_id`-Filter liefert Retouren zu einer Bestellung. Die eigentlichen
Bestelldaten liefert `GET /api/v1/orders/{order_id}`.

### Retouren anlegen

```json
{
  "marketplace": "amazon",
  "order_id": "AMZ-2026-10001",
  "customer_reference": "AMZ-CUSTOMER-42",
  "item": {"sku": "SE-TSHIRT-BLUE-M", "name": "T-Shirt Blau, Größe M"},
  "return_reason": "Der Artikel ist zu klein.",
  "registered_at": "2026-10-28T10:30:00+01:00"
}
```

Alle Felder sind Pflichtfelder. Eine Retoure enthält in diesem vereinfachten Mock
genau ein Stück eines Artikels; Bestellungen können mehrere Positionen enthalten.
Referenzen und SKU erlauben 1-100 Zeichen, der Artikelname 1-200 Zeichen und der
Retourengrund 1-1000 Zeichen. Äußere Leerzeichen werden entfernt. Leere Texte,
Zahlen statt Text und unbekannte Felder werden abgewiesen. Im POST wird der
Marktplatz zusätzlich auf Kleinschreibung normalisiert.

`registered_at` erfordert einen ISO-8601-Zeitstempel mit Zeitzone, der nicht in der
Zukunft liegt. Numerische Zeitstempel, reine Datumswerte und zeitzonenlose Werte
werden abgewiesen. Gültige Zeitpunkte werden nach UTC normalisiert.

Der Server vergibt `id`, `received_at`, `updated_at` und `status=NEW`.
Diese Felder gehören nicht in den POST-Body. Anfangs sind `received_at` und
`updated_at` gleich. Der `Location`-Header verweist auf die angelegte Retoure.
`id` ist die in der Aufgabenstellung genannte `returnID`; `order_id` entspricht
der `orderID`. `registered_at` ist der Anmeldezeitpunkt beim Marketplace,
`received_at` der Erfassungszeitpunkt im Mock und `updated_at` der Zeitpunkt
der letzten Statusänderung.
Identische POSTs erzeugen jeweils neue Retouren; Dublettenerkennung ist nicht enthalten.
Es gibt keine Prüfung auf die Existenz einer Bestellung oder einen Erstattungsanspruch.

### Status aktualisieren

Request: `PATCH /api/v1/returns/{return_id}/status`

```json
{"status": "RECEIVED"}
```

Die Antwort enthält die vollständige Retoure mit neuem `status` und `updated_at`.
Die Regeln sind eine Festlegung dieses Mocks; die Aufgabenstellung schreibt keine
konkreten Statusnamen vor.

| Aktueller Status | Erlaubte Folgestatus |
| --- | --- |
| `NEW` | `RECEIVED` |
| `RECEIVED` | `IN_REVIEW`, `APPROVED`, `REJECTED` |
| `IN_REVIEW` | `APPROVED`, `REJECTED` |
| `APPROVED` | `REFUNDED` |
| `REJECTED` | Keine |
| `REFUNDED` | Keine |

Das erneute Setzen desselben Status ist erlaubt und ändert den Zeitstempel nicht.
Unzulässige Übergänge liefern `409`; unbekannte Statuswerte liefern `422`.
Konkurrierende Änderungen überschreiben keinen inzwischen geänderten Status:
Die unterlegene Anfrage erhält `409` und muss die Retoure erneut abrufen.

### Bestelldaten

Beim Start werden zwei eigenständige Bestellungen aus `mock-data/orders.json`
in SQLite hinterlegt: `AMZ-2026-10001` und `ZAL-2026-20002`.
Sie sind auch ohne Retouren abrufbar. Die Antwort enthält Bestellnummer,
Marktplatz, Kundenreferenz, Bestellzeitpunkt, Währung und Bestellpositionen mit
SKU, Name, Menge und Einzelpreis. Dezimalpreise werden als JSON-Strings ausgegeben,
z. B. `"24.90"`. Bestellnummern sind in diesem Mock marktplatzübergreifend eindeutig.

Die vorbereiteten Bestellungen werden bei Neustarts nicht dupliziert oder
überschrieben. Änderungen an der Fixture wirken für bereits gespeicherte
Bestellungen erst mit einer neuen Datenbank. Der POST legt nur eine Retoure an
und erzeugt keine fiktiven Bestelldaten aus deren Inhalt.

### Fehlerantworten

- `404 Not Found`: syntaktisch gültige Retouren-ID oder Bestellnummer unbekannt.
- `409 Conflict`: unzulässiger Statuswechsel oder konkurrierende Statusänderung.
- `422 Unprocessable Entity`: ungültiger Body, UUID, Filter oder Pagination.

`404` und `409` enthalten `{"detail":"Fehlerbeschreibung"}`.
`422` enthält unter `detail` Feldpfad (`loc`), Meldung (`msg`) und Fehlertyp (`type`).
Ungültige Anfragen verändern den gespeicherten Bestand nicht.

## Speicherung und Aufbau

Ohne Konfiguration wird `data/returns.sqlite3` verwendet. Relative Werte von
`REST_API_DB_PATH` beziehen sich auf den Komponentenordner. Datenbank und
virtuelle Umgebung sind in `.gitignore` ausgeschlossen. Bestehende Datenbanken
werden beim Start automatisch um `status` und `updated_at` erweitert:
Bisherige Retouren erhalten `NEW` und ihren Eingangszeitpunkt als Änderungszeitpunkt.
IDs und vorhandene Daten bleiben erhalten. Es gibt keinen Lösch-Endpunkt.

- `app/main.py`: App-Factory, Konfiguration, Lebenszyklus und Mock-Bestellungen.
- `app/models.py`: Eingabe-/Ausgabemodelle und Validierung.
- `app/routes.py`: HTTP-Endpunkte und Dependency Injection.
- `app/service.py`: Statusregeln und Verarbeitung.
- `app/repository.py`: SQLite-Zugriffe und Schema-Migration.
- `mock-data/`: Beispielrequests, ungültiger Request und Bestellungen.
- `examples/demo.py`: ausführbarer Client für die Vorführung.
- `tests/test_api.py`: HTTP-Integrationstests und Migrationstest.
- `../.vscode/settings.json`: Interpreter, Importsuchpfad und Test-Erkennung.

Der Dienst ist lokal ohne Authentifizierung ausgelegt. gRPC, Message Broker,
ERP-Anbindung, tatsächliche Erstattung und KPI-Berechnung gehören zu anderen
Komponenten bzw. späteren Integrationen. Das Setzen von `REFUNDED` dokumentiert
hier nur einen Status; es löst keine Zahlung aus.

## Umsetzungshinweis

Initiale Implementierung und Dokumentation am 01.11.2026 mit OpenAI Codex erstellt.
Am 02.11.2026 wurden nach Abgleich mit der Aufgabenstellung Bestellabruf,
Statusverwaltung, Statusfilter, Datenbankmigration, Demo und Tests mit Codex ergänzt.
Die README wurde anschließend auf diese Funktionen und die VSCode-Einrichtung abgestimmt.
Für die Projektabgabe sollte die Gruppe ihre tatsächliche Prüfung, Anpassung und
Nutzung der KI-Unterstützung ergänzen.
