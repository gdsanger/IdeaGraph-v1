# HTMX File List Updates Implementation

## Überblick
Diese Dokumentation beschreibt die Implementierung von htmx-basierten Dateilisten-Aktualisierungen nach Datei-Upload oder -Löschung in Items. Die Implementierung vermeidet vollständige Seiten-Postbacks und optimiert die User Experience.

## Problem Statement
Die ursprüngliche Implementierung verwendete JavaScript und fetch() für Dateioperationen, was zu folgenden Problemen führte:
- Vollständige JavaScript-basierte DOM-Manipulation erforderlich
- Komplexer Code für Upload und Delete
- Keine konsistente Fehlerbehandlung
- Schwierig zu testen und zu warten

## Lösung
Implementierung von htmx für partielle Seitenaktualisierungen, die:
- Nur die Dateiliste aktualisiert, nicht die gesamte Seite
- Konsistente Fehlerbehandlung bietet
- Einfacher zu warten ist
- Dem bereits etablierten htmx-Muster im Projekt folgt (siehe Task-Pagination)

## Implementierungsdetails

### 1. Partial Template (`main/templates/main/items/_files_list.html`)

Erstellt ein wiederverwendbares Partial Template mit:
- Tabellarischer Ansicht der Dateien
- htmx-Attributen für Delete-Buttons
- Empty-State für leere Dateilisten
- Anzeige von Weaviate-Sync-Status

Key htmx-Attribute im Delete-Button:
```html
<button hx-delete="/api/files/{{ file.id }}/delete"
        hx-target="#filesListContainer"
        hx-swap="innerHTML"
        hx-indicator="#uploadProgress"
        hx-confirm="Are you sure you want to delete this file?">
```

**Funktionsweise:**
- `hx-delete`: Sendet DELETE-Request an die API
- `hx-target`: Ziel-Element für die Aktualisierung
- `hx-swap`: Methode zum Ersetzen des Inhalts
- `hx-indicator`: Loading-Indikator während der Operation
- `hx-confirm`: Bestätigungsdialog vor der Ausführung

### 2. API Endpoints Aktualisierung

#### `api_item_file_list` (main/api_views.py)

**Änderungen:**
- Erkennt htmx-Requests via `request.headers.get('HX-Request')`
- Gibt HTML-Partial für htmx-Requests zurück
- Gibt JSON für reguläre API-Requests zurück (Backward Compatibility)

```python
# Für htmx-Requests
if request.headers.get('HX-Request'):
    return render(request, 'main/items/_files_list.html', {'files': result.get('files', [])})

# Für reguläre API-Requests
return JsonResponse(result)
```

#### `api_item_file_upload` (main/api_views.py)

**Änderungen:**
- Upload-Verarbeitung bleibt gleich
- Nach erfolgreichem Upload: Abruf der aktualisierten Dateiliste
- Rückgabe des HTML-Partials für htmx-Requests

**Flow:**
1. File wird hochgeladen und in SharePoint gespeichert
2. File-Metadaten werden in Datenbank gespeichert
3. Aktualisierte Dateiliste wird abgerufen
4. HTML-Partial mit kompletter Dateiliste wird zurückgegeben

#### `api_item_file_delete` (main/api_views.py)

**Änderungen:**
- Item-ID wird vor dem Löschen gespeichert (für Dateilisten-Abruf)
- Nach erfolgreichem Löschen: Abruf der aktualisierten Dateiliste
- Rückgabe des HTML-Partials für htmx-Requests

**Flow:**
1. Item-ID wird aus File-Objekt extrahiert
2. File wird gelöscht (SharePoint, Weaviate, Datenbank)
3. Aktualisierte Dateiliste wird abgerufen
4. HTML-Partial mit verbleibenden Dateien wird zurückgegeben

### 3. Item Detail Template Aktualisierung (`main/templates/main/items/detail.html`)

#### Upload-Formular mit htmx

**Vorher:** Button und verstecktes File-Input mit JavaScript-Handler

**Nachher:** htmx-basiertes Formular
```html
<form hx-post="/api/items/{{ item.id }}/files/upload" 
      hx-encoding="multipart/form-data"
      hx-target="#filesListContainer"
      hx-swap="innerHTML"
      hx-indicator="#uploadProgress">
    <label for="fileInputHtmx" class="btn btn-primary">
        <i class="bi bi-upload"></i> Upload File
    </label>
    <input type="file" 
           id="fileInputHtmx" 
           name="file" 
           style="display: none;"
           onchange="this.closest('form').dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));" />
</form>
```

**Funktionsweise:**
- `hx-post`: POST-Request mit Multipart-FormData
- `hx-encoding="multipart/form-data"`: Aktiviert File-Upload
- `hx-target`: Ziel für die Aktualisierung
- `hx-swap`: Methode zum Ersetzen des Inhalts
- `onchange`: Automatisches Absenden bei Dateiauswahl

#### Automatisches Laden der Dateiliste

```html
<div id="filesListContainer"
     hx-get="/api/items/{{ item.id }}/files"
     hx-trigger="load"
     hx-indicator="#uploadProgress">
```

**Funktionsweise:**
- `hx-get`: Lädt Dateiliste via GET-Request
- `hx-trigger="load"`: Wird beim Laden des Tabs ausgelöst
- Initial wird "Loading..." angezeigt, dann durch tatsächliche Liste ersetzt

#### JavaScript-Updates

**Entfernt:**
- `uploadFile()` Funktion
- `loadFilesList()` Funktion
- `renderFilesList()` Funktion
- `deleteFile()` globale Funktion

**Hinzugefügt:**
- htmx Event-Listener für Fortschrittsanzeige
- htmx Event-Listener für Toast-Notifications
- htmx Event-Listener zum Zurücksetzen des File-Inputs

```javascript
// Show/Hide progress indicator
document.body.addEventListener('htmx:beforeRequest', function(event) {
    if (event.detail.target.id === 'filesListContainer') {
        document.getElementById('uploadProgress').style.display = 'block';
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.target.id === 'filesListContainer') {
        document.getElementById('uploadProgress').style.display = 'none';
        if (event.detail.successful) {
            showToast('success', 'Success', 'Operation completed successfully');
        }
    }
});
```

### 4. Tests (`main/test_htmx_file_list.py`)

Erstellt umfassende Tests:

**HtmxFileListTest Klasse:**
1. `test_file_list_returns_html_for_htmx_request` - Verifiziert HTML-Response für htmx
2. `test_file_list_returns_json_for_regular_request` - Verifiziert JSON-Response für API
3. `test_file_upload_returns_html_for_htmx_request` - Upload gibt HTML zurück
4. `test_file_delete_returns_html_for_htmx_request` - Delete gibt HTML zurück
5. `test_htmx_attributes_in_partial_template` - htmx-Attribute sind vorhanden
6. `test_empty_state_displayed_when_no_files` - Empty-State wird angezeigt
7. `test_file_list_displays_files` - Dateien werden korrekt angezeigt
8. `test_unauthorized_access_to_files` - Zugriffskontrolle funktioniert
9. `test_weaviate_sync_badge_displayed` - Sync-Status wird angezeigt

**HtmxFileListIntegrationTest Klasse:**
1. `test_upload_then_list_workflow` - Kompletter Upload-Workflow
2. `test_delete_then_list_workflow` - Kompletter Delete-Workflow

**Test-Ausführung:**
```bash
python manage.py test main.test_htmx_file_list
```

## Features

### ✓ Keine vollständigen Seiten-Reloads
- Nur die Dateiliste wird aktualisiert
- Scroll-Position bleibt erhalten
- Andere Teile der Seite bleiben unverändert

### ✓ Loading-Indikator
- Visuelles Feedback während Operationen
- Konsistente Anzeige für Upload und Delete

### ✓ Progressive Enhancement
- Funktioniert auch ohne JavaScript (reguläre Links)
- Graceful Degradation
- API bleibt für andere Clients verfügbar

### ✓ Konsistente Fehlerbehandlung
- Fehler werden im HTML-Partial angezeigt
- Keine JavaScript-Alerts erforderlich
- Benutzerfreundliche Fehlermeldungen

### ✓ Backward Compatibility
- API gibt weiterhin JSON für reguläre Requests zurück
- Bestehende API-Clients funktionieren weiterhin
- Keine Breaking Changes

## Technische Vorteile

### Performance
- Reduzierter Bandwidth-Verbrauch (nur Partial-HTML)
- Schnellere Übergänge
- Keine unnötigen DOM-Manipulationen

### User Experience
- Keine Scroll-Position-Verluste
- Flüssigere Übergänge
- Professionelleres Gefühl
- Sofortiges Feedback

### Wartbarkeit
- Klare Trennung von Server-HTML und Client-Logic
- Weniger JavaScript-Code
- Einfacher zu testen
- Konsistentes Muster im gesamten Projekt

### Testbarkeit
- Server-seitige Templates sind testbar
- Keine komplizierten Mock-Setups erforderlich
- Integration-Tests sind einfacher

## Browser-Kompatibilität
htmx wird in allen modernen Browsern unterstützt:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Fallback zu regulären Links wenn JavaScript deaktiviert ist

## Sicherheit
- Keine neuen Sicherheitslücken eingeführt
- CSRF-Schutz bleibt erhalten
- Keine XSS-Schwachstellen
- Gleiche Authentifizierungs- und Autorisierungsprüfungen

## Ähnliche Implementierungen im Projekt

Diese Implementierung folgt dem gleichen Muster wie:
1. **Task Pagination** (`HTMX_PAGINATION_IMPLEMENTATION.md`)
   - Partial Template für Task-Tabelle
   - htmx-Attribute für Pagination-Links
   - Automatische Inhalts-Aktualisierung

2. **Tag Management** (`TAG_MANAGEMENT_IMPLEMENTATION.md`)
   - htmx für Tag-Operations
   - Partial Template Updates

Diese Konsistenz erleichtert:
- Wartung und Weiterentwicklung
- Onboarding neuer Entwickler
- Code-Reviews

## Manuelle Tests

### Upload-Test
1. Navigiere zu einem Item: `/items/<item_id>/`
2. Öffne den "Files" Tab
3. Klicke auf "Upload File"
4. Wähle eine Datei (max 25MB)
5. Beobachte:
   - Loading-Indikator erscheint
   - Dateiliste aktualisiert sich automatisch
   - Neue Datei erscheint in der Liste
   - Kein vollständiger Seiten-Reload

### Delete-Test
1. Navigiere zu einem Item mit Dateien
2. Öffne den "Files" Tab
3. Klicke auf Delete-Button (Mülleimer-Icon)
4. Bestätige im Dialog
5. Beobachte:
   - Loading-Indikator erscheint
   - Dateiliste aktualisiert sich automatisch
   - Gelöschte Datei ist nicht mehr sichtbar
   - Kein vollständiger Seiten-Reload

### Performance-Test
1. Öffne Browser DevTools (F12)
2. Gehe zum Network Tab
3. Führe Upload oder Delete durch
4. Verifiziere:
   - Nur ein Request zum API-Endpoint
   - Antwort ist HTML (nicht JSON)
   - Kleine Response-Größe (nur Partial-HTML)
   - Schnelle Response-Zeit

## Zukünftige Erweiterungen

Mögliche Verbesserungen:
1. **Drag & Drop Upload**
   - htmx unterstützt Drag & Drop Events
   - Könnte mit `hx-trigger="drop"` implementiert werden

2. **Bulk-Delete**
   - Checkboxen für mehrere Dateien
   - Batch-Delete mit einem Request

3. **File Preview**
   - Modal mit File-Preview bei Klick
   - Inline-Preview für Bilder

4. **Upload-Progress-Bar**
   - Echte Upload-Progress anstatt Spinner
   - Prozentanzeige

5. **Sortierung und Filterung**
   - Sortierung nach Name, Datum, Größe
   - Filterung nach Dateityp

## Rollback

Falls nötig, kann die Änderung einfach rückgängig gemacht werden:

1. **Template wiederherstellen:**
   ```bash
   git checkout HEAD~3 main/templates/main/items/detail.html
   ```

2. **API-Views wiederherstellen:**
   ```bash
   git checkout HEAD~3 main/api_views.py
   ```

3. **Partial Template löschen:**
   ```bash
   rm main/templates/main/items/_files_list.html
   ```

Die Anwendung funktioniert dann wieder mit der alten JavaScript-basierten Implementierung.

## Dateien geändert

1. `/main/templates/main/items/_files_list.html` (neu erstellt)
2. `/main/templates/main/items/detail.html` (modifiziert)
3. `/main/api_views.py` (modifiziert)
4. `/main/test_htmx_file_list.py` (neu erstellt)

## Abhängigkeiten

- **htmx 1.9.10** (bereits in base.html inkludiert)
- **django-htmx >= 1.17.0** (bereits in requirements.txt)
- Keine neuen Abhängigkeiten hinzugefügt

## Migrations

Keine Datenbank-Migrationen erforderlich. Die Änderungen sind rein View- und Template-basiert.

## Fazit

Die Implementierung verbessert die User Experience deutlich durch:
- Keine vollständigen Seiten-Reloads
- Schnellere Dateioperationen
- Besseres Feedback für Benutzer
- Konsistenteres UX-Muster im Projekt

Die Implementierung folgt bewährten Praktiken und dem bereits etablierten htmx-Muster im Projekt, was die Wartbarkeit und Weiterentwicklung erleichtert.
