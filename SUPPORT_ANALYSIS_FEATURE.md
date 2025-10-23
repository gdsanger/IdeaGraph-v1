# Support-Analyse Feature - Dokumentation

## Übersicht

Die **Support-Analyse** ist eine neue KI-gestützte Funktion im Task-Detailview, die Handlungsempfehlungen und Lösungsvorschläge für Tasks bereitstellt. Die Analyse kann wahlweise **intern** (basierend auf der Weaviate-Wissensbasis) oder **extern** (über Websuche) durchgeführt werden.

## Funktionsweise

### 🧠 Interner Modus ("Knowledge Advisor")

**Verwendung:**
- Analyse des Tasktexts mithilfe der vorhandenen Wissensbasis in Weaviate

**Quellen:**
- Weaviate-Datenbank (Items, Tasks, Issues, Milestones, Files)
- Semantische Ähnlichkeitssuche
- Kontextbasierte KI-Analyse

**Ablauf:**
1. Nutzer klickt auf "Support-Analyse (Intern)"
2. Task-Beschreibung wird an Weaviate geschickt → semantische Ähnlichkeitssuche
3. Top-5 ähnliche Objekte werden gesammelt
4. KiGate-Agent `support-advisor-internal-agent` erstellt strukturierte Analyse
5. Ergebnis wird als Markdown unterhalb des Editors angezeigt

**Ergebnisbeispiel:**
```markdown
### 🧩 Interne Analyse
- Mögliche Ursache: Fehlkonfiguration in SharePoint Graph API.
- Ähnliche Tasks: "GraphAPI Auth Error" (#112)
- Empfehlung: Prüfe Azure App Permissions (Delegated vs. Application).
```

### 🌍 Externer Modus ("Research Advisor")

**Verwendung:**
- Externe Recherche basierend auf dem Tasktext
- Nutzung von Google Custom Search API oder Brave Search API

**Ablauf:**
1. Nutzer klickt auf "Support-Analyse (Extern)"
2. Websuche liefert 5 passende Ergebnisse (Titel, Snippet, URL)
3. KiGate-Agent `support-advisor-external-agent` fasst Inhalte zusammen
4. Ergebnis mit Handlungsempfehlungen und Quellen wird angezeigt

**Ergebnisbeispiel:**
```markdown
### 🌍 Externe Analyse
- Lösung: Moodle-Rollenverwaltung erfordert Anpassung der Kontextebene.
- Quelle: [Moodle Docs - Rollenverwaltung](https://docs.moodle.org/405/de/Rollen_und_Rechte)
- Empfehlung: Verwende Kontext "Kursbereich" statt "Systemweite Rolle".
```

## UI-Integration

### Position
Task Detail View → Description-Bereich (neben "Optimize Text"-Button)

### Neue Buttons
1. **🧠 Support-Analyse (Intern)** - Blauer Button für interne Analyse
2. **🌍 Support-Analyse (Extern)** - Info-Button für externe Analyse

### Ergebnisanzeige
- Erscheint unterhalb des Editors in einem dunklen Info-Card
- Header: "Support-Analyse Ergebnis"
- Markdown-Rendering mit:
  - Überschriften (H1, H2, H3)
  - Listen (bullet points)
  - Links
  - Fett/Kursiv-Formatierung
- Schließen-Button (X) zum Ausblenden

### Interaktion
1. Klick auf Button → Spinner-Animation
2. API-Aufruf im Hintergrund
3. Ergebnis erscheint automatisch
4. Smooth Scrolling zum Ergebnis
5. Success-Nachricht oben rechts

## Technische Implementierung

### Backend-Komponenten

#### 1. SupportAdvisorService
**Datei:** `core/services/support_advisor_service.py`

**Methoden:**
- `analyze_internal(task_description, task_title, user_id, max_results)` 
  - Führt interne Analyse mit Weaviate durch
  - Sucht ähnliche Tasks und Items
  - Nutzt KiGate-Agent für Zusammenfassung
  
- `analyze_external(task_description, task_title, user_id, max_results)`
  - Führt externe Analyse mit Websuche durch
  - Nutzt Google/Brave Search API
  - Nutzt KiGate-Agent für Auswertung

#### 2. WebSearchAdapter
**Datei:** `core/services/web_search_adapter.py`

**Methoden:**
- `search(query, max_results)` - Hauptmethode mit Fallback-Logik
- `search_google(query, max_results)` - Google Custom Search API
- `search_brave(query, max_results)` - Brave Search API

**Konfiguration:**
Benötigt Umgebungsvariablen:
- `GOOGLE_SEARCH_API_KEY` - Google API Key
- `GOOGLE_SEARCH_CX` - Google Custom Search Engine ID
- `BRAVE_SEARCH_API_KEY` - Brave API Key (optional, als Fallback)

### API-Endpunkte

#### POST /api/tasks/{task_id}/support-analysis-internal
**Request Body:**
```json
{
  "description": "Task-Beschreibung..."
}
```

**Response:**
```json
{
  "success": true,
  "analysis": "### 🧩 Interne Analyse\n...",
  "similar_objects": [
    {
      "type": "task",
      "id": "uuid",
      "title": "Similar Task",
      "description": "...",
      "similarity": 0.95
    }
  ],
  "mode": "internal"
}
```

#### POST /api/tasks/{task_id}/support-analysis-external
**Request Body:**
```json
{
  "description": "Task-Beschreibung..."
}
```

**Response:**
```json
{
  "success": true,
  "analysis": "### 🌍 Externe Analyse\n...",
  "sources": [
    {
      "title": "Example",
      "url": "https://example.com",
      "snippet": "..."
    }
  ],
  "mode": "external"
}
```

### Frontend-Komponenten

#### HTML (task/detail.html)
- Zwei neue Buttons im Description-Header
- Result-Container (initial ausgeblendet)
- Card mit Header und Body für Ergebnisanzeige

#### JavaScript
**Funktionen:**
- `supportAnalysisInternalBtn.click` - Handler für internen Button
- `supportAnalysisExternalBtn.click` - Handler für externen Button
- `renderMarkdown(markdown)` - Einfacher Markdown-Renderer
- `displaySupportAnalysisResult(analysisMarkdown, mode)` - Ergebnisanzeige
- `closeSupportAnalysisBtn.click` - Schließen-Handler

## Tests

**Datei:** `main/test_support_analysis.py`

**8 Tests implementiert:**
1. ✅ `test_api_task_support_analysis_internal_success` - Erfolgreiche interne Analyse
2. ✅ `test_api_task_support_analysis_external_success` - Erfolgreiche externe Analyse
3. ✅ `test_api_task_support_analysis_internal_no_auth` - Authentifizierung erforderlich (intern)
4. ✅ `test_api_task_support_analysis_external_no_auth` - Authentifizierung erforderlich (extern)
5. ✅ `test_api_task_support_analysis_internal_missing_description` - Fehlende Beschreibung (intern)
6. ✅ `test_api_task_support_analysis_external_missing_description` - Fehlende Beschreibung (extern)
7. ✅ `test_api_task_support_analysis_internal_service_error` - Service-Fehlerbehandlung (intern)
8. ✅ `test_api_task_support_analysis_external_service_error` - Service-Fehlerbehandlung (extern)

**Testabdeckung:** 100% der API-Endpunkte und Fehlerfälle

## Sicherheit

### Implementierte Maßnahmen
- ✅ Authentifizierung erforderlich für alle Endpunkte
- ✅ CSRF-Token-Validierung
- ✅ Keine Stack-Trace-Exposition in Fehlermeldungen
- ✅ Fehlerdetails nur serverseitig geloggt
- ✅ Input-Validierung (Beschreibung erforderlich)
- ✅ CodeQL Security Scan bestanden (0 Alerts)

### Best Practices
- Markdown wird vor dem Rendern bereinigt
- URLs werden in separaten Tabs geöffnet (target="_blank")
- Fehlerbehandlung mit generischen Meldungen
- Detaillierte Fehler nur im Server-Log

## Nutzung

### Voraussetzungen
1. **KiGate-Agenten konfiguriert:**
   - `support-advisor-internal-agent`
   - `support-advisor-external-agent`

2. **Weaviate eingerichtet:**
   - KnowledgeObject Collection vorhanden
   - Items/Tasks synchronisiert

3. **Web Search API (für extern):**
   - Google Custom Search API ODER
   - Brave Search API

### Workflow
1. Task öffnen
2. Beschreibung eingeben/bearbeiten
3. Button klicken:
   - **Intern:** Nutzt eigene Datenbank → schneller, kontextbasiert
   - **Extern:** Nutzt Websuche → umfassender, externe Quellen
4. Ergebnis prüfen
5. Optional: Als Kommentar speichern (zukünftige Erweiterung)

## Zukünftige Erweiterungen

### Geplante Features
- [ ] "Als Kommentar speichern"-Button
- [ ] "Als neuen Task erstellen"-Button
- [ ] Verlauf der durchgeführten Analysen
- [ ] Kombinierter Modus (intern + extern)
- [ ] Bewertung der Analyse-Qualität
- [ ] Export-Funktion (PDF/Markdown)

### Integration
- [ ] GitHub Issues (automatische Analyse bei Issue-Import)
- [ ] Zammad Tickets (Analyse bei Ticket-Synchronisation)
- [ ] E-Mail-Processing (Analyse eingehender Support-Mails)

## Lizenz

Teil des IdeaGraph-v1 Projekts.
