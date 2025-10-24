# Microsoft Teams Integration - Implementation Guide

## Übersicht
IdeaGraph v1.0 unterstützt jetzt die Integration mit Microsoft Teams. Diese Integration ermöglicht es, für Items automatisch Teams-Channels zu erstellen, in denen Nachrichten gesendet und diskutiert werden können.

## Features

✅ **Teams Channel Management**
- Automatische Erstellung von Channels für Items
- Willkommensnachricht mit konfigurierbarer Vorlage
- Visuelle Anzeige des Channel-Status im TileView
- Direkte Links zu Teams-Channels

✅ **Benutzerfreundliche UI**
- Grüner Indikator = Channel existiert (klicken zum Öffnen)
- Roter Indikator = Kein Channel (klicken zum Erstellen)
- Toast-Benachrichtigungen für Erfolg/Fehler
- Asynchrone Channel-Erstellung ohne Seitenreload

✅ **Sicherheit & Logging**
- Vollständiges Logging aller Teams-Operationen
- Fehlerbehandlung mit benutzerfreundlichen Nachrichten
- Keine Exposition von internen Fehlerdetails
- Authentifizierung erforderlich für alle Operationen

## Azure AD Konfiguration

### 1. Berechtigungen in Azure Portal konfigurieren

Die Teams Integration verwendet die gleiche App-Registrierung wie die Graph API Integration. Folgende Berechtigungen werden benötigt:

1. Gehe zu [Azure Portal](https://portal.azure.com)
2. Navigiere zu **Azure Active Directory** → **App registrations**
3. Wähle deine bestehende IdeaGraph App-Registrierung
4. Gehe zu **API permissions**
5. Füge folgende Microsoft Graph-Berechtigungen hinzu:
   - `Channel.Create` - Zum Erstellen von Channels
   - `ChannelMessage.Send` - Zum Senden von Nachrichten in Channels
   - `TeamMember.Read.All` - (Optional) Zum Lesen von Team-Mitgliedern
   - `Group.Read.All` - Zum Lesen von Team-Informationen
6. Klicke auf **Grant admin consent** für die Organisation

### 2. Teams Team ID ermitteln

Um die Team ID zu finden:

**Methode 1: Über Teams Web-App**
1. Öffne Microsoft Teams im Browser
2. Navigiere zu deinem Team
3. Klicke auf die drei Punkte (•••) neben dem Team-Namen
4. Wähle "Link zum Team abrufen"
5. Die Team ID ist im Link enthalten: `groupId=TEAM-ID-HIER`

**Methode 2: Über Graph Explorer**
1. Gehe zu [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer)
2. Führe aus: `GET https://graph.microsoft.com/v1.0/me/joinedTeams`
3. Suche dein Team und kopiere die `id`

**Methode 3: Über PowerShell**
```powershell
Connect-MicrosoftTeams
Get-Team -DisplayName "Dein Team Name"
```

## IdeaGraph Konfiguration

### 1. Graph API aktivieren

Stelle sicher, dass die Graph API Integration bereits konfiguriert ist:

1. Login als Admin
2. Navigiere zu **Admin** → **Settings**
3. Scrolle zum Abschnitt **Graph API Settings**
4. Konfiguriere:
   - ✅ **Enable Graph API**: Aktiviert
   - **CLIENT_ID**: Deine Azure AD Application (Client) ID
   - **CLIENT_SECRET**: Dein Azure AD Client Secret
   - **TENANT_ID**: Deine Azure AD Directory (Tenant) ID
5. Klicke auf **Update Settings**

### 2. Teams Integration aktivieren

1. Login als Admin
2. Navigiere zu **Admin** → **Settings**
3. Scrolle zum Abschnitt **Microsoft Teams Integration**
4. Konfiguriere:
   - ✅ **Enable Teams Integration**: Aktiviert
   - **Teams Team ID**: Deine Team ID (siehe oben)
   - **Teams Welcome Post Template**: Vorlage für Willkommensnachricht
5. Klicke auf **Update Settings**

### 3. Willkommensnachricht anpassen

Die Willkommensnachricht kann mit Platzhaltern angepasst werden:

**Standard-Vorlage:**
```
Willkommen im Channel für {{Item}}! Hier können Sie Nachrichten zu diesem Item senden und diskutieren.
```

**Platzhalter:**
- `{{Item}}` - Wird durch den Titel des Items ersetzt

**Beispiele:**
```
🎉 Willkommen im Channel für das Item "{{Item}}"!

Hier kannst du:
✅ Fragen stellen
💡 Ideen diskutieren
📝 Updates teilen
🤝 Zusammenarbeiten
```

## Verwendung

### Teams Channel für ein Item erstellen

**Im TileView (Kanban-Ansicht):**

1. Navigiere zu **Items** → **Tile View**
2. Finde das Item, für das du einen Channel erstellen möchtest
3. Schaue auf das Teams-Symbol in der oberen rechten Ecke der Kachel:
   - 🔴 **Roter Indikator** = Kein Channel vorhanden
   - 🟢 **Grüner Indikator** = Channel existiert bereits
4. Klicke auf das rote Teams-Symbol
5. Warte auf die Toast-Benachrichtigung "Teams channel created successfully!"
6. Der Indikator wird grün und zeigt an, dass der Channel erfolgreich erstellt wurde

**Was passiert automatisch:**
1. Ein neuer Channel wird im konfigurierten Teams-Workspace erstellt
2. Der Channel-Name entspricht dem Item-Titel
3. Eine Willkommensnachricht wird gepostet
4. Die Channel ID wird im Item gespeichert
5. Alle Team-Mitglieder haben automatisch Zugriff auf den Channel

### Auf einen bestehenden Teams Channel zugreifen

1. Navigiere zu **Items** → **Tile View**
2. Finde das Item mit grünem Teams-Indikator
3. Klicke auf das grüne Teams-Symbol
4. Microsoft Teams wird in einem neuen Tab geöffnet

## Technische Details

### Datenbank-Modell

**Settings Model - Erweiterungen:**
```python
teams_enabled = BooleanField(default=False)  # Aktiviert/Deaktiviert Teams Integration
teams_team_id = CharField(max_length=255)    # ID des Teams Workspace
team_welcome_post = TextField()              # Vorlage für Willkommensnachricht
```

**Item Model - Erweiterungen:**
```python
channel_id = CharField(max_length=255)  # Teams Channel ID
```

### API Endpoint

**POST** `/api/items/<item_id>/create-teams-channel`

Erstellt einen Teams Channel für das angegebene Item.

**Authentifizierung:** Erforderlich (Session-basiert)

**Request:**
```json
{
  // Keine zusätzlichen Parameter erforderlich
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Teams channel 'Item Title' created successfully",
  "channel_id": "19:abc123...",
  "web_url": "https://teams.microsoft.com/...",
  "display_name": "Item Title"
}
```

**Error Responses:**
```json
// Teams Integration nicht konfiguriert
{
  "error": "Teams integration not configured properly. Please contact your administrator."
}

// Channel existiert bereits
{
  "error": "Channel already exists for this item",
  "channel_id": "19:existing-channel-id"
}

// Allgemeiner Fehler
{
  "error": "Failed to create Teams channel. Please try again later."
}
```

### Teams Service

Der `TeamsService` in `core/services/teams_service.py` stellt folgende Methoden bereit:

```python
# Channel erstellen
create_channel(display_name: str, description: str) -> Dict

# Nachricht posten
post_message_to_channel(channel_id: str, message_content: str) -> Dict

# Web URL abrufen
get_channel_web_url(channel_id: str) -> str

# Komplette Channel-Einrichtung für Item
create_channel_for_item(item_title: str, item_description: str) -> Dict
```

### Logging

Alle Teams-Operationen werden protokolliert:

```python
logger.info('Creating channel for item: {item_title}')
logger.info('Successfully created channel with ID: {channel_id}')
logger.error('Failed to create channel: {error_message}')
```

Log-Einträge können im Django Admin oder über die Log-Analyzer-Funktion eingesehen werden.

## Bekannte Einschränkungen

### Nachricht-Pinning
Das automatische Anpinnen von Nachrichten erfordert die spezielle Berechtigung `ChannelMessage.UpdatePolicyViolation.All`, die typischerweise nicht für Standard-App-Registrierungen verfügbar ist. Diese Berechtigung erfordert erhöhte Rechte und muss möglicherweise manuell durchgeführt werden.

**Workaround:** Nachrichten manuell in Teams anpinnen.

### Mitglieder-Management
Das programmatische Hinzufügen von Mitgliedern zu Channels wird derzeit nicht unterstützt. Bei der Erstellung eines Standard-Channels haben automatisch alle Team-Mitglieder Zugriff.

Für private Channels oder spezifisches Mitglieder-Management würden zusätzliche Berechtigungen benötigt:
- `ChannelMember.ReadWrite.All`
- `TeamMember.ReadWrite.All`

## Troubleshooting

### Problem: "Teams integration not configured"

**Lösung:**
1. Überprüfe, ob Graph API aktiviert ist
2. Stelle sicher, dass CLIENT_ID, CLIENT_SECRET und TENANT_ID korrekt sind
3. Aktiviere Teams Integration in den Settings
4. Stelle sicher, dass eine gültige Teams Team ID konfiguriert ist

### Problem: Channel wird erstellt, aber keine Nachricht gepostet

**Mögliche Ursachen:**
1. Fehlende `ChannelMessage.Send` Berechtigung
2. Network-Timeout bei der Nachricht-Übermittlung

**Lösung:**
1. Überprüfe die Berechtigungen in Azure AD
2. Stelle sicher, dass Admin Consent erteilt wurde
3. Prüfe die Log-Dateien für detaillierte Fehlermeldungen

### Problem: "Channel already exists for this item"

**Ursache:** Das Item hat bereits eine Channel ID gespeichert.

**Lösung:**
- Wenn der Channel wirklich nicht existiert, kann die Channel ID im Django Admin gelöscht werden
- Navigiere zu Admin → Items → Wähle das Item → Lösche die Channel ID

### Problem: Token-Fehler oder Authentifizierungs-Fehler

**Lösung:**
1. Überprüfe, ob die Graph API Credentials korrekt sind
2. Stelle sicher, dass das Client Secret nicht abgelaufen ist
3. Prüfe, ob alle erforderlichen Berechtigungen erteilt wurden
4. Lösche den Token-Cache: `python manage.py shell` → `from django.core.cache import cache` → `cache.clear()`

## Sicherheit

### Best Practices

1. **Secrets Management**
   - Speichere CLIENT_SECRET niemals in der Versionskontrolle
   - Verwende Umgebungsvariablen oder Azure Key Vault für Produktionsumgebungen
   - Rotiere Secrets regelmäßig

2. **Berechtigungen**
   - Vergebe nur die minimal erforderlichen Berechtigungen
   - Prüfe regelmäßig die erteilten Berechtigungen
   - Dokumentiere alle verwendeten Berechtigungen

3. **Logging**
   - Alle Operationen werden geloggt
   - Sensitive Daten werden nicht in Logs geschrieben
   - Fehlerdetails sind nur für Administratoren sichtbar

4. **Error Handling**
   - Stack Traces werden nicht an Benutzer weitergegeben
   - Generische Fehlermeldungen für Benutzer
   - Detaillierte Fehler nur in Server-Logs

## Tests

Die Implementation enthält umfassende Tests:

**Ausführen der Tests:**
```bash
python manage.py test main.test_teams_integration
```

**Test-Abdeckung:**
- Settings Model Tests (6 Tests)
- Item Model Tests (3 Tests)
- View Integration Tests (3 Tests)
- Service Error Handling Tests

**Alle Tests bestanden:** ✅ 12/12

## Support

Bei Problemen oder Fragen:
1. Prüfe die Log-Dateien
2. Konsultiere die Troubleshooting-Sektion
3. Kontaktiere den System-Administrator
4. Erstelle ein GitHub Issue mit detaillierten Fehlerinformationen

## Changelog

### Version 1.0 (2025-10-24)
- ✅ Initial Implementation
- ✅ Settings Model Erweiterung
- ✅ Item Model Erweiterung
- ✅ Teams Service Implementation
- ✅ UI Integration im TileView
- ✅ API Endpoint für Channel-Erstellung
- ✅ Logging & Error Handling
- ✅ Toast-Benachrichtigungen
- ✅ Security Fixes (Stack Trace Exposure)
- ✅ Umfassende Tests
- ✅ Dokumentation

## Weiterführende Links

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/api/overview)
- [Teams API Reference](https://docs.microsoft.com/en-us/graph/api/resources/teams-api-overview)
- [Channel Resource Type](https://docs.microsoft.com/en-us/graph/api/resources/channel)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
