# GitHub Issues to Tasks Sync - Quick Reference

## Schnellstart

### UI (Web-Oberfläche)
1. Öffne Item Detail-Seite
2. Klicke **"Sync GitHub Issues"** Button
3. Bestätige Dialog
4. Fertig! ✓

### CLI (Command Line)

```bash
# Ein Item synchronisieren
python sync_github_issues_to_tasks.py --item-id <uuid>

# Alle Items synchronisieren
python sync_github_issues_to_tasks.py --all-items

# Mit Optionen
python sync_github_issues_to_tasks.py --item-id <uuid> --state open --verbose
```

## Wichtige Optionen

| Option | Beschreibung | Beispiel |
|--------|--------------|----------|
| `--item-id` | Spezifisches Item | `--item-id abc-123-def` |
| `--all-items` | Alle Items mit GitHub Repo | `--all-items` |
| `--state` | Filter: `open`, `closed`, `all` | `--state open` |
| `--verbose` | Detailliertes Logging | `-v` |
| `--dry-run` | Keine Änderungen | `--dry-run` |

## Duplikaterkennung

### Zwei Methoden:
1. **GitHub Issue ID** - Exakte Übereinstimmung
2. **Titel-Ähnlichkeit** - 85% Schwellenwert

### Duplikat-Markierung:
```
*** Duplikat? *** [Original-Titel]
```

## Cron Job Beispiele

```bash
# Täglich um 3 Uhr für alle Items
0 3 * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --all-items >> logs/sync.log 2>&1

# Stündlich für bestimmtes Item
0 * * * * cd /pfad/zu/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --item-id <uuid> >> logs/sync.log 2>&1
```

## Voraussetzungen

✓ GitHub API aktiviert (Settings)  
✓ GitHub Token konfiguriert  
✓ Item hat github_repo gesetzt (Format: `owner/repo`)

## API Endpoint

```bash
POST /api/github/sync-issues-to-tasks/<item_id>
Content-Type: application/json

{
  "state": "all"  // optional: "open", "closed", "all"
}
```

## Status-Mapping

| GitHub Issue | IdeaGraph Task |
|--------------|----------------|
| Open | `new` |
| Closed | `done` |

## Fehlersuche

### Button deaktiviert?
- ☑ GitHub API aktiviert?
- ☑ Item hat github_repo?

### "No GitHub repository"?
- Setze `github_repo` im Item: `owner/repository`

### Mehr Details?
```bash
python sync_github_issues_to_tasks.py --item-id <uuid> --verbose
```

## Hilfe

```bash
# CLI Hilfe
python sync_github_issues_to_tasks.py --help

# Dokumentation
cat GITHUB_ISSUES_TO_TASKS_SYNC_GUIDE.md
```
