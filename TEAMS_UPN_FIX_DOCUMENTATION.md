# Teams Bot Sender UPN Fix - Documentation

## Problem
Der Sender UPN (UserPrincipalName) ist in Chatnachrichten von Microsoft Teams über die Graph API leer. Dies ist ein bekanntes Problem bei Microsoft Teams in Verbindung mit der Graph API. Ohne UPN konnten wir:
1. Unsere eigenen Nachrichten nicht zuverlässig erkennen (Gefahr von Endlosschleifen)
2. Keine Benutzer ordnungsgemäß in der Datenbank anlegen (fehlende E-Mail, Vor- und Nachname)

## Lösung
Die Lösung verwendet die Microsoft User Object ID aus der Message JSON, um vollständige Benutzerinformationen über die Graph API abzurufen.

### Implementierte Änderungen

#### 1. GraphService: `get_user_by_id()` Methode
**Datei:** `core/services/graph_service.py`

```python
def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
    """
    Get user details by object ID
    
    Args:
        user_id: Microsoft User Object ID
        
    Returns:
        Dict with user details including UPN, email, name
    """
```

Diese Methode ruft `GET https://graph.microsoft.com/v1.0/users/{id}` auf und liefert:
- `userPrincipalName`: UPN des Benutzers
- `mail`: E-Mail-Adresse
- `displayName`: Anzeigename
- `givenName`: Vorname
- `surname`: Nachname

#### 2. TeamsListenerService: Erweiterte Nachrichtenanreicherung
**Datei:** `core/services/teams_listener_service.py`

**Bot Object ID Caching:**
Bei der Initialisierung wird die Object ID des Bots abgerufen und gecacht:
```python
self.bot_object_id = None  # Wird beim Start gefüllt
```

**Nachrichtenanreicherung:**
Neue Methode `_enrich_message_sender_info()`:
- Prüft, ob UPN leer ist
- Wenn ja: Ruft vollständige Benutzerinformationen über Object ID ab
- Reichert die Nachricht mit UPN, E-Mail und Namen an

**Verbessertes Bot-Filtering:**
Die Filterung erfolgt jetzt in drei Stufen:
1. **Primary:** Vergleich der Object IDs (funktioniert auch bei leerem UPN)
2. **Secondary:** Vergleich der UPNs (für Backward Compatibility)
3. **Tertiary:** Vergleich des Display Names (als Fallback)

#### 3. MessageProcessingService: Erweiterte Benutzerverwaltung
**Datei:** `core/services/message_processing_service.py`

**Neue Methode:** `get_or_create_user_from_sender(sender)`
- Akzeptiert vollständiges Sender-Objekt mit allen angereicherten Informationen
- Verwendet Object ID als primären Identifier
- Sucht zuerst nach `ms_user_id` (Object ID)
- Falls nicht gefunden, sucht nach `username` (UPN)
- Erstellt Benutzer mit vollständigen Informationen:
  - `ms_user_id`: Object ID
  - `username`: UPN oder Email
  - `email`: E-Mail-Adresse
  - `first_name`: Vorname
  - `last_name`: Nachname
  - `auth_type`: 'msauth'

**Backward Compatibility:**
Die alte Methode `get_or_create_user_from_upn()` bleibt als Wrapper erhalten.

## Vorteile

### 1. Zuverlässige Bot-Message-Filterung
- Funktioniert auch wenn UPN leer ist
- Verwendet Object ID als primäre Methode
- Verhindert Endlosschleifen zuverlässig

### 2. Vollständige Benutzerinformationen
- UPN wird immer verfügbar sein
- E-Mail-Adresse vorhanden
- Vor- und Nachname korrekt erfasst
- Benutzer können ordnungsgemäß angelegt werden

### 3. Robuste Implementierung
- Drei Stufen der Bot-Filterung
- Graceful Degradation bei Fehlern
- Umfangreiche Logging für Debugging
- Backward Compatible mit bestehendem Code

### 4. Vollständig getestet
- 8 neue Tests für Object ID Funktionalität
- Alle 43 bestehenden Tests bestehen
- Keine Regressionen
- Keine Security-Vulnerabilities (CodeQL Check)

## Verwendung

### Konfiguration
Stellen Sie sicher, dass das Feld `default_mail_sender` in den GraphAPI-Einstellungen korrekt konfiguriert ist:
```python
settings.default_mail_sender = 'bot@example.com'  # Bot UPN
```

### Nachrichtenverarbeitung
Die Änderungen sind transparent und erfordern keine Anpassungen im bestehenden Code:

```python
# TeamsListenerService holt automatisch Nachrichten und reichert sie an
service = TeamsListenerService(settings=settings)
messages = service.get_new_messages_for_item(item)
# Messages sind jetzt vollständig angereichert mit UPN, E-Mail, Namen

# MessageProcessingService erstellt Benutzer automatisch mit vollständigen Infos
processing_service = MessageProcessingService(settings=settings)
task = processing_service.create_task_from_analysis(item, message, analysis_result)
# Benutzer wird mit Object ID, UPN, E-Mail, Vor- und Nachname erstellt
```

## Technische Details

### Graph API Calls
Für jede Nachricht mit leerem UPN wird ein zusätzlicher API Call gemacht:
```
GET https://graph.microsoft.com/v1.0/users/{user_object_id}
```

Dies ist notwendig und acceptable, da:
- Es nur bei leeren UPNs passiert (bekanntes Microsoft Problem)
- Die Information gecached wird (im Message-Objekt)
- Es eine einmalige Operation pro Nachricht ist
- Die Alternative (keine Bot-Filterung, keine User-Creation) nicht akzeptabel ist

### Performance
- Bot Object ID wird einmalig beim Start abgerufen und gecacht
- User-Informationen werden pro Message angereichert (nur wenn UPN leer)
- Keine zusätzlichen DB-Queries (Object ID nutzt bestehenden Index)

## Testing

### Neue Tests (TeamsObjectIDTestCase)
1. `test_get_user_by_id_success` - Erfolgreicher User-Abruf
2. `test_get_user_by_id_not_found` - Fehlerbehandlung bei nicht vorhandenem User
3. `test_enrich_message_sender_info_when_upn_empty` - Nachrichtenanreicherung
4. `test_filter_bot_messages_by_object_id` - Bot-Filterung via Object ID
5. `test_get_or_create_user_from_sender_with_object_id` - User-Creation mit Object ID
6. `test_get_or_create_user_finds_existing_by_object_id` - User-Lookup via Object ID
7. `test_get_or_create_user_updates_object_id` - Object ID Update bei existierenden Usern
8. `test_get_or_create_user_from_sender_with_empty_upn` - User-Creation mit leerem UPN

Alle Tests bestehen erfolgreich.

## Logging

Umfangreiches Logging für Debugging:

```
INFO: DEBUG: Processing message msg-123
INFO:   - Sender Object ID: 'abc-123' (empty: False)
INFO:   - Sender UPN: '' (empty: True)
INFO:   - Sender Name: 'Test User'
INFO:   - Bot Object ID configured: 'bot-456' (empty: False)
INFO:   - Bot UPN configured: 'bot@example.com' (empty: False)
INFO:   - Sender UPN is empty, fetching user details by object ID: abc-123
INFO:   ✓ Enriched sender info: UPN=testuser@example.com, Name=Test User
INFO:   → ACCEPTED: Message msg-123 from testuser@example.com will be processed
```

## Zusammenfassung

Diese Lösung behebt definitiv das Problem mit leeren UPNs in Teams-Nachrichten:
- ✅ Zuverlässige Bot-Message-Filterung via Object ID
- ✅ Vollständige Benutzerinformationen für User-Creation
- ✅ Robust und gut getestet
- ✅ Backward Compatible
- ✅ Keine Security-Vulnerabilities
