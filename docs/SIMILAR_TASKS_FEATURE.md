# Ähnliche Aufgaben Feature

## Übersicht

Die "Ähnliche Aufgaben" Funktion zeigt automatisch ähnliche Tasks und GitHub-Issues am unteren Ende der Task-Detailansicht an. Die Suche erfolgt asynchron im Hintergrund, sodass die Seite sofort geladen wird.

## Funktionsweise

### Backend (API Endpoint)

**Endpoint:** `GET /api/tasks/{task_id}/similar`

Das Backend verwendet die Task-Beschreibung als Suchtext und führt eine semantische Ähnlichkeitssuche in zwei ChromaDB-Sammlungen durch:

1. **Tasks Collection**: Sucht nach ähnlichen Tasks im System
2. **GitHubIssues Collection**: Sucht nach ähnlichen GitHub Issues und Pull Requests

#### Filterung

- **Ähnlichkeitsschwelle**: Nur Ergebnisse mit Ähnlichkeit >= 0.8 (80%) werden angezeigt
- **Ausschluss**: Die aktuelle Task wird automatisch aus den Ergebnissen ausgeschlossen
- **Sortierung**: Ergebnisse werden nach Ähnlichkeit sortiert (höchste zuerst)

#### Ähnlichkeitsberechnung

ChromaDB verwendet Cosine Distance zur Messung der Ähnlichkeit:
- Distance: 0 = identisch, 2 = gegensätzlich
- Similarity = 1 - (distance / 2)
- Beispiele:
  - Distance 0.0 → Similarity 1.0 (100%)
  - Distance 0.4 → Similarity 0.8 (80%)
  - Distance 1.0 → Similarity 0.5 (50%)

### Frontend (UI)

#### Darstellung

Die ähnlichen Tasks und GitHub-Issues werden als klickbare Karten angezeigt:

**Tasks:**
- Icon: Liste-Symbol (bi-list-task)
- Click-Verhalten: Navigation zur Task-Detailseite
- URL: `/tasks/{id}/`

**GitHub Issues:**
- Icon: GitHub-Symbol (bi-github)
- Click-Verhalten: Öffnet Issue in neuem Tab
- URL: GitHub Issue URL

#### Information pro Eintrag

- Titel
- Typ (Task oder GitHub Issue)
- Ähnlichkeit in Prozent
- Status-Badge (mit Icon und Text)

#### Ladezustände

1. **Loading**: Spinner mit Text "Suche nach ähnlichen Aufgaben und GitHub-Issues..."
2. **Mit Ergebnissen**: Liste der ähnlichen Items
3. **Keine Ergebnisse**: Info-Message "Keine ähnlichen Aufgaben oder GitHub-Issues gefunden"
4. **Fehler**: Warnung "Fehler beim Laden ähnlicher Aufgaben"

## Technische Details

### Verwendete Services

- `ChromaTaskSyncService`: Verwaltet Tasks in ChromaDB
- `GitHubIssueSyncService`: Verwaltet GitHub Issues in ChromaDB

### Asynchronität

- Die Funktion `loadSimilarTasks()` wird beim DOM-Load Event aufgerufen
- Verwendet `async/await` für nicht-blockierende API-Aufrufe
- Seite ist sofort interaktiv, während Ähnlichkeitssuche läuft

### Fehlerbehandlung

- ChromaDB-Fehler werden gefangen und geloggt (warning level)
- API gibt bei Fehlern leere Liste zurück statt Fehler zu werfen
- Graceful Degradation: Feature funktioniert auch wenn ChromaDB nicht verfügbar ist

### Sicherheit

- Authentifizierung erforderlich (JWT oder Session)
- Autorisierungsprüfung: Nur Task-Ersteller kann ähnliche Tasks sehen
- HTML Escaping im Frontend zur XSS-Prävention

## Abhängigkeiten

### Backend
- ChromaDB (>= 0.4.0)
- OpenAI API (für Embedding-Generierung)

### Frontend
- Bootstrap 5 (für Styling)
- Bootstrap Icons (für Icons)

## Konfiguration

### ChromaDB Setup

Die ChromaDB-Konfiguration erfolgt über Settings:
- `chroma_api_key`: API Key für ChromaDB Cloud
- `chroma_database`: Database URL
- `chroma_tenant`: Tenant Name

### OpenAI Setup

Für die Embedding-Generierung:
- `openai_api_enabled`: Muss auf `True` gesetzt sein
- `openai_api_key`: OpenAI API Key
- `openai_api_base_url`: OpenAI API URL (Standard: https://api.openai.com/v1)

## Tests

Bestehende Tests in `main/test_api_hybrid_auth.py`:
- `test_api_task_similar_with_jwt`: JWT-Authentifizierung
- `test_api_task_similar_with_session`: Session-Authentifizierung
- `test_api_task_similar_without_auth`: Ohne Authentifizierung (401)
- `test_api_task_similar_access_denied_for_other_user`: Autorisierung (403)

Alle Tests bestehen erfolgreich ✓

## Beispiel API Response

```json
{
  "success": true,
  "similar_tasks": [
    {
      "id": "uuid-1",
      "title": "Implement user authentication",
      "similarity": 0.92,
      "status": "working",
      "status_display": "Working",
      "type": "task",
      "url": "/tasks/uuid-1/"
    },
    {
      "id": "123",
      "title": "Add OAuth support",
      "similarity": 0.85,
      "status": "working",
      "status_display": "Open",
      "type": "github_issue",
      "issue_number": 123,
      "url": "https://github.com/owner/repo/issues/123"
    }
  ]
}
```

## Bekannte Einschränkungen

1. **Leere Beschreibung**: Tasks ohne Beschreibung haben keine Ähnlichkeitssuche
2. **OpenAI Abhängigkeit**: Benötigt OpenAI API für Embedding-Generierung
3. **Performance**: Große Datenmenken können die Suche verlangsamen (empfohlen: n_results <= 10)
4. **Sprachabhängig**: Funktioniert am besten mit deutschem oder englischem Text

## Zukünftige Verbesserungen

- [ ] Caching von Similarity-Ergebnissen
- [ ] Verwendung von Task-Titel zusätzlich zur Beschreibung
- [ ] Filter-Optionen (nur Tasks, nur Issues, nach Status)
- [ ] Konfigurierbare Ähnlichkeitsschwelle
- [ ] Pagination für große Ergebnismengen
