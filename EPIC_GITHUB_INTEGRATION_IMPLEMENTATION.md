# Epic: Verbesserte Task-/GitHub-Integration & Kanban-Übersicht

## 📋 Zusammenfassung

Diese Dokumentation beschreibt die Implementierung der verbesserten Task-/GitHub-Integration und Kanban-Übersicht für IdeaGraph v1.0.

## ✅ Implementierte Features

### 1. Navigation Menu Updates

**Problem:** Die Kanban-Ansichten waren vorhanden, aber nicht über die Navigation erreichbar. Der Nutzer fragte: "Wo sind die KanbanViews? Hast Du die vergessen?"

**Lösung:** Das Tasks-Dropdown-Menü wurde erweitert und strukturiert:

#### Liste der neuen Menüpunkte:
- **List Views:**
  - All Tasks
  - My Tasks
  - Tasks in Arbeit (neu sichtbar!)
  - Tasks zum Testen (neu sichtbar!)
  
- **Kanban Views:**
  - Meine Tasks (neu sichtbar!)
  - Meine Anforderungen (neu sichtbar!)

**Datei:** `main/templates/main/base.html`

### 2. Automatischer Statusflow

#### 2.1 GitHub Issue → Task Status "Testing"

**Anforderung:** Wenn ein GitHub Issue geschlossen wird, soll der zugehörige Task automatisch auf Status "Testing" gesetzt werden.

**Implementierung:**
- **Datei:** `core/services/github_task_sync_service.py`
- **Funktion:** `sync_github_issues_to_tasks()`
- **Logik:**
  ```python
  # Check if task already exists by GitHub Issue ID
  existing_task = Task.objects.filter(
      item=item,
      github_issue_id=issue_number
  ).first()
  
  if existing_task:
      # Update task status based on GitHub issue state
      if issue_state == 'closed' and existing_task.status not in ['done', 'testing']:
          existing_task.status = 'testing'
          existing_task.github_synced_at = timezone.now()
          existing_task.save()
  ```

**Verhalten:**
- Bestehende Tasks werden aktualisiert (keine Duplikate mehr)
- Status 'done' und 'testing' werden respektiert (nicht überschrieben)
- Nur Tasks mit Status 'new', 'review', 'ready', 'working' werden auf 'testing' gesetzt

#### 2.2 Task → GitHub Issue: Status "Working"

**Anforderung:** Wenn ein Task an GitHub gesendet wird, soll der Status automatisch auf "Working" gesetzt werden.

**Status:** ✅ Bereits implementiert!

**Datei:** `main/api_views.py`
**Funktion:** `api_task_create_github_issue()`
**Zeile:** 2523

```python
# Automatic status change: Task sent to GitHub → status = "working"
task.status = 'working'
```

### 3. Bestehende Features (bereits vorhanden)

Die folgenden Features waren bereits implementiert:

#### Kanban Views:
- `my_tasks_kanban` - Zeigt alle Tasks des eingeloggten Users
- `my_requirements_kanban` - Zeigt Tasks, bei denen User Autor oder Stakeholder ist
- Drag & Drop Status-Änderung funktioniert via HTMX
- Farbcodierung nach Status:
  - Neu = Grau (⚪)
  - Review = Lila (🟣)
  - Ready = Hellgrün (🟢)
  - Working = Blau (🔵)
  - Testing = Gelb (🟡)
  - Erledigt = Grün (✅)

#### Filtered Views:
- `tasks_in_progress` - Zeigt alle Tasks mit Status "working"
- `tasks_for_testing` - Zeigt alle Tasks mit Status "testing"

#### Item-Übersicht:
- Task-Badges in List- und Tile-View
- Zeigt Anzahl neuer, offener und erledigter Tasks
- Bereits implementiert in `main/views.py` (Zeilen 903-908)

## 🧪 Tests

### Test Suite: `main/test_github_status_sync.py`

Vier umfassende Tests wurden erstellt:

1. **test_existing_task_status_updated_when_github_issue_closed**
   - Testet, ob bestehende Tasks auf 'testing' aktualisiert werden
   
2. **test_new_task_created_with_testing_status_for_closed_issue**
   - Testet, ob neue Tasks mit 'testing' Status erstellt werden für geschlossene Issues
   
3. **test_new_task_created_with_new_status_for_open_issue**
   - Testet, ob neue Tasks mit 'new' Status erstellt werden für offene Issues
   
4. **test_task_status_not_updated_if_already_done**
   - Testet, ob 'done' Status respektiert wird

**Ergebnis:** ✅ Alle 4 Tests bestanden

```bash
python manage.py test main.test_github_status_sync
```

## 📊 Technische Details

### Statusflow-Diagramm

```
GitHub Issue erstellt (open)
    ↓
Task erstellt (status = 'new')
    ↓
Task manuell auf 'ready' gesetzt
    ↓
Task zu GitHub gesendet
    ↓
Task Status = 'working' (automatisch)
Task assigned_to = copilot (automatisch)
    ↓
GitHub Copilot bearbeitet Issue
    ↓
GitHub Issue geschlossen
    ↓
Sync ausgeführt
    ↓
Task Status = 'testing' (automatisch)
    ↓
Manueller Test durchgeführt
    ↓
Task Status = 'done' (manuell)
```

### API Endpoints

- **POST** `/tasks/{task_id}/set_status` - Drag & Drop Status-Änderung (Kanban)
- **POST** `/api/tasks/{task_id}/create-github-issue` - Task zu GitHub senden
- **POST** `/api/github/sync-issues-to-tasks/{item_id}` - GitHub Issues synchronisieren

### Konfiguration

#### Settings Model Felder:
- `github_api_enabled` - GitHub Integration aktivieren
- `github_token` - GitHub PAT Token
- `github_default_owner` - Standard GitHub Owner
- `github_default_repo` - Standard GitHub Repository
- `github_copilot_username` - GitHub Copilot Username für Auto-Assignment

## 🚀 Verwendung

### Sync-Script ausführen

```bash
# Sync für spezifisches Item
python sync_github_issues_to_tasks.py --item-id <uuid>

# Sync für alle Items mit GitHub Repo
python sync_github_issues_to_tasks.py --all-items

# Nur offene Issues
python sync_github_issues_to_tasks.py --item-id <uuid> --state open

# Verbose Logging
python sync_github_issues_to_tasks.py --item-id <uuid> --verbose
```

### Cron Job Setup

```bash
# Täglich um 3 Uhr morgens alle Items synchronisieren
0 3 * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --all-items >> logs/sync_github_tasks.log 2>&1
```

## 📝 Dateien geändert

1. `main/templates/main/base.html` - Navigation Menu erweitert
2. `core/services/github_task_sync_service.py` - Status-Update-Logik hinzugefügt
3. `main/test_github_status_sync.py` - Neue Test-Suite erstellt

## 🔍 Review Checklist

- [x] Alle Tests bestehen
- [x] Django Check läuft ohne Fehler
- [x] Navigation Menu zeigt alle Views korrekt an
- [x] Automatischer Statusflow funktioniert
- [x] Keine Duplikate mehr beim Sync
- [x] Status 'done' und 'testing' werden respektiert
- [x] Dokumentation erstellt

## 🎯 Zusammenfassung

Die Epic-Anforderungen wurden vollständig implementiert:

✅ Automatischer Statuswechsel zwischen GitHub und IdeaGraph  
✅ Kanban-Ansichten sind über Navigation erreichbar  
✅ Filtered Views für "Tasks in Arbeit" und "Tasks zum Testen" zugänglich  
✅ Item-Übersicht zeigt Task-Badges (war bereits implementiert)  
✅ Drag & Drop Statusänderung funktioniert (war bereits implementiert)  
✅ Farbcodierung nach Status vorhanden (war bereits implementiert)  

Die Hauptarbeit bestand darin, die Navigation zu erweitern und die GitHub-Sync-Logik zu verbessern, damit bestehende Tasks aktualisiert werden statt Duplikate zu erstellen.
