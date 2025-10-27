# 🔄 GitHub Documentation Synchronization - User Guide

## 📋 Übersicht

Die automatische GitHub-Dokumentations-Synchronisation ermöglicht es IdeaGraph, Markdown-Dateien (`.md`) aus GitHub-Repositories automatisch zu erfassen, in SharePoint zu speichern und semantisch in Weaviate zu indexieren.

## ✨ Features

- **Automatische Erkennung**: Rekursives Scannen von GitHub-Repositories nach `.md`-Dateien
- **SharePoint-Integration**: Upload in Item-spezifische SharePoint-Ordner
- **Datenbank-Registrierung**: Automatische Erstellung von ItemFile-Einträgen
- **Weaviate-Synchronisation**: Semantische Indexierung als KnowledgeObject (type: "documentation")
- **Flexible Ausführung**: Einzelne Items oder alle Items mit GitHub-Repositories
- **Fehlertoleranz**: Robuste Fehlerbehandlung und detailliertes Logging

## 🚀 Schnellstart

### Voraussetzungen

1. **GitHub Personal Access Token**
   - Erstelle einen Token mit `repo` Berechtigung
   - Füge den Token in die Settings hinzu oder setze `GITHUB_TOKEN` in `.env`

2. **GitHub API aktivieren**
   - In IdeaGraph Settings: GitHub API aktivieren
   - Token konfigurieren

3. **Item mit GitHub Repository**
   - Item erstellen oder bearbeiten
   - GitHub Repository URL im Feld `github_repo` eintragen
   - Format: `https://github.com/owner/repo` oder `owner/repo`

### Erste Verwendung

```bash
# Dokumentation für ein spezifisches Item synchronisieren
python manage.py sync_github_docs --item <item_id>

# Dokumentation für alle Items mit GitHub-Repositories synchronisieren
python manage.py sync_github_docs --all
```

## 📖 Detaillierte Verwendung

### Command-Line-Interface

#### Einzelnes Item synchronisieren

```bash
python manage.py sync_github_docs --item 7d6b9aee-2e6f-4e7a-bae4-28face017a97
```

**Ausgabe:**
```
Syncing documentation for item: 7d6b9aee-2e6f-4e7a-bae4-28face017a97

✓ Sync completed successfully!
Item: Feature: Kommentarbereich für Tasks
Files processed: 15
Files synced: 15
```

#### Alle Items synchronisieren

```bash
python manage.py sync_github_docs --all
```

**Ausgabe:**
```
Syncing documentation for all items with GitHub repositories

✓ Sync completed!
Items processed: 5
Items synced: 5
Total files synced: 47
```

### Cron-Job Einrichtung

#### Alle 3 Stunden synchronisieren

```bash
# Crontab bearbeiten
crontab -e

# Folgende Zeile hinzufügen
0 */3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all >> logs/sync_github_docs.log 2>&1
```

#### Täglich um 3 Uhr nachts synchronisieren

```bash
0 3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all >> logs/sync_github_docs.log 2>&1
```

#### Stündlich synchronisieren

```bash
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all >> logs/sync_github_docs.log 2>&1
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)

```env
# GitHub Personal Access Token
GITHUB_TOKEN=ghp_your_token_here

# Sync-Intervall in Minuten (optional, Standard: 180 = 3 Stunden)
GITHUB_DOC_SYNC_INTERVAL=180
```

### IdeaGraph Settings

In der Admin-Oberfläche unter **Settings**:

1. **GitHub API aktivieren**: `github_api_enabled = True`
2. **GitHub Token**: `github_token = ghp_...`
3. **Default Owner** (optional): `github_default_owner = gdsanger`
4. **Default Repo** (optional): `github_default_repo = IdeaGraph-v1`

## 📁 Ablauf der Synchronisation

### 1. Repository-Scan

```python
# GitHubDocSyncService scannt rekursiv das Repository
markdown_files = service.scan_repository(owner="gdsanger", repo="IdeaGraph-v1")
```

Das System:
- Durchsucht alle Verzeichnisse rekursiv
- Filtert auf `.md`-Dateien
- Sammelt Datei-Metadaten (Name, Pfad, Größe, Download-URL)

### 2. Datei-Download

```python
# Download der Markdown-Datei
content = service.download_markdown_file(
    download_url=file['download_url'],
    file_path=file['path']
)
```

- Download über GitHub API
- Größenlimit: 10 MB pro Datei
- UTF-8 Encoding

### 3. SharePoint-Upload

```python
# Upload zu SharePoint in Item-Ordner
sharepoint_result = service.upload_to_sharepoint(
    item=item,
    filename=filename,
    content=content
)
```

- Ordnerstruktur: `IdeaGraph/{ItemTitle}/{filename}.md`
- Automatische Ordner-Normalisierung (SharePoint-kompatible Namen)
- Rückgabe: File ID und Web URL

### 4. Datenbank-Registrierung

```python
# ItemFile-Eintrag erstellen
item_file = service.register_in_database(
    item=item,
    filename=filename,
    file_size=size,
    sharepoint_file_id=file_id,
    sharepoint_url=web_url
)
```

- Duplikat-Erkennung nach Dateiname
- Update bei existierenden Dateien
- Content-Type: `text/markdown`

### 5. Weaviate-Synchronisation

```python
# KnowledgeObject in Weaviate erstellen
weaviate_result = service.sync_to_weaviate(
    item=item,
    filename=filename,
    content=content,
    file_url=sharepoint_url,
    github_file_path=github_path,
    repo_owner=owner,
    repo_name=repo
)
```

**KnowledgeObject Schema:**
```json
{
  "type": "documentation",
  "title": "Feature: Kommentarbereich für Tasks",
  "description": "Erweiterung der Task-Detailansicht um einen modernen Chat-Kommentarbereich...",
  "source": "GitHub",
  "file_url": "https://sharepoint.com/...",
  "github_url": "https://github.com/gdsanger/IdeaGraph-v1/blob/main/docs/feature.md",
  "github_path": "docs/feature.md",
  "github_repo": "gdsanger/IdeaGraph-v1",
  "related_item": "uuid-of-item",
  "tags": ["docs", "documentation", "github"],
  "last_synced": "2025-10-27T17:30:00Z"
}
```

## 🔍 Weaviate-Integration

### KnowledgeObject-Eigenschaften

| Eigenschaft | Typ | Beschreibung |
|------------|-----|--------------|
| `type` | string | Immer "documentation" |
| `title` | string | Dateiname oder erste Markdown-Überschrift |
| `description` | string | Erste 500 Zeichen des Inhalts |
| `source` | string | Immer "GitHub" |
| `file_url` | string | SharePoint URL zur Datei |
| `github_url` | string | GitHub URL zur Quelldatei |
| `github_path` | string | Pfad im Repository |
| `github_repo` | string | owner/repo Format |
| `related_item` | string | UUID des verknüpften Items |
| `tags` | array | ["docs", "documentation", "github"] |
| `last_synced` | string | ISO 8601 Timestamp |

### Suche in dokumentierten Inhalten

Die synchronisierten Dokumentationen sind über die Weaviate-Suche auffindbar:

```python
# Semantische Suche nach Dokumentationen
results = weaviate_client.query.get(
    "KnowledgeObject"
).with_where({
    "path": ["type"],
    "operator": "Equal",
    "valueString": "documentation"
}).with_near_text({
    "concepts": ["authentication", "login"]
}).do()
```

## 🛠️ Programmatische Verwendung

### Python API

```python
from core.services.github_doc_sync_service import GitHubDocSyncService

# Service initialisieren
service = GitHubDocSyncService()

# Einzelnes Item synchronisieren
result = service.sync_item(item_id="uuid-here")

# Alle Items synchronisieren
result = service.sync_all_items()

# Ergebnis prüfen
if result['success']:
    print(f"Synced {result['files_synced']} files")
    if result['errors']:
        for error in result['errors']:
            print(f"Error: {error}")
```

### Repository manuell scannen

```python
# Repository nach Markdown-Dateien durchsuchen
markdown_files = service.scan_repository(
    owner="gdsanger",
    repo="IdeaGraph-v1",
    path="docs"  # optional: nur bestimmtes Verzeichnis
)

for file in markdown_files:
    print(f"{file['path']} - {file['size']} bytes")
```

## 📊 Logging

### Log-Dateien

Alle Aktivitäten werden geloggt:

```bash
# Haupt-Log
logs/ideagraph.log

# Service-spezifisches Logging
logs/github_doc_sync.log  # (falls konfiguriert)
```

### Log-Levels

- **INFO**: Normale Synchronisations-Aktivitäten
- **WARNING**: Übersprungene Dateien, kleinere Probleme
- **ERROR**: Fehler beim Synchronisieren einzelner Dateien
- **CRITICAL**: Schwerwiegende Fehler, die den gesamten Sync betreffen

### Beispiel-Log-Ausgabe

```log
2025-10-27 17:30:00 INFO [github_doc_sync_service] Starting GitHub docs sync for item: Feature ABC (uuid)
2025-10-27 17:30:01 INFO [github_doc_sync_service] Repository: gdsanger/IdeaGraph-v1
2025-10-27 17:30:02 INFO [github_doc_sync_service] Found 15 markdown files
2025-10-27 17:30:03 INFO [github_doc_sync_service] Processing: docs/feature.md
2025-10-27 17:30:04 INFO [github_doc_sync_service] Downloading docs/feature.md
2025-10-27 17:30:05 INFO [github_doc_sync_service] Uploading feature.md to SharePoint
2025-10-27 17:30:07 INFO [github_doc_sync_service] Successfully synced: feature.md
2025-10-27 17:30:15 INFO [github_doc_sync_service] Sync completed. Synced 15/15 files
```

## ❌ Fehlerbehandlung

### Häufige Fehler und Lösungen

#### 1. "GitHub API not enabled"

**Problem**: GitHub API ist in den Settings nicht aktiviert.

**Lösung**:
```python
# In IdeaGraph Settings
github_api_enabled = True
github_token = "ghp_your_token_here"
```

#### 2. "Item has no GitHub repository configured"

**Problem**: Item hat keine `github_repo` URL.

**Lösung**:
```python
# Item bearbeiten und github_repo setzen
item.github_repo = "gdsanger/IdeaGraph-v1"
item.save()
```

#### 3. "Invalid GitHub repository URL format"

**Problem**: Ungültiges URL-Format.

**Lösung**: Verwende eines der folgenden Formate:
- `https://github.com/owner/repo`
- `owner/repo`

#### 4. "File too large"

**Problem**: Datei überschreitet das 10 MB Limit.

**Lösung**: Datei ist zu groß für die automatische Synchronisation. Ggf. manuell hochladen oder in kleinere Dateien aufteilen.

#### 5. "SharePoint upload failed"

**Problem**: SharePoint-Authentifizierung oder Berechtigung fehlt.

**Lösung**:
```python
# Prüfe Graph API Settings
client_id = "..."
client_secret = "..."
tenant_id = "..."
```

## 🔒 Sicherheit

### GitHub Token Berechtigungen

Minimale erforderliche Berechtigungen:
- `repo` (für private Repositories)
- `public_repo` (nur für öffentliche Repositories)

### Rate Limiting

GitHub API Rate Limits:
- **Authenticated**: 5000 Anfragen/Stunde
- **Unauthenticated**: 60 Anfragen/Stunde

Das System nutzt authentifizierte Anfragen, daher sind 5000 Anfragen/Stunde verfügbar.

### Datenschutz

- Keine Speicherung von sensiblen GitHub-Daten
- Markdown-Inhalte werden nur in SharePoint und Weaviate gespeichert
- GitHub Token wird verschlüsselt in der Datenbank gespeichert

## 🧪 Testing

### Manueller Test

```bash
# Test-Script ausführen
python test_github_doc_sync.py
```

### Unit Tests

```bash
# Django Tests ausführen
python manage.py test core.services.github_doc_sync_service
```

## 📈 Performance

### Benchmark-Zahlen

Bei einem typischen Repository mit 50 Markdown-Dateien:
- **Scan-Zeit**: ~5 Sekunden
- **Download pro Datei**: ~0.5 Sekunden
- **SharePoint Upload**: ~2 Sekunden
- **Weaviate Sync**: ~0.3 Sekunden
- **Gesamt**: ~2-3 Minuten für 50 Dateien

### Optimierungen

- Dateien werden nur bei Änderung erneut hochgeladen
- Parallele Verarbeitung möglich (zukünftige Erweiterung)
- Caching von Repository-Scans (zukünftige Erweiterung)

## 🔄 Workflow-Integration

### CI/CD Pipeline

```yaml
# GitHub Actions Workflow
name: Sync Documentation to IdeaGraph

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**/*.md'
      - '*.md'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger IdeaGraph Sync
        run: |
          ssh user@ideagraph-server "cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all"
```

## 📚 Weitere Ressourcen

- [GitHub API Dokumentation](https://docs.github.com/en/rest)
- [Weaviate Dokumentation](https://weaviate.io/developers/weaviate)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)

## 💡 Best Practices

1. **Regelmäßige Synchronisation**: Nutze Cron-Jobs für automatische Updates
2. **Strukturierte Repositories**: Organisiere Dokumentationen in `/docs` Verzeichnissen
3. **Markdown-Konventionen**: Nutze aussagekräftige Headings für bessere Titel-Extraktion
4. **Fehler-Monitoring**: Überwache Log-Dateien für Sync-Fehler
5. **Token-Rotation**: Erneuere GitHub Tokens regelmäßig aus Sicherheitsgründen

## 🆘 Support

Bei Problemen oder Fragen:
1. Prüfe die Log-Dateien in `logs/`
2. Führe `python test_github_doc_sync.py` aus
3. Kontaktiere den Support mit Log-Auszügen

## 📝 Changelog

### Version 1.0.0 (2025-10-27)
- ✨ Initial Release
- ✨ Automatischer Repository-Scan
- ✨ SharePoint-Integration
- ✨ Weaviate-Synchronisation
- ✨ Management Command
- ✨ Fehlerbehandlung und Logging
