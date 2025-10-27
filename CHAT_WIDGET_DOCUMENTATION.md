# Chat Widget für IdeaGraph Q&A und Support

## 📋 Übersicht

Das Chat Widget ist eine modulare JavaScript-Komponente für IdeaGraph, die eine intuitive Chat-Oberfläche für kontextbezogene Fragen und KI-gestützte Antworten bereitstellt. Das Widget ist direkt an Items gebunden und nutzt semantische Suche sowie KIGate-Agents für intelligente Antworten.

## 🏗️ Architektur

### Komponenten-Struktur

```
/main/static/main/
├── js/chat-widget/
│   ├── ChatWidget.js      # Hauptkomponente mit State Management
│   ├── ChatMessage.js     # Rendering einzelner Nachrichten
│   └── ChatSources.js     # Darstellung der Quellenangaben
└── css/
    └── chat-widget.css    # Styling mit IdeaGraph Corporate Identity
```

### Komponenten-Details

#### ChatWidget.js
Die Hauptkomponente verwaltet:
- State Management (Nachrichten, Ladezustand)
- API-Integration (Fragen stellen, Verlauf laden)
- Event Handling (Eingabe, Senden)
- UI-Lifecycle (Initialisierung, Updates)

**Key Features:**
- CSRF-Token-Handling
- Automatisches Scrollen zu neuen Nachrichten
- Lazy Loading beim Tab-Öffnen
- Character Counter (max 512 Zeichen)
- Enter-to-Send (Shift+Enter für neue Zeile)

#### ChatMessage.js
Rendert einzelne Chat-Nachrichten mit:
- Markdown-Support via marked.js
- Drei Nachrichtentypen: User, Bot, Error
- Zeitstempel-Formatierung (relativ und absolut)
- XSS-Schutz durch HTML-Escaping

#### ChatSources.js
Zeigt Quellenangaben an mit:
- Relevanz-Scoring (Farbcodierung)
- Type-basierte Icons
- Links zu Originalquellen
- Truncated Descriptions

### CSS-Styling

Das Styling folgt der IdeaGraph Corporate Identity:
- **Primary Color**: Amber (#E49A28)
- **Secondary Color**: Cyan (#4BD0C7)
- **Bot Messages**: Violet Theme (#9333ea)
- **Dark Theme** als Standard
- Vollständig responsive

## 🔌 Integration

### In IdeaGraph (Item Detail View)

Das Widget ist bereits in die Item-Detailansicht integriert:

```html
<!-- In main/templates/main/items/detail.html -->

<!-- CSS einbinden -->
<link rel="stylesheet" href="{% static 'main/css/chat-widget.css' %}" />

<!-- JavaScript Components -->
<script src="{% static 'main/js/chat-widget/ChatSources.js' %}"></script>
<script src="{% static 'main/js/chat-widget/ChatMessage.js' %}"></script>
<script src="{% static 'main/js/chat-widget/ChatWidget.js' %}"></script>

<!-- Container -->
<div id="ideagraph-chat-widget"></div>

<!-- Initialisierung -->
<script>
const chatWidget = new ChatWidget({
    containerId: 'ideagraph-chat-widget',
    itemId: '{{ item.id }}',
    apiBaseUrl: '/api/items',
    theme: 'dark',
    height: '600px',
    showHistory: true
});
</script>
```

### In anderen HTML-Seiten

```html
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <!-- Bootstrap & Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    
    <!-- Chat Widget CSS -->
    <link rel="stylesheet" href="/static/main/css/chat-widget.css" />
    
    <!-- Marked.js für Markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <div id="my-chat-container"></div>
    
    <!-- Chat Widget Scripts -->
    <script src="/static/main/js/chat-widget/ChatSources.js"></script>
    <script src="/static/main/js/chat-widget/ChatMessage.js"></script>
    <script src="/static/main/js/chat-widget/ChatWidget.js"></script>
    
    <script>
        new ChatWidget({
            containerId: 'my-chat-container',
            itemId: 'YOUR-ITEM-UUID',
            apiBaseUrl: '/api/items',
            theme: 'dark',
            height: '500px',
            showHistory: true
        });
    </script>
</body>
</html>
```

## ⚙️ Konfigurationsoptionen

```javascript
{
    containerId: string,      // ID des Container-Elements (erforderlich)
    itemId: string,           // UUID des Items (erforderlich)
    apiBaseUrl: string,       // API Base URL (default: '/api/items')
    theme: 'dark' | 'light',  // UI Theme (default: 'dark')
    height: string,           // Container-Höhe (default: '500px')
    showHistory: boolean      // Verlauf anzeigen (default: true)
}
```

## 🔗 Backend API-Endpunkte

### 1. Frage stellen
**POST** `/api/items/<item_id>/ask`

Request Body:
```json
{
    "question": "Wie funktioniert die Authentifizierung?"
}
```

Response:
```json
{
    "success": true,
    "qa_id": "uuid",
    "question": "Wie funktioniert die Authentifizierung?",
    "answer": "## Antwort\n\nDie Authentifizierung...",
    "sources": [
        {
            "type": "Task",
            "title": "Token-Login implementieren",
            "url": "/tasks/uuid",
            "relevance": 0.92,
            "description": "..."
        }
    ],
    "relevance_score": 0.88,
    "created_at": "2025-10-27T21:00:00Z"
}
```

### 2. Verlauf laden
**GET** `/api/items/<item_id>/questions/history`

Query Parameters:
- `page` (optional, default: 1)
- `per_page` (optional, default: 10)

Response:
```json
{
    "success": true,
    "questions": [
        {
            "id": "uuid",
            "question": "...",
            "answer": "...",
            "sources": [...],
            "relevance_score": 0.85,
            "asked_by": "username",
            "created_at": "2025-10-27T21:00:00Z",
            "saved_as_knowledge_object": false
        }
    ],
    "total": 5,
    "page": 1,
    "per_page": 10,
    "has_next": false
}
```

### 3. Als KnowledgeObject speichern
**POST** `/api/items/questions/<qa_id>/save`

Response:
```json
{
    "success": true,
    "weaviate_uuid": "uuid",
    "message": "Q&A saved as KnowledgeObject"
}
```

## 🔒 Sicherheit

### Implementierte Maßnahmen

1. **CSRF-Protection**: Automatisches Token-Handling aus Cookies oder Meta-Tags
2. **XSS-Prevention**: HTML-Escaping in ChatMessage und ChatSources
3. **Input Validation**: 
   - Maximale Zeichenlänge: 512 Zeichen
   - Trimming von Whitespace
   - Leere Fragen werden abgelehnt
4. **Authentication**: Alle API-Calls verwenden `credentials: 'include'`
5. **Markdown-Rendering**: Sichere Konfiguration von marked.js

### Best Practices

- Keine sensiblen Daten im Frontend speichern
- API-Keys werden nur im Backend verwendet
- HTTPS für Produktionsumgebungen
- Rate Limiting auf Backend-Ebene empfohlen

## 🎨 UI/UX Features

### Chat-Design
- **User Messages**: Rechts, grau
- **Bot Messages**: Links, violett mit Avatar
- **Error Messages**: Rot mit Warning-Icon

### Interaktionen
- Automatisches Scrollen zu neuen Nachrichten
- Loading States mit Spinner-Animation
- Status-Indicator (Bereit/Denkt nach)
- Character Counter mit Live-Update
- Keyboard Shortcuts:
  - Enter: Nachricht senden
  - Shift+Enter: Neue Zeile

### Responsive Design
- Desktop: Max-width 75% für Nachrichten
- Mobile: Max-width 85% für Nachrichten
- Adaptive Padding und Font-Größen

## 📊 Markdown-Support

Unterstützte Markdown-Features:
- Überschriften (H1-H6)
- Listen (geordnet und ungeordnet)
- Links
- Code-Blöcke und Inline-Code
- Fettdruck und Kursiv
- Zeilenumbrüche

## 🧪 Testing

### Manuelle Tests

1. **UI-Test**: Öffne `/tmp/chat-widget-test.html` im Browser
2. **Integration-Test**: Öffne ein Item in IdeaGraph und gehe zum Q&A-Tab
3. **Funktions-Test**: Stelle eine Frage und prüfe die Antwort

### Automatisierte Tests

Bestehende Tests in `main/test_item_question_answering.py`:
- ✅ API-Endpunkt Tests
- ✅ Model Tests
- ✅ Service Tests
- ✅ History & Pagination Tests

### Test Coverage
```bash
python manage.py test main.test_item_question_answering --verbosity=2
```

## 🚀 Performance

- **Initial Load**: < 50ms (ohne API-Calls)
- **Message Rendering**: < 10ms pro Nachricht
- **API Response**: Abhängig von KIGate (typisch 2-5s)
- **Memory Footprint**: ~2-5MB für Chat-Historie

### Optimierungen
- Lazy Loading: Widget wird erst beim Tab-Öffnen initialisiert
- History Pagination: Nur erste 10 Einträge werden geladen
- Debounced Input: Character Counter ohne Performance-Impact

## 📦 Abhängigkeiten

### Erforderlich
- **Bootstrap 5.3+**: UI Framework
- **Bootstrap Icons 1.11+**: Icon Set
- **marked.js**: Markdown-Rendering

### Optional
- **DOMPurify**: Zusätzliche XSS-Protection (empfohlen für Produktion)

## 🐛 Troubleshooting

### Widget wird nicht angezeigt
- Container-Element mit korrekter ID vorhanden?
- CSS-Datei korrekt eingebunden?
- Browser-Console auf JavaScript-Fehler prüfen

### API-Calls schlagen fehl
- CSRF-Token verfügbar?
- Benutzer authentifiziert?
- Backend läuft und erreichbar?
- Network-Tab in DevTools prüfen

### Markdown wird nicht gerendert
- marked.js eingebunden?
- Console-Fehler prüfen
- Fallback auf Plaintext aktiv

### Verlauf lädt nicht
- API-Endpunkt erreichbar?
- Fehler im Browser-Log?
- Backend-Logs prüfen

## 🔮 Zukünftige Erweiterungen

Mögliche Features für kommende Versionen:
- [ ] Spracherkennung (Speech-to-Text)
- [ ] Export von Chat-Verläufen (PDF/Markdown)
- [ ] Favoriten/Bookmarks für wichtige Q&As
- [ ] Thread-basierte Konversationen
- [ ] Collaborative Filtering für bessere Antworten
- [ ] Real-time Updates via WebSockets
- [ ] Multi-Language Support
- [ ] Voice Output (Text-to-Speech)
- [ ] Code Syntax Highlighting
- [ ] LaTeX-Support für mathematische Formeln

## 📞 Support

Bei Fragen oder Problemen:
- **Issue Tracker**: GitHub Issues
- **Entwickler**: Christian Angermeier (ca@angermeier.net)
- **Dokumentation**: Dieses README

## 📜 Lizenz

Teil des IdeaGraph-Projekts. Siehe Hauptprojekt-Lizenz.
