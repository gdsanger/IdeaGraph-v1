# Task Move Notification Feature - Implementation

## Zusammenfassung

Diese Implementierung erweitert die bestehende "Move to" Funktion für Tasks um eine E-Mail-Benachrichtigung an den Requester.

## Anforderungen (aus dem Issue)

✅ **Frage anzeigen, ob Requester informiert werden soll**
   - Modal zeigt Checkbox "Notify requester about this move"
   - Nur sichtbar wenn Task einen Requester hat

✅ **Requester-Information anzeigen**
   - Zeigt Requester-Namen und E-Mail-Adresse im Modal
   - Hilft dem Benutzer bei der Orientierung

✅ **E-Mail-Benachrichtigung an Requester**
   - Sendet E-Mail mit Task-Beschreibung
   - Informiert über Verschiebung von SourceItem zu TargetItem
   - Verwendet neues Mail-Template mit Ersetzungsvariablen

✅ **Mail-Template mit Variablen**
   - Template: `main/templates/main/mailtemplates/task_moved.html`
   - Variablen: `requester_name`, `task_title`, `task_description`, `source_item_title`, `target_item_title`

## Implementierte Änderungen

### 1. E-Mail-Template
**Datei**: `main/templates/main/mailtemplates/task_moved.html`

Neues HTML-E-Mail-Template für Benachrichtigungen über Task-Verschiebungen:
- Professionelles Design mit IdeaGraph-Branding
- Zeigt Task-Titel, Quell- und Ziel-Item
- Beinhaltet Task-Beschreibung
- Verwendet Template-Variablen für Personalisierung

### 2. E-Mail-Versand Funktion
**Datei**: `main/mail_utils.py`

Neue Funktion: `send_task_moved_notification(task_id, source_item_title, target_item_title)`

Funktionalität:
- Lädt Task mit Requester-Information
- Prüft ob Requester existiert und E-Mail-Adresse hat
- Rendert E-Mail-Template mit Kontext-Daten
- Sendet E-Mail über Microsoft Graph API
- Gibt Status und Fehlermeldungen zurück

### 3. API-Endpoint Erweiterung
**Datei**: `main/api_views.py`

Funktion: `api_task_move(request, task_id)`

Erweitert um:
- Optionaler Parameter `notify_requester` im Request-Body
- Rückgabe von Requester-Informationen in Response
- Automatische E-Mail-Benachrichtigung wenn gewünscht
- Status-Felder für Benachrichtigungsergebnis

Request-Beispiel:
```json
{
    "target_item_id": "uuid-of-target-item",
    "notify_requester": true
}
```

Response-Beispiel:
```json
{
    "success": true,
    "message": "Task moved successfully",
    "moved": true,
    "files_moved": true,
    "files_count": 2,
    "requester": {
        "id": "uuid",
        "username": "username",
        "email": "email@example.com"
    },
    "notification_sent": true,
    "notification_message": "Notification email sent successfully"
}
```

### 4. Frontend-Änderungen
**Datei**: `main/templates/main/tasks/detail.html`

#### Modal-Erweiterung:
- Neue Checkbox "Notify requester about this move"
- Info-Box mit Requester-Name und E-Mail
- Nur sichtbar wenn Task einen Requester hat

#### JavaScript-Erweiterung:
- Liest Checkbox-Status aus
- Sendet `notify_requester` Parameter an API
- Zeigt Benachrichtigungsstatus in Erfolgsmeldung

### 5. Tests
**Datei**: `main/test_task_move.py`

Neue Test-Klasse: `TaskMoveNotificationTest`

Test-Coverage:
- ✅ Erfolgreiche E-Mail-Benachrichtigung
- ✅ Task ohne Requester (keine E-Mail)
- ✅ Requester ohne E-Mail-Adresse (Fehlerbehandlung)
- ✅ API mit Benachrichtigung aktiviert
- ✅ API mit Benachrichtigung deaktiviert
- ✅ API ohne Requester gibt None zurück

**Test-Ergebnisse**: Alle 17 Tests bestanden ✓

## Workflow

```
1. Benutzer klickt "Move Task" Button
   ↓
2. Modal öffnet sich und lädt Items
   ↓
3. Wenn Task einen Requester hat:
   - Checkbox "Notify requester" wird angezeigt
   - Requester-Info wird angezeigt
   ↓
4. Benutzer wählt Ziel-Item
   ↓
5. Benutzer kann optional Checkbox aktivieren
   ↓
6. Benutzer klickt "Move Task"
   ↓
7. POST Request an /api/tasks/{id}/move
   - Mit target_item_id
   - Optional: notify_requester=true
   ↓
8. Backend verschiebt Task
   ↓
9. Falls notify_requester=true:
   - E-Mail wird an Requester gesendet
   - Benachrichtigungsstatus wird zurückgegeben
   ↓
10. Erfolgsmeldung wird angezeigt
    - Inkl. Benachrichtigungsstatus
   ↓
11. Seite wird neu geladen
```

## E-Mail-Inhalt

Die E-Mail enthält:
- **Betreff**: "Task verschoben: {Task-Titel}"
- **Anrede**: "Hallo {Requester-Name}"
- **Info-Box** mit:
  - Task-Titel
  - Von: Source Item
  - Nach: Target Item
- **Task-Beschreibung**: Vollständiger Beschreibungstext
- **Nachricht**: Erklärung warum Task verschoben wurde
- **Footer**: Automatisch generierte Nachricht

## Sicherheit

- Benutzer-Authentifizierung erforderlich
- Nur Task-Ersteller oder Admin können Tasks verschieben
- E-Mail wird nur gesendet wenn explizit aktiviert
- Validierung von Task-ID und Item-ID
- Fehlerbehandlung für fehlende Requester oder E-Mail-Adressen

## Verwendete Technologien

- **Backend**: Django 5.1+
- **E-Mail**: Microsoft Graph API
- **Template-Engine**: Django Templates
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Tests**: Django TestCase mit Mock

## Kompatibilität

- ✅ Kompatibel mit bestehender Task-Move-Funktionalität
- ✅ Keine Breaking Changes für bestehende Aufrufe
- ✅ Abwärtskompatibel (notify_requester ist optional)
- ✅ Funktioniert mit und ohne Requester

## Nächste Schritte

Für Produktiv-Einsatz empfohlen:
1. ✅ Tests durchgeführt und bestanden
2. 🔄 Code Review durchführen
3. 🔄 Sicherheitsscan durchführen (CodeQL)
4. 🔄 Manuelle Tests auf Test-System
5. 🔄 Deployment auf Produktiv-System
