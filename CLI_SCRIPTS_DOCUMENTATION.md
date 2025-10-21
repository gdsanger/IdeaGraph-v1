# CLI Scripts Dokumentation - IdeaGraph

Diese Dokumentation bietet eine vollständige Übersicht über alle CLI-Skripte im IdeaGraph-Projekt, einschließlich Verwendungsbeispielen und Cron-Automatisierung.

---

## 📑 Inhaltsverzeichnis

1. [Standalone CLI Scripts](#standalone-cli-scripts)
   - [cleanup_tasks.py](#1-cleanup_taskspy)
   - [cleanup_unused_tags.py](#2-cleanup_unused_tagspy)
   - [sync_github_issues.py](#3-sync_github_issuespy)
   - [create_test_tasks.py](#4-create_test_taskspy)
   - [generate_test_logs.py](#5-generate_test_logspy)
   - [demo_log_analyzer.py](#6-demo_log_analyzerpy)

2. [Django Management Commands](#django-management-commands)
   - [analyze_logs](#1-analyze_logs)
   - [process_mails](#2-process_mails)
   - [sync_tags_to_weaviate](#3-sync_tags_to_weaviate)
   - [init_admin](#4-init_admin)

3. [Cron Automation](#cron-automation)
4. [Best Practices](#best-practices)

---

## Standalone CLI Scripts

### 1. cleanup_tasks.py

**Zweck**: Identifiziert und entfernt fehlerhafte Tasks, die keinen Owner (assigned_to) und/oder kein Item zugeordnet haben.

#### Features
- ✅ Identifiziert Tasks ohne Owner und/oder ohne Item
- ✅ Entfernt alle identifizierten Tasks aus dem System
- ✅ Dry-Run Modus zur Vorschau
- ✅ Detaillierte Zusammenfassung der Aktionen
- ✅ Robuste Fehlerbehandlung
- ✅ Flexible Filteroptionen
- ✅ Ausführliches Logging

#### Verwendung

```bash
# Vorschau der zu löschenden Tasks (Dry-Run)
python cleanup_tasks.py --dry-run

# Tasks mit Bestätigungsaufforderung bereinigen
python cleanup_tasks.py

# Nur Tasks ohne Owner löschen
python cleanup_tasks.py --no-owner-only

# Nur Tasks ohne Item löschen
python cleanup_tasks.py --no-item-only

# Mit ausführlichem Logging
python cleanup_tasks.py --verbose

# Kombinierte Optionen
python cleanup_tasks.py --dry-run --verbose
```

#### Hilfe anzeigen

```bash
python cleanup_tasks.py --help
```

#### Cron Automation

```bash
# Täglich um 3:00 Uhr ausführen
0 3 * * * cd /path/to/IdeaGraph-v1 && python cleanup_tasks.py --yes >> logs/cleanup_tasks.log 2>&1

# Wöchentlich am Sonntag um 2:00 Uhr ausführen
0 2 * * 0 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python cleanup_tasks.py --yes >> logs/cleanup_tasks_weekly.log 2>&1

# Monatlich am ersten Tag des Monats ausführen (mit verbose logging)
0 2 1 * * cd /path/to/IdeaGraph-v1 && python cleanup_tasks.py --yes --verbose >> logs/cleanup_tasks_monthly.log 2>&1
```

#### Log-Datei

```
logs/cleanup_tasks.log
```

---

### 2. cleanup_unused_tags.py

**Zweck**: Identifiziert und entfernt Tags, die nicht mehr verwendet werden (usage_count = 0).

#### Features
- ✅ Identifiziert automatisch alle Tags mit usage_count = 0
- ✅ Doppelte Überprüfung vor dem Löschen
- ✅ Dry-Run Modus zur Vorschau
- ✅ Bestätigung vor dem Löschen (überspringbar mit --yes)
- ✅ Detailliertes Feedback
- ✅ Robuste Fehlerbehandlung
- ✅ Ausführliches Logging
- ✅ Verbose Mode für Debugging

#### Verwendung

```bash
# Vorschau der zu löschenden Tags (Dry-Run)
python cleanup_unused_tags.py --dry-run

# Tags mit Bestätigungsaufforderung löschen
python cleanup_unused_tags.py

# Tags ohne Bestätigung löschen
python cleanup_unused_tags.py --yes

# Mit ausführlichem Logging
python cleanup_unused_tags.py --verbose

# Kombinierte Optionen
python cleanup_unused_tags.py --dry-run --verbose
```

#### Hilfe anzeigen

```bash
python cleanup_unused_tags.py --help
```

#### Cron Automation

```bash
# Täglich um 4:00 Uhr ausführen
0 4 * * * cd /path/to/IdeaGraph-v1 && python cleanup_unused_tags.py --yes >> logs/cleanup_tags.log 2>&1

# Wöchentlich am Montag um 3:00 Uhr ausführen
0 3 * * 1 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python cleanup_unused_tags.py --yes >> logs/cleanup_tags_weekly.log 2>&1

# Monatlich am ersten Tag des Monats ausführen
0 3 1 * * cd /path/to/IdeaGraph-v1 && python cleanup_unused_tags.py --yes --verbose >> logs/cleanup_tags_monthly.log 2>&1
```

#### Log-Datei

```
logs/cleanup_unused_tags.log
```

---

### 3. sync_github_issues.py

**Zweck**: Überwacht GitHub Issues und synchronisiert sie mit IdeaGraph Tasks.

#### Features
- ✅ Überwacht GitHub Issues und aktualisiert Task-Status bei Schließung
- ✅ Speichert Issue-Beschreibungen und PR-Informationen in Weaviate
- ✅ Filterung nach Repository und Owner
- ✅ Konfigurierbar über Kommandozeilen-Argumente oder Umgebungsvariablen
- ✅ Dry-Run Modus
- ✅ Ausführliches Logging

#### Verwendung

```bash
# Mit Standardeinstellungen aus Datenbank ausführen
python sync_github_issues.py

# Mit spezifischem Repository
python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1

# Mit ausführlichem Logging
python sync_github_issues.py --verbose

# Dry-Run (keine Änderungen)
python sync_github_issues.py --dry-run

# Kombinierte Optionen
python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1 --verbose
```

#### Hilfe anzeigen

```bash
python sync_github_issues.py --help
```

#### Umgebungsvariablen

```bash
# Umgebungsvariablen setzen
export GITHUB_SYNC_OWNER=gdsanger
export GITHUB_SYNC_REPO=IdeaGraph-v1

# Script ausführen
python sync_github_issues.py
```

#### Cron Automation

```bash
# Stündlich ausführen
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Alle 15 Minuten ausführen (für aktive Entwicklung)
*/15 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Alle 30 Minuten während Geschäftszeiten (8-18 Uhr, Montag-Freitag)
*/30 8-18 * * 1-5 cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Täglich um 2:00 Uhr
0 2 * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Mit verbose Logging stündlich
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py --verbose >> logs/sync_github_verbose.log 2>&1

# Mit spezifischem Repository stündlich
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1 >> logs/sync_github.log 2>&1

# Mit Umgebungsvariablen
0 * * * * cd /path/to/IdeaGraph-v1 && GITHUB_SYNC_OWNER=gdsanger GITHUB_SYNC_REPO=IdeaGraph-v1 python sync_github_issues.py >> logs/sync_github.log 2>&1

# Mit Python Virtual Environment
0 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Mit E-Mail-Benachrichtigung bei Fehlern
MAILTO=admin@example.com
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1 || echo "GitHub sync failed at $(date)" | mail -s "IdeaGraph Sync Error" admin@example.com

# Mit täglicher Log-Rotation
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github_$(date +\%Y\%m\%d).log 2>&1
```

#### Log-Datei

```
logs/github_sync.log
```

#### GitHub API Rate Limits

- Authentifizierte Anfragen: 5000 Anfragen/Stunde
- Jede Task-Prüfung benötigt mindestens 1 API-Aufruf
- Planen Sie die Cron-Frequenz entsprechend

**Empfohlene Frequenzen:**
- Entwicklung: Alle 15-30 Minuten
- Produktion: Stündlich
- Geringe Aktivität: Täglich

---

### 4. create_test_tasks.py

**Zweck**: Erstellt Testdaten für das cleanup_tasks.py Script.

#### Features
- ✅ Erstellt Test-Benutzer
- ✅ Erstellt Test-Items
- ✅ Erstellt gültige und ungültige Tasks
- ✅ Zeigt Zusammenfassung der erstellten Daten

#### Verwendung

```bash
# Testdaten erstellen
python create_test_tasks.py
```

#### Beispiel-Output

```
Creating test data...
Created user: testuser1
Created user: testuser2
Created section: Test Section
Created tag: test-tag
Created item: Test Item 1
Created item: Test Item 2

Creating test tasks...
✅ Created valid task: Valid Task - Has Owner and Item
❌ Created invalid task (no owner): Invalid Task - No Owner
❌ Created invalid task (no item): Invalid Task - No Item
❌ Created invalid task (no owner, no item): Invalid Task - No Owner and No Item
✅ Created valid task: Valid Task 2 - Has Owner and Item

============================================================
Test Data Summary
============================================================
Total tasks created: 5
Valid tasks (has owner and item): 2
Tasks without owner: 2
Tasks without item: 2
Tasks to be cleaned up: 3
============================================================

Test data created successfully!

Next steps:
  1. Run dry-run: python cleanup_tasks.py --dry-run
  2. Run cleanup: python cleanup_tasks.py
```

#### Verwendung im Testing-Workflow

```bash
# 1. Testdaten erstellen
python create_test_tasks.py

# 2. Dry-Run ausführen
python cleanup_tasks.py --dry-run

# 3. Cleanup durchführen
python cleanup_tasks.py

# 4. Ergebnis überprüfen
python manage.py shell
>>> from main.models import Task
>>> Task.objects.filter(assigned_to__isnull=True).count()
0
```

---

### 5. generate_test_logs.py

**Zweck**: Generiert Test-Log-Einträge für das Log-Analyzer-Testing.

#### Features
- ✅ Generiert verschiedene Log-Level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
- ✅ Simuliert realistische Fehlerszenarien
- ✅ Erstellt Log-Dateien für verschiedene Module

#### Verwendung

```bash
# Test-Logs generieren
python generate_test_logs.py
```

#### Beispiel-Output

```
Generating test log entries...

✅ Test logs generated successfully!
Check the logs directory at: /path/to/IdeaGraph-v1/logs
```

#### Generierte Log-Typen

1. **INFO**: Normale Anwendungsinformationen
2. **DEBUG**: Debug-Informationen
3. **WARNING**: Warnungen (z.B. API Rate Limits)
4. **ERROR**: Fehler (z.B. Datenbankfehler, Datei nicht gefunden)
5. **CRITICAL**: Kritische Systemfehler

#### Verwendung im Testing-Workflow

```bash
# 1. Test-Logs generieren
python generate_test_logs.py

# 2. Demo des Log Analyzers ausführen
python demo_log_analyzer.py

# 3. Log-Analyse mit Django Management Command
python manage.py analyze_logs --fetch-local --analyze --create-tasks
```

---

### 6. demo_log_analyzer.py

**Zweck**: Demonstriert die vollständige Funktionalität des AI Log Analyzers & Auto-Task Creators.

#### Features
- ✅ Überprüft vorhandene Log-Dateien
- ✅ Analysiert Logs und zeigt Statistiken
- ✅ Speichert Einträge in Datenbank
- ✅ Zeigt Datenbankstatistiken
- ✅ Zeigt Error-Analysen
- ✅ Gibt nächste Schritte aus

#### Verwendung

```bash
# Demo ausführen
python demo_log_analyzer.py
```

#### Beispiel-Output

```
============================================================
  🔍 AI Log Analyzer Demo
============================================================

--- Step 1: Checking log files ---

✅ Found 3 log file(s):
  - ideagraph.log (15,234 bytes)
  - error_prone_service.log (8,456 bytes)
  - api_service.log (12,789 bytes)

--- Step 2: Analyzing logs ---

📊 Extracted 15 entries (WARNING and above)

📈 Breakdown by level:
  - WARNING: 5
  - ERROR: 8
  - CRITICAL: 2

--- Step 3: Saving to database ---

✅ Saved 15 new entries to database

--- Step 4: Database statistics ---

📊 Total log entries: 42
  - Analyzed: 20
  - Not analyzed: 22

🔴 Recent errors (5):
  - [ERROR] Configuration error: Invalid configuration: DATABASE_URL...
    2025-10-21 10:15:23 | error_prone_service
  - [ERROR] File operation failed: Log file not found: /var/logs/...
    2025-10-21 10:15:23 | test_module

--- Step 5: Error analyses ---

📊 Total error analyses: 10

  Status breakdown:
    - Pending: 5
    - Approved: 3
    - Task created: 2

  Severity breakdown:
    🔴 critical: 1
    🟠 high: 3
    🟡 medium: 4
    🟢 low: 2

  Recent analyses:
    - [critical] Database connection lost - cannot establish co...
      Confidence: 95% | Actionable: True
    - [high] Failed to connect to external API: timeout after ...
      Confidence: 87% | Actionable: True

--- Next Steps ---

📝 You have unanalyzed log entries!

  Analyze with AI:
    python manage.py analyze_logs --analyze --limit 10

📋 You have pending error analyses!

  Create tasks:
    python manage.py analyze_logs --create-tasks --min-severity medium

============================================================
  Demo Complete
============================================================
📚 For more information, see: AI_LOG_ANALYZER_GUIDE.md
```

#### Verwendung im Workflow

```bash
# 1. Test-Logs generieren (optional)
python generate_test_logs.py

# 2. Demo ausführen
python demo_log_analyzer.py

# 3. Bei Bedarf weitere Schritte durchführen (siehe Demo-Output)
python manage.py analyze_logs --analyze --limit 10
python manage.py analyze_logs --create-tasks --min-severity medium
```

---

## Django Management Commands

Django Management Commands werden mit `python manage.py <command>` ausgeführt.

### 1. analyze_logs

**Zweck**: Analysiert Logs, erkennt Fehler und erstellt automatisch Tasks.

#### Features
- ✅ Holt Logs aus lokalen Dateien und Sentry
- ✅ Analysiert Fehler mit KI
- ✅ Erstellt Tasks für behebbare Fehler
- ✅ Optional: Erstellt GitHub Issues für kritische Fehler
- ✅ Batch-Verarbeitung mit konfigurierbarem Limit
- ✅ Filterung nach Log-Level und Severity

#### Verwendung

```bash
# Kompletten Workflow ausführen
python manage.py analyze_logs --all

# Nur lokale Logs abrufen
python manage.py analyze_logs --fetch-local

# Nur Sentry Logs abrufen
python manage.py analyze_logs --fetch-sentry

# Mit KI analysieren
python manage.py analyze_logs --analyze

# Tasks erstellen
python manage.py analyze_logs --create-tasks

# Mit Minimum Severity Filter
python manage.py analyze_logs --create-tasks --min-severity high

# Mit Minimum Confidence Filter
python manage.py analyze_logs --create-tasks --min-confidence 0.8

# Automatische GitHub Issue-Erstellung für kritische Fehler
python manage.py analyze_logs --create-tasks --auto-github

# Zeitfenster anpassen (Standard: 24 Stunden)
python manage.py analyze_logs --fetch-local --hours 48

# Log-Level anpassen (Standard: WARNING)
python manage.py analyze_logs --fetch-local --min-level ERROR

# Limit für Batch-Verarbeitung (Standard: 50)
python manage.py analyze_logs --analyze --limit 100

# Kombinierte Optionen
python manage.py analyze_logs --fetch-local --analyze --create-tasks --min-severity medium --hours 24
```

#### Hilfe anzeigen

```bash
python manage.py analyze_logs --help
```

#### Sentry-Konfiguration

```bash
# Mit Sentry Organization und Project
python manage.py analyze_logs --fetch-sentry --sentry-org my-org --sentry-project my-project

# Mit Umgebungsvariablen
export SENTRY_DSN=https://...
export SENTRY_AUTH_TOKEN=...
python manage.py analyze_logs --fetch-sentry
```

#### Cron Automation

```bash
# Kompletten Workflow stündlich ausführen
0 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --all >> logs/analyze_logs.log 2>&1

# Lokale Logs alle 30 Minuten abrufen und analysieren
*/30 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --fetch-local --analyze >> logs/analyze_logs.log 2>&1

# Tasks für kritische Fehler täglich um 1:00 Uhr erstellen
0 1 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --create-tasks --min-severity high --auto-github >> logs/analyze_logs_tasks.log 2>&1

# Sentry Logs alle 4 Stunden abrufen
0 */4 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --fetch-sentry --sentry-org my-org --sentry-project my-project >> logs/sentry_sync.log 2>&1

# Kompletter Workflow während Geschäftszeiten
0 9-17 * * 1-5 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --all --min-severity medium >> logs/analyze_logs_business.log 2>&1
```

#### Empfohlene Workflow-Strategie

**Variante 1: Vollautomatisch**
```bash
# Alles in einem Schritt
0 * * * * python manage.py analyze_logs --all --min-severity medium --auto-github
```

**Variante 2: Schrittweise (empfohlen für Kontrolle)**
```bash
# 1. Logs stündlich abrufen und speichern
0 * * * * python manage.py analyze_logs --fetch-local --fetch-sentry

# 2. Analyse alle 2 Stunden
0 */2 * * * python manage.py analyze_logs --analyze --limit 100

# 3. Task-Erstellung manuell oder täglich
0 2 * * * python manage.py analyze_logs --create-tasks --min-severity medium
```

---

### 2. process_mails

**Zweck**: Verarbeitet eingehende E-Mails und erstellt automatisch Tasks.

#### Features
- ✅ Ruft ungelesene E-Mails aus konfiguriertem Postfach ab
- ✅ Verwendet KI und RAG zur Zuordnung zu Items
- ✅ Generiert normalisierte Task-Beschreibungen
- ✅ Sendet Bestätigungs-E-Mails an Absender
- ✅ Konfigurierbar über Kommandozeilen-Parameter

#### Verwendung

```bash
# Mit Standard-Postfach aus Einstellungen
python manage.py process_mails

# Mit spezifischem Postfach
python manage.py process_mails --mailbox idea@angermeier.net

# Mit spezifischem Ordner
python manage.py process_mails --folder inbox

# Mit Maximum-Anzahl von Nachrichten
python manage.py process_mails --max-messages 20

# Kombinierte Optionen
python manage.py process_mails --mailbox idea@angermeier.net --folder inbox --max-messages 50
```

#### Hilfe anzeigen

```bash
python manage.py process_mails --help
```

#### Beispiel-Output

```
Starting mail processing...
Mailbox: idea@angermeier.net
Folder: inbox
Max messages: 10

============================================================
Mail processing completed!
============================================================
Total messages found: 5
Successfully processed: 4
Failed: 1

Details:
------------------------------------------------------------

1. ✓ Neue Idee für Dashboard Feature
   Item: Dashboard Verbesserungen
   Task ID: 550e8400-e29b-41d4-a716-446655440000
   Confirmation sent: Yes

2. ✓ Bug Report: Login funktioniert nicht
   Item: Authentifizierung
   Task ID: 550e8400-e29b-41d4-a716-446655440001
   Confirmation sent: Yes

3. ✗ Re: Meeting nächste Woche
   Error: Keine passende Idee gefunden
```

#### Cron Automation

```bash
# Alle 15 Minuten Postfach prüfen
*/15 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py process_mails >> logs/process_mails.log 2>&1

# Alle 30 Minuten mit spezifischem Postfach
*/30 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py process_mails --mailbox idea@angermeier.net --max-messages 20 >> logs/process_mails.log 2>&1

# Stündlich während Geschäftszeiten
0 8-18 * * 1-5 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py process_mails >> logs/process_mails.log 2>&1

# Alle 5 Minuten für hochfrequente E-Mail-Verarbeitung
*/5 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py process_mails --max-messages 10 >> logs/process_mails_frequent.log 2>&1
```

#### E-Mail-Konfiguration

Stellen Sie sicher, dass die E-Mail-Konfiguration in den Settings korrekt ist:
- IMAP-Server und Port
- E-Mail-Adresse und Passwort
- SMTP-Server für Bestätigungs-E-Mails

---

### 3. sync_tags_to_weaviate

**Zweck**: Synchronisiert alle Tags aus der Datenbank mit Weaviate.

#### Features
- ✅ Synchronisiert alle Tags mit Weaviate Vector Database
- ✅ Kann einzelne Tags oder alle Tags synchronisieren
- ✅ Verbose Mode für detaillierte Ausgabe
- ✅ Fehlerbehandlung mit klaren Meldungen

#### Verwendung

```bash
# Alle Tags synchronisieren
python manage.py sync_tags_to_weaviate

# Einzelnen Tag synchronisieren
python manage.py sync_tags_to_weaviate --tag-id <uuid>

# Mit ausführlicher Ausgabe
python manage.py sync_tags_to_weaviate --verbose
```

#### Hilfe anzeigen

```bash
python manage.py sync_tags_to_weaviate --help
```

#### Beispiel-Output

```
Syncing all tags to Weaviate...
✓ Successfully synced 45/47 tags
⚠ 2 tags failed to sync
Total tags: 47
Synced: 45
Failed: 2
```

#### Cron Automation

```bash
# Täglich um 3:00 Uhr alle Tags synchronisieren
0 3 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py sync_tags_to_weaviate >> logs/sync_tags.log 2>&1

# Stündlich synchronisieren
0 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py sync_tags_to_weaviate >> logs/sync_tags.log 2>&1

# Alle 6 Stunden mit verbose logging
0 */6 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py sync_tags_to_weaviate --verbose >> logs/sync_tags_verbose.log 2>&1

# Nach Tag-Bereinigung (5 Minuten später)
5 4 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py sync_tags_to_weaviate >> logs/sync_tags.log 2>&1
```

#### Verwendung im Workflow

**Nach Tag-Änderungen:**
```bash
# 1. Tags bereinigen
python cleanup_unused_tags.py --yes

# 2. Weaviate synchronisieren
python manage.py sync_tags_to_weaviate
```

---

### 4. init_admin

**Zweck**: Initialisiert einen Standard-Admin-Benutzer, wenn kein Admin existiert.

#### Features
- ✅ Erstellt Standard-Admin-Benutzer
- ✅ Prüft, ob bereits ein Admin existiert
- ✅ Einfache Ersteinrichtung
- ✅ Sichere Passwort-Generierung

#### Verwendung

```bash
# Admin-Benutzer initialisieren
python manage.py init_admin
```

#### Beispiel-Output

**Wenn kein Admin existiert:**
```
Successfully created default admin user:
  Username: admin
  Password: admin1234
  Email: admin@local

Please change the password after first login!
```

**Wenn Admin bereits existiert:**
```
Admin user already exists. Skipping initialization.
```

#### Verwendung im Setup

```bash
# 1. Datenbank migrieren
python manage.py migrate

# 2. Admin initialisieren
python manage.py init_admin

# 3. Server starten
python manage.py runserver

# 4. Im Browser anmelden mit:
#    Username: admin
#    Password: admin1234
#    
# 5. WICHTIG: Passwort ändern nach erstem Login!
```

#### Cron Automation

Dieses Kommando ist normalerweise nicht für Cron gedacht, da es nur einmalig bei der Ersteinrichtung benötigt wird. Es kann jedoch in Deployment-Skripten verwendet werden:

```bash
# In Deployment-Script
python manage.py migrate
python manage.py init_admin
python manage.py collectstatic --noinput
```

---

## Cron Automation

### Cron-Grundlagen

Cron-Format:
```
┌───────────── Minute (0 - 59)
│ ┌───────────── Stunde (0 - 23)
│ │ ┌───────────── Tag des Monats (1 - 31)
│ │ │ ┌───────────── Monat (1 - 12)
│ │ │ │ ┌───────────── Wochentag (0 - 6) (Sonntag bis Samstag)
│ │ │ │ │
* * * * * Befehl ausführen
```

### Crontab bearbeiten

```bash
# Crontab bearbeiten
crontab -e

# Aktuelle Crontab anzeigen
crontab -l

# Crontab einer anderen Benutzerin bearbeiten
sudo crontab -u username -e
```

### Empfohlene Cron-Konfiguration für IdeaGraph

```bash
# IdeaGraph Cron Jobs
# Pfad anpassen: /path/to/IdeaGraph-v1

# ============================================================
# GitHub Issue Synchronization
# ============================================================
# Stündlich GitHub Issues synchronisieren
0 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python sync_github_issues.py >> logs/sync_github.log 2>&1

# ============================================================
# Log Analysis & Task Creation
# ============================================================
# Alle 30 Minuten Logs abrufen und analysieren
*/30 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --fetch-local --analyze >> logs/analyze_logs.log 2>&1

# Täglich um 2:00 Uhr Tasks aus Analysen erstellen
0 2 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py analyze_logs --create-tasks --min-severity medium >> logs/analyze_logs_tasks.log 2>&1

# ============================================================
# Mail Processing
# ============================================================
# Alle 15 Minuten E-Mails verarbeiten
*/15 * * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py process_mails >> logs/process_mails.log 2>&1

# ============================================================
# Cleanup Tasks
# ============================================================
# Wöchentlich am Sonntag um 3:00 Uhr Tasks bereinigen
0 3 * * 0 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python cleanup_tasks.py --yes >> logs/cleanup_tasks.log 2>&1

# Wöchentlich am Montag um 3:00 Uhr Tags bereinigen
0 3 * * 1 cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python cleanup_unused_tags.py --yes >> logs/cleanup_tags.log 2>&1

# ============================================================
# Weaviate Synchronization
# ============================================================
# Täglich um 4:00 Uhr Tags mit Weaviate synchronisieren
0 4 * * * cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python manage.py sync_tags_to_weaviate >> logs/sync_tags.log 2>&1

# ============================================================
# Log Rotation (optional)
# ============================================================
# Monatlich alte Logs archivieren
0 0 1 * * cd /path/to/IdeaGraph-v1/logs && tar -czf archive/logs_$(date +\%Y\%m).tar.gz *.log && > *.log
```

### Alternative: Systemd Timer (modern)

Für moderne Linux-Systeme können Sie statt Cron auch systemd Timer verwenden:

**Beispiel: GitHub Sync Service**

`/etc/systemd/system/ideagraph-github-sync.service`:
```ini
[Unit]
Description=IdeaGraph GitHub Issues Synchronization
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/path/to/IdeaGraph-v1
Environment="PATH=/path/to/IdeaGraph-v1/.venv/bin"
ExecStart=/path/to/IdeaGraph-v1/.venv/bin/python sync_github_issues.py
StandardOutput=append:/path/to/IdeaGraph-v1/logs/sync_github.log
StandardError=append:/path/to/IdeaGraph-v1/logs/sync_github.log
```

`/etc/systemd/system/ideagraph-github-sync.timer`:
```ini
[Unit]
Description=Run IdeaGraph GitHub Sync Hourly
Requires=ideagraph-github-sync.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

**Aktivieren:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable ideagraph-github-sync.timer
sudo systemctl start ideagraph-github-sync.timer

# Status prüfen
sudo systemctl status ideagraph-github-sync.timer
```

---

## Best Practices

### 1. Logging

✅ **DO:**
- Immer Output in Log-Dateien umleiten (`>> logs/script.log 2>&1`)
- Verschiedene Log-Dateien für verschiedene Scripts verwenden
- Log-Rotation implementieren für große Log-Dateien
- Zeitstempel in Log-Dateinamen für bessere Organisation

❌ **DON'T:**
- Logs nicht in `/tmp` speichern (werden beim Neustart gelöscht)
- Keine unbegrenzten Logs ohne Rotation

### 2. Virtual Environment

✅ **Immer Virtual Environment aktivieren:**
```bash
source .venv/bin/activate && python script.py
```

Oder absoluten Pfad zum Python-Interpreter verwenden:
```bash
/path/to/IdeaGraph-v1/.venv/bin/python script.py
```

### 3. Fehlerbehandlung

✅ **E-Mail-Benachrichtigungen bei Fehlern:**
```bash
MAILTO=admin@example.com
0 * * * * cd /path/to/IdeaGraph-v1 && python script.py || echo "Script failed" | mail -s "Error" admin@example.com
```

✅ **Exit-Status prüfen:**
```bash
0 * * * * cd /path/to/IdeaGraph-v1 && python script.py >> logs/script.log 2>&1 || echo "Failed at $(date)" >> logs/script_errors.log
```

### 4. Pfade

✅ **Immer absolute Pfade verwenden:**
```bash
# Richtig
cd /home/user/IdeaGraph-v1 && python script.py

# Falsch
cd ../IdeaGraph-v1 && python script.py
```

### 5. Timing

✅ **Berücksichtigen Sie:**
- API Rate Limits (GitHub: 5000 Anfragen/Stunde)
- Systemlast (keine resource-intensive Scripts zur Hauptnutzungszeit)
- Abhängigkeiten zwischen Scripts

**Empfohlene Zeiten:**
- Cleanup-Scripts: Nachts (2-4 Uhr)
- Synchronisations-Scripts: Stündlich oder alle 15-30 Minuten
- Mail-Verarbeitung: Alle 5-15 Minuten während Geschäftszeiten

### 6. Testing

✅ **Vor Produktiv-Einsatz testen:**
```bash
# 1. Dry-Run ausführen
python script.py --dry-run

# 2. Manuell mit verbose logging testen
python script.py --verbose

# 3. Cron-Job in Testumgebung testen
# Cron-Eintrag mit */5 für 5-Minuten-Intervall erstellen und überwachen

# 4. Logs überprüfen
tail -f logs/script.log
```

### 7. Monitoring

✅ **Log-Überwachung:**
```bash
# Fehler in Logs finden
grep -i error logs/*.log

# Letzte Ausführungen prüfen
tail -n 50 logs/script.log

# Log-Größe überwachen
du -sh logs/*.log
```

✅ **Cron-Ausführung überprüfen:**
```bash
# Cron-Logs (Ubuntu/Debian)
grep CRON /var/log/syslog

# Oder
tail -f /var/log/cron
```

### 8. Sicherheit

✅ **DO:**
- Passwörter und API-Keys in `.env` speichern, nicht in Cron-Jobs
- Berechtigungen korrekt setzen (`chmod 600 .env`)
- Logs vor unbefugtem Zugriff schützen
- Virtual Environment verwenden

❌ **DON'T:**
- Keine Credentials in Cron-Einträgen
- Keine sensiblen Daten in Logs ausgeben

### 9. Log-Rotation

**Manuelle Log-Rotation:**
```bash
# In Cron-Job
0 0 * * 0 cd /path/to/IdeaGraph-v1/logs && gzip -9 *.log.1 && mv *.log *.log.1
```

**Mit logrotate (empfohlen):**

`/etc/logrotate.d/ideagraph`:
```
/path/to/IdeaGraph-v1/logs/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    notifempty
    missingok
    create 0644 www-data www-data
}
```

### 10. Dokumentation

✅ **Dokumentieren Sie:**
- Welche Cron-Jobs laufen
- Warum sie zu bestimmten Zeiten laufen
- Erwartete Ausführungszeit
- Benötigte Ressourcen
- Abhängigkeiten zu anderen Jobs

**Beispiel-Kommentar in Crontab:**
```bash
# GitHub Sync: Läuft stündlich, benötigt ca. 2-5 Minuten
# Abhängigkeit: Benötigt GITHUB_TOKEN in .env
# Rate Limit: Max 5000 API calls/hour
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1
```

---

## Troubleshooting

### Problem: Cron-Job läuft nicht

**Lösung:**
```bash
# 1. Cron-Service prüfen
sudo systemctl status cron

# 2. Cron-Logs prüfen
grep CRON /var/log/syslog

# 3. Manuell testen
cd /path/to/IdeaGraph-v1 && source .venv/bin/activate && python script.py

# 4. Pfade überprüfen
which python
echo $PATH
```

### Problem: "Module not found" Fehler in Cron

**Lösung:**
Virtual Environment aktivieren oder absoluten Pfad verwenden:
```bash
# Option 1: Virtual Environment aktivieren
source /path/to/IdeaGraph-v1/.venv/bin/activate && python script.py

# Option 2: Absoluten Pfad zu Python verwenden
/path/to/IdeaGraph-v1/.venv/bin/python script.py
```

### Problem: Script funktioniert manuell, aber nicht in Cron

**Ursache:** Umgebungsvariablen fehlen in Cron

**Lösung:**
```bash
# In Crontab Umgebungsvariablen setzen
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash
HOME=/home/username

# Oder .env laden
0 * * * * cd /path/to/IdeaGraph-v1 && source .env && python script.py
```

### Problem: Logs werden nicht geschrieben

**Lösung:**
```bash
# 1. Log-Verzeichnis erstellen
mkdir -p /path/to/IdeaGraph-v1/logs

# 2. Berechtigungen setzen
chmod 755 /path/to/IdeaGraph-v1/logs

# 3. In Cron-Job Output umleiten
... >> logs/script.log 2>&1
```

### Problem: Script läuft zu lange

**Lösung:**
```bash
# Timeout verwenden
timeout 300 python script.py  # 5 Minuten Timeout

# Oder limit Parameter verwenden
python manage.py analyze_logs --analyze --limit 50
```

---

## Zusammenfassung

Diese Dokumentation bietet einen vollständigen Überblick über alle CLI-Scripts im IdeaGraph-Projekt. Für weitere Details zu einzelnen Scripts, siehe auch:

- [AI_LOG_ANALYZER_GUIDE.md](AI_LOG_ANALYZER_GUIDE.md) - Detaillierte Anleitung zum Log Analyzer
- [TASK_CLEANUP_GUIDE.md](TASK_CLEANUP_GUIDE.md) - Task Cleanup Implementation
- [TAG_CLEANUP_GUIDE.md](TAG_CLEANUP_GUIDE.md) - Tag Cleanup Implementation
- [GITHUB_SYNC_GUIDE.md](GITHUB_SYNC_GUIDE.md) - GitHub Synchronization Guide
- [MAIL_PROCESSING_GUIDE.md](MAIL_PROCESSING_GUIDE.md) - Mail Processing Guide

---

**Letzte Aktualisierung:** 2025-10-21  
**Version:** 1.0  
**Autor:** IdeaGraph Team
