# GitHub Issues und Tasks Synchronisation

> **⚠️ DEPRECATED DOCUMENTATION**
> 
> This document describes an older ChromaDB-based implementation.
> 
> **For the current implementation**, see [GITHUB_ISSUES_KNOWLEDGEOBJECT_MIGRATION.md](./GITHUB_ISSUES_KNOWLEDGEOBJECT_MIGRATION.md)
> 
> GitHub Issues are now stored in Weaviate's `KnowledgeObject` collection, not in a separate ChromaDB collection.

## Übersicht

Dieses Feature implementiert eine automatische Synchronisation zwischen GitHub Issues/Pull Requests und IdeaGraph Tasks. Es ermöglicht:

1. **Automatische Task-Status-Aktualisierung**: Wenn ein GitHub Issue geschlossen wird, wird der zugehörige Task automatisch auf "Erledigt" gesetzt
2. **ChromaDB Speicherung**: Issue- und PR-Beschreibungen werden in der ChromaDB Collection `GitHubIssues` gespeichert für semantische Suche
3. **Umfassende Metadaten**: Speicherung von Task-UUID, Titel, Item-Informationen, Tags und GitHub-Daten

## Komponenten

### 1. GitHub Issue Sync Service (`core/services/github_issue_sync_service.py`)

Kernservice für die Synchronisation mit folgenden Funktionen:

- `sync_tasks_with_github_issues()`: Synchronisiert alle Tasks mit ihren verknüpften GitHub Issues
- `sync_issue_to_chroma()`: Speichert ein GitHub Issue in ChromaDB
- `sync_pull_request_to_chroma()`: Speichert einen Pull Request in ChromaDB
- `search_similar()`: Semantische Suche nach ähnlichen Issues/PRs

### 2. Erweiterte GitHub Service (`core/services/github_service.py`)

Neue Methoden für Pull Request Unterstützung:

- `get_pull_request()`: Abrufen eines einzelnen Pull Requests
- `list_pull_requests()`: Auflisten aller Pull Requests eines Repositories

### 3. CLI Script (`sync_github_issues.py`)

Ausführbares Python-Skript für manuelle Ausführung oder als Cron Job.

## Installation und Konfiguration

### Voraussetzungen

1. **GitHub API Zugriff**:
   - GitHub Token in den Settings konfigurieren
   - Default Owner und Repository einstellen

2. **ChromaDB Konfiguration**:
   - ChromaDB API Key, Database und Tenant in Settings
   - OpenAI API Key für Embeddings

3. **Django Einstellungen**:
   - Alle erforderlichen Einstellungen in der Settings-Tabelle

### Verwendung

#### Manuelle Ausführung

```bash
# Mit Standard-Einstellungen aus der Datenbank
python sync_github_issues.py

# Mit spezifischem Repository
python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1

# Mit verbose Logging
python sync_github_issues.py --verbose

# Dry-Run (keine Änderungen)
python sync_github_issues.py --dry-run
```

#### Als Cron Job

Crontab-Eintrag für stündliche Ausführung:

```cron
# Stündliche Synchronisation (jede volle Stunde)
0 * * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Alle 15 Minuten
*/15 * * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Täglich um 2 Uhr nachts
0 2 * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1
```

#### Mit Umgebungsvariablen

```bash
# Umgebungsvariablen setzen
export GITHUB_SYNC_OWNER=gdsanger
export GITHUB_SYNC_REPO=IdeaGraph-v1

# Skript ausführen
python sync_github_issues.py
```

## ChromaDB Collection Schema

### Collection Name: `GitHubIssues`

Enthält sowohl Issues als auch Pull Requests mit folgenden Metadaten:

#### Gemeinsame Felder

- `type`: `"issue"` oder `"pull_request"`
- `github_issue_id`: Nummer des Issues/PRs
- `github_issue_title`: Titel des Issues/PRs
- `github_issue_state`: Status (`"open"` oder `"closed"`)
- `github_issue_url`: URL zum Issue/PR

#### Task-bezogene Felder

- `task_id`: UUID des verknüpften Tasks
- `task_title`: Titel des Tasks
- `task_status`: Status des Tasks
- `task_tags`: Komma-getrennte Liste der Task-Tags
- `item_id`: UUID des Items
- `item_title`: Titel des Items

#### Pull Request spezifische Felder

- `pr_merged`: Boolean ob PR gemerged wurde
- `pr_mergeable`: Boolean ob PR mergeable ist

## Fehlerbehandlung

Das System ist fehlertolerant implementiert:

1. **Logging**: Alle Operationen werden ausführlich geloggt
2. **Einzelne Fehler**: Fehler bei einzelnen Tasks stoppen nicht die gesamte Synchronisation
3. **Fehlerberichte**: Am Ende wird eine Zusammenfassung mit allen Fehlern ausgegeben
4. **Retry-Mechanismus**: Bei Netzwerkfehlern werden Requests mit Timeout wiederholt

## Beispiel-Ausgabe

```
================================================================================
GitHub Issues and Tasks Synchronization
Started at: 2025-10-19T19:17:23.897Z
================================================================================
Initializing GitHub Issue Sync Service...
Starting synchronization...
Syncing issue #42 to ChromaDB: Fix authentication bug
Successfully synced issue #42 to ChromaDB
Task abc-123-def marked as done (GitHub issue #42 closed)
================================================================================
Synchronization Results:
  Tasks checked: 15
  Tasks updated: 3
  Issues synced to ChromaDB: 10
  Pull Requests synced to ChromaDB: 5
  No errors encountered
================================================================================
Synchronization completed successfully!
Finished at: 2025-10-19T19:17:45.123Z
================================================================================
```

## Sicherheitshinweise

1. **API Keys**: Alle API-Schlüssel werden sicher in der Datenbank gespeichert
2. **Logging**: Sensible Daten werden nicht in Logs ausgegeben
3. **Berechtigungen**: Das Skript benötigt Lese-/Schreibzugriff auf:
   - Task-Datenbank
   - ChromaDB
   - GitHub API (nur Lesen)

## Wartung

### Log-Dateien

Log-Dateien werden in `logs/github_sync.log` gespeichert. Empfohlene Log-Rotation:

```bash
# Logrotate-Konfiguration
/pfad/zu/IdeaGraph-v1/logs/github_sync.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Monitoring

Überwachen Sie:

1. **Ausführungszeit**: Normale Ausführung sollte < 1 Minute dauern
2. **Fehlerrate**: Weniger als 5% Fehler bei Tasks
3. **API-Rate-Limits**: GitHub API hat Rate Limits (5000 Requests/Stunde für authentifizierte Requests)

## Troubleshooting

### Häufige Probleme

1. **"No settings found in database"**
   - Lösung: Settings-Eintrag in der Datenbank erstellen

2. **"GitHub API is not enabled"**
   - Lösung: `github_api_enabled=True` in Settings setzen

3. **"OpenAI API is not enabled"**
   - Lösung: `openai_api_enabled=True` und API-Key konfigurieren

4. **"Failed to initialize ChromaDB"**
   - Lösung: ChromaDB Credentials überprüfen (API Key, Database, Tenant)

### Debug-Modus

Für detailliertes Debugging:

```bash
python sync_github_issues.py --verbose
```

## Erweiterungen

Mögliche zukünftige Erweiterungen:

1. **Webhook-Integration**: Echtzeit-Updates statt Polling
2. **Bi-direktionale Sync**: Änderungen an Tasks zurück zu GitHub
3. **Issue-Kommentare**: Synchronisation von Kommentaren
4. **Label-Mapping**: Automatisches Mapping von GitHub Labels zu IdeaGraph Tags
5. **Milestone-Support**: Synchronisation von GitHub Milestones

## Support

Bei Fragen oder Problemen:

- GitHub Issues: [IdeaGraph-v1 Issues](https://github.com/gdsanger/IdeaGraph-v1/issues)
- Email: ca@angermeier.net
