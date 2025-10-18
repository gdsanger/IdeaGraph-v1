# OpenAI API Integration für IdeaGraph

## Übersicht

Diese Integration ermöglicht die Nutzung der **OpenAI API** in IdeaGraph mit automatischem Fallback zu **KiGate-Agenten**, falls diese verfügbar sind.

## Features

- ✅ Direkte OpenAI API Anfragen mit GPT-4 und anderen Modellen
- ✅ Automatisches Routing zu KiGate-Agenten wenn verfügbar
- ✅ Strukturierte Fehlerbehandlung und Logging
- ✅ REST API Endpunkte für externe Integration
- ✅ Comprehensive Unit Tests (25 Tests)
- ✅ Keine Sicherheitslücken (CodeQL geprüft)

## Konfiguration

### Settings Model Erweiterung

Die folgenden Felder wurden zur `Settings` Entität hinzugefügt:

```python
openai_api_enabled = BooleanField(default=False)
openai_api_key = CharField(max_length=255)
openai_org_id = CharField(max_length=255)  # Optional
openai_default_model = CharField(max_length=100, default='gpt-4')
openai_api_base_url = CharField(max_length=255, default='https://api.openai.com/v1')
openai_api_timeout = IntegerField(default=30)
```

### Konfigurationsbeispiel

```python
from main.models import Settings

# Erstelle oder aktualisiere Settings
settings = Settings.objects.first()
settings.openai_api_enabled = True
settings.openai_api_key = 'sk-your-api-key-here'
settings.openai_org_id = 'org-your-org-id'  # Optional
settings.openai_default_model = 'gpt-4'
settings.save()
```

## Verwendung

### 1. Direkte OpenAI Anfrage

```python
from core.services.openai_service import OpenAIService

openai_service = OpenAIService()

response = openai_service.query(
    prompt="Erkläre kurz, was ein neuronales Netzwerk ist.",
    user_id="christian.angermeier@isartec.de"
)

print(response["result"])
print(f"Tokens verwendet: {response['tokens_used']}")
print(f"Modell: {response['model']}")
print(f"Quelle: {response['source']}")  # 'openai'
```

### 2. Anfrage mit KiGate Agent (Fallback zu OpenAI)

```python
response = openai_service.query_with_agent(
    prompt="Optimiere folgenden Text: Das haus ist alt aber schön.",
    agent_name="text-optimization-agent",
    user_id="christian.angermeier@isartec.de"
)

print(response["result"])
print(f"Quelle: {response['source']}")  # 'kigate' oder 'openai'
if 'agent' in response:
    print(f"Agent verwendet: {response['agent']}")
```

### 3. Verfügbare Modelle abrufen

```python
response = openai_service.get_models()

for model in response['models']:
    print(f"- {model['id']}")
```

### 4. Erweiterte Parameter

```python
response = openai_service.query(
    prompt="Schreibe einen Artikel über KI.",
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=1000,
    user_id="user@example.com"
)
```

## REST API Endpunkte

### POST /api/openai/query

Führt eine KI-Anfrage aus (direkt oder über KiGate).

**Request Body:**
```json
{
  "prompt": "Was ist maschinelles Lernen?",
  "model": "gpt-4",
  "user_id": "user@example.com",
  "agent_name": "text-optimization-agent",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "success": true,
  "result": "Maschinelles Lernen ist...",
  "tokens_used": 150,
  "model": "gpt-4",
  "source": "openai"
}
```

**Authentifizierung:**
```bash
curl -X POST http://localhost:8000/api/openai/query \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Erkläre KI in einfachen Worten"
  }'
```

### GET /api/openai/models

Listet verfügbare OpenAI Modelle auf.

**Response:**
```json
{
  "success": true,
  "models": [
    {
      "id": "gpt-4",
      "object": "model",
      "owned_by": "openai"
    },
    {
      "id": "gpt-3.5-turbo",
      "object": "model",
      "owned_by": "openai"
    }
  ]
}
```

**Authentifizierung:**
```bash
curl -X GET http://localhost:8000/api/openai/models \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Fehlerbehandlung

### Strukturierte Fehlerantworten

```json
{
  "success": false,
  "error": "OpenAI API request failed with status 401",
  "details": "Invalid API key"
}
```

### HTTP Status Codes

| Code | Bedeutung |
|------|-----------|
| 200 | Erfolgreiche Anfrage |
| 400 | Ungültige Parameter (z.B. fehlender prompt) |
| 401 | Ungültiger API Key oder fehlende Authentifizierung |
| 408 | Request Timeout |
| 429 | Rate Limit überschritten |
| 500 | Interner Serverfehler |
| 503 | Verbindungsfehler zu OpenAI API |

### Exception Handling

```python
from core.services.openai_service import OpenAIService, OpenAIServiceError

try:
    openai_service = OpenAIService()
    response = openai_service.query(prompt="Test")
except OpenAIServiceError as e:
    print(f"Fehler: {e.message}")
    print(f"Status Code: {e.status_code}")
    print(f"Details: {e.details}")
```

## KiGate Integration

### Automatisches Agent Routing

Wenn `kigate_api_enabled=True` in den Settings:

1. Service prüft, ob ein KiGate Agent mit dem angegebenen Namen existiert
2. Falls ja → Anfrage wird über KiGate geleitet
3. Falls nein → Automatischer Fallback zu direkter OpenAI API
4. Bei KiGate Fehlern → Fallback zu OpenAI API

```python
# KiGate Agent wird verwendet, falls vorhanden
response = openai_service.query_with_agent(
    prompt="Übersetze ins Englische: Guten Tag",
    agent_name="translation-agent",
    user_id="user@example.com"
)

if response['source'] == 'kigate':
    print("KiGate Agent wurde verwendet")
else:
    print("Fallback zu OpenAI API erfolgt")
```

## Logging

Alle Anfragen werden geloggt:

```
INFO: Querying OpenAI with model: gpt-4, user: user@example.com
INFO: Query successful. Tokens used: 150
INFO: Found KiGate agent: text-optimization-agent
INFO: Routing to KiGate agent: text-optimization-agent
```

Log-Datei: `openai_service.log` (wenn konfiguriert)

## Tests

### Unit Tests ausführen

```bash
python manage.py test main.test_openai_service
```

**Test Coverage:**
- Service Initialisierung
- Direkte OpenAI Anfragen
- KiGate Agent Routing
- Fehlerbehandlung (Timeout, Connection Error, API Errors)
- API Endpunkte
- Authentifizierung

Alle Tests: ✅ 25/25 passing

### Integration Tests

```bash
python manage.py test main
```

Alle Tests: ✅ 145/145 passing

## Sicherheit

### CodeQL Analyse

✅ Keine Sicherheitslücken gefunden

### Best Practices

- ✅ API Keys werden sicher in der Datenbank gespeichert
- ✅ Authentifizierung über JWT Token erforderlich
- ✅ Timeout-Schutz (30 Sekunden Standard)
- ✅ Structured Error Handling
- ✅ Input Validation
- ✅ Keine Secrets in Logs

## Architektur

### Komponenten

```
┌─────────────────────────────────────────────┐
│           IdeaGraph Application              │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│          OpenAIService (Core)                │
│  - query()                                   │
│  - query_with_agent()                        │
│  - get_models()                              │
└─────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│   OpenAI API     │   │  KiGate Service  │
│   (Direct)       │   │  (Fallback)      │
└──────────────────┘   └──────────────────┘
```

### Ablauf bei query_with_agent()

```
1. Check: Ist KiGate aktiviert?
   ├─ Nein → Direkt zu OpenAI API
   └─ Ja → Weiter zu 2.

2. Check: Existiert KiGate Agent?
   ├─ Nein → Fallback zu OpenAI API
   └─ Ja → Weiter zu 3.

3. Execute: KiGate Agent ausführen
   ├─ Erfolg → Ergebnis von KiGate zurückgeben
   └─ Fehler → Fallback zu OpenAI API

4. Return: Strukturierte Antwort mit source='kigate' oder 'openai'
```

## Beispiele

Siehe `/tmp/openai_service_examples.py` für vollständige Verwendungsbeispiele.

## Migration

Die Migration `0007_settings_openai_api_base_url_and_more.py` fügt die neuen Felder hinzu:

```bash
python manage.py migrate
```

## Unterstützte Modelle

Standard: `gpt-4`

Weitere Modelle (konfigurierbar):
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo
- Alle von OpenAI verfügbaren GPT-Modelle

## Performance

- **Timeout:** 30 Sekunden (konfigurierbar)
- **Retry Logic:** Automatischer Fallback zu OpenAI bei KiGate Fehlern
- **Async Support:** Vorbereitet für zukünftige async Integration

## Roadmap

Zukünftige Erweiterungen:
- [ ] Streaming Support für lange Antworten
- [ ] Caching für häufige Anfragen
- [ ] Rate Limiting
- [ ] Batch Processing
- [ ] Custom Agent Configuration UI

## Support

Bei Fragen oder Problemen:
- **Autor:** Christian Angermeier
- **Email:** ca@angermeier.net
- **Datum:** 2025-10-17

## Lizenz

Teil des IdeaGraph Projekts
