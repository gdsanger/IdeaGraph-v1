# Chat Widget Quickstart Guide

## 🚀 Schnellstart für Entwickler

### Grundlegende Integration (3 Schritte)

#### 1. CSS einbinden
```html
<link rel="stylesheet" href="{% static 'main/css/chat-widget.css' %}" />
```

#### 2. JavaScript-Komponenten laden
```html
<script src="{% static 'main/js/chat-widget/ChatSources.js' %}"></script>
<script src="{% static 'main/js/chat-widget/ChatMessage.js' %}"></script>
<script src="{% static 'main/js/chat-widget/ChatWidget.js' %}"></script>
```

#### 3. Widget initialisieren
```html
<div id="chat-container"></div>

<script>
new ChatWidget({
    containerId: 'chat-container',
    itemId: '{{ item.id }}',
    apiBaseUrl: '/api/items'
});
</script>
```

## 💡 Verwendung in IdeaGraph

Das Widget ist bereits in der Item-Detailansicht integriert:

1. Öffne ein Item
2. Klicke auf den Tab "Frage stellen"
3. Stelle eine Frage im Chat-Eingabefeld
4. Die KI antwortet mit relevanten Informationen und Quellenangaben

## 🎯 Hauptfeatures

### Für Benutzer
- ✅ Intuitive Chat-Oberfläche
- ✅ Markdown-formatierte Antworten
- ✅ Quellenangaben mit Relevanz-Scores
- ✅ Verlaufsanzeige vergangener Fragen
- ✅ Echtzeit-Feedback mit Loading-Indicator

### Für Entwickler
- ✅ Modulare JavaScript-Komponenten
- ✅ Zero-Dependencies (außer marked.js)
- ✅ CSRF-Token-Handling automatisch
- ✅ Responsive Design out-of-the-box
- ✅ IdeaGraph CI-konform

## 🔧 Konfiguration

### Minimalkonfiguration
```javascript
new ChatWidget({
    containerId: 'chat',
    itemId: 'uuid-here'
});
```

### Vollständige Konfiguration
```javascript
new ChatWidget({
    containerId: 'chat-widget-container',
    itemId: '12345678-1234-1234-1234-123456789abc',
    apiBaseUrl: '/api/items',
    theme: 'dark',
    height: '600px',
    showHistory: true
});
```

## 📝 Beispiel: Standalone-Seite

```html
<!DOCTYPE html>
<html lang="de" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>IdeaGraph Chat</title>
    
    <!-- Dependencies -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    <link rel="stylesheet" href="/static/main/css/chat-widget.css" />
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <h1>Fragen zu Item XYZ</h1>
        <div id="my-chat"></div>
    </div>
    
    <!-- Chat Widget -->
    <script src="/static/main/js/chat-widget/ChatSources.js"></script>
    <script src="/static/main/js/chat-widget/ChatMessage.js"></script>
    <script src="/static/main/js/chat-widget/ChatWidget.js"></script>
    
    <script>
        new ChatWidget({
            containerId: 'my-chat',
            itemId: 'YOUR-ITEM-UUID',
            theme: 'dark',
            height: '700px'
        });
    </script>
</body>
</html>
```

## 🧪 Testen

### Schnelltest
1. Kopiere `/tmp/chat-widget-test.html` in einen Browser
2. Prüfe, ob das Widget geladen wird
3. Tippe im Eingabefeld
4. Character Counter sollte sich aktualisieren

### Integration-Test
```bash
python manage.py test main.test_item_question_answering
```

## 🐛 Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Widget nicht sichtbar | CSS-Datei eingebunden? Container-ID korrekt? |
| API-Fehler 403 | CSRF-Token fehlt oder ungültig |
| Markdown nicht gerendert | marked.js nicht geladen |
| Verlauf nicht sichtbar | Backend-Endpunkt erreichbar? |

## 📖 Weitere Dokumentation

- [CHAT_WIDGET_DOCUMENTATION.md](./CHAT_WIDGET_DOCUMENTATION.md) - Vollständige Dokumentation
- [main/test_item_question_answering.py](./main/test_item_question_answering.py) - Tests
- [API Documentation](./ITEM_QA_QUICKREF.md) - Backend API

## 🎨 Styling anpassen

### Theme wechseln
```javascript
new ChatWidget({
    theme: 'light'  // oder 'dark'
});
```

### Höhe anpassen
```javascript
new ChatWidget({
    height: '400px'  // beliebige CSS-Höhe
});
```

### Eigene CSS-Klassen
```css
/* In deiner CSS-Datei */
.chat-widget-container[data-theme="custom"] {
    /* Deine Anpassungen */
}
```

## 🔐 Sicherheit

✅ **Automatisch implementiert:**
- CSRF-Protection
- XSS-Prevention (HTML-Escaping)
- Input Validation (max 512 chars)
- Authentication via Session/JWT

❗ **Wichtig für Produktion:**
- HTTPS verwenden
- Rate Limiting konfigurieren
- DOMPurify für zusätzliche XSS-Sicherheit

## 📊 Performance-Tipps

1. **Lazy Loading**: Widget nur laden, wenn benötigt
2. **History Pagination**: Nur erste Seite laden
3. **Debouncing**: Bei häufigen Updates
4. **Caching**: Geladene Historie im State halten

## 💬 Support & Feedback

- **GitHub Issues**: Bug Reports & Feature Requests
- **Email**: ca@angermeier.net
- **Dokumentation**: Dieses Quickstart + CHAT_WIDGET_DOCUMENTATION.md

---

**Version**: 1.0  
**Letzte Aktualisierung**: 2025-10-27  
**Autor**: Christian Angermeier
