# 🚀 GitHub Documentation Sync - Quick Reference

## 📋 Schnellübersicht

Automatische Synchronisation von Markdown-Dokumentationen aus GitHub-Repositories nach IdeaGraph.

## ⚡ Quick Commands

```bash
# Einzelnes Item synchronisieren
python manage.py sync_github_docs --item <item_id>

# Alle Items synchronisieren
python manage.py sync_github_docs --all

# Test ausführen
python test_github_doc_sync.py
```

## 🔧 Setup (5 Minuten)

1. **GitHub Token erstellen**
   - Gehe zu GitHub → Settings → Developer Settings → Personal Access Tokens
   - Erstelle Token mit `repo` Berechtigung
   - Kopiere Token

2. **In IdeaGraph konfigurieren**
   ```python
   # Settings in Admin-Oberfläche
   github_api_enabled = True
   github_token = "ghp_YOUR_TOKEN"
   ```

3. **Item konfigurieren**
   ```python
   # Item bearbeiten
   github_repo = "owner/repo"  # oder "https://github.com/owner/repo"
   ```

4. **Erste Synchronisation**
   ```bash
   python manage.py sync_github_docs --item <item_id>
   ```

## 📦 Was wird synchronisiert?

- ✅ Alle `.md` Dateien (rekursiv)
- ✅ In SharePoint: `IdeaGraph/{ItemTitle}/`
- ✅ In Datenbank: ItemFile-Einträge
- ✅ In Weaviate: KnowledgeObjects (type: "documentation")

## 🔄 Automatisierung

### Cron-Job (alle 3 Stunden)
```bash
0 */3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all >> logs/sync_github_docs.log 2>&1
```

### Systemd Timer
```ini
# /etc/systemd/system/ideagraph-sync-docs.timer
[Unit]
Description=IdeaGraph GitHub Documentation Sync Timer

[Timer]
OnCalendar=*-*-* 00/3:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/ideagraph-sync-docs.service
[Unit]
Description=IdeaGraph GitHub Documentation Sync

[Service]
Type=oneshot
WorkingDirectory=/path/to/IdeaGraph-v1
ExecStart=/usr/bin/python manage.py sync_github_docs --all
User=ideagraph
```

```bash
# Aktivieren
sudo systemctl daemon-reload
sudo systemctl enable ideagraph-sync-docs.timer
sudo systemctl start ideagraph-sync-docs.timer

# Status prüfen
sudo systemctl status ideagraph-sync-docs.timer
```

## 🗂️ Dateistruktur

```
IdeaGraph-v1/
├── core/services/
│   ├── github_service.py              # GitHub API (erweitert)
│   └── github_doc_sync_service.py     # Sync Service (NEU)
├── main/management/commands/
│   └── sync_github_docs.py            # CLI Command (NEU)
├── logs/
│   └── ideagraph.log                  # Log-Ausgabe
└── GITHUB_DOC_SYNC_GUIDE.md           # Vollständige Dokumentation
```

## 🎯 Typische Workflows

### Workflow 1: Neues Item mit Doku erstellen
```bash
# 1. Item in IdeaGraph erstellen
# 2. GitHub Repository URL setzen
# 3. Synchronisieren
python manage.py sync_github_docs --item <item_id>
```

### Workflow 2: Bestehende Items aktualisieren
```bash
# Alle Items mit GitHub-Repos synchronisieren
python manage.py sync_github_docs --all
```

### Workflow 3: Nach Git Push automatisch syncen
```yaml
# .github/workflows/sync-to-ideagraph.yml
name: Sync to IdeaGraph
on:
  push:
    branches: [main]
    paths: ['docs/**', '*.md']
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger IdeaGraph Sync
        run: |
          ssh user@server "cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all"
```

## 📊 Weaviate Schema

```json
{
  "type": "documentation",
  "title": "Dateiname oder erste Überschrift",
  "description": "Erste 500 Zeichen",
  "source": "GitHub",
  "file_url": "SharePoint URL",
  "github_url": "https://github.com/owner/repo/blob/main/path/file.md",
  "github_path": "path/file.md",
  "github_repo": "owner/repo",
  "related_item": "item-uuid",
  "tags": ["docs", "documentation", "github"],
  "last_synced": "2025-10-27T17:30:00Z"
}
```

## 🔍 Troubleshooting

| Problem | Lösung |
|---------|--------|
| "GitHub API not enabled" | Settings: `github_api_enabled = True` |
| "No GitHub token" | Settings: `github_token = "ghp_..."` |
| "Invalid repo URL" | Format: `owner/repo` oder `https://github.com/owner/repo` |
| "File too large" | Max 10 MB pro Datei |
| "SharePoint error" | Prüfe Graph API Credentials |
| "No .md files found" | Repository hat keine Markdown-Dateien |

## 📈 Performance

| Metrik | Wert |
|--------|------|
| Scan-Zeit | ~5s für 100 Dateien |
| Download pro Datei | ~0.5s |
| SharePoint Upload | ~2s |
| Weaviate Sync | ~0.3s |
| **Total** | ~2-3 Minuten für 50 Dateien |

## 🔐 Sicherheit

### Minimale GitHub Token Permissions
```
✅ repo (für private repos)
✅ public_repo (für public repos)
❌ Keine anderen Permissions nötig
```

### Rate Limits
- **Mit Token**: 5000 Requests/Stunde
- **Ohne Token**: 60 Requests/Stunde

## 🧪 Testing

```bash
# Syntax-Check
python -m py_compile core/services/github_doc_sync_service.py

# Integration Test
python test_github_doc_sync.py

# Django Tests
python manage.py test

# Management Command Test
python manage.py sync_github_docs --help
```

## 📝 Konfigurationsdateien

### .env
```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_DOC_SYNC_INTERVAL=180
```

### Settings (Datenbank)
```python
github_api_enabled = True
github_token = "ghp_..."
github_api_base_url = "https://api.github.com"
github_default_owner = "gdsanger"  # optional
github_default_repo = "IdeaGraph-v1"  # optional
```

## 🎨 Beispiel-Output

```
Syncing documentation for all items with GitHub repositories

✓ Sync completed!
Items processed: 5
Items synced: 5
Total files synced: 47

⚠ Errors occurred:
  - Error processing docs/large_file.md: File too large (12MB > 10MB limit)
```

## 🔗 API Beispiele

### Python
```python
from core.services.github_doc_sync_service import GitHubDocSyncService

service = GitHubDocSyncService()
result = service.sync_item(item_id="uuid-here")

print(f"Synced {result['files_synced']} files")
```

### Django Shell
```python
python manage.py shell

>>> from core.services.github_doc_sync_service import GitHubDocSyncService
>>> service = GitHubDocSyncService()
>>> result = service.sync_all_items()
>>> result
{'success': True, 'items_synced': 5, 'total_files_synced': 47}
```

## 📚 Weiterführende Links

- [Vollständige Dokumentation](GITHUB_DOC_SYNC_GUIDE.md)
- [GitHub API Docs](https://docs.github.com/en/rest)
- [Weaviate Docs](https://weaviate.io/developers/weaviate)

## 💡 Pro-Tips

1. **Strukturiere Markdown-Dateien** mit klaren Überschriften für bessere Titel
2. **Nutze `/docs` Ordner** für übersichtliche Repository-Struktur
3. **Regelmäßige Syncs** mit Cron-Jobs für automatische Updates
4. **Monitoring** der Log-Dateien für frühzeitige Fehlererkennung
5. **Token-Rotation** alle 90 Tage aus Sicherheitsgründen

## 🆘 Schnelle Hilfe

```bash
# Logs prüfen
tail -f logs/ideagraph.log | grep github_doc_sync

# Service-Status testen
python test_github_doc_sync.py

# Einzelnes Item neu syncen
python manage.py sync_github_docs --item <item_id>

# Alle Items neu syncen
python manage.py sync_github_docs --all
```

---

**Version**: 1.0.0  
**Erstellt**: 2025-10-27  
**Autor**: IdeaGraph Team
