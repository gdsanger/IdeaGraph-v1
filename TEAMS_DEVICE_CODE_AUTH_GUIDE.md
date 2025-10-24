# Teams Device Code Authentication - Implementation Guide

## Übersicht

Diese Implementierung löst das Problem, dass das Posten von Nachrichten in Teams-Channels nicht mit reinen App-Berechtigungen (client credentials) funktioniert, sondern delegierte Benutzerberechtigungen erfordert.

## Das Problem

Microsoft Graph API unterstützt zwei Arten von Authentifizierung:

1. **Application Permissions (App-only)**: 
   - Verwendet Client Credentials Flow
   - Funktioniert ohne Benutzerkontext
   - **Kann NICHT für Channel-Nachrichten verwendet werden**

2. **Delegated Permissions (On-behalf-of-user)**:
   - Erfordert Benutzerkontext
   - **Erforderlich für Channel-Nachrichten**
   - Unterstützt Device Code Flow für Server-Anwendungen

## Die Lösung: Device Code Flow mit Token-Persistierung

### Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│  1. Einmalige Device Code Authentifizierung                 │
│     - User führt "python manage.py auth_teams" aus          │
│     - Authentifiziert sich mit Microsoft Account            │
│     - Token wird mit offline_access Scope gespeichert       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Token-Persistierung                                      │
│     - Access Token & Refresh Token auf Disk gespeichert     │
│     - Datei: data/msal_token_cache.bin                      │
│     - MSAL SerializableTokenCache                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Automatische Token-Erneuerung                           │
│     - MSAL prüft Token-Ablauf automatisch                   │
│     - Verwendet Refresh Token bei Bedarf                    │
│     - Transparente Erneuerung ohne User-Interaktion         │
│     - 90 Tage "sliding window" mit regelmäßiger Nutzung     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Teams Channel Posting                                    │
│     - GraphService nutzt delegierten Token                  │
│     - TeamsService postet Nachrichten als User              │
│     - Keine User-Interaktion mehr erforderlich              │
└─────────────────────────────────────────────────────────────┘
```

### Komponenten

#### 1. DelegatedAuthService (`core/services/delegated_auth_service.py`)

Hauptservice für delegierte Authentifizierung:

**Funktionen:**
- `initiate_device_flow()` - Startet Device Code Flow
- `acquire_token_by_device_flow()` - Wartet auf User-Authentifizierung
- `get_access_token()` - Liefert gültigen Token (cached oder erneuert)
- `has_valid_token()` - Prüft Token-Verfügbarkeit
- `clear_token_cache()` - Löscht Token-Cache

**Token-Scopes:**
```python
SCOPES = [
    'https://graph.microsoft.com/ChannelMessage.Send',
    'https://graph.microsoft.com/Channel.ReadBasic.All',
    'https://graph.microsoft.com/Team.ReadBasic.All',
    'offline_access'  # Ermöglicht Refresh Token
]
```

**Token-Persistierung:**
- Verwendet MSAL's SerializableTokenCache
- Speichert in `data/msal_token_cache.bin`
- Automatisches Serialisieren/Deserialisieren
- Threadsafe durch MSAL

#### 2. GraphService Updates (`core/services/graph_service.py`)

Erweitert um Delegated Auth Support:

**Neue Parameter:**
- `use_delegated_auth` - Bool, ob delegierte Auth verwendet werden soll
- `delegated_auth_service` - Instanz von DelegatedAuthService

**Token-Acquisition Logic:**
```python
def _get_access_token(self) -> str:
    # Priorität 1: Delegated Token (falls aktiviert)
    if self.use_delegated_auth:
        return self.delegated_auth_service.get_access_token()
    
    # Priorität 2: Client Credentials (fallback)
    return self._get_client_credentials_token()
```

#### 3. TeamsService Updates (`core/services/teams_service.py`)

Verwendet automatisch delegierte Auth wenn aktiviert:

```python
use_delegated = getattr(self.settings, 'teams_use_delegated_auth', True)
self.graph_service = GraphService(
    settings=settings, 
    use_delegated_auth=use_delegated
)
```

#### 4. Management Command (`main/management/commands/auth_teams.py`)

CLI-Tool für Authentifizierung:

**Verwendung:**
```bash
# Erstmalige Authentifizierung
python manage.py auth_teams

# Status prüfen
python manage.py auth_teams --check

# Token löschen (für Re-Auth)
python manage.py auth_teams --clear
```

**Ablauf:**
1. Startet Device Code Flow
2. Zeigt User Code und URL an
3. Wartet auf User-Authentifizierung
4. Speichert Token automatisch
5. Bestätigt erfolgreiche Authentifizierung

#### 5. Database Updates (`main/models.py`)

Neue Settings-Felder:

```python
teams_use_delegated_auth = BooleanField(
    default=True,
    help_text='Use delegated user authentication for Teams posting'
)

teams_delegated_user_id = CharField(
    max_length=255,
    blank=True,
    help_text='User ID for delegated authentication'
)
```

## Setup & Konfiguration

### 1. Azure AD App-Registrierung aktualisieren

**API Permissions hinzufügen:**
1. Gehe zu Azure Portal → App Registrations → Deine App
2. Navigiere zu "API permissions"
3. Füge hinzu (als **Delegated** permissions):
   - `ChannelMessage.Send`
   - `Channel.ReadBasic.All`
   - `Team.ReadBasic.All`
   - `offline_access` (automatisch inkludiert)
4. **WICHTIG**: Klicke "Grant admin consent"

**Wichtiger Hinweis:**
- Diese Berechtigungen müssen als **Delegated** (nicht Application) hinzugefügt werden
- Delegated Permissions = Im Namen eines Users
- Application Permissions = App-only (funktioniert NICHT für Channel-Nachrichten)

### 2. Datenbank migrieren

```bash
python manage.py migrate
```

### 3. Einstellungen konfigurieren

Im Django Admin oder Settings:
- ✅ **teams_enabled**: True
- ✅ **teams_use_delegated_auth**: True (Standard)
- **teams_team_id**: Deine Teams Team ID
- **client_id**: Azure AD Application ID
- **tenant_id**: Azure AD Tenant ID

### 4. Erstmalige Authentifizierung

```bash
python manage.py auth_teams
```

**Was passiert:**
1. Befehl startet Device Code Flow
2. Du siehst:
   ```
   Please follow these steps:
   1. Open a browser and go to: https://microsoft.com/devicelogin
   2. Enter this code: XXXX-XXXX
   3. Sign in with your Microsoft account
   
   Waiting for authentication...
   ```
3. Öffne Browser → Gehe zur URL → Gib Code ein
4. Melde dich mit deinem Microsoft-Account an (derselbe, der Teams nutzt)
5. Bestätige die Berechtigungen
6. Befehl bestätigt: "✓ Authentication successful!"

**Token wird gespeichert in:** `data/msal_token_cache.bin`

### 5. Teams Channel Posting testen

Nun kannst du Nachrichten in Channels posten:

```python
from core.services.teams_service import TeamsService

teams_service = TeamsService()
result = teams_service.create_channel_for_item(
    item_title="Test Item",
    item_description="Test Description"
)
# Channel wird erstellt UND Welcome-Message gepostet!
```

## Token-Lifecycle

### Access Token
- **Gültigkeit**: 60 Minuten
- **Erneuerung**: Automatisch durch MSAL
- **Verwendung**: Für API-Calls

### Refresh Token
- **Gültigkeit**: 90 Tage (sliding window)
- **Erneuerung**: Bei jeder Verwendung verlängert
- **Speicherung**: In msal_token_cache.bin
- **Scope**: `offline_access` erforderlich

### Automatische Erneuerung

MSAL's `acquire_token_silent()` prüft automatisch:
1. Ist Access Token noch gültig? → Verwende aus Cache
2. Access Token abgelaufen? → Verwende Refresh Token
3. Refresh Token abgelaufen? → User muss erneut authentifizieren

```python
# Dieser Code funktioniert automatisch für 90 Tage:
token = auth_service.get_access_token()
if token is None:
    # Nur nach 90 Tagen ohne Nutzung
    print("Re-authentication required: python manage.py auth_teams")
```

## Troubleshooting

### Problem: "Delegated authentication token not available"

**Ursache:** Kein gültiger Token vorhanden

**Lösung:**
```bash
python manage.py auth_teams
```

### Problem: Token abgelaufen nach 90 Tagen

**Ursache:** Refresh Token ist abgelaufen

**Lösung:**
```bash
python manage.py auth_teams --clear
python manage.py auth_teams
```

### Problem: "Failed to post channel message" mit 403 Forbidden

**Mögliche Ursachen:**
1. Delegated Permissions nicht erteilt
2. Admin Consent fehlt
3. User hat keine Berechtigung für Team/Channel

**Lösung:**
1. Prüfe Azure AD Permissions (müssen "Delegated" sein)
2. Erteile Admin Consent
3. Stelle sicher, dass der authentifizierte User Mitglied des Teams ist

### Problem: Channel wird erstellt, aber keine Nachricht gepostet

**Ursache:** Wahrscheinlich werden noch App-only Permissions verwendet

**Lösung:**
1. Prüfe `teams_use_delegated_auth = True` in Settings
2. Führe Device Code Auth aus: `python manage.py auth_teams`
3. Prüfe Logs für Fehlerdetails

### Problem: Device Code Authentication schlägt fehl

**Mögliche Ursachen:**
1. Falscher Client ID / Tenant ID
2. App nicht als Public Client konfiguriert
3. Device Code Flow in Azure AD blockiert

**Lösung:**
1. Prüfe Azure AD App-Registrierung → Authentication
2. Aktiviere "Allow public client flows" = Yes
3. Prüfe Conditional Access Policies

## Status prüfen

```bash
# Token-Status prüfen
python manage.py auth_teams --check

# Ausgabe bei erfolgreicher Auth:
✓ Authenticated
  User: user@domain.com
  Account ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  ✓ Valid token available

# Ausgabe wenn nicht authentifiziert:
✗ Not authenticated
  Run this command without --check to authenticate.
```

## Sicherheit

### Token-Speicherung
- Token werden lokal in `data/msal_token_cache.bin` gespeichert
- Datei sollte nur vom Applikations-User lesbar sein
- In Production: Verwende sichere Dateiberechtigungen (600)

**Empfohlen:**
```bash
chmod 600 data/msal_token_cache.bin
```

### Best Practices
1. **Secrets Management**: Client Secret weiterhin in Umgebungsvariablen
2. **Token Cache**: Nicht in Versionskontrolle committen (bereits in .gitignore)
3. **User Account**: Verwende dedizierten Service-Account für Production
4. **Monitoring**: Überwache Token-Erneuerung in Logs

### Service Account empfohlen

Für Production:
1. Erstelle dedizierten Microsoft-User (z.B. ideagraph-bot@domain.com)
2. Füge diesen User zum Team hinzu
3. Authentifiziere mit diesem Account
4. Verwende separaten Token-Cache pro Environment

## Migration von alter Implementation

### Schritte für bestehende Installation

1. **Code Update**
   ```bash
   git pull
   pip install -r requirements.txt
   ```

2. **Datenbank Migration**
   ```bash
   python manage.py migrate
   ```

3. **Azure AD Permissions aktualisieren**
   - Füge Delegated Permissions hinzu (siehe oben)
   - Grant Admin Consent

4. **Settings aktualisieren**
   - Setze `teams_use_delegated_auth = True`

5. **Initiale Authentifizierung**
   ```bash
   python manage.py auth_teams
   ```

6. **Testen**
   - Erstelle Test-Channel in UI
   - Prüfe ob Welcome-Message gepostet wird
   - Prüfe Logs für Fehler

### Backwards Compatibility

Die Implementation ist abwärtskompatibel:
- Wenn `teams_use_delegated_auth = False`: Verwendet alte Client Credentials
- Wenn delegated auth fehlschlägt: Automatischer Fallback zu app-only
- Bestehende Channels funktionieren weiterhin

## Logs & Monitoring

### Relevante Log-Einträge

**Erfolgreiche Auth:**
```
[delegated_auth_service] Device flow initiated successfully
[delegated_auth_service] Successfully acquired token via device flow
[graph_service] Using delegated user access token
[teams_service] Successfully posted message with ID: xxx
```

**Token Refresh:**
```
[delegated_auth_service] Successfully acquired token (from cache or refresh)
```

**Re-Auth erforderlich:**
```
[delegated_auth_service] No accounts in token cache - device flow authentication required
[graph_service] Delegated authentication token not available
```

## Vorteile dieser Lösung

1. ✅ **Einmalige Setup**: Device Code nur beim ersten Mal
2. ✅ **90 Tage Gültigkeit**: Sliding window mit automatischer Verlängerung
3. ✅ **Transparent**: Automatische Token-Erneuerung
4. ✅ **Keine User-Interaktion**: Nach Setup komplett automatisch
5. ✅ **MSAL-basiert**: Verwendet offizielle Microsoft-Bibliothek
6. ✅ **Sicher**: Token-Cache auf Disk, kein Token in Datenbank
7. ✅ **Monitored**: Vollständiges Logging aller Operationen

## Weitere Informationen

- [Microsoft Identity Platform - Device Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Microsoft Graph API Permissions](https://docs.microsoft.com/en-us/graph/permissions-reference)
- [Teams Channel Messages API](https://docs.microsoft.com/en-us/graph/api/channel-post-messages)
