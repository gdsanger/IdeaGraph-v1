# Web Search Adapter Debugging Guide

## Übersicht

Diese Anleitung beschreibt die erweiterten Debugging-Funktionen für den `web_search_adapter`, die implementiert wurden, um Probleme mit der Google Search API und Brave Search API besser zu diagnostizieren.

## Problem

Der `web_search_adapter` zeigte zuvor nur generische Fehlermeldungen wie:
```
[WARNING] [web_search_adapter] - Google search failed: Google Search failed
```

Dies machte es schwierig, die genaue Ursache von Problemen zu identifizieren.

## Lösung

Es wurden umfassende Logging-Funktionen hinzugefügt, die detaillierte Informationen über:
- API-Konfiguration
- HTTP-Anfragen und -Antworten
- Fehlermeldungen und -details
- Ausnahmen mit vollständigen Tracebacks

bereitstellen.

## Debugging-Features

### 1. Konfigurations-Logging (DEBUG-Level)

Bei der Initialisierung des `WebSearchAdapter` werden die Konfigurationsdetails geloggt:

```
[DEBUG] [web_search_adapter] - Google API Key configured: True (length: 39)
[DEBUG] [web_search_adapter] - Google CX configured: True (length: 21)
[DEBUG] [web_search_adapter] - Brave API Key configured: False
```

**Wichtig:** API-Keys werden niemals im Klartext geloggt, nur deren Vorhandensein und Länge.

### 2. Anfrage-Logging (DEBUG-Level)

Bei jeder Suchanfrage werden Details geloggt:

```
[INFO] [web_search_adapter] - Searching Google for: Integration und Evaluierung eines MCP-Servers
[DEBUG] [web_search_adapter] - Google Search request URL: https://www.googleapis.com/customsearch/v1
[DEBUG] [web_search_adapter] - Google Search params: cx=0123456789..., num=5
[DEBUG] [web_search_adapter] - Google Search response status: 200
```

### 3. Fehler-Logging (ERROR-Level)

Wenn ein Fehler auftritt, werden detaillierte Informationen geloggt:

#### HTTP-Fehler (z.B. 403 Forbidden)
```
[ERROR] [web_search_adapter] - Google Search API error (status 403): {"error": {...}}
[ERROR] [web_search_adapter] - Google API Error: API key not valid (reason: forbidden)
```

#### Timeout-Fehler
```
[ERROR] [web_search_adapter] - Google Search API timeout: Connection timeout after 10 seconds
```

#### JSON-Parse-Fehler
```
[ERROR] [web_search_adapter] - Failed to parse Google Search response as JSON: Expecting value: line 1 column 1 (char 0)
```

#### Unerwartete Ausnahmen
```
[ERROR] [web_search_adapter] - Unexpected error in Google Search: ValueError: Invalid parameter
[ERROR] [web_search_adapter] - Full traceback:
Traceback (most recent call last):
  File "...", line X, in search_google
    ...
ValueError: Invalid parameter
```

### 4. Warnungen (WARNING-Level)

Wenn die API keine Ergebnisse zurückgibt:

```
[WARNING] [web_search_adapter] - Google Search returned no items. Response keys: ['searchInformation', 'queries']
```

Wenn ein Provider fehlschlägt:

```
[WARNING] [web_search_adapter] - Google search failed: Google Search API returned status 403 - Details: API key not valid (reason: forbidden)
```

### 5. Fallback-Logging

Wenn Google fehlschlägt und Brave als Fallback verwendet wird:

```
[INFO] [web_search_adapter] - Google Search not configured, skipping
[INFO] [web_search_adapter] - Searching Brave for: ...
```

Wenn alle Provider fehlschlagen:

```
[ERROR] [web_search_adapter] - All search providers failed: Google: Google Search API returned status 403; Brave: Brave Search API not configured
```

## Logging-Level konfigurieren

Um detaillierte Debug-Informationen zu sehen, setzen Sie den Logging-Level in der Django-Konfiguration:

### In `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'web_search_adapter': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Oder 'INFO', 'WARNING', 'ERROR'
            'propagate': False,
        },
    },
}
```

## Häufige Fehlerszenarien und deren Diagnostik

### Szenario 1: "API key not valid"

**Fehlermeldung:**
```
[ERROR] [web_search_adapter] - Google API Error: API key not valid (reason: forbidden)
```

**Ursache:** Der API-Key ist ungültig oder wurde deaktiviert.

**Lösung:**
1. Überprüfen Sie den API-Key in den Einstellungen
2. Stellen Sie sicher, dass der API-Key für die Custom Search API aktiviert ist
3. Überprüfen Sie, ob der API-Key abgelaufen ist

### Szenario 2: "quotaExceeded"

**Fehlermeldung:**
```
[ERROR] [web_search_adapter] - Google API Error: Quota exceeded for quota metric 'Queries' (reason: quotaExceeded)
```

**Ursache:** Das tägliche Anfragekontingent wurde überschritten.

**Lösung:**
1. Warten Sie bis zum nächsten Tag
2. Erwägen Sie ein Upgrade des API-Plans
3. Konfigurieren Sie Brave Search als Fallback

### Szenario 3: "Invalid CX"

**Fehlermeldung:**
```
[ERROR] [web_search_adapter] - Google API Error: Invalid Value (reason: invalid)
```

**Ursache:** Die Search Engine ID (CX) ist ungültig.

**Lösung:**
1. Überprüfen Sie die CX in den Einstellungen
2. Stellen Sie sicher, dass die Custom Search Engine existiert
3. Überprüfen Sie die Berechtigung für die Search Engine

### Szenario 4: Timeout

**Fehlermeldung:**
```
[ERROR] [web_search_adapter] - Google Search API timeout: Connection timeout
```

**Ursache:** Die API-Anfrage dauert zu lange.

**Lösung:**
1. Überprüfen Sie die Netzwerkverbindung
2. Überprüfen Sie, ob die Google API erreichbar ist
3. Erhöhen Sie ggf. den Timeout-Wert

### Szenario 5: Keine Konfiguration

**Fehlermeldung:**
```
[ERROR] [web_search_adapter] - Google Search API credentials not configured
[ERROR] [web_search_adapter] - All search providers failed: No search provider configured
```

**Ursache:** Weder Google noch Brave API-Keys sind konfiguriert.

**Lösung:**
1. Fügen Sie die Google Search API-Credentials in den Einstellungen hinzu
2. Oder konfigurieren Sie die Brave Search API als Alternative

## Tests

Es wurden umfassende Tests hinzugefügt, um die Logging-Funktionalität zu überprüfen:

```bash
python manage.py test main.test_web_search_adapter_debug
```

Diese Tests validieren:
- Konfigurations-Logging
- Anfrage/Antwort-Logging
- Fehlerbehandlung für verschiedene Fehlertypen
- Fallback-Mechanismus
- Vollständige Exception-Tracebacks

## Weiterführende Informationen

- **Datei:** `core/services/web_search_adapter.py`
- **Tests:** `main/test_web_search_adapter_debug.py`
- **API-Dokumentation:** 
  - [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)
  - [Brave Search API](https://brave.com/search/api/)
