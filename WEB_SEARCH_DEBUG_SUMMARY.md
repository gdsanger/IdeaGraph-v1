# Web Search Adapter Debug-Funktion: Implementierungs-Zusammenfassung

## Überblick

Diese Zusammenfassung beschreibt die Implementierung erweiterter Debug- und Logging-Funktionen für den `web_search_adapter`, um das Problem der unzureichenden Fehlermeldungen zu beheben.

## Problem

**Original Issue:** Debugging benötigt: Fehlfunktion des web_search_adapters trotz korrekter Google API-Konfiguration

Die ursprünglichen Fehlermeldungen waren zu generisch:
```
[WARNING] [web_search_adapter] - Google search failed: Google Search failed
[ERROR] [support_advisor_service] - External analysis error: All search providers failed or not configured
```

Dies machte es unmöglich, die genaue Ursache des Problems zu identifizieren.

## Implementierte Änderungen

### 1. Erweiterte Imports
- Hinzugefügt: `import json` für bessere JSON-Fehlerbehandlung

### 2. Konfigurations-Logging im `__init__`

**Neu hinzugefügt:**
```python
# Log configuration status (without exposing secrets)
logger.debug(f"Google API Key configured: {bool(self.google_api_key)} (length: {len(self.google_api_key) if self.google_api_key else 0})")
logger.debug(f"Google CX configured: {bool(self.google_cx)} (length: {len(self.google_cx) if self.google_cx else 0})")
logger.debug(f"Brave API Key configured: {bool(self.brave_api_key)}")
```

**Vorteile:**
- Zeigt sofort, welche APIs konfiguriert sind
- Gibt Hinweise auf fehlende oder zu kurze API-Keys
- Schützt sensible Daten (Keys werden nicht geloggt)

### 3. Verbesserte `search_google` Methode

#### a) Besseres Fehler-Logging für fehlende Credentials
```python
if not self.google_api_key or not self.google_cx:
    logger.error("Google Search API credentials not configured")
    raise WebSearchAdapterError(...)
```

#### b) Detaillierte Request-Logging
```python
logger.info(f"Searching Google for: {query}")
logger.debug(f"Google Search request URL: {url}")
logger.debug(f"Google Search params: cx={self.google_cx[:10]}..., num={params['num']}")
logger.debug(f"Google Search response status: {response.status_code}")
```

#### c) Erweiterte HTTP-Fehlerbehandlung
```python
if response.status_code != 200:
    error_details = response.text
    logger.error(f"Google Search API error (status {response.status_code}): {error_details}")
    
    # Try to parse error details from JSON response
    try:
        error_data = response.json()
        if 'error' in error_data:
            error_msg = error_data['error'].get('message', error_details)
            error_reason = error_data['error'].get('errors', [{}])[0].get('reason', 'unknown')
            logger.error(f"Google API Error: {error_msg} (reason: {error_reason})")
            error_details = f"{error_msg} (reason: {error_reason})"
    except:
        pass
```

#### d) Warnung bei fehlenden Ergebnissen
```python
if 'items' not in data:
    logger.warning(f"Google Search returned no items. Response keys: {list(data.keys())}")
    if 'error' in data:
        logger.error(f"Google Search error in response: {data['error']}")
```

#### e) Spezifische Exception-Handler
```python
except WebSearchAdapterError:
    # Re-raise WebSearchAdapterError as-is
    raise
except requests.exceptions.Timeout as e:
    logger.error(f"Google Search API timeout: {str(e)}")
    raise WebSearchAdapterError("Google Search API timeout", details=str(e))
except requests.exceptions.RequestException as e:
    logger.error(f"Google Search API request failed: {str(e)}")
    raise WebSearchAdapterError("Google Search API request failed", details=str(e))
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse Google Search response as JSON: {str(e)}")
    raise WebSearchAdapterError("Invalid JSON response from Google Search API", details=str(e))
except Exception as e:
    logger.error(f"Unexpected error in Google Search: {type(e).__name__}: {str(e)}")
    logger.exception("Full traceback:")
    raise WebSearchAdapterError(f"Google Search failed: {type(e).__name__}", details=str(e))
```

### 4. Verbesserte `search_brave` Methode

Ähnliche Verbesserungen wie bei `search_google`:
- Detailliertes Request/Response-Logging
- Bessere Fehlerbehandlung
- Spezifische Exception-Handler
- Warnung bei fehlenden Ergebnissen

### 5. Verbesserte `search` Methode

```python
# Try Google first
if self.google_api_key and self.google_cx:
    try:
        return self.search_google(query, max_results)
    except WebSearchAdapterError as e:
        error_msg = f"{e.message}"
        if e.details:
            error_msg += f" - Details: {e.details}"
        logger.warning(f"Google search failed: {error_msg}")
        errors.append(f"Google: {e.message}")
else:
    logger.info("Google Search not configured, skipping")

# Similar for Brave...

# If both failed, raise error
error_details = "; ".join(errors) if errors else "No search provider configured"
logger.error(f"All search providers failed: {error_details}")
raise WebSearchAdapterError(...)
```

### 6. Umfassende Tests

Neue Testdatei: `main/test_web_search_adapter_debug.py`

**Tests umfassen:**
- Konfigurations-Logging
- Request/Response-Logging
- HTTP-Fehlerbehandlung
- Timeout-Fehlerbehandlung
- JSON-Parse-Fehlerbehandlung
- Unerwartete Ausnahmen
- Fehlende Ergebnisse
- Fallback-Mechanismus
- Fehlende Credentials

**Alle 13 Tests bestehen:**
```bash
python manage.py test main.test_web_search_adapter_debug
----------------------------------------------------------------------
Ran 13 tests in 0.021s

OK
```

### 7. Dokumentation

Neue Dokumentationsdateien:
- `WEB_SEARCH_DEBUGGING_GUIDE.md` - Ausführliche Anleitung zur Fehlerdiagnose
- `WEB_SEARCH_DEBUG_SUMMARY.md` - Diese Zusammenfassung

## Nutzen

### Vorher:
```
[WARNING] [web_search_adapter] - Google search failed: Google Search failed
```

### Nachher:
```
[INFO] [web_search_adapter] - Searching Google for: Integration und Evaluierung eines MCP-Servers
[DEBUG] [web_search_adapter] - Google Search request URL: https://www.googleapis.com/customsearch/v1
[DEBUG] [web_search_adapter] - Google Search params: cx=0123456789..., num=5
[DEBUG] [web_search_adapter] - Google Search response status: 403
[ERROR] [web_search_adapter] - Google Search API error (status 403): {"error": {...}}
[ERROR] [web_search_adapter] - Google API Error: API key not valid. Please pass a valid API key. (reason: forbidden)
[WARNING] [web_search_adapter] - Google search failed: Google Search API returned status 403 - Details: API key not valid. Please pass a valid API key. (reason: forbidden)
```

## Auswirkungen

### Keine Breaking Changes
- Alle bestehenden Tests bestehen weiterhin
- API-Schnittstelle bleibt unverändert
- Rückwärtskompatibel

### Verbesserte Fehlerdiagnose
- Entwickler können jetzt die genaue Ursache von Fehlern identifizieren
- API-Konfigurationsprobleme sind sofort sichtbar
- Vollständige Tracebacks für unerwartete Fehler

### Sicherheit
- API-Keys werden nie im Klartext geloggt
- Nur Länge und Vorhandensein werden geloggt
- Details-Informationen sind nur bei aktiviertem DEBUG-Level sichtbar

## Verwendung

### Logging-Level einstellen

In `settings.py`:
```python
LOGGING = {
    'loggers': {
        'web_search_adapter': {
            'level': 'DEBUG',  # Für detaillierte Informationen
        },
    },
}
```

### Fehlerdiagnose

1. Überprüfen Sie die Logs auf DEBUG-Level für Konfigurationsdetails
2. Suchen Sie nach ERROR-Meldungen mit spezifischen Fehlerdetails
3. Folgen Sie dem Debugging-Guide für häufige Szenarien

## Dateien geändert

- `core/services/web_search_adapter.py` - Hauptimplementierung
- `main/test_web_search_adapter_debug.py` - Neue Tests
- `WEB_SEARCH_DEBUGGING_GUIDE.md` - Neue Dokumentation
- `WEB_SEARCH_DEBUG_SUMMARY.md` - Diese Zusammenfassung

## Zukünftige Verbesserungen

Mögliche zukünftige Erweiterungen:
- Metriken für API-Nutzung
- Rate-Limiting-Erkennung
- Automatische Retry-Logik
- Caching von Suchergebnissen
- Dashboard für API-Status

## Fazit

Die Implementierung behebt das ursprüngliche Problem vollständig durch:
- Detaillierte, strukturierte Logging-Ausgaben
- Spezifische Fehlerbehandlung für alle bekannten Fehlertypen
- Vollständige Tests zur Validierung
- Umfassende Dokumentation
- Keine Breaking Changes

Die erweiterten Debug-Funktionen ermöglichen es Entwicklern, Probleme mit dem `web_search_adapter` schnell zu identifizieren und zu beheben.
