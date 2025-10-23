# Web Search Adapter Debug Implementation - Quick Reference

## Was wurde geändert?

### Hauptdatei: `core/services/web_search_adapter.py`

**Zeilen geändert:** ~92 neue Zeilen hinzugefügt
**Funktionalität:** Umfassendes Debug-Logging für bessere Fehlerdiagnose

### Neue Dateien:

1. **`main/test_web_search_adapter_debug.py`** - 13 neue Tests
2. **`WEB_SEARCH_DEBUGGING_GUIDE.md`** - Ausführliche Anleitung
3. **`WEB_SEARCH_DEBUG_SUMMARY.md`** - Implementierungs-Zusammenfassung
4. **`demo_web_search_debug.py`** - Demo-Script (optional)

### Migrations:

- **`main/migrations/0029_merge_20251023_1909.py`** - Merge-Migration

## Wie kann ich die neuen Features nutzen?

### 1. Debug-Logging aktivieren

In `ideagraph/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] [{name}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'web_search_adapter': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Oder 'INFO' für weniger Details
            'propagate': False,
        },
    },
}
```

### 2. Log-Ausgaben verstehen

#### Beispiel: Erfolgreiche Suche

```
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google API Key configured: True (length: 39)
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google CX configured: True (length: 21)
2025-10-23 18:32:22 [INFO] [web_search_adapter] - Searching Google for: MCP-Server Integration
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google Search request URL: https://www.googleapis.com/customsearch/v1
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google Search params: cx=0123456789..., num=5
2025-10-23 18:32:23 [DEBUG] [web_search_adapter] - Google Search response status: 200
2025-10-23 18:32:23 [INFO] [web_search_adapter] - Google Search returned 5 results
```

#### Beispiel: Fehlerhafte API-Konfiguration

**Alt (vorher):**
```
2025-10-23 18:32:23 [WARNING] [web_search_adapter] - Google search failed: Google Search failed
```

**Neu (jetzt):**
```
2025-10-23 18:32:22 [INFO] [web_search_adapter] - Searching Google for: MCP-Server Integration
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google Search request URL: https://www.googleapis.com/customsearch/v1
2025-10-23 18:32:22 [DEBUG] [web_search_adapter] - Google Search params: cx=0123456789..., num=5
2025-10-23 18:32:23 [DEBUG] [web_search_adapter] - Google Search response status: 403
2025-10-23 18:32:23 [ERROR] [web_search_adapter] - Google Search API error (status 403): {"error": {"code": 403, "message": "API key not valid. Please pass a valid API key.", "errors": [{"message": "API key not valid. Please pass a valid API key.", "domain": "global", "reason": "forbidden"}], "status": "PERMISSION_DENIED"}}
2025-10-23 18:32:23 [ERROR] [web_search_adapter] - Google API Error: API key not valid. Please pass a valid API key. (reason: forbidden)
2025-10-23 18:32:23 [WARNING] [web_search_adapter] - Google search failed: Google Search API returned status 403 - Details: API key not valid. Please pass a valid API key. (reason: forbidden)
```

### 3. Tests ausführen

```bash
# Alle Web Search Adapter Tests
python manage.py test main.test_web_search_adapter_debug

# Spezifischer Test
python manage.py test main.test_web_search_adapter_debug.WebSearchAdapterDebugTest.test_search_google_logs_http_error_details

# Alle relevanten Tests
python manage.py test main.test_web_search_adapter_debug main.test_google_pse_settings main.test_support_analysis
```

### 4. Demo ausführen

```bash
python demo_web_search_debug.py
```

## Häufige Probleme und Lösungen

### Problem 1: "API key not valid"

**Log-Ausgabe:**
```
[ERROR] [web_search_adapter] - Google API Error: API key not valid (reason: forbidden)
```

**Lösung:**
1. Überprüfen Sie `GOOGLE_SEARCH_API_KEY` in den Einstellungen
2. Stellen Sie sicher, dass der API-Key für Custom Search API aktiviert ist
3. Prüfen Sie, ob der API-Key nicht abgelaufen ist

### Problem 2: "quotaExceeded"

**Log-Ausgabe:**
```
[ERROR] [web_search_adapter] - Google API Error: Quota exceeded (reason: quotaExceeded)
```

**Lösung:**
1. Tägliches Kontingent wurde überschritten
2. Warten Sie bis zum nächsten Tag
3. Oder konfigurieren Sie Brave Search als Fallback

### Problem 3: "Invalid CX"

**Log-Ausgabe:**
```
[ERROR] [web_search_adapter] - Google API Error: Invalid Value (reason: invalid)
```

**Lösung:**
1. Überprüfen Sie `GOOGLE_SEARCH_CX` in den Einstellungen
2. Stellen Sie sicher, dass die Search Engine ID korrekt ist
3. Prüfen Sie die Berechtigung für die Custom Search Engine

### Problem 4: Keine Ergebnisse

**Log-Ausgabe:**
```
[WARNING] [web_search_adapter] - Google Search returned no items
```

**Lösung:**
- Dies ist kein Fehler, sondern bedeutet, dass die Suche keine Ergebnisse fand
- Der Adapter gibt eine leere Ergebnisliste zurück

## Wichtige Log-Level

| Level | Wann verwenden | Was wird geloggt |
|-------|----------------|------------------|
| `DEBUG` | Entwicklung & Debugging | Alle Details inkl. Konfiguration, Requests, Responses |
| `INFO` | Produktion (Standard) | Start/Ende von Operationen, Erfolge |
| `WARNING` | Produktion (Empfohlen) | Fallbacks, nicht-kritische Fehler |
| `ERROR` | Produktion (Minimal) | Nur kritische Fehler |

## Weitere Ressourcen

- **Ausführliche Anleitung:** `WEB_SEARCH_DEBUGGING_GUIDE.md`
- **Implementierungs-Details:** `WEB_SEARCH_DEBUG_SUMMARY.md`
- **Code:** `core/services/web_search_adapter.py`
- **Tests:** `main/test_web_search_adapter_debug.py`

## Zusammenfassung der Verbesserungen

✅ Konfigurationsstatus wird beim Start geloggt
✅ Request-Details werden geloggt (URL, Parameter)
✅ Response-Details werden geloggt (Status, Daten)
✅ Spezifische Fehlermeldungen statt generischer Texte
✅ Vollständige Tracebacks für unerwartete Fehler
✅ Warnung bei fehlenden Ergebnissen
✅ Detailliertes Logging für Fallback-Mechanismus
✅ API-Keys werden NIE im Klartext geloggt
✅ 13 neue Tests zur Validierung
✅ Keine Breaking Changes
✅ Rückwärtskompatibel
