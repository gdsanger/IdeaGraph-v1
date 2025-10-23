# Task-Verschiebung Feature - Schnellanleitung

## Übersicht

Dieses Feature ermöglicht es, einen Task von einem Item zu einem anderen zu verschieben. Dabei werden automatisch alle zugehörigen SharePoint-Dateien mit verschoben.

## API Endpoint

```
POST /api/tasks/{task_id}/move
```

### Request Body

```json
{
  "target_item_id": "uuid-des-ziel-items"
}
```

### Erfolgreiche Antwort

```json
{
  "success": true,
  "message": "Task moved successfully to Item Name",
  "moved": true,
  "files_moved": true,
  "files_count": 2,
  "task_id": "task-uuid",
  "source_item_id": "quell-item-uuid",
  "target_item_id": "ziel-item-uuid"
}
```

## SharePoint Ordnerstruktur

### Vorher (Task in Item 1)
```
IdeaGraph/
  └── Item 1/
      └── {task-uuid}/
          ├── datei1.pdf
          └── datei2.docx
```

### Nachher (Task in Item 2)
```
IdeaGraph/
  └── Item 2/
      └── {task-uuid}/
          ├── datei1.pdf
          └── datei2.docx
```

## Funktionen

1. **Automatische Ordnerverschiebung**: Der komplette Task-Ordner mit allen Dateien wird verschoben
2. **Ordner-Erstellung**: Falls der Ziel-Item-Ordner nicht existiert, wird er automatisch erstellt
3. **Sicherheitsprüfungen**: 
   - Benutzer muss eingeloggt sein
   - Benutzer muss der Ersteller des Tasks sein oder Admin-Rechte haben
4. **Fehlerbehandlung**: Robuste Fehlerbehandlung für alle möglichen Szenarien

## Verwendungsbeispiel (JavaScript/Fetch)

```javascript
async function moveTask(taskId, targetItemId) {
    const response = await fetch(`/api/tasks/${taskId}/move`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            target_item_id: targetItemId
        })
    });
    
    const result = await response.json();
    
    if (result.success) {
        console.log('Task verschoben:', result.message);
        console.log('Dateien verschoben:', result.files_count);
    } else {
        console.error('Fehler:', result.error);
    }
}

// Verwendung
moveTask('task-uuid', 'ziel-item-uuid');
```

## Verwendungsbeispiel (Python)

```python
from main.models import Settings
from core.services.task_move_service import TaskMoveService

# Service initialisieren
settings = Settings.objects.first()
move_service = TaskMoveService(settings)

# Task verschieben
result = move_service.move_task(
    task_id='task-uuid',
    target_item_id='ziel-item-uuid',
    user=current_user
)

if result['success']:
    print(f"Task erfolgreich verschoben")
    print(f"Anzahl Dateien: {result['files_count']}")
```

## Wichtige Hinweise

1. **SharePoint-Konfiguration erforderlich**: Die Graph API muss konfiguriert sein
2. **Ordnernamen**: Item-Titel werden für SharePoint normalisiert (ungültige Zeichen werden ersetzt)
3. **Transaktionssicherheit**: Bei Datenbankfehlern wird ein Rollback durchgeführt
4. **Logging**: Alle Operationen werden protokolliert

## Fehlerbehandlung

### Mögliche Fehler

- **401 Unauthorized**: Benutzer ist nicht eingeloggt
- **403 Forbidden**: Benutzer hat keine Berechtigung
- **404 Not Found**: Task oder Ziel-Item existiert nicht
- **400 Bad Request**: Ungültige Anfrage (z.B. fehlende target_item_id)
- **500 Internal Server Error**: Serverfehler

### Beispiel Fehlerantwort

```json
{
  "error": "Task not found"
}
```

## Tests ausführen

```bash
python manage.py test main.test_task_move
```

## Weitere Informationen

Siehe [TASK_MOVE_FEATURE.md](TASK_MOVE_FEATURE.md) für detaillierte Dokumentation.
