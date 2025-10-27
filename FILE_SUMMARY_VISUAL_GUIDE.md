# File Summary Popup - Visual Guide

## Feature Overview

Diese Feature fügt einen "Show Summary" Button zu allen hochgeladenen Dateien hinzu, der eine KI-generierte Zusammenfassung in einem Modal anzeigt.

## UI-Komponenten

### 1. Neuer Button in der Aktionsspalte

```
+------------------+----------+---------------+------------------+------------------+
| Filename         | Size     | Uploaded By   | Weaviate Status  | Actions          |
+------------------+----------+---------------+------------------+------------------+
| document.pdf     | 2.5 MB   | Max Muster    | [✓ Synced]       | [📂] [📄] [🗑️]  |
|                  |          | 15.10.2024    |                  | Open  Sum  Del   |
+------------------+----------+---------------+------------------+------------------+
```

**Neu**: [📄] Button mit dem Tooltip "Show Summary"
- Position: Zwischen "Open in SharePoint" und "Delete" Button
- Style: `btn btn-sm btn-outline-info` (blauer Rand)
- Icon: `bi-file-text`

### 2. Modal-Popup beim Klick

```
┌────────────────────────────────────────────────────────────────┐
│ 📄 document.pdf                                          [X]    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Loading Spinner]                                              │
│  Generating summary...                                          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Loading State**: Zeigt Spinner während die KI-Zusammenfassung generiert wird

### 3. Modal mit gerenderte Zusammenfassung

```
┌────────────────────────────────────────────────────────────────┐
│ 📄 document.pdf                                          [X]    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  # Projektplanung Q4 2024                                       │
│                                                                 │
│  Dieses Dokument beschreibt die wichtigsten Meilensteine       │
│  für das vierte Quartal 2024:                                   │
│                                                                 │
│  - **Phase 1**: Anforderungsanalyse (Oktober)                   │
│  - **Phase 2**: Implementierung (November)                      │
│  - **Phase 3**: Testing und Deployment (Dezember)               │
│                                                                 │
│  Das Budget für dieses Projekt beträgt 150.000€.                │
│                                                                 │
│  ────────────────────────────────────────────────────────      │
│                                                                 │
│  [🔗 Open File]                                                 │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│                                            [Close]              │
└────────────────────────────────────────────────────────────────┘
```

**Zusammenfassung**: 
- Markdown-formatiert mit Überschriften, Listen, Fettdruck
- Scrollbar für lange Inhalte (max-height: 60vh)
- "Open File" Button zum Öffnen der Originaldatei

### 4. Fehler-Anzeige

```
┌────────────────────────────────────────────────────────────────┐
│ 📄 document.pdf                                          [X]    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚠️ File content not available in Weaviate                      │
│                                                                 │
│  Please wait for the file to be synchronized with               │
│  Weaviate, then try again.                                      │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│                                            [Close]              │
└────────────────────────────────────────────────────────────────┘
```

## Benutzer-Workflow

```
1. Benutzer lädt Datei hoch
   ↓
2. Datei wird mit Weaviate synchronisiert (automatisch)
   ↓
3. Weaviate-Status zeigt "✓ Synced"
   ↓
4. Benutzer klickt auf [📄] "Show Summary" Button
   ↓
5. Modal öffnet sich mit Loading-Spinner
   ↓
6. API-Request an /api/files/{file_id}/summary
   ↓
7. Backend holt Content aus Weaviate
   ↓
8. KIGate Agent generiert Zusammenfassung
   ↓
9. Markdown-gerenderte Zusammenfassung wird angezeigt
   ↓
10. Optional: Benutzer klickt "Open File" für Originaldatei
```

## Markdown-Rendering

Das Modal verwendet `marked.js` um folgende Markdown-Elemente zu rendern:

- **Überschriften**: # H1, ## H2, ### H3
- **Fettdruck**: **bold**
- **Listen**: 
  - Ungeordnet: - item
  - Geordnet: 1. item
- **Code**: `inline code` und ```code blocks```
- **Links**: [text](url)
- **Absätze**: Automatische Formatierung

## CSS-Styling

```css
.markdown-content {
    max-height: 60vh;          /* Scrollbar bei langen Inhalten */
    overflow-y: auto;
}

.markdown-content h1, h2, h3 {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}

.markdown-content code {
    background-color: rgba(255, 255, 255, 0.1);
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
}

.markdown-content pre {
    background-color: rgba(255, 255, 255, 0.05);
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
}
```

## Responsive Design

- **Desktop**: Modal mit 800px Breite (`modal-lg`)
- **Mobile**: Modal passt sich der Bildschirmbreite an
- **Tablet**: Optimale Lesbarkeit durch responsive Schriftgrößen

## Integration

Das Feature ist in zwei Templates integriert:
1. **Items**: `main/templates/main/items/_files_list.html`
2. **Tasks**: `main/templates/main/tasks/_files_list.html`

Beide Templates haben identische Funktionalität und UI.
