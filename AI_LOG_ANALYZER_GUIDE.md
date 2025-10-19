# AI Log Analyzer & Auto-Task Creator

## 🎯 Übersicht

Das **AI Log Analyzer & Auto-Task Creator** System automatisiert die Erfassung, Analyse und Verarbeitung von Fehlern aus lokalen Logdateien und der Sentry-API. Relevante Fehler werden durch KI analysiert, bewertet und automatisch als Tasks in IdeaGraph angelegt. Bei bestätigten Fehlern können optional GitHub Issues erzeugt werden.

## ⚙️ Funktionsumfang

### 1️⃣ Datenquellen

- **Lokale Logs**: Zugriff auf rotierende Logdateien (`/logs/*.log`)
- **Sentry API**: Verbindung über REST API mit Authentifizierung via DSN/Token

### 2️⃣ KI-Analyse

Die KI analysiert jeden Fehler und bewertet:
- **Severity** (low, medium, high, critical)
- **Is Actionable** (ob der Fehler durch Code-Änderung behoben werden kann)
- **Root Cause** (wahrscheinliche Ursache)
- **Recommended Action** (konkrete Handlungsempfehlung)
- **Confidence** (0.0-1.0 - KI-Sicherheit in der Analyse)

### 3️⃣ Automatische Task-Erstellung

Für als "actionable" bewertete Fehler werden automatisch Tasks erstellt mit:
- Strukturiertem Markdown-Inhalt
- AI-generierten Tags (bug, auto-generated, urgent, etc.)
- Verlinkung zur Original-Fehleranalyse
- Optional: GitHub Issue-Erstellung für high/critical Fehler

## 📊 Datenmodelle

### LogEntry

Speichert einzelne Log-Einträge aus lokalen Logs und Sentry:

```python
class LogEntry(models.Model):
    source = models.CharField(max_length=20)  # 'local' oder 'sentry'
    level = models.CharField(max_length=20)   # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField()
    
    # Exception Details
    exception_type = models.CharField(max_length=255)
    exception_value = models.TextField()
    stack_trace = models.TextField()
    
    # Sentry-spezifisch
    sentry_event_id = models.CharField(max_length=100)
    sentry_issue_id = models.CharField(max_length=100)
    
    analyzed = models.BooleanField(default=False)
```

### ErrorAnalysis

Speichert KI-Analyse-Ergebnisse:

```python
class ErrorAnalysis(models.Model):
    log_entry = models.ForeignKey(LogEntry)
    
    # KI-Analyse
    severity = models.CharField(max_length=20)  # low, medium, high, critical
    is_actionable = models.BooleanField()
    summary = models.TextField()
    root_cause = models.TextField()
    recommended_action = models.TextField()
    
    # KI-Metadaten
    ai_model = models.CharField(max_length=100)
    ai_confidence = models.FloatField()  # 0.0 bis 1.0
    
    # Status
    status = models.CharField(max_length=20)  # pending, approved, rejected, task_created, issue_created
    
    # Verlinkungen
    task = models.ForeignKey(Task, null=True)
    github_issue_url = models.URLField()
```

## 🔧 Services

### LogAnalyzerService

Liest und parst lokale Logdateien:

```python
from core.services.log_analyzer_service import LogAnalyzerService

# Service initialisieren
analyzer = LogAnalyzerService()

# Logs der letzten 24 Stunden analysieren
entries = analyzer.analyze_logs(hours_back=24, min_level='WARNING')

# In Datenbank speichern
saved_count = analyzer.save_to_database(entries)
```

### SentryService

Integration mit Sentry API:

```python
from core.services.sentry_service import SentryService

# Service konfigurieren
sentry = SentryService(dsn="...", auth_token="...")
sentry.configure(organization="my-org", project_slug="my-project", auth_token="...")

# Verbindung testen
if sentry.test_connection():
    # Events der letzten 24 Stunden abrufen
    saved_count = sentry.fetch_and_save_events(hours_back=24)
```

### AIErrorAnalyzerService

KI-basierte Fehleranalyse:

```python
from core.services.ai_error_analyzer_service import AIErrorAnalyzerService

# Service initialisieren (nutzt KiGate oder OpenAI)
analyzer = AIErrorAnalyzerService(use_kigate=True)

# Einzelnen Log-Eintrag analysieren
log_entry = LogEntry.objects.get(id="...")
error_analysis = analyzer.analyze_and_save(log_entry)

# Batch-Analyse
analyses = analyzer.batch_analyze(min_level='WARNING', limit=50)
```

### AutoTaskCreatorService

Automatische Task-Erstellung:

```python
from core.services.auto_task_creator_service import AutoTaskCreatorService

# Service initialisieren
creator = AutoTaskCreatorService()

# Task aus Analyse erstellen
task = creator.create_task_from_analysis(
    error_analysis,
    create_github_issue=True  # Optional GitHub Issue erstellen
)

# Pending-Analysen verarbeiten
tasks = creator.process_pending_analyses(
    min_severity='medium',
    min_confidence=0.7,
    auto_create_github=True  # Für high/critical automatisch GitHub Issue
)
```

## 🚀 Verwendung

### Management Command

Der einfachste Weg ist der Django Management Command:

```bash
# Kompletter Workflow: Logs holen, analysieren, Tasks erstellen
python manage.py analyze_logs --all

# Nur lokale Logs holen
python manage.py analyze_logs --fetch-local --hours 24 --min-level WARNING

# Nur Sentry Events holen
python manage.py analyze_logs --fetch-sentry --hours 24

# Logs analysieren (bereits gespeicherte)
python manage.py analyze_logs --analyze --min-level ERROR

# Tasks erstellen
python manage.py analyze_logs --create-tasks --min-severity high --min-confidence 0.8

# Mit GitHub Issue-Erstellung für kritische Fehler
python manage.py analyze_logs --all --auto-github
```

### Optionen

```
--hours HOURS                  Anzahl Stunden zurück (default: 24)
--min-level LEVEL              Minimum Log-Level (WARNING, ERROR, CRITICAL)
--fetch-local                  Lokale Logs holen
--fetch-sentry                 Sentry Events holen
--analyze                      Mit KI analysieren
--create-tasks                 Tasks erstellen
--min-severity SEVERITY        Minimum Severity für Tasks (low, medium, high, critical)
--min-confidence CONFIDENCE    Minimum KI-Confidence (0.0-1.0, default: 0.7)
--auto-github                  Automatisch GitHub Issues für high/critical
--all                          Alle Schritte ausführen
--sentry-org ORG               Sentry Organisation (überschreibt Settings)
--sentry-project PROJECT       Sentry Projekt (überschreibt Settings)
--limit LIMIT                  Maximum Einträge zu verarbeiten (default: 50)
```

### Programmatische Verwendung

```python
from core.services.log_analyzer_service import LogAnalyzerService
from core.services.sentry_service import SentryService
from core.services.ai_error_analyzer_service import AIErrorAnalyzerService
from core.services.auto_task_creator_service import AutoTaskCreatorService

# 1. Logs sammeln
log_analyzer = LogAnalyzerService()
entries = log_analyzer.analyze_logs(hours_back=24, min_level='WARNING')
log_analyzer.save_to_database(entries)

# Optional: Sentry Events
sentry = SentryService(dsn=SENTRY_DSN, auth_token=SENTRY_TOKEN)
sentry.configure(org="my-org", project_slug="my-project", auth_token=SENTRY_TOKEN)
sentry.fetch_and_save_events(hours_back=24)

# 2. Mit KI analysieren
ai_analyzer = AIErrorAnalyzerService(use_kigate=True)
analyses = ai_analyzer.batch_analyze(min_level='ERROR', limit=50)

# 3. Tasks erstellen
task_creator = AutoTaskCreatorService()
tasks = task_creator.process_pending_analyses(
    min_severity='medium',
    min_confidence=0.7,
    auto_create_github=True
)

print(f"Created {len(tasks)} tasks from error analyses")
```

## 🔐 Konfiguration

### Umgebungsvariablen (.env)

```bash
# Sentry Configuration
ENABLE_SENTRY=True
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_AUTH_TOKEN=your_auth_token_here
APP_ENVIRONMENT=production

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE_NAME=ideagraph.log
LOG_MAX_BYTES=5000000
LOG_BACKUP_COUNT=5
```

### Sentry API Token

Um Sentry API zu nutzen, benötigen Sie einen Auth Token:

1. Gehen Sie zu Sentry → Settings → Auth Tokens
2. Erstellen Sie einen neuen Token mit Berechtigung: `event:read`, `project:read`
3. Setzen Sie `SENTRY_AUTH_TOKEN` in `.env`

### KiGate / OpenAI

Die KI-Analyse nutzt entweder KiGate oder direkt OpenAI:

- **KiGate**: Konfigurieren Sie in Settings → KiGate API
- **OpenAI**: Konfigurieren Sie in Settings → OpenAI API

## 📈 Workflow

```
┌─────────────────┐
│  Lokale Logs    │
│   /logs/*.log   │
└────────┬────────┘
         │
         v
┌─────────────────┐        ┌─────────────────┐
│  Log Analyzer   │───────>│   LogEntry      │
│    Service      │        │   (Datenbank)   │
└─────────────────┘        └────────┬────────┘
                                    │
         ┌──────────────────────────┘
         │
         v
┌─────────────────┐        ┌─────────────────┐
│  Sentry API     │───────>│   LogEntry      │
│    Service      │        │   (Datenbank)   │
└─────────────────┘        └────────┬────────┘
                                    │
                                    v
                           ┌─────────────────┐
                           │  AI Analyzer    │
                           │    Service      │
                           └────────┬────────┘
                                    │
                                    v
                           ┌─────────────────┐
                           │ ErrorAnalysis   │
                           │  (Datenbank)    │
                           └────────┬────────┘
                                    │
                                    v
                           ┌─────────────────┐
                           │  Auto-Task      │
                           │   Creator       │
                           └────────┬────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    v                               v
           ┌─────────────────┐           ┌─────────────────┐
           │      Task       │           │  GitHub Issue   │
           │   (IdeaGraph)   │           │   (Optional)    │
           └─────────────────┘           └─────────────────┘
```

## 🔍 Beispiel-Output

### Log-Analyse

```bash
$ python manage.py analyze_logs --all

=== AI Log Analyzer & Auto-Task Creator ===
Looking back: 24 hours
Minimum level: WARNING

📂 Fetching local logs...
✅ Saved 6 new log entries from local files

🔍 Fetching Sentry events...
✅ Saved 12 new events from Sentry

🤖 Analyzing errors with AI...
✅ Created 15 error analyses

📊 Analysis Summary:
  - critical: 2
  - high: 5
  - medium: 6
  - low: 2
  - Actionable: 11

📝 Creating tasks from analyses...
✅ Created 8 tasks

📋 Created Tasks:
  - 🐛 Fix Database connection lost
    GitHub: https://github.com/user/repo/issues/123
  - 🐛 Fix ValueError: Invalid configuration
  - 🐛 Handle FileNotFoundError in log operations
  ... and 5 more

✨ Log analysis complete!
```

### Erstellter Task (Beispiel)

```markdown
# 🐛 Fehlerbehebung

Dieser Task wurde automatisch aus einem Fehler-Log erstellt.

## 📊 Fehler-Details

- **Severity:** Critical
- **Source:** Local Log
- **Level:** CRITICAL
- **Logger:** error_prone_service
- **Timestamp:** 2025-10-19 11:34:34
- **AI Confidence:** 95%

## 🤖 KI-Analyse

**Zusammenfassung:** Database connection lost - kritischer Systemfehler

**Ursache:** Die Datenbankverbindung wurde unerwartet geschlossen, 
möglicherweise durch Netzwerk-Timeout oder DB-Server-Neustart.

## ✅ Empfohlene Maßnahmen

1. Implementieren Sie Connection-Pooling mit automatischem Reconnect
2. Fügen Sie Retry-Logik für DB-Operationen hinzu
3. Überwachen Sie die DB-Verbindung mit Health-Checks

## 📝 Original-Fehlermeldung

```
CRITICAL: System failure: Database connection lost - cannot 
establish connection to primary database
```

## 🔍 Exception Details

**Type:** `RuntimeError`

**Stack Trace:**
```
  File "/path/to/file.py", line 58, in <module>
    raise RuntimeError("Database connection lost...")
RuntimeError: Database connection lost - cannot establish 
connection to primary database
```

---
**Log Entry ID:** `abc123-def456-...`
**Analysis ID:** `xyz789-abc123-...`
```

## 🧪 Testen

### Test-Logs generieren

```bash
python generate_test_logs.py
```

Dies erzeugt verschiedene Log-Einträge (INFO, WARNING, ERROR, CRITICAL) 
mit Exceptions für Testing.

### Workflow testen

```bash
# 1. Test-Logs generieren
python generate_test_logs.py

# 2. Logs analysieren (ohne KI)
python manage.py analyze_logs --fetch-local --hours 1

# 3. Mit KI analysieren (erfordert KiGate/OpenAI)
python manage.py analyze_logs --analyze --limit 5

# 4. Tasks erstellen
python manage.py analyze_logs --create-tasks --min-severity low
```

## 🛠️ Troubleshooting

### Logs werden nicht gefunden

- Prüfen Sie ob `/logs` Verzeichnis existiert
- Verifizieren Sie `LOG_DIR` in `.env`
- Stellen Sie sicher, dass Logs geschrieben wurden

### Sentry Connection fehlschlägt

- Verifizieren Sie `SENTRY_DSN` und `SENTRY_AUTH_TOKEN`
- Testen Sie mit `sentry_service.test_connection()`
- Prüfen Sie Token-Berechtigungen (event:read, project:read)

### KI-Analyse schlägt fehl

- Verifizieren Sie KiGate oder OpenAI Konfiguration
- Prüfen Sie ob der Agent `error_analyzer` in KiGate existiert
- Fallback zu OpenAI Direct API wird automatisch versucht

### Tasks werden nicht erstellt

- Prüfen Sie `min_severity` und `min_confidence` Parameter
- Stellen Sie sicher, dass Analysen als "actionable" markiert sind
- Prüfen Sie ob Error-Analysen den Status "pending" haben

## 📝 Weitere Informationen

- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - Allgemeine Logging-Dokumentation
- [KIGate_Documentation.md](docs/KIGate_Documentation.md) - KiGate Integration
- [GITHUB_API_USAGE.md](docs/GITHUB_API_USAGE.md) - GitHub Integration

## 🔄 Automatisierung

### Cron Job (Linux/Mac)

```bash
# Täglich um 2 Uhr morgens ausführen
0 2 * * * cd /path/to/IdeaGraph-v1 && python manage.py analyze_logs --all --auto-github
```

### Windows Task Scheduler

Erstellen Sie eine Task mit:
- Programm: `python.exe`
- Argumente: `manage.py analyze_logs --all --auto-github`
- Arbeitsverzeichnis: `C:\path\to\IdeaGraph-v1`
- Zeitplan: Täglich um 02:00

## 🎯 Best Practices

1. **Regelmäßige Ausführung**: Führen Sie den Analyzer täglich aus
2. **Threshold anpassen**: Passen Sie `min_severity` und `min_confidence` an
3. **GitHub Issues**: Nur für high/critical automatisch erstellen
4. **Review**: Überprüfen Sie pending Analysen manuell vor Task-Erstellung
5. **Cleanup**: Löschen Sie alte Log-Einträge regelmäßig

---

*Entwickelt für IdeaGraph v1.0*
