# File Summary Popup Feature

## Übersicht

Diese Feature ermöglicht es Benutzern, eine KI-generierte Zusammenfassung von hochgeladenen Dateien direkt in einem Popup-Fenster anzuzeigen.

## Funktionsweise

### 1. Datei-Zusammenfassungs-Button

In den Dateilisten (sowohl für Items als auch für Tasks) wurde ein neuer Button hinzugefügt:
- **Icon**: 📄 (bi-file-text)
- **Farbe**: Outline-Info (blauer Rand)
- **Tooltip**: "Show Summary"

### 2. API-Endpunkt

**URL**: `/api/files/<file_id>/summary`
**Methode**: GET
**Authentifizierung**: Erforderlich

#### Funktionsweise:

1. **Datei-Lookup**: Sucht die Datei in ItemFile oder TaskFile Modellen
2. **Weaviate-Abfrage**: Holt den Dateiinhalt aus der Weaviate Vektordatenbank
   - Unterstützt auch mehrteilige Dateien (Chunks)
   - Kombiniert alle Chunks zu einem vollständigen Inhalt
3. **KI-Zusammenfassung**: Sendet den Inhalt an den KIGate-Agent `weaviate-data-summary-agent`
   - Provider: OpenAI
   - Model: GPT-4
   - Prompt: Fordert eine prägnante Zusammenfassung an
4. **Fallback-Mechanismus**: Bei KIGate-Fehlern wird ein Textauszug als Zusammenfassung verwendet

#### Response-Format:

```json
{
  "success": true,
  "summary": "# Dateiname\n\nMarkdown-formatierte Zusammenfassung...",
  "filename": "document.txt",
  "file_url": "https://sharepoint.example.com/document.txt"
}
```

### 3. Modal-Fenster

Das Modal wird dynamisch erstellt und zeigt:
- **Titel**: Dateiname mit Icon
- **Inhalt**: Markdown-gerenderte Zusammenfassung (via marked.js)
- **Link**: Button zum Öffnen der Originaldatei in SharePoint
- **Loading State**: Spinner während die Zusammenfassung generiert wird

### 4. Markdown-Rendering

Verwendet die `marked.js` Bibliothek für die Darstellung von:
- Überschriften (h1, h2, h3)
- Listen (geordnet und ungeordnet)
- Code-Blöcke
- Inline-Code
- Absätze und Formatierungen

## Implementierte Dateien

### Backend
- **main/api_views.py**: `api_file_summary()` Funktion
- **main/urls.py**: URL-Route für den API-Endpunkt
- **main/test_file_summary.py**: Umfassende Unit-Tests (6 Tests)

### Frontend
- **main/templates/main/items/_files_list.html**: Modal und JavaScript für Item-Dateien
- **main/templates/main/tasks/_files_list.html**: Modal und JavaScript für Task-Dateien

## Verwendung

1. **Datei hochladen**: Eine Datei zu einem Item oder Task hochladen
2. **Weaviate-Sync**: Warten bis die Datei mit Weaviate synchronisiert ist (grüner Indikator)
3. **Zusammenfassung anzeigen**: Auf den 📄-Button in der Aktionsspalte klicken
4. **Zusammenfassung lesen**: Die KI-generierte Zusammenfassung im Modal lesen
5. **Datei öffnen**: Optional auf "Open File" klicken, um die Originaldatei zu öffnen

## Technische Details

### Dependencies
- **marked.js**: CDN-Version für Markdown-Rendering
- **Bootstrap 5**: Modal-Komponenten
- **htmx**: Für dynamisches Laden der Dateilisten

### Unterstützte Dateitypen
Alle Dateitypen, die vom `FileExtractionService` unterstützt werden:
- Text-Dateien (.txt, .md)
- Code-Dateien (.py, .cs, .js, .java, etc.)
- PDF-Dateien (.pdf)
- Word-Dokumente (.docx)

### Fehlerbehandlung
- **Authentifizierung fehlt**: HTTP 401
- **Datei nicht gefunden**: HTTP 404
- **Nicht mit Weaviate synchronisiert**: HTTP 404
- **KIGate-Fehler**: Fallback auf Textauszug
- **Allgemeine Fehler**: HTTP 500 mit Fehlermeldung

## Tests

Alle Tests befinden sich in `main/test_file_summary.py`:

1. **test_file_summary_requires_authentication**: Prüft Authentifizierungspflicht
2. **test_file_summary_not_found**: Prüft Fehlerbehandlung für nicht existierende Dateien
3. **test_file_summary_not_synced**: Prüft Fehlerbehandlung für nicht-synchronisierte Dateien
4. **test_file_summary_success**: Prüft erfolgreiche Zusammenfassungsgenerierung (ItemFile)
5. **test_file_summary_fallback_on_kigate_error**: Prüft Fallback-Mechanismus
6. **test_task_file_summary_success**: Prüft erfolgreiche Zusammenfassungsgenerierung (TaskFile)

Alle Tests bestehen ✓

## Zukünftige Verbesserungen

Mögliche Erweiterungen:
- Caching von Zusammenfassungen
- Auswahl verschiedener Zusammenfassungslängen
- Mehrsprachige Zusammenfassungen
- Zusammenfassungen in verschiedenen Formaten (bullets, abstract, etc.)
