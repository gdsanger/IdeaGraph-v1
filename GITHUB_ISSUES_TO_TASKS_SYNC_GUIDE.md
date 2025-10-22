# GitHub Issues to Tasks Synchronization

## Übersicht

Diese Funktion ermöglicht die automatische Synchronisation von GitHub-Issues (sowohl geschlossen als auch offen) in die Aufgabenliste eines Items in IdeaGraph. Die Funktion erkennt automatisch bereits vorhandene Issues und markiert potenzielle Duplikate.

## Features

### 1. Automatische Task-Erstellung
- Erstellt Tasks aus GitHub-Issues, die noch nicht in IdeaGraph existieren
- Unterstützt sowohl offene als auch geschlossene Issues
- Setzt den Task-Status automatisch:
  - `new` für offene Issues
  - `done` für geschlossene Issues

### 2. Duplikatserkennung

Die Funktion erkennt Duplikate auf zwei Wegen:

#### a) GitHub Issue ID Prüfung
Prüft, ob ein Task mit der gleichen GitHub-Issue-ID bereits im Item existiert.

#### b) Titel-Ähnlichkeitsvergleich
Vergleicht die Titel der GitHub-Issues mit den vorhandenen Tasks und erkennt ähnliche Titel (Schwellenwert: 85% Ähnlichkeit).

### 3. Duplikat-Behandlung
Bei erkannten Duplikaten wird der Task trotzdem erstellt, aber mit dem Präfix **"*** Duplikat? ***"** im Titel markiert. Dies ermöglicht es dem Benutzer, die Situation manuell zu überprüfen und zu entscheiden.

## Verwendung

### Über die Benutzeroberfläche

#### Voraussetzungen
- GitHub API muss in den Einstellungen aktiviert sein
- Das Item muss ein GitHub-Repository gesetzt haben

#### Schritte
1. Öffnen Sie ein Item in der Detail-Ansicht
2. Klicken Sie auf den Button **"Sync GitHub Issues"** (rechts oben bei den Action-Buttons)
3. Bestätigen Sie den Dialog
4. Die Synchronisation läuft und erstellt neue Tasks
5. Die Seite wird automatisch neu geladen, um die neuen Tasks anzuzeigen

Der Button ist nur aktiviert, wenn:
- GitHub API in den Einstellungen aktiviert ist
- Das Item ein GitHub-Repository gesetzt hat

### Über das CLI-Skript

Das CLI-Skript `sync_github_issues_to_tasks.py` ermöglicht die Automatisierung der Synchronisation.

#### Grundlegende Verwendung

```bash
# Synchronisiere Issues für ein bestimmtes Item (per UUID)
python sync_github_issues_to_tasks.py --item-id <uuid>

# Synchronisiere Issues für alle Items mit GitHub-Repositories
python sync_github_issues_to_tasks.py --all-items

# Synchronisiere nur offene Issues
python sync_github_issues_to_tasks.py --item-id <uuid> --state open

# Synchronisiere nur geschlossene Issues
python sync_github_issues_to_tasks.py --item-id <uuid> --state closed

# Verbose-Modus (detailliertes Logging)
python sync_github_issues_to_tasks.py --item-id <uuid> --verbose

# Dry-Run (keine Änderungen vornehmen)
python sync_github_issues_to_tasks.py --item-id <uuid> --dry-run
```

#### Optionen

| Option | Beschreibung |
|--------|--------------|
| `--item-id <uuid>` | UUID des Items, für das Issues synchronisiert werden sollen |
| `--all-items` | Synchronisiere für alle Items mit gesetztem GitHub-Repository |
| `--owner <owner>` | GitHub Repository Owner (überschreibt Item-Einstellung) |
| `--repo <repo>` | GitHub Repository Name (überschreibt Item-Einstellung) |
| `--state <state>` | Filter nach Issue-Status: `open`, `closed`, oder `all` (Standard: `all`) |
| `-v, --verbose` | Aktiviere detailliertes (DEBUG) Logging |
| `--dry-run` | Führe eine Test-Ausführung ohne Änderungen durch |

#### Als Cron Job

Für regelmäßige automatische Synchronisation können Sie einen Cron Job einrichten:

```bash
# Täglich um 3 Uhr morgens für alle Items
0 3 * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --all-items >> logs/sync_github_tasks.log 2>&1

# Jede Stunde für ein bestimmtes Item
0 * * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --item-id abc-123-def >> logs/sync_github_tasks.log 2>&1

# Alle 6 Stunden für alle Items (nur offene Issues)
0 */6 * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --all-items --state open >> logs/sync_github_tasks.log 2>&1
```

#### Umgebungsvariablen

Sie können Standardwerte über Umgebungsvariablen setzen:

```bash
export GITHUB_SYNC_ITEM_ID=abc-123-def
export GITHUB_SYNC_OWNER=gdsanger
export GITHUB_SYNC_REPO=IdeaGraph-v1
export GITHUB_SYNC_STATE=all

# Dann einfach ausführen
python sync_github_issues_to_tasks.py
```

## API-Endpunkt

### POST /api/github/sync-issues-to-tasks/<item_id>

Synchronisiert GitHub Issues zu Tasks für ein bestimmtes Item.

#### Request Body (JSON)
```json
{
  "owner": "optional-owner",
  "repo": "optional-repo",
  "state": "all"
}
```

#### Response (Erfolg)
```json
{
  "success": true,
  "issues_checked": 15,
  "tasks_created": 10,
  "duplicates_by_id": 3,
  "duplicates_by_title": 2,
  "errors": []
}
```

#### Response (Fehler)
```json
{
  "success": false,
  "error": "Fehlermeldung",
  "details": "Detaillierte Informationen"
}
```

## Beispiel-Ausgabe

### Erfolgreiche Synchronisation (CLI)

```
================================================================================
GitHub Issues to Tasks Synchronization
Started at: 2025-10-22T15:30:00.000Z
================================================================================
Initializing GitHub Task Sync Service...
Found 3 items with GitHub repositories

✓ Item 'IdeaGraph Development': 8 tasks created from 15 issues
✓ Item 'Documentation Updates': 3 tasks created from 5 issues
✓ Item 'Bug Fixes': 12 tasks created from 20 issues

================================================================================
Synchronization Results:
  Items processed: 3
  Items succeeded: 3
  Items failed: 0
  Total issues checked: 40
  Total tasks created: 23
  Total duplicates by ID: 10
  Total duplicates by title: 7
  No errors encountered
================================================================================
Synchronization completed successfully!
Finished at: 2025-10-22T15:31:23.456Z
================================================================================
```

### Mit Duplikaten

```
Processing issue #42: Fix authentication bug
Issue #42 already exists (by ID)
Created task for issue #42: *** Duplikat? *** Fix authentication bug

Processing issue #43: Update documentation
Issue #43 appears to be duplicate of: Update docs
Created task for issue #43: *** Duplikat? *** Update documentation
```

## Funktionsweise

### Workflow

1. **Abrufen der GitHub Issues**
   - Verwendet GitHub API um alle Issues des Repositories abzurufen
   - Unterstützt Paginierung für große Issue-Listen
   - Filtert nach dem gewünschten Status (open/closed/all)

2. **Duplikatsprüfung für jedes Issue**
   - Prüft GitHub Issue ID gegen vorhandene Tasks
   - Berechnet Titel-Ähnlichkeit mit allen vorhandenen Tasks
   - Markiert Issue als Duplikat wenn Schwellenwert überschritten

3. **Task-Erstellung**
   - Erstellt Task mit Issue-Details (Titel, Beschreibung, URL)
   - Setzt Status basierend auf Issue-Status
   - Fügt "*** Duplikat? ***" Präfix hinzu wenn nötig
   - Verknüpft Task mit GitHub Issue ID

4. **Weaviate-Synchronisation** (optional)
   - Speichert Issue-Daten in Weaviate für semantische Suche
   - Fehler bei Weaviate-Sync stoppen nicht die Task-Erstellung

### Titel-Ähnlichkeitsberechnung

Die Titel-Ähnlichkeit wird mit dem **SequenceMatcher** Algorithmus berechnet:

```python
# Beispiel
"Fix authentication bug"  vs. "Fix Authentication Bug"  → 100% ähnlich
"Fix login issue"        vs. "Fix Login Problem"       → ~85% ähnlich
"Add new feature"        vs. "Fix bug in login"        → ~30% ähnlich
```

Schwellenwert: **85%** - Titel mit 85% oder mehr Ähnlichkeit werden als Duplikate erkannt.

## Konfiguration

### Erforderliche Settings

In der Django-Settings-Tabelle müssen folgende Felder konfiguriert sein:

```python
github_api_enabled = True              # GitHub API aktivieren
github_token = "ghp_xxx..."           # GitHub Personal Access Token
github_default_owner = "username"      # Standard GitHub Owner
github_default_repo = "repository"     # Standard Repository
```

### GitHub Token Berechtigungen

Der GitHub Token benötigt folgende Berechtigungen:
- `repo` - Vollzugriff auf Repositories (zum Lesen von Issues)

## Fehlerbehebung

### Häufige Probleme

#### "No GitHub repository specified"
**Problem:** Item hat kein GitHub-Repository gesetzt.
**Lösung:** Setzen Sie das `github_repo` Feld im Item (Format: `owner/repo`).

#### "GitHub API is not enabled"
**Problem:** GitHub API ist in den Settings nicht aktiviert.
**Lösung:** Aktivieren Sie `github_api_enabled` in den Settings.

#### "No admin user found"
**Problem:** Kein Admin-Benutzer im System (nur CLI-Skript).
**Lösung:** Erstellen Sie einen Benutzer mit der Rolle `admin`.

#### Button ist deaktiviert
**Mögliche Gründe:**
- GitHub API nicht aktiviert in Settings
- Item hat kein GitHub-Repository gesetzt
**Lösung:** Überprüfen Sie beide Voraussetzungen.

### Debug-Modus

Für detailliertes Debugging verwenden Sie:

```bash
python sync_github_issues_to_tasks.py --item-id <uuid> --verbose
```

Dies aktiviert DEBUG-Level Logging mit detaillierten Informationen über:
- Jedes verarbeitete Issue
- Duplikatsprüfungen
- API-Aufrufe
- Fehler und Warnungen

## Sicherheitshinweise

1. **API-Token-Sicherheit**
   - GitHub Token wird verschlüsselt in der Datenbank gespeichert
   - Token erscheint nicht in Logs

2. **Berechtigungen**
   - Nur Admin und Item-Besitzer können Synchronisation auslösen
   - CLI-Skript verwendet Admin-Benutzer für Task-Erstellung

3. **Rate Limiting**
   - GitHub API hat Rate Limits (5000 Requests/Stunde für authentifizierte Requests)
   - Bei großen Repositories kann das Limit erreicht werden

## Technische Details

### Architektur

```
GitHubTaskSyncService
  ├── _calculate_title_similarity()
  ├── _check_duplicate_by_issue_id()
  ├── _check_duplicate_by_title()
  └── sync_github_issues_to_tasks()
      ├── GitHubService.list_issues()
      ├── Task.objects.create()
      └── WeaviateGitHubIssueSyncService (optional)
```

### Abhängigkeiten

- `core.services.github_service.GitHubService` - GitHub API Integration
- `core.services.weaviate_github_issue_sync_service` - Weaviate Synchronisation
- `main.models.Task` - Task Model
- `difflib.SequenceMatcher` - Titel-Ähnlichkeitsberechnung

### Datenbank-Schema

Relevante Task-Felder:
- `github_issue_id` (Integer) - GitHub Issue Nummer
- `github_issue_url` (URL) - Link zum GitHub Issue
- `github_synced_at` (DateTime) - Zeitpunkt der Synchronisation
- `title` (String) - Task-Titel (mit optionalem Duplikat-Präfix)
- `description` (Text) - Issue-Body
- `status` (String) - Task-Status

## Erweiterungsmöglichkeiten

Zukünftige Verbesserungen könnten umfassen:

1. **Bidirektionale Synchronisation**
   - Änderungen an Tasks zurück zu GitHub synchronisieren
   - Task-Status mit Issue-Status synchronisieren

2. **Label-Mapping**
   - Automatisches Mapping von GitHub Labels zu IdeaGraph Tags

3. **Milestone-Support**
   - GitHub Milestones mit IdeaGraph Milestones synchronisieren

4. **Comment-Synchronisation**
   - Issue-Kommentare als Task-Notizen importieren

5. **Webhook-Integration**
   - Echtzeit-Updates statt Polling
   - Automatische Task-Aktualisierung bei Issue-Änderungen

## Support

Bei Fragen oder Problemen:

- GitHub Issues: [IdeaGraph-v1 Issues](https://github.com/gdsanger/IdeaGraph-v1/issues)
- Email: ca@angermeier.net

## Changelog

### Version 1.0.0 (2025-10-22)
- Initiale Implementierung
- Duplikatserkennung (ID und Titel)
- UI-Integration
- CLI-Skript
- API-Endpunkt
- Umfassende Tests
