# Teams Bot Debug Output Guide

## Übersicht

Als Reaktion auf das Problem, dass der Teams Bot möglicherweise immer noch seine eigenen Nachrichten abruft, wurde umfangreiche Debug-Ausgabe implementiert. Diese Dokumentation erklärt, wie die Debug-Ausgabe zu interpretieren ist.

## Problem

Der Issue beschreibt:
- Der Bot `poll_teams_messages` holt immer noch seine eigenen Nachrichten ab
- Es ist unklar, warum der String-Vergleich mit `default_mail_sender` nicht funktioniert
- Debug-Ausgabe wird benötigt, um zu verstehen, was passiert

## Lösung

Es wurde umfassende Debug-Ausgabe an zwei kritischen Stellen implementiert:

### 1. Bei der Service-Initialisierung

**Wenn `default_mail_sender` konfiguriert ist:**
```
[INFO] TeamsListenerService initialized with team_id: test-team-id
[INFO] DEBUG: Bot UPN configured as: 'idea@isartec.de' (will filter messages from this sender)
```

**Wenn `default_mail_sender` NICHT konfiguriert ist:**
```
[WARNING] TeamsListenerService initialized with team_id: test-team-id
[WARNING] DEBUG: Bot UPN is NOT configured (default_mail_sender is empty)! Bot messages will NOT be filtered!
```

### 2. Bei der Nachrichtenverarbeitung

Für jede Nachricht wird detaillierte Information geloggt:

#### Beispiel 1: Bot-Nachricht wird korrekt gefiltert
```
[INFO] DEBUG: Processing message 1732478840000
  - Sender UPN: 'idea@isartec.de' (empty: False)
  - Sender Name: 'ISARtec IdeaGraph Bot'
  - Bot UPN configured: 'idea@isartec.de' (empty: False)
  - Comparing UPNs: 'idea@isartec.de' == 'idea@isartec.de' ? True
  ✓ SKIPPED: Message 1732478840000 from bot itself (UPN match)
```

#### Beispiel 2: Benutzer-Nachricht wird akzeptiert
```
[INFO] DEBUG: Processing message 1732478850000
  - Sender UPN: 'user@isartec.de' (empty: False)
  - Sender Name: 'Max Mustermann'
  - Bot UPN configured: 'idea@isartec.de' (empty: False)
  - Comparing UPNs: 'user@isartec.de' == 'idea@isartec.de' ? False
  → ACCEPTED: Message 1732478850000 from user@isartec.de will be processed
```

#### Beispiel 3: Bot UPN nicht konfiguriert (Problem!)
```
[INFO] DEBUG: Processing message 1732478860000
  - Sender UPN: 'idea@isartec.de' (empty: False)
  - Sender Name: 'ISARtec IdeaGraph Bot'
  - Bot UPN configured: '' (empty: True)
  ⚠ Cannot filter by UPN: bot_upn not configured (default_mail_sender is empty)
  → ACCEPTED: Message 1732478860000 from idea@isartec.de will be processed
```
**Problem:** Bot-Nachricht wird akzeptiert, weil `default_mail_sender` leer ist!

#### Beispiel 4: Sender UPN ist leer
```
[INFO] DEBUG: Processing message 1732478870000
  - Sender UPN: '' (empty: True)
  - Sender Name: 'Max Mustermann'
  - Bot UPN configured: 'idea@isartec.de' (empty: False)
  ⚠ Cannot compare UPNs: sender_upn is empty for message 1732478870000
  → ACCEPTED: Message 1732478870000 from Max Mustermann will be processed
```

## Verwendung zur Diagnose

### Schritt 1: Prüfen Sie die Service-Initialisierung

Suchen Sie im Log nach:
```
DEBUG: Bot UPN configured as:
```

**Wenn Sie eine WARNING sehen:**
```
DEBUG: Bot UPN is NOT configured (default_mail_sender is empty)!
```
→ **Das ist Ihr Problem!** Der `default_mail_sender` muss in den Einstellungen konfiguriert werden.

### Schritt 2: Prüfen Sie die Nachrichtenverarbeitung

Für jede verarbeitete Nachricht sehen Sie:
- **Sender UPN**: Die E-Mail-Adresse des Absenders
- **Bot UPN configured**: Der konfigurierte Bot-UPN
- **Comparing UPNs**: Das Ergebnis des Vergleichs

### Schritt 3: Identifizieren Sie das Problem

**Problem A: Bot-Nachrichten werden NICHT gefiltert**
```
  - Comparing UPNs: 'idea@isartec.de' == 'idea@isartec.de' ? True
  ✓ SKIPPED: Message ... from bot itself (UPN match)
```
→ **Gut!** Die Filterung funktioniert.

**Problem B: Bot-Nachrichten werden AKZEPTIERT**
```
  ⚠ Cannot filter by UPN: bot_upn not configured (default_mail_sender is empty)
  → ACCEPTED: Message ... from idea@isartec.de will be processed
```
→ **Schlecht!** `default_mail_sender` ist nicht konfiguriert.

**Problem C: UPN-Vergleich schlägt fehl**
```
  - Comparing UPNs: 'idea@isartec.de' == 'other@isartec.de' ? False
  → ACCEPTED: Message ... from idea@isartec.de will be processed
```
→ **Schlecht!** `default_mail_sender` ist falsch konfiguriert (zeigt auf einen anderen Benutzer).

## Erweiterte Debug-Ausgabe in MessageProcessingService

Wenn eine Nachricht trotzdem analysiert wird (zweite Verteidigungslinie), sehen Sie:

```
[INFO] DEBUG: Analyzing message from sender:
  - Sender UPN: 'idea@isartec.de'
  - Sender Name: 'ISARtec IdeaGraph Bot'
  - Bot UPN check: comparing 'idea@isartec.de' vs 'idea@isartec.de'
[ERROR] CRITICAL: Attempted to analyze message from bot itself! Message ID: ..., Sender: idea@isartec.de
[ERROR]   This message should have been filtered in TeamsListenerService!
```

Wenn Sie diesen ERROR sehen, bedeutet das:
1. Die erste Filterung in TeamsListenerService hat versagt
2. Die zweite Verteidigungslinie hat die Bot-Nachricht abgefangen
3. Die Ursache muss in der TeamsListenerService-Filterung gefunden werden

## Konfigurationsprüfung

### Wo ist `default_mail_sender` konfiguriert?

In der Django Admin-Oberfläche unter **Settings**:
- Feld: `default_mail_sender`
- Beispiel: `idea@isartec.de`

### Was sollte dort stehen?

Die User Principal Name (UPN) des System-Benutzers, der als Bot agiert. Dies ist typischerweise:
- Ein dedizierter Service-Account
- Format: `username@domain.com`
- Muss EXAKT mit der UPN übereinstimmen, die in Teams-Nachrichten angezeigt wird

### Wie finde ich die richtige UPN?

1. Lassen Sie den Bot eine Nachricht in Teams posten
2. Prüfen Sie die Debug-Ausgabe für diese Nachricht:
   ```
   - Sender UPN: 'idea@isartec.de'
   ```
3. Verwenden Sie diese UPN als `default_mail_sender`

## Symbole in der Debug-Ausgabe

- `✓ SKIPPED`: Nachricht wurde korrekt gefiltert
- `→ ACCEPTED`: Nachricht wird verarbeitet
- `⚠`: Warnung - potentielles Problem

## Zusammenfassung

Die neue Debug-Ausgabe bietet vollständige Transparenz über:
1. **Konfiguration**: Ob `default_mail_sender` gesetzt ist
2. **Nachrichtenquelle**: Sender UPN und Name jeder Nachricht
3. **Vergleichslogik**: Exakte Werte, die verglichen werden
4. **Filterentscheidungen**: Warum Nachrichten akzeptiert oder abgelehnt werden
5. **Edge Cases**: Warnungen bei leeren UPNs oder fehlender Konfiguration

Mit dieser Ausgabe können Sie genau diagnostizieren, warum der Bot seine eigenen Nachrichten verarbeitet (oder nicht).
