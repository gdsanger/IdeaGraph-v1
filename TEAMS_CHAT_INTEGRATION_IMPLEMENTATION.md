# Teams Kontextbezogener Chat und automatische Task-Ableitung - Implementierung

## Übersicht

Diese Implementierung ermöglicht es IdeaGraph, Microsoft Teams als primären Kommunikationsraum zu nutzen. Das System überwacht Teams-Kanäle auf neue Nachrichten, analysiert diese mit KI und erstellt automatisch Tasks basierend auf den Anforderungen.

## Komponenten

### 1. Datenbankmodelle

**Neue Felder in Settings:**
- `graph_poll_interval` (IntegerField, default: 60): Intervall in Sekunden für das Polling von Teams-Kanälen

**Neue Felder in Task:**
- `message_id` (CharField): ID der Teams-Nachricht, die den Task ausgelöst hat

### 2. GraphService Erweiterung

**Neue Methoden:**
- `get_channel_messages(team_id, channel_id, top=50)`: Ruft Nachrichten aus einem Teams-Kanal ab
- `post_channel_message(team_id, channel_id, message_content)`: Sendet eine Nachricht an einen Teams-Kanal

### 3. Neue Services

#### TeamsListenerService
**Zweck:** Überwacht Teams-Kanäle auf neue Nachrichten

**Funktionen:**
- `get_items_with_channels()`: Findet alle Items mit konfigurierten Teams-Kanälen
- `get_new_messages_for_item(item)`: Holt neue Nachrichten für ein Item
  - Filtert Nachrichten vom IdeaGraph Bot aus
  - Prüft, ob bereits Tasks für Nachrichten existieren
- `poll_all_channels()`: Durchläuft alle konfigurierten Kanäle

#### MessageProcessingService
**Zweck:** Analysiert Nachrichten mit KI und erstellt Tasks

**Funktionen:**
- `extract_message_content(message)`: Extrahiert Text aus Teams-Nachrichten (HTML/Plain Text)
- `get_or_create_user_from_upn(upn, display_name)`: Erstellt Benutzer automatisch aus UPN
  - Extrahiert Vor- und Nachname aus Display Name
  - Setzt Rolle auf 'user' und auth_type auf 'msauth'
- `search_similar_context(query_text, item_id, max_results)`: **NEU** - Sucht ähnliche Objekte in Weaviate (RAG)
  - Durchsucht Tasks und Items nach semantisch ähnlichen Inhalten
  - Liefert max. 3 relevante Treffer mit Metadaten
  - Graceful Degradation: Funktioniert auch ohne Weaviate
- `analyze_message(message, item)`: Analysiert Nachricht mit KIGate Agent `teams-support-analysis-agent`
  - **Verwendet RAG-Kontext:** Sucht ähnliche Tasks/Items in Weaviate
  - Reichert AI-Prompt mit relevanten historischen Informationen an
  - Liefert kontextbasierte, informierte Antworten
- `_should_create_task(ai_response)`: Bestimmt, ob ein Task erstellt werden soll
- `create_task_from_analysis(item, message, analysis_result)`: Erstellt Task mit AI-Response und Original-Nachricht

#### GraphResponseService
**Zweck:** Sendet AI-generierte Antworten zurück an Teams

**Funktionen:**
- `post_response(channel_id, response_content, task_created, task_url)`: Postet Antwort mit optionalem Task-Link
- `_format_text_to_html(text)`: Konvertiert Plain Text zu HTML für Teams

#### WeaviateConversationSyncService
**Zweck:** Speichert Konversationen in Weaviate

**Funktionen:**
- `sync_conversation(message_content, ai_response, item_id, item_title, created_by)`: Speichert Konversation als KnowledgeObject (type: "conversation")

#### TeamsIntegrationService
**Zweck:** Orchestriert den gesamten Workflow

**Funktionen:**
- `process_message(item, message)`: Verarbeitet eine einzelne Nachricht
  1. Analysiert mit AI
  2. Erstellt Task bei Bedarf
  3. Sendet Antwort an Teams
  4. Synchronisiert mit Weaviate
- `poll_and_process()`: Führt kompletten Polling-Zyklus aus

### 4. Management Command

**Command:** `python manage.py poll_teams_messages`

**Optionen:**
- `--once`: Einmaliger Poll statt kontinuierlich
- `--interval SECONDS`: Überschreibt Poll-Intervall aus Settings

**Verwendung:**
```bash
# Kontinuierliches Polling (empfohlen für Cron/Systemd)
python manage.py poll_teams_messages

# Einmaliger Test-Durchlauf
python manage.py poll_teams_messages --once

# Mit spezifischem Intervall (300 Sekunden = 5 Minuten)
python manage.py poll_teams_messages --interval 300
```

### 5. API Endpoints

#### POST /api/teams/poll
**Zweck:** Manuelles Auslösen des Polling (Admin nur)

**Authentifizierung:** Bearer Token (Admin-Rolle erforderlich)

**Response:**
```json
{
  "success": true,
  "result": {
    "items_checked": 5,
    "messages_found": 10,
    "messages_processed": 8,
    "tasks_created": 3,
    "responses_posted": 8,
    "errors": 0
  }
}
```

#### GET /api/teams/status
**Zweck:** Status der Teams-Integration abrufen

**Authentifizierung:** Bearer Token (alle Rollen)

**Response:**
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "team_id": "abc123...",
    "poll_interval": 60,
    "items_with_channels": 12,
    "tasks_from_teams": 45
  }
}
```

## Workflow

### 1. Nachricht empfangen
1. Benutzer sendet Nachricht in Teams-Kanal
2. `TeamsListenerService` holt Nachricht über Graph API
3. Prüfung: Ist Nachricht von IdeaGraph Bot? → Überspringen
4. Prüfung: Existiert bereits Task für diese Message-ID? → Überspringen

### 2. Nachricht analysieren
1. `MessageProcessingService` extrahiert Nachrichteninhalt
2. **RAG-Kontext wird aus Weaviate geladen:**
   - Suche nach ähnlichen Tasks (max. 3 Treffer)
   - Suche nach ähnlichen Items (max. 3 Treffer)
   - Kombination der relevantesten Treffer
3. Kontext wird zusammengestellt (Item-Titel, -Beschreibung, Nachricht, **RAG-Kontext**)
4. KIGate Agent `teams-support-analysis-agent` analysiert Nachricht **mit RAG-Kontext**
5. AI-Response wird evaluiert: Task erstellen ja/nein?

### 3. Benutzer erstellen/finden
1. Prüfung auf existierenden Benutzer (UPN als username)
2. Falls nicht vorhanden: Automatische Erstellung
   - Username: UPN
   - Email: UPN
   - Vorname/Nachname: Aus Display Name extrahiert
   - Rolle: 'user'
   - Auth Type: 'msauth'

### 4. Task erstellen
Falls AI bestimmt, dass Task benötigt wird:
1. Task-Titel: Aus AI-Response extrahiert oder Standard
2. Task-Beschreibung: AI-Response + Original-Nachricht
3. Felder:
   - `item`: Zugehöriges Item
   - `requester`: Automatisch erstellter/gefundener Benutzer
   - `message_id`: Teams Message-ID
   - `ai_generated`: True
   - `status`: 'new'

### 5. Antwort senden
1. `GraphResponseService` formatiert AI-Response als HTML
2. Bei erstelltem Task: Link zum Task hinzufügen
3. Nachricht wird an Teams-Kanal gesendet

### 6. Weaviate-Synchronisation
1. `WeaviateConversationSyncService` speichert Konversation
2. KnowledgeObject Properties:
   - `title`: Erster Satz der Nachricht (max. 100 Zeichen)
   - `description`: Kombinierte Original-Nachricht + AI-Response
   - `type`: 'conversation'
   - `source`: 'Teams'
   - `related_item`: Item-UUID
   - `created_by`: UPN des Benutzers

## Konfiguration

### RAG-Funktionalität (Retrieval-Augmented Generation)

**NEU:** Der MessageProcessingService nutzt jetzt RAG, um Nachrichten mit historischem Kontext zu analysieren.

#### Funktionsweise
1. **Semantische Suche:** Bei jeder Nachricht wird Weaviate nach ähnlichen Tasks und Items durchsucht
2. **Kontext-Anreicherung:** Die Top-3 ähnlichsten Objekte werden dem AI-Prompt hinzugefügt
3. **Informierte Antworten:** Der KIGate-Agent kann auf historische Lösungen zurückgreifen
4. **Graceful Degradation:** Funktioniert auch ohne Weaviate (RAG wird übersprungen)

#### Beispiel
**Benutzer-Nachricht:** "Login funktioniert nicht"

**RAG findet ähnlichen Task:** "Login-Problem behoben durch Auth-Modul-Update"

**AI-Antwort:** "Basierend auf einem ähnlichen Problem empfehle ich, das Auth-Modul zu prüfen. Ein Update könnte helfen."

#### Vorteile
- ✅ Bessere, kontextbasierte Antworten
- ✅ Lernt aus historischen Tasks
- ✅ Reduziert doppelte Task-Erstellung
- ✅ Konsistente Lösungsvorschläge

### Voraussetzungen
1. **Graph API aktiviert** in Settings
2. **Teams Integration aktiviert** in Settings
3. **Teams Team ID** konfiguriert
4. **KIGate API aktiviert** und `teams-support-analysis-agent` verfügbar
5. **Weaviate konfiguriert** (optional, aber empfohlen für RAG-Funktionalität)
   - Lokale Instanz: localhost:8081
   - Cloud: Weaviate Cloud mit API-Key
   - RAG funktioniert auch ohne Weaviate (Graceful Degradation)

### Azure AD Berechtigungen
Folgende Berechtigungen werden benötigt:
- `Channel.ReadBasic.All`: Lesen von Kanälen
- `ChannelMessage.Read.All`: Lesen von Nachrichten
- `ChannelMessage.Send`: Senden von Nachrichten
- `User.Read.All`: Lesen von Benutzerinformationen

### Settings-Felder
```python
teams_enabled = True
teams_team_id = "abc123..."
graph_poll_interval = 60  # Sekunden
graph_api_enabled = True
kigate_api_enabled = True
```

## Tests

### Test-Coverage: 23 Tests (alle bestanden)

**TeamsListenerServiceTestCase:**
- Initialisierung mit deaktiviertem Teams
- Items mit Kanälen abrufen
- Filterung von Bot-Nachrichten
- Filterung von bereits verarbeiteten Nachrichten

**MessageProcessingServiceTestCase:**
- Extrahieren von Plain Text und HTML
- Benutzer-Erstellung/Abruf via UPN
- Task-Erstellung basierend auf AI-Response
- Erkennung, ob Task erstellt werden soll

**MessageProcessingServiceRAGTestCase:** **NEU**
- RAG-Kontext-Suche mit erfolgreichen Ergebnissen
- RAG-Kontext-Suche ohne Ergebnisse
- RAG-Funktion bei Weaviate-Ausfall (Graceful Degradation)
- Nachrichtenanalyse mit RAG-Kontext-Anreicherung
- Formatierung von RAG-Kontext für AI-Prompt
- Leerer RAG-Kontext

**TeamsIntegrationAPITestCase:**
- Status-Endpoint Authentifizierung
- Poll-Endpoint nur für Admins
- Erfolgreiche Polling-Durchführung

**TeamsManagementCommandTestCase:**
- Einmaliger Command-Durchlauf

## Deployment

### Option 1: Cron Job
```bash
# Alle 5 Minuten ausführen
*/5 * * * * cd /path/to/IdeaGraph && python manage.py poll_teams_messages --once
```

### Option 2: Systemd Service
```ini
[Unit]
Description=IdeaGraph Teams Integration Polling
After=network.target

[Service]
Type=simple
User=ideagraph
WorkingDirectory=/path/to/IdeaGraph
ExecStart=/path/to/venv/bin/python manage.py poll_teams_messages
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Option 3: Supervisor
```ini
[program:ideagraph-teams]
command=/path/to/venv/bin/python manage.py poll_teams_messages
directory=/path/to/IdeaGraph
user=ideagraph
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ideagraph-teams.log
```

## Sicherheit

### Botschutz
- Nachrichten vom "IdeaGraph Bot" werden automatisch gefiltert
- Verhindert Endlosschleifen

### Duplikatprävention
- Message-ID wird in Task gespeichert
- Doppelte Verarbeitung wird verhindert

### Authentifizierung
- API-Endpoints erfordern JWT-Token
- Poll-Endpoint nur für Admins
- Graph API verwendet OAuth2 Client Credentials Flow

### Datenschutz
- Benutzer werden nur bei Bedarf erstellt
- UPN wird als Identifikator verwendet
- Keine Passwörter für MS-Auth-Benutzer

## Logging

Alle Services loggen ihre Aktivitäten:
- `teams_listener_service`: Polling-Aktivitäten
- `message_processing_service`: Analyse und Task-Erstellung
- `graph_response_service`: Antworten an Teams
- `weaviate_conversation_sync_service`: Weaviate-Sync
- `teams_integration_service`: Orchestrierung

Log-Level: INFO für normale Operationen, ERROR für Fehler

## Fehlerbehebung

### Problem: Keine Nachrichten werden abgeholt
**Lösung:**
- Prüfen: Teams Integration in Settings aktiviert?
- Prüfen: Team ID korrekt konfiguriert?
- Prüfen: Items haben Channel-IDs?
- Prüfen: Graph API Berechtigungen korrekt?

### Problem: Tasks werden nicht erstellt
**Lösung:**
- Prüfen: KIGate API aktiviert und erreichbar?
- Prüfen: Agent `teams-support-analysis-agent` existiert?
- Prüfen: AI-Response wird korrekt evaluiert?
- Log-Dateien auf Fehlermeldungen prüfen

### Problem: Antworten kommen nicht in Teams an
**Lösung:**
- Prüfen: Graph API Berechtigung `ChannelMessage.Send`?
- Prüfen: Bot-Name korrekt konfiguriert?
- Log-Dateien auf API-Fehler prüfen

### Problem: Duplikate werden erstellt
**Lösung:**
- Prüfen: Message-ID wird korrekt gespeichert?
- Datenbank-Konsistenz prüfen
- Logs auf mehrfache Verarbeitung prüfen

## Erweiterungsmöglichkeiten

### Zukünftige Features
1. **Mehrsprachigkeit**: AI-Analyse in verschiedenen Sprachen
2. **Prioritätserkennung**: Automatische Task-Priorität basierend auf Dringlichkeit
3. **Eskalation**: Automatische Zuweisung basierend auf Komplexität
4. **Statusupdates**: Automatische Updates in Teams bei Task-Änderungen
5. **Mentions**: Benachrichtigungen über @mentions
6. **Attachments**: Verarbeitung von Dateianhängen
7. **Reactions**: Reaktionen als Feedback-Mechanismus

## Migration und Updates

Bei zukünftigen Updates:
1. Migrationen ausführen: `python manage.py migrate`
2. Tests ausführen: `python manage.py test main.test_teams_message_integration`
3. Service neu starten (bei Systemd/Supervisor)
4. Logs überwachen auf Fehler

## Support

Bei Fragen oder Problemen:
1. Logs prüfen: `/var/log/ideagraph-teams.log` (oder configured log location)
2. Tests ausführen für Diagnostik
3. API-Endpoints testen mit `/api/teams/status`
4. Graph Explorer verwenden für API-Debugging: https://developer.microsoft.com/graph/graph-explorer
