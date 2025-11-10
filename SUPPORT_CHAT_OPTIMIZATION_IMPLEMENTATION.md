# Support-Chat-Optimierung und Rebranding - Implementierung

## Übersicht

Diese Implementierung erfüllt alle Anforderungen aus Issue #XX zur Optimierung des Support-Chats mit neuem Design und effizienter Anfragenbearbeitung.

## Implementierte Features

### 1. ✅ Chat im Iframe auf 100% Breite

**Datei:** `main/templates/main/embed/support.html`

**Änderung:**
```css
/* Vorher */
body {
    max-width: 420px;
}

/* Nachher */
body {
    width: 100%;
    box-sizing: border-box;
}
```

**Effekt:** Der Chat nutzt nun die volle verfügbare Breite im Iframe und passt sich responsive an.

### 2. ✅ Tab-Umbenennung: "Chat" → "Q&A Assistant"

**Datei:** `main/templates/main/embed/support.html`

**Änderung:**
```html
<!-- Vorher -->
<i class="bi bi-chat-dots"></i> Chat

<!-- Nachher -->
<i class="bi bi-robot"></i> Q&A Assistant
```

**Effekt:** Der Chat-Tab zeigt nun ein Robot-Icon und den neuen Namen "Q&A Assistant".

### 3. ✅ Tab-Umbenennung: "Frage stellen" → "Support-Anfrage stellen"

**Datei:** `main/templates/main/embed/support.html`

**Änderung:**
```html
<!-- Vorher -->
<i class="bi bi-pencil-square"></i> Frage stellen

<!-- Nachher -->
<i class="bi bi-pencil-square"></i> Support-Anfrage stellen
```

**Effekt:** Der Submit-Tab hat jetzt einen klareren, professionelleren Namen.

### 4. ✅ E-Mail als Pflichtfeld

**Datei:** `main/templates/main/embed/support.html`

**Änderungen:**
```html
<!-- Label mit Pflichtfeld-Kennzeichnung -->
<label for="reporterEmail" class="form-label">
    E-Mail <span class="text-danger">*</span>
</label>

<!-- Input mit required Attribut -->
<input type="email" class="form-control" id="reporterEmail" required>
```

**JavaScript-Validierung:**
```javascript
if (!email) {
    alert('Bitte geben Sie Ihre E-Mail-Adresse ein.');
    return;
}
```

**Effekt:** E-Mail-Adresse ist nun verpflichtend für Support-Anfragen.

### 5. ✅ Avatare im Chat (Bot und Benutzer)

**Datei:** `main/templates/main/embed/support.html`

**CSS für Avatare:**
```css
.message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    font-size: 1.125rem;
    flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.message-user .message-avatar {
    background: linear-gradient(135deg, #475569, #64748b);
}

.message-assistant .message-avatar {
    background: linear-gradient(135deg, #9333ea, #7c3aed);
}
```

**JavaScript für Avatare:**
```javascript
function addMessage(role, content) {
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    if (role === 'user') {
        avatarDiv.innerHTML = '<i class="bi bi-person-fill"></i>';
    } else {
        avatarDiv.innerHTML = '<i class="bi bi-robot"></i>';
    }
    // ...
}
```

**Effekt:** Jede Nachricht zeigt nun einen Avatar (Person für User, Robot für Bot).

### 6. ✅ Design-Anpassung an IdeaGraph Chat-Widget

**Datei:** `main/templates/main/embed/support.html`

**Anpassungen:**
- Message-Bubbles mit abgerundeten Ecken (border-radius: 1rem)
- Gradient-Hintergründe für Avatare
- Box-Shadows für Tiefe
- Farben nach IdeaGraph Corporate Identity:
  - Amber: #E59A28 (Primär)
  - Cyan: #6ECADC (Sekundär)
  - Violet: #9333ea (Bot)

**Effekt:** Konsistentes Design mit dem Rest der IdeaGraph-Plattform.

### 7. ✅ E-Mail-ähnliche Verarbeitung

**Datei:** `core/services/support_submit_service.py`

#### Neue Methode: `_get_or_create_user_by_email()`

```python
def _get_or_create_user_by_email(self, email: str):
    """
    Get or create a user by email address (like email processing)
    """
    try:
        user = User.objects.get(email=email)
        logger.info(f"Found existing user for email {email}")
        return user
    except User.DoesNotExist:
        pass
    
    # Create new user
    username = email.split('@')[0]
    
    # Make username unique if needed
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    user = User.objects.create(
        username=username,
        email=email,
        first_name='',
        last_name='',
        is_active=True
    )
    
    logger.info(f"Created new user {user.username} for email {email}")
    return user
```

**Effekt:** User werden anhand ihrer E-Mail-Adresse identifiziert oder erstellt.

#### Neue Methode: `_send_confirmation_email()`

```python
def _send_confirmation_email(self, task, user, email: str):
    """
    Send confirmation email to the requester
    """
    try:
        from core.services.email_conversation_service import EmailConversationService
        
        email_service = EmailConversationService()
        
        subject = f"Ihre Anfrage wurde erfasst: {task.title}"
        body = f"""Guten Tag,

vielen Dank für Ihre Anfrage. Wir haben Ihre Support-Anfrage erfolgreich erfasst.

**Titel:** {task.title}
**Typ:** {task.get_type_display()}
**Referenz:** {task.short_id}

Sie erhalten eine Antwort, sobald ein Agent Ihre Anfrage bearbeitet hat.

Mit freundlichen Grüßen
Ihr IdeaGraph Support-Team
"""
        
        result = email_service.send_task_reply_email(
            task=task,
            recipient_email=email,
            subject=subject,
            body_text=body
        )
        
        if result.get('success'):
            logger.info(f"Confirmation email sent to {email} for task {task.id}")
    
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}", exc_info=True)
```

**Effekt:** User erhalten automatisch eine Bestätigungs-E-Mail mit Task-Referenz.

#### Aktualisierte `submit()` Methode

```python
def submit(self, ...):
    # Get or create user by email (like email processing)
    requester_user = None
    if reporter_email:
        requester_user = self._get_or_create_user_by_email(reporter_email)
        logger.info(f"Identified/created user for email {reporter_email}")
    
    # Create task (like an email-created task)
    task = Task.objects.create(
        # ...
        requester=requester_user,  # Link to user for email replies
        # ...
    )
    
    # Send confirmation email to requester
    if reporter_email and requester_user:
        self._send_confirmation_email(task, requester_user, reporter_email)
```

**Effekt:** Support-Anfragen werden wie E-Mails verarbeitet und können per E-Mail beantwortet werden.

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User stellt Support-Anfrage                             │
│    - Titel, Beschreibung, E-Mail (Pflicht)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. System identifiziert/erstellt User                      │
│    - Suche nach existierendem User mit E-Mail              │
│    - Falls nicht vorhanden: Neuer User wird erstellt       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Task wird erstellt                                       │
│    - Mit User als requester verknüpft                      │
│    - source='support' für Tracking                         │
│    - Enriched Description mit Metadaten                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Bestätigungs-E-Mail wird gesendet                       │
│    - An User-E-Mail-Adresse                                │
│    - Mit Task-Referenz (short_id)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Agent bearbeitet Task                                    │
│    - Sieht Task in der Task-Liste                          │
│    - Kann Antwort verfassen                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. E-Mail-Antwort wird gesendet                            │
│    - An User-E-Mail (requester.email)                      │
│    - User kann per E-Mail antworten                        │
└─────────────────────────────────────────────────────────────┘
```

## Tests

**Datei:** `main/test_support_chat_ui.py`

### Test-Kategorien:

1. **UI Tests** (`SupportChatUITest`):
   - `test_support_view_accessible`: Support-View ist erreichbar
   - `test_support_view_requires_item_id`: ItemId ist erforderlich

2. **Service Tests** (`SupportSubmitServiceTest`):
   - `test_get_or_create_user_by_email_existing`: Existierenden User finden
   - `test_get_or_create_user_by_email_new`: Neuen User erstellen
   - `test_get_or_create_user_handles_duplicate_username`: Duplicate Username handling
   - `test_submit_creates_task_with_requester`: Task mit Requester erstellen
   - `test_submit_sends_confirmation_email`: Bestätigungs-E-Mail senden
   - `test_enrich_description_includes_metadata`: Description-Enrichment

### Tests ausführen:

```bash
python manage.py test main.test_support_chat_ui
```

## Sicherheit

- ✅ **CodeQL-Scan**: 0 Schwachstellen gefunden
- ✅ **E-Mail-Validierung**: Frontend (HTML5 + required) und Backend
- ✅ **User-Erstellung**: Sichere Defaults (is_active=True, kein Passwort)
- ✅ **Keine SQL-Injection**: Django ORM wird verwendet

## Design-Konsistenz

Das neue Design folgt der **IdeaGraph Corporate Identity**:

| Element | Farbe | Verwendung |
|---------|-------|------------|
| **Primär** | Amber (#E59A28) | Buttons, User-Messages, Highlights |
| **Sekundär** | Cyan (#6ECADC) | Bot-Messages, Links |
| **Bot** | Violet (#9333ea) | Bot-Avatar, Thinking-Indicator |
| **User** | Slate (#475569) | User-Avatar |
| **Hintergrund** | Dark (#1a1a1a) | Body-Hintergrund |
| **Surface** | Dark Surface (#2d2d2d) | Cards, Inputs |

## Betroffene Dateien

### Frontend:
- ✏️ `main/templates/main/embed/support.html` (ca. 200 Zeilen geändert)

### Backend:
- ✏️ `core/services/support_submit_service.py` (ca. 100 Zeilen hinzugefügt)

### Tests:
- ➕ `main/test_support_chat_ui.py` (neu erstellt, ca. 200 Zeilen)

### Dokumentation:
- ➕ `SUPPORT_CHAT_OPTIMIZATION_IMPLEMENTATION.md` (dieses Dokument)

## Nächste Schritte

1. ✅ Implementierung abgeschlossen
2. ✅ Tests erstellt
3. ✅ CodeQL-Scan durchgeführt
4. ✅ Dokumentation erstellt
5. ⏳ Manuelle Verifikation in Staging-Umgebung
6. ⏳ Deployment in Produktion

## Screenshots

![Support-Chat Demo](https://github.com/user-attachments/assets/3b720833-0720-4afd-93a1-70a51b084d59)

*Screenshot zeigt alle implementierten Features: neue Tab-Namen, Avatare im Chat, Pflicht-E-Mail-Feld, und responsive 100% Breite*

## Fazit

Alle Anforderungen aus der Issue wurden erfolgreich implementiert:

1. ✅ Chat im Iframe nutzt 100% Breite
2. ✅ Tab "Chat" umbenannt in "Q&A Assistant"
3. ✅ Tab "Frage stellen" umbenannt in "Support-Anfrage stellen"
4. ✅ E-Mail ist Pflichtfeld
5. ✅ Avatare für Bot und User implementiert
6. ✅ Design an IdeaGraph angepasst
7. ✅ Support-Anfragen werden wie E-Mails verarbeitet
8. ✅ User wird anhand E-Mail erstellt/identifiziert
9. ✅ Bestätigungs-E-Mail wird gesendet
10. ✅ Antworten können per E-Mail erfolgen

**Status:** ✅ Bereit für Code Review und Deployment
