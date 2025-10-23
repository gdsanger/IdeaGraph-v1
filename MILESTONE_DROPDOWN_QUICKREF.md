# Milestone Dropdown - Quick Reference Guide

## Schnellübersicht (Quick Overview)

### Was wurde implementiert? (What was implemented?)
Ein Dropdown-Menü zur Zuweisung von Milestones zu Tasks in der Task-Detailansicht.

### Wo finde ich die Änderungen? (Where to find the changes?)
**URL:** `/tasks/<task_id>/`
**UI-Position:** Zwischen "Status" und "Requester" Feldern

## Verwendung (Usage)

### Milestone einem Task zuweisen (Assign milestone to task)
1. Öffnen Sie die Task-Detailansicht
2. Wählen Sie einen Milestone aus dem Dropdown "Milestone"
3. Klicken Sie auf "Save"
4. Der Milestone wird dem Task zugewiesen

### Milestone entfernen (Remove milestone)
1. Öffnen Sie die Task-Detailansicht
2. Wählen Sie "No Milestone" aus dem Dropdown
3. Klicken Sie auf "Save"
4. Der Milestone wird vom Task entfernt

## Technische Details (Technical Details)

### Geänderte Dateien (Modified Files)
```
main/views.py                          (Backend-Logik)
main/templates/main/tasks/detail.html  (UI-Template)
main/test_tasks.py                     (Unit Tests)
```

### Code-Änderungen (Code Changes)

#### 1. Backend (main/views.py)
```python
# POST-Datenverarbeitung
milestone_id = request.POST.get('milestone', '').strip()

# Milestone-Zuweisung
if milestone_id:
    try:
        milestone = Milestone.objects.get(id=milestone_id, item=task.item)
        task.milestone = milestone
    except Milestone.DoesNotExist:
        task.milestone = None
else:
    task.milestone = None

# Context-Daten
milestones = task.item.milestones.all() if task.item else []
context['milestones'] = milestones
```

#### 2. Frontend (detail.html)
```html
<div class="col-md-3 mb-3">
    <label for="milestone" class="form-label">Milestone</label>
    <select class="form-select" id="milestone" name="milestone">
        <option value="">No Milestone</option>
        {% for milestone in milestones %}
        <option value="{{ milestone.id }}" 
                {% if task.milestone and task.milestone.id == milestone.id %}selected{% endif %}>
            {{ milestone.name }} ({{ milestone.due_date|date:"d.m.Y" }})
        </option>
        {% endfor %}
    </select>
</div>
```

## Layout-Übersicht (Layout Overview)

### Vor der Änderung (Before)
```
┌─────────────────────────────────────────────┐
│ Status     │ Requester  │ GitHub Issue     │
│ [Dropdown] │ [Dropdown] │ [ReadOnly]       │
└─────────────────────────────────────────────┘
```

### Nach der Änderung (After)
```
┌──────────────────────────────────────────────────────────┐
│ Status     │ Milestone  │ Requester  │ GitHub Issue     │
│ [Dropdown] │ [Dropdown] │ [Dropdown] │ [ReadOnly]       │
└──────────────────────────────────────────────────────────┘
```

## Datenfluss (Data Flow)

```
1. User wählt Milestone → 2. POST Request → 3. View verarbeitet
                                                      ↓
                                                4. Validation
                                                      ↓
                                        5. Database Update (task.save())
                                                      ↓
                                        6. Weaviate Sync (optional)
                                                      ↓
                                        7. Success Message
```

## API-Konsistenz (API Consistency)

Die Implementierung folgt dem gleichen Muster wie:
- `task_create` (Task-Erstellung)
- `task_edit` (Task-Bearbeitung via separate Edit-Seite)

Alle drei Views verwenden nun identische Milestone-Logik.

## Validierung (Validation)

### Gültige Werte (Valid Values)
- UUID eines Milestones, der zum selben Item gehört
- Leerer String ("") zum Entfernen

### Ungültige Werte (Invalid Values)
- UUID eines Milestones von einem anderen Item → wird zu None
- Nicht-existierende UUID → wird zu None
- Keine Fehler-Nachricht für Benutzer (silent fail zu None)

## Test-Abdeckung (Test Coverage)

### Neuer Test: `test_task_detail_milestone_assignment`
```python
# Test 1: Milestone zuweisen
POST /tasks/<id>/ mit milestone=<milestone_id>
→ Assertion: task.milestone == milestone

# Test 2: Milestone entfernen
POST /tasks/<id>/ mit milestone=""
→ Assertion: task.milestone is None
```

## Fehlerbehebung (Troubleshooting)

### Problem: Dropdown ist leer
**Lösung:** Erstellen Sie zuerst Milestones für das Item unter `/items/<item_id>/milestones/`

### Problem: Milestone wird nicht gespeichert
**Prüfen Sie:**
- Gehört der Milestone zum selben Item wie der Task?
- Wurde das Formular abgesendet (Save-Button geklickt)?
- Gibt es Fehlermeldungen in den Django-Logs?

### Problem: Milestone wird beim Speichern auf None gesetzt
**Ursache:** Milestone gehört nicht zum selben Item wie der Task
**Lösung:** Nur Milestones des Parent-Items sind zulässig

## Entwickler-Notizen (Developer Notes)

### Warum keine Migrations?
Das `milestone` ForeignKey-Feld existierte bereits im Task-Model. Es wurde nur die UI und View-Logik hinzugefügt.

### Warum col-md-3?
Um Konsistenz mit den anderen Feldern in der Reihe zu gewährleisten. Bei 4 Feldern (Status, Milestone, Requester, GitHub Issue) passt col-md-3 perfekt.

### Warum kein AJAX?
Die Implementierung folgt dem bestehenden Pattern der Inline-Bearbeitung in der Task-Detail-Ansicht, die ebenfalls eine vollständige Form-Submission verwendet.

## Weitere Ressourcen (Additional Resources)

- Vollständige Dokumentation: `MILESTONE_DROPDOWN_IMPLEMENTATION.md`
- Task Model: `main/models.py` (Zeile 479)
- Milestone Model: `main/models.py` (Zeile 375)
- Task Detail View: `main/views.py` (Zeile 1334)
- Task Detail Template: `main/templates/main/tasks/detail.html`
