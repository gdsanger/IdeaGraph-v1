# ChromaDB Migration: Cloud to Local Instance

## Übersicht

Dieses Dokument beschreibt die Migration von ChromaDB von einer Cloud-basierten Lösung zu einer lokalen Instanz.

## Änderungen

### 1. ChromaDB Konfiguration

**Lokale Instanz Details:**
- **Host:** `localhost`
- **Port:** `8003`
- **Datenpfad:** `/opt/chromadb/data/chroma`

### 2. Embedding-Modell Upgrade

Das Embedding-Modell wurde von `text-embedding-ada-002` auf `text-embedding-3-large` aktualisiert:
- **Vorher:** `text-embedding-ada-002` (1536 Dimensionen)
- **Nachher:** `text-embedding-3-large` (3072 Dimensionen)

### 3. Geänderte Dateien

#### Backend Services

1. **core/services/chroma_sync_service.py**
   - ChromaDB Client verwendet jetzt `localhost:8003`
   - Embedding-Modell auf `text-embedding-3-large` aktualisiert
   - Embedding-Vektorgröße auf 3072 aktualisiert

2. **core/services/chroma_task_sync_service.py**
   - ChromaDB Client verwendet jetzt `localhost:8003`
   - Embedding-Modell auf `text-embedding-3-large` aktualisiert
   - Embedding-Vektorgröße auf 3072 aktualisiert

3. **core/services/github_issue_sync_service.py**
   - ChromaDB Client verwendet jetzt `localhost:8003`
   - Embedding-Modell auf `text-embedding-3-large` aktualisiert
   - Embedding-Vektorgröße auf 3072 aktualisiert

#### Frontend (UI)

4. **main/templates/main/settings_form.html**
   - Warnung "Derzeit nicht verfügbar" hinzugefügt
   - Cloud-ChromaDB Felder deaktiviert (disabled)
   - Hilfetext aktualisiert mit "Derzeit nicht verfügbar"

### 4. Beibehaltene Funktionen

Die folgenden Methoden wurden beibehalten, obwohl sie nicht mehr aktiv verwendet werden:
- `_resolve_cloud_credentials()` - Für mögliche zukünftige Cloud-Integration
- `_build_cloud_client_kwargs()` - Für mögliche zukünftige Cloud-Integration

Die Cloud-Konfigurationsfelder im Settings-Modell bleiben ebenfalls erhalten.

## Verwendung

### Voraussetzungen

1. ChromaDB muss lokal installiert sein unter `/opt/chromadb`
2. ChromaDB Server muss auf Port 8003 laufen
3. OpenAI API Key muss in den Settings konfiguriert sein (für Embeddings)

### ChromaDB Server starten

```bash
# Beispielbefehl (anpassen je nach Installation)
cd /opt/chromadb
chroma run --host localhost --port 8003 --path /opt/chromadb/data/chroma
```

### Konfiguration prüfen

Die ChromaDB-Verbindung wird automatisch beim Start der Services initialisiert. Logs überprüfen:

```bash
tail -f logs/ideagraph.log | grep -i chroma
```

Erwartete Log-Einträge:
```
Initializing ChromaDB local client at localhost:8003
ChromaDB collection 'items' initialized
ChromaDB collection 'tasks' initialized
ChromaDB collection 'GitHubIssues' initialized
```

## OpenAI API Integration

Die Embeddings werden weiterhin über die OpenAI API generiert. Stellen Sie sicher, dass:
1. `openai_api_enabled` auf `True` gesetzt ist
2. `openai_api_key` konfiguriert ist
3. `openai_api_base_url` korrekt ist (Standard: `https://api.openai.com/v1`)

## Migrationshinweise

### Bestehende Daten

- Alte Cloud-ChromaDB-Daten müssen **nicht** migriert werden
- Das System erstellt neue Collections in der lokalen Instanz
- Items, Tasks und GitHub Issues werden bei Bedarf neu synchronisiert

### Embedding-Größe

**Wichtig:** Das neue Embedding-Modell `text-embedding-3-large` erzeugt 3072-dimensionale Vektoren (vorher 1536). Dies bedeutet:
- Bessere semantische Genauigkeit
- Höherer Speicherbedarf
- Alle neuen Embeddings verwenden automatisch das neue Modell

## Fehlerbehebung

### ChromaDB Verbindungsfehler

**Symptom:** `Failed to initialize ChromaDB client`

**Lösung:**
1. Prüfen Sie, ob ChromaDB läuft: `curl http://localhost:8003/api/v1/heartbeat`
2. Prüfen Sie die Logs: `tail -f logs/ideagraph.log`
3. Starten Sie ChromaDB neu

### OpenAI API Fehler

**Symptom:** `Failed to generate embedding`

**Lösung:**
1. Überprüfen Sie den API-Key in den Settings
2. Prüfen Sie die Netzwerkverbindung zu OpenAI
3. Überprüfen Sie das API-Rate-Limit

## Tests

Die bestehenden Tests verwenden Mocks für ChromaDB. Für echte Integrationstests:

```bash
# ChromaDB Server muss laufen
python manage.py test main.test_chroma_integration
python manage.py test main.test_task_chroma_integration
```

## Rollback-Plan

Falls ein Rollback zur Cloud-Version erforderlich ist:

1. Revertieren Sie die Änderungen an den drei Service-Dateien
2. Konfigurieren Sie die Cloud-Credentials in den Settings
3. Entfernen Sie das `disabled` Attribut von den UI-Feldern

Die alten Methoden (`_resolve_cloud_credentials`, `_build_cloud_client_kwargs`) sind noch vorhanden und können wiederverwendet werden.
