# Link Content Download Feature

## Übersicht

Diese Funktion ermöglicht es, Webinhalte direkt von URLs herunterzuladen, zu verarbeiten und als strukturierte Markdown-Dateien in Items und Tasks zu speichern.

## Funktionsweise

### 1. Benutzer-Interface
- Im Task-Detail-View unter dem "Files"-Tab befindet sich ein Bereich "Download von Link-Inhalten"
- Im Item-Detail-View unter dem "Files"-Tab befindet sich ebenfalls ein Bereich "Download von Link-Inhalten"
- Der Benutzer gibt eine URL ein und klickt auf "Link verarbeiten"

### 2. Verarbeitungsprozess

Der Prozess läuft in mehreren Schritten ab:

1. **Download**: Die URL wird heruntergeladen (mit Validierung und Timeout-Schutz)
2. **HTML-Reinigung**: 
   - Entfernung von Scripts, Styles, Kommentaren
   - Extraktion des Body-Inhalts
   - Konvertierung in reinen Text
3. **KI-Verarbeitung**: 
   - Der bereinigte Text wird an den KiGate-Agent "web-content-extraction-and-formatting-agent" gesendet
   - Die KI formatiert den Inhalt als sauberes Markdown
4. **Speicherung**: 
   - Die Markdown-Datei wird im Task oder Item gespeichert
   - Automatische Synchronisation mit Weaviate für Vektorsuche

## Technische Details

### Service-Klassen

**`LinkContentService`** (`core/services/link_content_service.py`)
- Hauptklasse für die Link-Verarbeitung
- Methoden:
  - `download_url_content()`: Lädt HTML von URL herunter
  - `clean_html_content()`: Bereinigt HTML-Content
  - `process_with_ai()`: Verarbeitet mit KiGate AI
  - `save_as_task_file()`: Speichert als Task-Datei
  - `save_as_item_file()`: Speichert als Item-Datei
  - `process_link()`: Kompletter Workflow für Tasks
  - `process_link_for_item()`: Kompletter Workflow für Items

### API Endpoints

**POST** `/api/tasks/{task_id}/process-link`

Request Body:
```json
{
  "url": "https://example.com/article"
}
```

Response:
```json
{
  "success": true,
  "message": "Successfully processed and saved content from: Article Title",
  "title": "Article Title",
  "file_id": "uuid"
}
```

**POST** `/api/items/{item_id}/process-link`

Request Body:
```json
{
  "url": "https://example.com/article"
}
```

Response:
```json
{
  "success": true,
  "message": "Successfully processed and saved content from: Article Title",
  "title": "Article Title",
  "file_id": "uuid"
}
```

### Sicherheit

- **ReDoS-Schutz**: Alle HTML-Parsing-Operationen verwenden sichere String-Operationen statt Regex
- **Größenlimits**: HTML-Content ist auf 1MB begrenzt
- **Token-Limits**: Content wird bei Bedarf auf die konfigurierten Token-Limits gekürzt
- **URL-Validierung**: Nur gültige HTTP/HTTPS URLs werden akzeptiert
- **Content-Type-Prüfung**: Nur HTML-Content wird verarbeitet

### Konfiguration

Die folgenden Settings werden berücksichtigt:
- `kigate_max_tokens`: Maximale Token-Anzahl für KI-Verarbeitung
- `kigate_api_enabled`: KiGate API muss aktiviert sein
- `kigate_api_token`: API-Token für KiGate
- `kigate_api_base_url`: KiGate API Base URL

## Verwendung

### Im Task-Detail-View

1. Öffnen Sie einen Task
2. Navigieren Sie zum "Files"-Tab
3. Finden Sie den Bereich "Download von Link-Inhalten"
4. Geben Sie die gewünschte URL ein
5. Klicken Sie auf "Link verarbeiten"
6. Nach einigen Sekunden erscheint die neue Markdown-Datei in der Dateiliste

### Im Item-Detail-View

1. Öffnen Sie ein Item
2. Navigieren Sie zum "Files"-Tab
3. Finden Sie den Bereich "Download von Link-Inhalten"
4. Geben Sie die gewünschte URL ein
5. Klicken Sie auf "Link verarbeiten"
6. Nach einigen Sekunden erscheint die neue Markdown-Datei in der Dateiliste

### Programmatisch

**Für Tasks:**
```python
from core.services.link_content_service import LinkContentService

# Service initialisieren
service = LinkContentService()

# Link verarbeiten
result = service.process_link(
    task=task_object,
    url="https://example.com/article",
    user=user_object
)

if result['success']:
    print(f"Saved as: {result['file'].filename}")
```

**Für Items:**
```python
from core.services.link_content_service import LinkContentService

# Service initialisieren
service = LinkContentService()

# Link verarbeiten
result = service.process_link_for_item(
    item=item_object,
    url="https://example.com/article",
    user=user_object
)

if result['success']:
    print(f"Saved as: {result['file'].filename}")
```

## Fehlerbehandlung

Mögliche Fehler:
- **Invalid URL**: URL ist nicht korrekt formatiert
- **HTTP Error**: Server antwortet mit Fehlercode
- **Non-HTML Content**: URL liefert keinen HTML-Inhalt
- **Timeout**: Request dauert zu lange
- **KiGate Error**: AI-Verarbeitung schlägt fehl

Alle Fehler werden dem Benutzer mit verständlichen Meldungen angezeigt.

## Tests

Die Funktion ist vollständig getestet:
- 13 Unit-Tests in `main/test_link_content_service.py`
- Tests für HTML-Parsing, URL-Download, AI-Integration
- Alle Tests bestehen

## Weaviate-Integration

- Gespeicherte Dateien werden automatisch in Weaviate als KnowledgeObject indexiert
- Dies ermöglicht semantische Suche über den Web-Content
- Die Integration erfolgt durch den bestehenden `TaskFileService`

## Zukünftige Erweiterungen

Mögliche Verbesserungen:
- Batch-Processing mehrerer URLs
- Automatische Extraktion von Links aus Text
- Konfigurierbare Bereinigungsregeln
- Unterstützung für PDF-URLs
- Screenshot-Erstellung
