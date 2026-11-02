# ShopEasy REST API

<!-- Hinweis: Dieses Dokument wurde mithilfe von KI auf Basis des vorhandenen Programmcodes generiert.-->

Eigenständige Komponente für Sprint 2 des DvG-Projekts. Die FastAPI-Anwendung
nimmt Retourenanmeldungen eines simulierten Marketplaces entgegen und stellt
sie zum Abruf bereit. Ein Request enthält genau einen Artikel.

Der Marketplace ist der aufrufende Client, ShopEasy stellt die empfangende API
bereit. `examples/demo.py` übernimmt für die Vorführung die Rolle des Marketplaces.
Amazon und Zalando werden durch ein gemeinsames vereinfachtes JSON-Format
abgebildet; die Formate ihrer echten APIs werden nicht nachgebildet.

## Starten

Zielversion ist **Python 3.15.2**, die am 01.11.2026 aktuellste stabile Version.
Die Version steht zusätzlich in `.python-version`; die Projektmetadaten verlangen
Python 3.15.2 oder neuer innerhalb von Python 3.15.
Quelle: [Python.org, Release 3.15.2](https://www.python.org/downloads/release/python-3152/).

Alle folgenden Befehle werden im Komponentenordner `rest-api` ausgeführt.
Eine Aktivierung der virtuellen Umgebung ist nicht erforderlich.

### Windows / PowerShell

Python 3.15 muss installiert und über `py` erreichbar sein:

```powershell
cd rest-api
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Die ausgegebene Python-Version muss mindestens 3.15.2 sein. Falls `py` nicht
vorhanden ist, kann stattdessen der vollständige Pfad zu Python 3.15.2 verwendet
werden. Die Anwendung bindet für die lokale Demonstration an `127.0.0.1`.

### Linux / macOS

```bash
cd rest-api
python3.15 -m venv .venv
.venv/bin/python --version
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Danach sind erreichbar:

- Interaktive API-Dokumentation: <http://127.0.0.1:8000/docs>
- Alternative Dokumentation: <http://127.0.0.1:8000/redoc>
- OpenAPI-Schema: <http://127.0.0.1:8000/openapi.json>
- Erreichbarkeitsprüfung: <http://127.0.0.1:8000/health>

Mit `Strg+C` wird der Server beendet. `--reload` ist für die lokale Entwicklung.

## Funktionen

| Methode | Pfad | Funktion | Erfolg |
| --- | --- | --- | --- |
| `POST` | `/api/v1/returns` | Eine Retourenanmeldung validieren und speichern | `201 Created` |
| `GET` | `/api/v1/returns` | Gespeicherte Anmeldungen auflisten und filtern | `200 OK` |
| `GET` | `/api/v1/returns/{return_id}` | Eine Anmeldung anhand ihrer UUID abrufen | `200 OK` |
| `GET` | `/health` | Erreichbarkeit der gestarteten Anwendung prüfen | `200 OK` |

Beim Anlegen erzeugt die Komponente eine UUID als `id` und den Eingangszeitpunkt
`received_at`. Der `Location`-Header enthält die URL der angelegten Ressource.
Ein `201` bestätigt die Speicherung der Anmeldung, keine fachliche Annahme der
zurückgesendeten Ware.

Die Liste liefert `items`, `total`, `limit` und `offset`, sortiert nach
Eingangszeitpunkt absteigend. `total` zählt alle zu den Filtern passenden
Anmeldungen, unabhängig von der aktuellen Seite.

| Query-Parameter | Bedeutung | Standard / Grenzen |
| --- | --- | --- |
| `marketplace` | Nach `amazon` oder `zalando` filtern | Optional, kleingeschrieben |
| `order_id` | Exakt nach Bestellnummer filtern | Optional, 1–100 Zeichen |
| `limit` | Maximale Anzahl pro Seite | 20, erlaubt: 1–100 |
| `offset` | Anzahl zu überspringender Treffer | 0, mindestens 0 |

Beispiel: `GET /api/v1/returns?marketplace=amazon&limit=5&offset=0`.

## Datenformat und Validierung

Beispiel für den JSON-Body von `POST /api/v1/returns`:

```json
{
  "marketplace": "amazon",
  "order_id": "AMZ-2026-10001",
  "customer_reference": "AMZ-CUSTOMER-42",
  "item": {
    "sku": "SE-TSHIRT-BLUE-M",
    "name": "T-Shirt Blau, Größe M"
  },
  "return_reason": "Der Artikel ist zu klein.",
  "registered_at": "2026-10-28T10:30:00+01:00"
}
```

| Feld | Validierung |
| --- | --- |
| `marketplace` | Pflichtfeld; `amazon` oder `zalando`; im POST werden äußere Leerzeichen entfernt und Großbuchstaben normalisiert |
| `order_id` | Pflichtfeld; Text mit 1–100 Zeichen |
| `customer_reference` | Pflichtfeld; Text mit 1–100 Zeichen |
| `item` | Pflichtfeld; genau ein Objekt mit `sku` und `name`; keine Artikelliste |
| `item.sku` | Pflichtfeld; Artikelnummer mit 1–100 Zeichen |
| `item.name` | Pflichtfeld; Artikelbezeichnung mit 1–200 Zeichen |
| `return_reason` | Pflichtfeld; Freitext mit 1–1000 Zeichen |
| `registered_at` | Pflichtfeld; ISO-8601-Zeitstempel mit Zeitzone, höchstens aktueller Zeitpunkt |

Äußere Leerzeichen werden bei Textfeldern entfernt. Leere Texte und ausschließlich
aus Leerzeichen bestehende Texte werden abgewiesen. Unbekannte Felder werden auf
beiden Objektebenen abgewiesen. Zahlen werden nicht als Textreferenzen akzeptiert.
Eine Menge ist nicht vorgesehen: Jede Anmeldung betrifft ein einzelnes Stück.

Anmeldezeitpunkte benötigen eine Zeitzone (`Z` oder beispielsweise `+01:00`).
Ein reines Datum, ein zeitzonenloser Zeitpunkt oder ein numerischer Unix-Zeitstempel
reichen nicht aus. Gültige Zeitpunkte werden nach UTC normalisiert.
`registered_at` bezeichnet die Anmeldung beim Marketplace; `received_at` bezeichnet
den Eingang bei ShopEasy. `id` und `received_at` werden ausschließlich vom Server
vergeben und gehören nicht in den Request.

Die Prüfung ist eine Struktur- und Plausibilitätsprüfung. Es gibt derzeit keine
Anbindung an Bestellungen oder Kundenstammdaten; daher werden weder die Existenz
einer Bestellung noch eine Retourenfrist oder ein Erstattungsanspruch geprüft.
Jeder gültige POST erzeugt eine neue Anmeldung, auch bei identischem Inhalt.
Eine spätere Dublettenerkennung sollte mit einer externen Meldungs-ID oder einem
Idempotency-Key vereinbart werden.

### Fehlerantworten

- `422 Unprocessable Entity`: ungültige Felder, fehlende Pflichtfelder, ungültige
  UUID oder ungültige Query-Parameter. Die FastAPI-Antwort enthält unter `detail`
  eine Liste mit Feldpfad (`loc`), Fehlermeldung (`msg`) und Fehlertyp (`type`).
- `404 Not Found`: syntaktisch gültige UUID ohne gespeicherte Anmeldung.
  Antwort: `{"detail": "Retourenanmeldung nicht gefunden"}`.

Bei einer ungültigen Anmeldung wird nichts gespeichert. Das Demo-Dokument
`mock-data/invalid-return.json` zeigt mehrere Validierungsfehler gleichzeitig.

## Beispielausführung

Der Server muss bereits in einem ersten Terminal laufen. In einem zweiten
PowerShell-Terminal, ebenfalls im Ordner `rest-api`:

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/demo.py
```

Unter Linux/macOS:

```bash
.venv/bin/python -X utf8 examples/demo.py
```

Das Skript verwendet nur die Python-Standardbibliothek und führt aus:

1. Erreichbarkeitsprüfung mit `GET /health` → `200`.
2. Amazon-Beispiel als neue Anmeldung senden → `201`.
3. Die erzeugte Amazon-Anmeldung über ihre UUID abrufen → `200`.
4. Zalando-Beispiel senden und über seine UUID abrufen → `201`, `200`.
5. Nach Amazon-Anmeldungen filtern → `200`.
6. Das bewusst ungültige Beispiel senden → `422`.
7. Eine unbekannte UUID abrufen → `404`.

Das Skript gibt die tatsächlichen Antwortdaten aus. Bei einem unerwarteten
HTTP-Status oder einem nicht erreichbaren Server endet es mit einer Fehlermeldung.
UUIDs und Eingangszeitpunkte ändern sich bei jeder Ausführung. Jede vollständige
Ausführung legt zwei neue Meldungen an. Die JSON-Dateien werden nicht automatisch
beim Serverstart importiert; sie sind vorbereitete Requests des Demo-Marketplaces.

Eine vollständig ausgeführte Demonstration mit Python 3.15.2 vom 01.11.2026 ist
in [examples/demo-output.txt](examples/demo-output.txt) protokolliert. Die
Erfolgscodes `200` und `201` sowie die erwarteten Fehler `422` und `404` wurden
dabei über echte lokale HTTP-Aufrufe erreicht.

Ein abweichender Server ist über `--base-url http://127.0.0.1:8001` einstellbar.
Es ist keine automatisierte Testsuite enthalten.

Ein einzelner Aufruf ist auch direkt in PowerShell möglich:

```powershell
$payload = Get-Content -LiteralPath .\mock-data\amazon-return.json -Raw -Encoding utf8
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/returns `
  -ContentType 'application/json; charset=utf-8' `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
```

## Speicherung und Konfiguration

Die Anwendung legt beim ersten Start `data/returns.sqlite3` an. SQLite gehört
zur Python-Standardbibliothek; ein eigener Datenbankserver ist nicht erforderlich.
Gespeicherte Anmeldungen bleiben nach Neustarts erhalten. Die Datenbank und die
virtuelle Umgebung sind durch `.gitignore` vom späteren Repository ausgeschlossen.

Ein anderer Datenbankpfad kann vor dem Serverstart gesetzt werden:

```powershell
$env:REST_API_DB_PATH = 'data/demo.sqlite3'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Unter Linux/macOS: `REST_API_DB_PATH=data/demo.sqlite3 .venv/bin/python -m uvicorn app.main:app`.
Relative Datenbankpfade beziehen sich stets auf den Komponentenordner `rest-api`.
Zum Wiederholen der Demo mit leerem Bestand kann ein neuer Datenbankpfad gewählt
werden. Der Server erstellt die Datei automatisch. Es gibt keinen Lösch-Endpunkt.

## Aufbau und spätere Erweiterung

```text
rest-api/
├── app/
│   ├── main.py           # App-Factory, Konfiguration und Lebenszyklus
│   ├── models.py         # Eingabe-/Ausgabemodelle und Validierung
│   ├── routes.py         # HTTP-Endpunkte und Dependency Injection
│   ├── service.py        # Verarbeitung validierter Anmeldungen
│   └── repository.py     # SQLite-Zugriff
├── mock-data/
│   ├── amazon-return.json
│   ├── zalando-return.json
│   └── invalid-return.json
├── examples/
│   ├── demo.py           # Beispielaufrufe eines simulierten Marketplaces
│   └── demo-output.txt   # Protokoll einer tatsächlichen Beispielausführung
├── .python-version
├── pyproject.toml
├── requirements.txt
└── README.md
```

Der Komponentenordner kann später unverändert in das gemeinsame Projekt
übernommen werden. Er benötigt keine Dateien der anderen Sprint-2-Komponenten.
`create_app()` verdrahtet Repository, Service und HTTP-Schicht. Spätere
Integrationen können an der Service-Schicht ergänzt werden; die Transportlogik
und die Datenbankzugriffe sind getrennt. Die API ist über `/api/v1` versioniert.

Der Bezug zum Sprint-1-Soll-Prozess ist der Eingang über das Marktplatz-Tool mit
anschließender Normalisierung und Validierung. Die erzeugte Retouren-ID kann
später als gemeinsame Referenz verwendet werden. Ungültige Anmeldungen werden
hier mit konkreten Fehlern zurückgegeben; das Anfordern fehlender Daten und die
weitere Prozesssteuerung werden in dieser Komponente nicht umgesetzt.

Die beiden Zeitstempel schaffen eine Grundlage für spätere zeitbezogene
Auswertungen. Für eine vollständige Durchlaufzeit bis zur Erstattung fehlen
die nachgelagerten Ereignisse. KPI-Berechnung ist kein Bestandteil dieser API.

gRPC, Message Broker, ERP-Anbindung, Labelerstellung, Zustandsprüfung und
Erstattung sind außerhalb des aktuellen Umfangs. Der lokale Mock besitzt keine
Authentifizierung und ist für die Vorführung auf dem eigenen Rechner ausgelegt.

## Umsetzungshinweis

Die initiale Implementierung und Dokumentation wurden am 01.11.2026 mit
Unterstützung von OpenAI Codex erstellt. Für die Projektabgabe sollte die Gruppe
ihre tatsächliche Prüfung, Anpassung und Nutzung der KI-Unterstützung ergänzen.
