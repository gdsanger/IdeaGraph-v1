# KI-gesteuerte Funktionen in Task/Item Detailansicht

## Übersicht

Dieses Dokument beschreibt die Implementierung der KI-gesteuerten Funktionen in der Task- und Item-Detailansicht gemäß der Issue-Anforderung.

## Implementierte Funktionen

### 1. Titel-Generierung
- **Button-Position**: Neben dem Titel-Textfeld
- **KI-Agent**: `text-to-title-generator`
- **Funktion**: Generiert einen Titel basierend auf der Beschreibung
- **API-Endpunkte**:
  - `/api/tasks/{task_id}/generate-title`
  - `/api/items/{item_id}/generate-title`
- **Besonderheit**: Funktioniert auch für ungespeicherte Tasks/Items (task_id/item_id = 'new')

### 2. Tag-Extraktion
- **Button-Position**: Neben dem Tags-Feld
- **KI-Agent**: `text-keyword-extractor-de`
- **Funktion**: Extrahiert maximal 5 Tags aus der Beschreibung
- **API-Endpunkte**:
  - `/api/tasks/{task_id}/extract-tags`
  - `/api/items/{item_id}/extract-tags`
- **Tag-Verwaltung**: 
  - Tags werden automatisch in der Datenbank erstellt, falls sie nicht existieren
  - Duplikate werden durch case-insensitive Suche vermieden
  - Verwendet die gleiche `clean_tag_name()` Funktion wie der AI Enhancer

### 3. Text-Optimierung
- **Button-Position**: Oberhalb der Beschreibung mit Label "Optimize Text"
- **KI-Agent**: `text-optimization-agent`
- **Funktion**: Normalisiert und verbessert die Beschreibung (Rechtschreibung, Grammatik, Fluss)
- **API-Endpunkte**:
  - `/api/tasks/{task_id}/optimize-description`
  - `/api/items/{item_id}/optimize-description`

## Technische Details

### API-Implementierung

Alle neuen API-Endpunkte befinden sich in `main/api_views.py`:
- `api_task_generate_title()`
- `api_task_extract_tags()`
- `api_task_optimize_description()`
- `api_item_generate_title()`
- `api_item_extract_tags()`
- `api_item_optimize_description()`

**Gemeinsame Merkmale**:
- Authentifizierung: Hybrid (JWT oder Session-basiert)
- CSRF-geschützt mit `@csrf_exempt` und manueller Token-Überprüfung
- Fehlerbehandlung mit aussagekräftigen Fehlermeldungen
- Unterstützung für ungespeicherte Entities (task_id/item_id = 'new')

### UI-Integration

**Task Detail Template** (`main/templates/main/tasks/detail.html`):
- Titel-Feld: Input-Group mit KI-Button
- Beschreibung: Button oberhalb des Toast UI Editors
- Tags: Button neben dem Label

**Item Detail Template** (`main/templates/main/items/detail.html`):
- Identische Struktur wie bei Tasks

**JavaScript-Handler**:
- Separate Event-Handler für jeden Button
- Spinner-Animation während API-Aufrufen
- Alert-Benachrichtigungen für Erfolg/Fehler
- Automatisches Update der Formularfelder mit KI-Ergebnissen

### Sicherheit

- **Authentifizierung**: Alle Endpunkte erfordern Authentifizierung
- **Autorisierung**: Benutzer können nur ihre eigenen Tasks/Items bearbeiten
- **CSRF-Schutz**: Aktiviert für alle POST-Requests
- **CodeQL-Analyse**: Keine Sicherheitslücken gefunden

### Tests

**Test-Dateien**:
- `main/test_task_individual_ai_functions.py`: 6 Tests für Task-Funktionen
- `main/test_item_individual_ai_functions.py`: 7 Tests für Item-Funktionen

**Test-Abdeckung**:
- Erfolgreiche API-Aufrufe
- Authentifizierungs-Fehler
- Validierungs-Fehler (fehlende Beschreibung)
- Autorisierungs-Fehler (Zugriff auf fremde Items/Tasks)
- Unterstützung für ungespeicherte Entities

Alle 13 Tests bestehen erfolgreich.

## Verwendung

### Für Entwickler

1. **Titel generieren**:
   - Beschreibung eingeben
   - Auf KI-Button neben dem Titel-Feld klicken
   - Generierter Titel wird automatisch eingefügt

2. **Tags extrahieren**:
   - Beschreibung eingeben
   - Auf KI-Button neben den Tags klicken
   - Bis zu 5 relevante Tags werden automatisch hinzugefügt

3. **Text optimieren**:
   - Beschreibung eingeben
   - Auf "Optimize Text" Button klicken
   - Optimierte Beschreibung ersetzt die aktuelle Version

### API-Verwendung

```javascript
// Titel generieren
const response = await fetch('/api/tasks/{task_id}/generate-title', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
        description: 'Task description here'
    })
});

const data = await response.json();
console.log(data.title); // Generierter Titel
```

## Unterschied zum AI Enhancer

Der bestehende "AI Enhancer" Button führt alle drei Funktionen nacheinander aus:
1. Text-Normalisierung mit Kontext aus ChromaDB
2. Titel-Generierung
3. Tag-Extraktion

Die neuen individuellen Buttons ermöglichen:
- Gezielte Nutzung einzelner KI-Funktionen
- Schnellere Ausführung (nur eine KI-Anfrage)
- Flexiblere Workflow-Gestaltung
- Verwendung auch bei ungespeicherten Entities

## Konfiguration

Die KI-Funktionen verwenden folgende Einstellungen aus dem Settings-Modell:
- `kigate_api_enabled`: KIGate API aktivieren/deaktivieren
- `kigate_api_base_url`: KIGate API Basis-URL
- `kigate_api_token`: Authentifizierungs-Token
- `max_tags_per_idea`: Maximale Anzahl generierter Tags (Standard: 5)

## Abhängigkeiten

- KIGate API Service (`core/services/kigate_service.py`)
- OpenAI Provider (konfiguriert in KIGate)
- GPT-4 Modell
- Django 5.1+
- Toast UI Editor (für Markdown-Beschreibungen)

## Performance-Überlegungen

- Jeder KI-Button macht genau einen API-Aufruf zur KIGate API
- Timeout-Handling durch KiGateService
- Fehler werden graceful behandelt mit Fallback-Werten
- Spinner-Animation informiert den Benutzer über laufende Prozesse
