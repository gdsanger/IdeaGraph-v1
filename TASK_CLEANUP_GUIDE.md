# Task Cleanup Script - Benutzeranleitung

## Überblick

Das `cleanup_tasks.py` Script ist ein Python CLI-Tool zur Identifizierung und Entfernung fehlerhafter Tasks, die keinen Owner (assigned_to) und/oder kein Item zugeordnet haben. Diese Tasks sind aufgrund eines Fehlers in der Anwendung entstanden und müssen bereinigt werden.

## Funktionen

- ✅ Identifiziert alle Tasks ohne Owner und/oder ohne Item
- ✅ Entfernt alle identifizierten Tasks aus dem System
- ✅ Bietet einen Dry-Run Modus zur Vorschau
- ✅ Gibt eine detaillierte Zusammenfassung der Aktionen aus
- ✅ Robuste Fehlerbehandlung mit entsprechenden Meldungen
- ✅ Flexible Filteroptionen
- ✅ Ausführliches Logging in Log-Dateien

## Installation

Keine zusätzliche Installation erforderlich. Das Script verwendet die bereits vorhandenen Django-Abhängigkeiten aus `requirements.txt`.

## Verwendung

### Basis-Kommandos

#### 1. Dry-Run (Vorschau ohne Löschung)

```bash
python cleanup_tasks.py --dry-run
```

Dieser Befehl zeigt alle Tasks an, die gelöscht würden, ohne sie tatsächlich zu löschen. **Empfohlen für den ersten Test!**

#### 2. Tasks bereinigen

```bash
python cleanup_tasks.py
```

Dieser Befehl führt die eigentliche Bereinigung durch. Das Script fragt zur Sicherheit nach Bestätigung, bevor es Tasks löscht.

### Erweiterte Optionen

#### Nur Tasks ohne Owner löschen

```bash
python cleanup_tasks.py --no-owner-only
```

Löscht nur Tasks, bei denen `assigned_to` NULL ist.

#### Nur Tasks ohne Item löschen

```bash
python cleanup_tasks.py --no-item-only
```

Löscht nur Tasks, bei denen `item` NULL ist.

#### Verbose-Modus (detailliertes Logging)

```bash
python cleanup_tasks.py --verbose
```

Zeigt zusätzliche Debug-Informationen an, einschließlich Details zu jedem Task wie Beschreibung und Ersteller.

#### Kombinierte Optionen

```bash
python cleanup_tasks.py --dry-run --verbose
python cleanup_tasks.py --no-owner-only --verbose
```

### Hilfe anzeigen

```bash
python cleanup_tasks.py --help
```

## Output-Beispiel

### Dry-Run Ausgabe

```
================================================================================
Task Cleanup Script
Started at: 2025-10-19T22:25:30.748905
================================================================================
Step 1: Identifying tasks to cleanup...
Found 3 task(s) to cleanup

Step 2: Task Summary
================================================================================
  Tasks Identified for Cleanup
================================================================================

Task ID: a30b8f3a-5fd9-4f6e-a07d-f4bfa24cb37c
  Title: Invalid Task - No Owner and No Item
  Status: new
  Has Owner: No
  Has Item: No
  Created At: 2025-10-19 22:24:28.897181+00:00

[weitere Tasks...]

================================================================================
Cleanup Results:
  Tasks identified: 3
  Tasks deleted: 3 (DRY RUN)
  No errors encountered
================================================================================
DRY RUN COMPLETED - No tasks were actually deleted
```

### Tatsächliche Bereinigung

```
================================================================================
WARNING: This will delete 3 task(s)
================================================================================

Do you want to proceed? (yes/no): yes

Step 3: Deleting tasks...
Successfully deleted 3 tasks

================================================================================
Cleanup Results:
  Tasks identified: 3
  Tasks deleted: 3
  No errors encountered
================================================================================
Cleanup completed successfully!
```

## Logging

Das Script erstellt automatisch Log-Dateien im Verzeichnis `logs/`:

- `logs/cleanup_tasks.log` - Enthält alle Aktionen und Ereignisse

## Testdaten erstellen

Für Tests steht ein Hilfsskript zur Verfügung:

```bash
python create_test_tasks.py
```

Dieses Script erstellt:
- 2 gültige Tasks (mit Owner und Item)
- 1 Task ohne Owner
- 1 Task ohne Item
- 1 Task ohne Owner und ohne Item

## Tests ausführen

Unit-Tests für das Cleanup-Script:

```bash
python manage.py test main.test_task_cleanup
```

Alle Tests:

```bash
python manage.py test main.test_task_cleanup -v 2
```

## Akzeptanzkriterien (erfüllt)

✅ **1. CLI-Tool Implementation**: Das Script ist als CLI-Tool implementiert und in Python geschrieben.

✅ **2. Task-Identifizierung**: Das Script identifiziert alle Tasks ohne Owner und/oder ohne Item korrekt.

✅ **3. Task-Entfernung**: Das Script entfernt alle identifizierten Tasks sicher aus dem System.

✅ **4. Zusammenfassung**: Das Script gibt eine detaillierte Zusammenfassung aus:
   - Anzahl der identifizierten Tasks
   - Anzahl der gelöschten Tasks
   - Liste aller betroffenen Tasks mit Details
   - Fehlermeldungen falls vorhanden

✅ **5. Fehlerbehandlung**: Das Script fängt Fehler ab und gibt entsprechende Meldungen aus:
   - Database-Transaktionen für sichere Löschung
   - Try-Catch Blöcke für robuste Fehlerbehandlung
   - Ausführliche Fehlermeldungen im Log

## Sicherheitshinweise

⚠️ **Wichtig**: 
- Führen Sie immer zuerst einen **Dry-Run** durch!
- Erstellen Sie vor der Bereinigung ein **Backup** der Datenbank
- Das Script fragt vor der Löschung nach Bestätigung
- Gelöschte Tasks können **nicht** wiederhergestellt werden

## Technische Details

### Lösch-Kriterien

Das Script löscht Tasks, wenn:
- `assigned_to` ist NULL (kein Owner) **ODER**
- `item` ist NULL (kein Item) **ODER**
- Beide Felder sind NULL

### Erhaltene Objekte

Das Löschen von Tasks betrifft **nicht**:
- Users (created_by, assigned_to)
- Items
- Tags
- Andere Tasks

Alle Beziehungen werden durch Django's CASCADE-Handling korrekt verwaltet.

### Performance

- Verwendet Django QuerySets für effiziente Abfragen
- Transaktionen sichern Datenintegrität
- Batch-Operationen für bessere Performance

## Fehlerbehebung

### Problem: "No module named django"

**Lösung**: Installieren Sie die Abhängigkeiten:
```bash
pip install -r requirements.txt
```

### Problem: Keine Tasks gefunden

**Lösung**: Das ist normal, wenn alle Tasks gültig sind. Verwenden Sie `create_test_tasks.py` zum Testen.

### Problem: Permission denied

**Lösung**: Machen Sie das Script ausführbar:
```bash
chmod +x cleanup_tasks.py
```

## Support und Fragen

Bei Fragen oder Problemen:
1. Überprüfen Sie die Log-Dateien in `logs/cleanup_tasks.log`
2. Führen Sie Tests aus: `python manage.py test main.test_task_cleanup`
3. Verwenden Sie den `--verbose` Modus für mehr Details

## Changelog

### Version 1.0.0 (2025-10-19)
- Initiale Implementation
- Dry-Run Modus
- Flexible Filteroptionen
- Umfassende Tests
- Ausführliche Dokumentation
