# Teams Chat Integration - Quick Reference

## 🚀 Schnellstart

### 1. Konfiguration

**Settings aktivieren:**
```
Admin → Settings
- ✅ Teams Integration aktivieren
- Teams Team ID eingeben
- Graph Poll Interval: 60 Sekunden (Standard)
```

**Voraussetzungen:**
- Graph API aktiviert
- KIGate API aktiviert
- Agent `teams-support-analysis-agent` verfügbar

### 2. Item mit Teams-Kanal verbinden

**Option A: Automatisch (empfohlen)**
- Item in Tile View öffnen
- Auf roten Teams-Indikator klicken → Kanal wird erstellt

**Option B: Manuell**
- Channel-ID des Teams-Kanals in Item-Feld `channel_id` eintragen

### 3. Polling starten

**Einmaliger Test:**
```bash
python manage.py poll_teams_messages --once
```

**Kontinuierlich (Terminal):**
```bash
python manage.py poll_teams_messages
```

**Produktiv (Systemd):**
```bash
sudo systemctl start ideagraph-teams
sudo systemctl enable ideagraph-teams
```

## 📊 Status prüfen

**Via API:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/teams/status
```

**Via Management Command:**
```bash
python manage.py shell
>>> from main.models import Settings, Item, Task
>>> Settings.objects.first().teams_enabled
>>> Item.objects.filter(channel_id__isnull=False).count()
>>> Task.objects.filter(message_id__isnull=False).count()
```

## 🔄 Workflow Übersicht

```
1. Benutzer postet in Teams-Kanal
           ↓
2. IdeaGraph holt Nachricht (Graph API)
           ↓
3. KI analysiert Nachricht (KIGate)
           ↓
4. Task wird erstellt (falls nötig)
           ↓
5. Antwort wird gepostet (Teams)
           ↓
6. Konversation wird gespeichert (Weaviate)
```

## 🛡️ Sicherheitsfeatures

- ✅ Bot-Nachrichten werden ignoriert (Name: "IdeaGraph Bot")
- ✅ Duplikate werden verhindert (Message-ID Check)
- ✅ Benutzer werden automatisch erstellt (UPN-basiert)
- ✅ API-Endpoints sind authentifiziert

## 📝 Wichtige Konzepte

### Message-ID
- Eindeutige ID der Teams-Nachricht
- Wird in Task gespeichert
- Verhindert doppelte Verarbeitung

### UPN (User Principal Name)
- Microsoft-Email des Benutzers
- Wird als Username verwendet
- Automatische Benutzererstellung

### Channel-ID
- ID des Teams-Kanals
- Muss im Item konfiguriert sein
- Leer = Feature nicht aktiv

### Poll-Intervall
- Standard: 60 Sekunden
- Konfigurierbar in Settings
- Überschreibbar via `--interval` Parameter

## 🐛 Troubleshooting

### Problem: Keine Nachrichten werden verarbeitet
```bash
# 1. Settings prüfen
python manage.py shell
>>> from main.models import Settings
>>> s = Settings.objects.first()
>>> print(f"Teams enabled: {s.teams_enabled}")
>>> print(f"Team ID: {s.teams_team_id}")

# 2. Items mit Kanälen prüfen
>>> from main.models import Item
>>> items = Item.objects.filter(channel_id__isnull=False).exclude(channel_id='')
>>> print(f"Items with channels: {items.count()}")

# 3. Manuellen Poll testen
python manage.py poll_teams_messages --once
```

### Problem: Tasks werden nicht erstellt
```bash
# KIGate Status prüfen
curl http://localhost:8000/api/agents

# Agent prüfen
curl http://localhost:8000/api/agents/teams-support-analysis-agent

# Logs ansehen
tail -f /var/log/ideagraph.log | grep teams
```

### Problem: Antworten kommen nicht in Teams an
```bash
# Graph API Berechtigungen prüfen
# - ChannelMessage.Send muss vorhanden sein

# Manuell testen
python manage.py shell
>>> from core.services.graph_service import GraphService
>>> gs = GraphService()
>>> gs.post_channel_message(
...     team_id="YOUR_TEAM_ID",
...     channel_id="YOUR_CHANNEL_ID",
...     message_content="<p>Test message</p>"
... )
```

## 📚 API Endpoints

### GET /api/teams/status
**Response:**
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "team_id": "abc123...",
    "poll_interval": 60,
    "items_with_channels": 12,
    "tasks_from_teams": 45
  }
}
```

### POST /api/teams/poll (Admin only)
**Response:**
```json
{
  "success": true,
  "result": {
    "items_checked": 5,
    "messages_found": 10,
    "messages_processed": 8,
    "tasks_created": 3,
    "responses_posted": 8,
    "errors": 0
  }
}
```

## 🔧 Konfigurationsbeispiele

### Cron Job (Alle 5 Minuten)
```cron
*/5 * * * * cd /opt/ideagraph && /opt/ideagraph/venv/bin/python manage.py poll_teams_messages --once >> /var/log/ideagraph-teams-cron.log 2>&1
```

### Systemd Service
```bash
# /etc/systemd/system/ideagraph-teams.service
[Unit]
Description=IdeaGraph Teams Integration
After=network.target postgresql.service

[Service]
Type=simple
User=ideagraph
WorkingDirectory=/opt/ideagraph
Environment="DJANGO_SETTINGS_MODULE=ideagraph.settings"
ExecStart=/opt/ideagraph/venv/bin/python manage.py poll_teams_messages
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Aktivieren
sudo systemctl daemon-reload
sudo systemctl enable ideagraph-teams
sudo systemctl start ideagraph-teams
sudo systemctl status ideagraph-teams
```

### Supervisor
```ini
# /etc/supervisor/conf.d/ideagraph-teams.conf
[program:ideagraph-teams]
command=/opt/ideagraph/venv/bin/python manage.py poll_teams_messages
directory=/opt/ideagraph
user=ideagraph
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ideagraph-teams.log
environment=DJANGO_SETTINGS_MODULE="ideagraph.settings"
```

## 📖 Weitere Dokumentation

- **Vollständige Implementierung:** `TEAMS_CHAT_INTEGRATION_IMPLEMENTATION.md`
- **Original Feature Guide:** `TEAMS_INTEGRATION_GUIDE.md`
- **Tests:** `main/test_teams_message_integration.py`

## 💡 Best Practices

1. **Intervall:** Start mit 60 Sekunden, bei Bedarf anpassen
2. **Monitoring:** Logs regelmäßig prüfen
3. **Testing:** Vor Produktiveinsatz mit `--once` testen
4. **Backups:** Regelmäßige Datenbank-Backups
5. **Updates:** Nach Updates Tests ausführen

## 🆘 Support

Bei Problemen:
1. Logs prüfen: `tail -f /var/log/ideagraph.log`
2. Status-API verwenden: `GET /api/teams/status`
3. Tests ausführen: `python manage.py test main.test_teams_message_integration`
4. Graph Explorer: https://developer.microsoft.com/graph/graph-explorer
