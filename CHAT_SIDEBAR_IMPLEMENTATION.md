# Chat Sidebar Integration - Implementierungsanleitung

## Übersicht

Diese Implementierung ersetzt das bisherige Chat-Modal durch eine effiziente, animierte Sidebar-Lösung für Items und Tasks.

## Hauptänderungen

### 1. Aktivitäten-Stream entfernt
- **Datei**: `main/templates/main/base.html`
- **Änderung**: Die gesamte Activity Sidebar wurde entfernt
- **Grund**: Unübersichtlich und nicht hilfreich

### 2. Chat aus Floating-Action-Dock entfernt
- **Datei**: `main/templates/main/items/_floating_action_dock.html`
- **Änderung**: Chat-Button und Q&A Modal wurden entfernt
- **Beibehaltene Funktionen**: Graph, Files, Global Search

### 3. Neue Chat-Sidebar erstellt
- **Datei**: `main/templates/main/partials/chat_sidebar.html`
- **Features**:
  - Slidebare Sidebar (rechts)
  - 100% Höhe (full viewport)
  - Animierte Ein-/Ausblendung (0.3s)
  - Backdrop-Overlay beim Öffnen
  - Escape-Taste zum Schließen
  - Responsive Design (100% Breite auf Mobile)

### 4. Floating Chat-Button im Breadcrumb
- **Dateien**: 
  - `main/templates/main/items/detail.html`
  - `main/templates/main/tasks/detail.html`
- **Position**: Rechts neben Breadcrumb-Navigation
- **Farbe**: Cyan (var(--secondary-cyan))
- **Größe**: 42x42px
- **Sichtbarkeit**: Nur in Item- und Task-Detailansichten

### 5. "Thinking..." Indikator
- **Datei**: `main/static/main/js/chat-widget/ChatWidget.js`
- **Features**:
  - Animierte Punkte (pulsierend)
  - Wird unter User-Nachricht angezeigt
  - Automatische Entfernung bei Antwort
  - CSS Animation mit Keyframes

### 6. Debug-Kontext entfernt
- **Datei**: `main/static/main/js/chat-widget/ChatWidget.js`
- **Änderung**: Kontext-Badge (Object Type + ID) aus Chat-Header entfernt (Lines 115-123)
- **Grund**: Nur für Debugging, nicht für Produktivbetrieb
- **Entfernt**: `.chat-widget-context` div mit context-badge und context-id

### 7. Quellen in kleinerer Schrift
- **Datei**: `main/templates/main/partials/chat_sidebar.html`
- **Änderung**: 
  - `.message-sources`: 0.8rem
  - `.sources-header`: 0.75rem
  - `.source-item`: 0.75rem
  - `.source-title`: 0.8rem
  - `.source-description`: 0.7rem

## Technische Details

### Chat-Sidebar Toggle
```javascript
// Located in: main/templates/main/partials/chat_sidebar.html
function toggleChatSidebar() {
    // Sidebar ein-/ausblenden
    // Overlay erstellen/entfernen
    // ChatWidget initialisieren (lazy loading)
}
```

### Data Attributes
Die Chat-Sidebar erhält folgende Attribute:
- `data-object-type`: "item" oder "task"
- `data-object-id`: UUID des Objekts

### Kontext-History
- **Anzahl**: Letzte 10 Nachrichten
- **Bereits implementiert**: Keine Änderungen nötig
- **Datei**: `ChatWidget.js` Line 248
- **Code**: `const conversationHistory = this.messages.slice(-10);`

### Weaviate/KnowledgeObject Suche
- Filtert automatisch nach `object_id`
- Kontext ist auf das jeweilige Item/Task beschränkt

## Styling

### Chat-Sidebar
```css
.chat-sidebar {
    position: fixed;
    width: 450px;
    height: 100vh;
    right: 0;
    transform: translateX(100%); /* Initially hidden */
}

.chat-sidebar.show {
    transform: translateX(0); /* Slide in */
}
```

### Thinking Animation
```css
@keyframes thinkingPulse {
    0%, 60%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
    }
    30% {
        transform: scale(1.2);
        opacity: 1;
    }
}
```

## Tests

Alle Tests befinden sich in `main/test_chat_sidebar.py`:

1. `test_chat_sidebar_in_item_detail` - Sidebar in Item-View
2. `test_chat_sidebar_in_task_detail` - Sidebar in Task-View
3. `test_chat_sidebar_has_correct_data_attributes_item` - Data Attributes (Item)
4. `test_chat_sidebar_has_correct_data_attributes_task` - Data Attributes (Task)
5. `test_activity_sidebar_removed_from_base` - Activity Sidebar entfernt
6. `test_chat_button_not_in_floating_dock` - Chat-Button aus Dock entfernt
7. `test_chat_sidebar_styling` - Styling vorhanden
8. `test_breadcrumb_chat_button_styling` - Breadcrumb-Button Styling
9. `test_chat_sidebar_javascript_functions` - JavaScript Funktionen

### Tests ausführen
```bash
python manage.py test main.test_chat_sidebar
```

## Responsive Design

### Desktop (> 768px)
- Sidebar: 450px Breite
- Button: Im Breadcrumb

### Mobile (≤ 768px)
- Sidebar: 100% Breite (Fullscreen)
- Button: Im Breadcrumb (gleiche Position)

## Browser-Kompatibilität

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Mobile Browser: ✅

Alle modernen Browser mit CSS Transitions und Flexbox Support.

## Zukünftige Erweiterungen

Mögliche Verbesserungen:
- Chat-Sidebar Breite anpassbar machen
- Chat-Sidebar Position (links/rechts) konfigurierbar
- Mehrere Chat-Instanzen gleichzeitig öffnen
- Chat-History persistent speichern

## Troubleshooting

### Chat öffnet nicht
- Prüfen: `data-object-id` ist gesetzt
- Prüfen: `object_id` ist gültige UUID
- Console-Log: "ChatWidget: Cannot initialize without object_id"

### Thinking-Indikator bleibt sichtbar
- API-Fehler abfangen in `handleSendMessage` (ChatWidget.js)
- `removeThinkingIndicator()` wird im finally-Block aufgerufen (Line 290)
- Prüfen: API-Endpunkt erreichbar

### Sidebar bleibt offen
- Escape-Taste drücken
- Auf Overlay klicken
- JavaScript-Fehler in Console prüfen

## Support

Bei Fragen oder Problemen:
- Issue erstellen im Repository
- Test-Suite ausführen zur Diagnose
- Browser Console für JavaScript-Fehler prüfen
