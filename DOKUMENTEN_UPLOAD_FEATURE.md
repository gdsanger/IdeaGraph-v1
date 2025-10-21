# SharePoint-basiertes Dokumenten-Upload-System mit Weaviate-DB-Integration

## Übersicht

Dieses Feature ermöglicht das Hochladen von Dokumenten zu Items, mit automatischer Speicherung in SharePoint und intelligenter Integration in die Weaviate-Vektor-Datenbank für semantische Suche.

## Hauptfunktionen

### 1. Dokumenten-Upload
- Upload von Dateien bis zu 25 MB
- Unterstützte Dateiformate:
  - **Text-Dateien**: .txt, .md
  - **Code-Dateien**: .py, .cs, .js, .java, .c, .cpp, .h, .html, .css, .json, .xml, .yaml, etc.
  - **PDF-Dateien**: .pdf
  - **Word-Dokumente**: .docx

### 2. SharePoint-Integration
- Automatische Speicherung in SharePoint über Microsoft Graph API
- Organisierte Ordnerstruktur: `IdeaGraph/{Normalisierter Item-Titel}/`
- Normalisierung der Ordnernamen (Entfernung von Sonderzeichen)
- Automatische Erstellung von Ordnern bei Bedarf

### 3. Weaviate-DB-Integration
- Automatische Textextraktion aus unterstützten Dateiformaten
- Intelligentes Chunking für große Dateien (max. 50.000 Zeichen pro Chunk)
- Speicherung als KnowledgeObject mit folgenden Eigenschaften:
  - **title**: Dateiname (mit Chunk-Index bei mehrteiligen Dateien)
  - **description**: Extrahierter Textinhalt
  - **type**: "File"
  - **url**: SharePoint-Download-URL
  - **owner**: Benutzername des Item-Erstellers
  - **section**: Item-Sektion
  - **status**: Item-Status
  - **tags**: Item-Tags

### 4. Dateiverwaltung
- Anzeige aller hochgeladenen Dateien im "Files"-Reiter
- Download-Funktion über SharePoint
- Löschen von Dateien mit automatischer Bereinigung in SharePoint und Weaviate

## Technische Implementierung

### Komponenten

#### 1. ItemFile-Model (`main/models.py`)
```python
class ItemFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    sharepoint_file_id = models.CharField(max_length=255)
    sharepoint_url = models.URLField(max_length=1000)
    content_type = models.CharField(max_length=100)
    weaviate_synced = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 2. FileExtractionService (`core/services/file_extraction_service.py`)
Extrahiert Text aus verschiedenen Dateiformaten:
- **Text-Dateien**: Direkte UTF-8-Dekodierung mit Fallback-Encodings
- **PDF**: PyPDF2-basierte Extraktion
- **DOCX**: python-docx-basierte Extraktion

Features:
- Automatisches Chunking für große Dateien
- Text-Bereinigung (Entfernung überflüssiger Leerzeichen und Zeilenumbrüche)
- Größenlimit-Validierung (25 MB)

#### 3. ItemFileService (`core/services/item_file_service.py`)
Hauptservice für Dateioperationen:
- `upload_file()`: Hochladen mit SharePoint- und Weaviate-Synchronisation
- `delete_file()`: Löschen mit Bereinigung
- `get_download_url()`: Abrufen der SharePoint-URL
- `list_files()`: Auflisten aller Dateien eines Items
- `normalize_folder_name()`: Normalisierung von Ordnernamen für SharePoint

#### 4. API-Endpunkte (`main/api_views.py`, `main/urls.py`)
- `POST /api/items/<item_id>/files/upload`: Datei hochladen
- `GET /api/items/<item_id>/files`: Dateien auflisten
- `GET /api/files/<file_id>`: Download-URL abrufen
- `DELETE /api/files/<file_id>/delete`: Datei löschen

### Benutzeroberfläche

Der "Similar Items"-Reiter wurde in "Files" umbenannt und bietet:
- Upload-Button mit Dateiauswahl
- Fortschrittsanzeige während des Uploads
- Tabelle mit allen hochgeladenen Dateien:
  - Dateiname
  - Größe (MB)
  - Hochgeladen von
  - Upload-Datum
  - Weaviate-Sync-Status
  - Aktionen (Download, Löschen)

## Konfiguration

### Voraussetzungen

1. **SharePoint-Konfiguration** in Settings:
   - `graph_api_enabled`: True
   - `client_id`: Microsoft App Client ID
   - `client_secret`: Microsoft App Client Secret
   - `tenant_id`: Microsoft Tenant ID
   - `sharepoint_site_id`: SharePoint Site ID für Dokumentenspeicherung

2. **Weaviate-Konfiguration**:
   - `weaviate_cloud_enabled`: True/False (je nach Setup)
   - `weaviate_url`: Weaviate-Cluster-URL (bei Cloud)
   - `weaviate_api_key`: Weaviate API-Key (bei Cloud)

3. **Python-Abhängigkeiten**:
   ```
   PyPDF2>=3.0.0
   python-docx>=1.1.0
   ```

### SharePoint-Setup

1. Erstellen Sie einen Ordner "IdeaGraph" im Dokumentenbereich Ihrer SharePoint-Site
2. Stellen Sie sicher, dass die App-Registrierung die erforderlichen Berechtigungen hat:
   - `Files.ReadWrite.All`
   - `Sites.ReadWrite.All`

## Verwendung

### Datei hochladen

1. Navigieren Sie zum Item-Detail
2. Wechseln Sie zum "Files"-Reiter
3. Klicken Sie auf "Upload File"
4. Wählen Sie eine Datei aus (max. 25 MB)
5. Die Datei wird automatisch hochgeladen und verarbeitet

### Datei herunterladen

1. Klicken Sie auf das Download-Symbol in der Dateieintabelle
2. Die Datei öffnet sich in SharePoint

### Datei löschen

1. Klicken Sie auf das Löschen-Symbol
2. Bestätigen Sie die Löschung
3. Die Datei wird aus SharePoint, Weaviate und der Datenbank entfernt

## Dateiverarbeitung

### Upload-Ablauf

```
1. Datei-Upload (Browser → Server)
   ↓
2. Validierung (Größe, Format)
   ↓
3. SharePoint-Upload
   - Ordner-Normalisierung
   - Ordner-Erstellung (falls nötig)
   - Datei-Upload
   ↓
4. Text-Extraktion
   - Format-Erkennung
   - Text-Extraktion
   - Text-Bereinigung
   - Chunking (bei großen Dateien)
   ↓
5. Weaviate-Synchronisation
   - KnowledgeObject-Erstellung
   - Vektor-Embedding (automatisch durch Weaviate)
   ↓
6. Datenbank-Speicherung
   - ItemFile-Eintrag
   - Metadaten
```

### Chunk-Strategie

Bei großen Dateien (>50.000 Zeichen):
1. Text wird in Absätze aufgeteilt
2. Absätze werden zu Chunks zusammengefasst
3. Jeder Chunk erhält eine eindeutige UUID: `{file_id}_{chunk_index}`
4. Jeder Chunk wird als separates KnowledgeObject gespeichert

## Fehlerbehandlung

- **Datei zu groß**: Fehlermeldung, Upload wird abgelehnt
- **SharePoint-Fehler**: Wird geloggt, Upload schlägt fehl
- **Text-Extraktion fehlgeschlagen**: Datei wird in SharePoint gespeichert, aber nicht in Weaviate synchronisiert
- **Weaviate-Fehler**: Wird geloggt, Datei bleibt in SharePoint, `weaviate_synced=False`

## Sicherheit

- **Dateigrößenlimit**: 25 MB (konfigurierbar)
- **Berechtigungsprüfung**: Nur Item-Besitzer und Admins können Dateien hochladen/löschen
- **CSRF-Schutz**: Alle API-Endpunkte sind CSRF-geschützt
- **Ordner-Normalisierung**: Verhindert Pfad-Traversal-Angriffe
- **Keine bekannten Schwachstellen**: CodeQL-Analyse bestanden

## Tests

17 Tests decken folgende Bereiche ab:
- Text-Extraktion aus verschiedenen Formaten
- Dateigrößen-Validierung
- Chunk-Logik
- Ordner-Normalisierung
- Model-Operationen
- Beziehungen und Kaskaden-Löschen

Alle Tests: ✅ BESTANDEN

## Troubleshooting

### Problem: Dateien werden nicht in SharePoint gespeichert
**Lösung**: 
- Überprüfen Sie die Graph API-Einstellungen in Settings
- Stellen Sie sicher, dass `sharepoint_site_id` korrekt ist
- Überprüfen Sie die App-Berechtigungen

### Problem: Text wird nicht extrahiert
**Lösung**:
- Überprüfen Sie, ob das Dateiformat unterstützt wird
- Stellen Sie sicher, dass PyPDF2/python-docx installiert sind
- Überprüfen Sie die Logs auf spezifische Fehler

### Problem: Weaviate-Synchronisation schlägt fehl
**Lösung**:
- Überprüfen Sie die Weaviate-Verbindung
- Stellen Sie sicher, dass das KnowledgeObject-Schema existiert
- Überprüfen Sie die Weaviate-Logs

## Zukünftige Erweiterungen

Mögliche zukünftige Verbesserungen:
- Unterstützung für größere Dateien (>25 MB) mit Chunk-Upload
- Weitere Dateiformate (XLSX, PPTX, etc.)
- Versionierung von Dateien
- Vorschau-Funktionen
- Volltextsuche über alle Dateien
- Automatische Tagging basierend auf Dateiinhalt

## Lizenz

Dieses Feature ist Teil von IdeaGraph und steht unter der gleichen Lizenz wie das Hauptprojekt.
