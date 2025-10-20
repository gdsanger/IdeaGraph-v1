# Migration von ChromaDB zu Weaviate

## Übersicht

Dieses Dokument beschreibt die vollständige Migration von ChromaDB zu Weaviate als Vectordatenbank für IdeaGraph.

## Änderungen

### 1. Weaviate Konfiguration

**Weaviate Instance Details:**
- **Host:** `localhost`
- **Port:** `8081`
- **Authentifizierung:** Keine (lokale Instanz)
- **Vectorizer:** `text2vec-transformers` (lokal, kein OpenAI erforderlich)

### 2. Vectorisierung

Die Vectorisierung wird jetzt von Weaviate's `text2vec-transformers` übernommen:
- **Vorher:** OpenAI `text-embedding-3-large` (3072 Dimensionen)
- **Nachher:** text2vec-transformers (lokale Verarbeitung)
- **Vorteil:** Keine externen API-Aufrufe, keine Kosten, konsistente Ergebnisse

### 3. Schema

Das Weaviate Schema wurde implementiert gemäß der Issue-Anforderung:
- **Tag** Collection mit name und description
- **Item** Collection mit cross-references zu Tags
- **Task** Collection mit cross-references zu Items und Tags
- **GitHubIssue** Collection mit cross-references zu Tasks und Items

### 4. Geänderte Dateien

#### Models
1. **main/models.py**
   - Tag-Modell erweitert um `description` Feld

#### Migrations
2. **main/migrations/0014_add_tag_description.py**
   - Database Migration für Tag description Feld

#### Services
3. **core/services/weaviate_sync_service.py** (neu)
   - Weaviate Item Synchronization Service
   - Ersetzt ChromaItemSyncService

4. **core/services/weaviate_task_sync_service.py** (neu)
   - Weaviate Task Synchronization Service
   - Ersetzt ChromaTaskSyncService

5. **core/services/weaviate_github_issue_sync_service.py** (neu)
   - Weaviate GitHub Issue Synchronization Service
   - Ersetzt GitHubIssueSyncService

6. **core/services/weaviate_tag_sync_service.py** (neu)
   - Weaviate Tag Synchronization Service (neu)
   - Ermöglicht Tag-Synchronisierung

#### Views
7. **main/views.py**
   - Alle ChromaDB Service Imports ersetzt durch Weaviate Services
   - sync_service.close() Aufrufe hinzugefügt

8. **main/api_views.py**
   - Alle ChromaDB Service Imports ersetzt durch Weaviate Services
   - Alle Referenzen zu ChromaDB auf Weaviate aktualisiert

#### Tests
9. **main/test_settings_openai_toggle.py**
   - Test aktualisiert für Weaviate (kein OpenAI erforderlich)

#### Scripts
10. **sync_github_issues.py**
    - Kommentare und Logging auf Weaviate aktualisiert

#### Management Commands
11. **main/management/commands/sync_tags_to_weaviate.py** (neu)
    - CLI Command zum Synchronisieren von Tags zu Weaviate
    - Kann als Cron-Job ausgeführt werden

#### Dependencies
12. **requirements.txt**
    - `chromadb>=0.4.0` entfernt
    - `weaviate-client>=4.9.0` hinzugefügt

#### Documentation
13. **docs/WEAVIATE_SYNC.md** (neu)
    - Vollständige Dokumentation der Weaviate Integration

### 5. Entfernte Abhängigkeiten

Die folgenden ChromaDB-bezogenen Services wurden beibehalten aber werden nicht mehr verwendet:
- `core/services/chroma_sync_service.py`
- `core/services/chroma_task_sync_service.py`
- `core/services/github_issue_sync_service.py` (ChromaDB-Teile)

**Hinweis:** Diese Dateien können später entfernt werden, nachdem die Migration erfolgreich abgeschlossen wurde.

## Verwendung

### Voraussetzungen

1. Weaviate muss lokal auf Port 8081 laufen
2. Schema muss in Weaviate angelegt sein (gemäß Issue-Beschreibung)
3. **Keine** OpenAI API Key erforderlich (text2vec-transformers)

### Weaviate Server starten

```bash
# Docker Compose Beispiel
docker-compose up -d weaviate
```

### Tag-Synchronisierung

Tags können jetzt synchronisiert werden:

```bash
# Alle Tags synchronisieren
python manage.py sync_tags_to_weaviate

# Spezifischen Tag synchronisieren
python manage.py sync_tags_to_weaviate --tag-id <UUID>

# Als Cron-Job (stündlich)
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_tags_to_weaviate
```

### Konfiguration prüfen

Die Weaviate-Verbindung wird automatisch beim Start der Services initialisiert. Logs überprüfen:

```bash
tail -f logs/ideagraph.log | grep -i weaviate
```

Erwartete Log-Einträge:
```
Initializing Weaviate client at localhost:8081
Weaviate client initialized, collection 'Item' ready
Weaviate client initialized, collection 'Task' ready
Weaviate client initialized, collection 'GitHubIssue' ready
Weaviate client initialized, collection 'Tag' ready
```

## UUID Management

**Wichtig:** Wir verwenden immer unsere internen UUIDs als ID in Weaviate. Dies stellt sicher:

1. Konsistenz zwischen unserer Datenbank und Weaviate
2. Einfaches Mapping von Weaviate-Ergebnissen zu unseren Datensätzen
3. Keine Duplikate beim erneuten Synchronisieren

Beispiel:
```python
collection.data.insert(
    properties=properties,
    uuid=str(item.id)  # Immer unsere interne UUID verwenden
)
```

## Migrationshinweise

### Bestehende Daten

- Alte ChromaDB-Daten müssen **nicht** migriert werden
- Das System erstellt neue Einträge in Weaviate
- Items, Tasks und GitHub Issues werden bei Bedarf automatisch synchronisiert
- Tags müssen einmalig mit `sync_tags_to_weaviate` synchronisiert werden

### Cross-References

Weaviate unterstützt native Cross-References zwischen Collections:
- Items haben Referenzen zu Tags
- Tasks haben Referenzen zu Items und Tags
- GitHubIssues haben Referenzen zu Tasks und Items

### Keine OpenAI API mehr erforderlich

Ein großer Vorteil: Die Vectorisierung erfolgt lokal durch Weaviate's text2vec-transformers. Das bedeutet:
- Keine API-Kosten
- Schnellere Verarbeitung
- Keine Rate Limits
- Konsistente Ergebnisse

## Fehlerbehebung

### Weaviate Verbindungsfehler

**Symptom:** `Failed to initialize Weaviate client`

**Lösung:**
1. Prüfen Sie, ob Weaviate läuft: `curl http://localhost:8081/v1/.well-known/ready`
2. Prüfen Sie die Logs: `tail -f logs/ideagraph.log`
3. Starten Sie Weaviate neu

### Schema nicht gefunden

**Symptom:** `Collection 'Item' not found`

**Lösung:**
1. Überprüfen Sie, ob das Schema in Weaviate angelegt ist
2. Schema kann über Weaviate API angelegt werden
3. Siehe Schema-Details in der Issue-Beschreibung

### Tags werden nicht synchronisiert

**Symptom:** Tags fehlen in Weaviate

**Lösung:**
1. Führen Sie `python manage.py sync_tags_to_weaviate` aus
2. Überprüfen Sie die Logs
3. Prüfen Sie, ob Tag-Einträge ein description Feld haben

## Tests

Die bestehenden Tests wurden angepasst:

```bash
# Weaviate Service Tests
python manage.py test main.test_weaviate*

# Integration Tests
python manage.py test main.test_weaviate_integration
```

## Rollback-Plan

Falls ein Rollback erforderlich ist:

1. Requirements.txt auf chromadb zurücksetzen
2. Views und API Views auf ChromaDB Services zurücksetzen
3. Alte ChromaDB Services wieder aktivieren

Die alten Service-Dateien sind noch vorhanden und können wiederverwendet werden.

## Vorteile der Migration

1. **Keine externen API-Kosten**: Lokale Vectorisierung
2. **Bessere Schema-Unterstützung**: Native Cross-References
3. **Konsistente UUIDs**: Verwendung interner UUIDs
4. **Automatische Vectorisierung**: text2vec-transformers
5. **Mehrsprachige Unterstützung**: Inklusive Deutsch
6. **Tag-Synchronisierung**: Neue Funktion für Tags

## Offene Punkte

- [ ] ChromaDB-Service Dateien können nach erfolgreicher Migration entfernt werden
- [ ] ChromaDB Settings-Felder in UI können entfernt/deaktiviert werden
- [ ] Alte ChromaDB-Dokumentation kann archiviert werden

