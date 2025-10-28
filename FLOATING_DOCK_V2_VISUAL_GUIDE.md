# Floating Action Dock v2 - Visual Comparison

## 🎨 Button Color Scheme

### Chat Button (💬)
- **Color**: Cyan `#4BD0C7` (var(--secondary-cyan))
- **Context**: Item View only
- **Hover**: Lighter cyan `#5dd4c7`
- **Shadow**: `rgba(75, 208, 199, 0.4)`

### Graph Button (🕸️)
- **Color**: Amber `#E49A28` (var(--primary-amber))
- **Context**: Item & Task Views
- **Hover**: Lighter amber `#f5a524`
- **Shadow**: `rgba(228, 154, 40, 0.4)`

### Files Button (📁)
- **Color**: Neutral Gray `#6b7280`
- **Context**: Item & Task Views
- **Hover**: Lighter gray `#9ca3af`
- **Shadow**: `rgba(107, 114, 128, 0.4)`

### Search Button (🔍)
- **Color**: Gradient `linear-gradient(135deg, amber, cyan)`
- **Context**: All Views
- **Hover**: Enhanced gradient
- **Shadow**: `rgba(151, 181, 119, 0.4)`

---

## 📋 Context-Based Visibility

### Item Detail View
```
┌──────────┐
│   💬 Chat │  ← Cyan
├──────────┤
│ 🕸️ Graph  │  ← Amber
├──────────┤
│ 📁 Files  │  ← Gray
├──────────┤
│ 🔍 Search │  ← Gradient
└──────────┘
```

### Task Detail View
```
┌──────────┐
│ 🕸️ Graph  │  ← Amber
├──────────┤
│ 📁 Files  │  ← Gray
├──────────┤
│ 🔍 Search │  ← Gradient
└──────────┘
(Chat button hidden in task view)
```

---

## 🔄 Before vs After: Task Detail View

### BEFORE (Embedded Graph)
```
┌────────────────────────────────────────────────┐
│  Task Detail                                    │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │              │  │                       │   │
│  │  Task Info   │  │   Embedded Graph      │   │
│  │              │  │   (Always loaded)     │   │
│  │              │  │                       │   │
│  │              │  │   [Sigma.js Canvas]   │   │
│  │              │  │                       │   │
│  └──────────────┘  └──────────────────────┘   │
└────────────────────────────────────────────────┘
```

**Issues:**
- Graph always loaded (performance impact)
- Takes up screen space even when not needed
- Not consistent with item view
- Can't resize or reposition graph

### AFTER (Modal-Based)
```
┌────────────────────────────────────────────────┐
│  Task Detail                                    │
│  ┌─────────────────────────────────────────┐   │
│  │                                          │   │
│  │  Task Info                               │   │
│  │  (Full width, cleaner layout)            │   │
│  │                                          │   │
│  │                                          │   │
│  └─────────────────────────────────────────┘   │
└────────────────────────────────────────────────┘
                                          ┌──────────┐
                                          │ 🕸️ Graph  │ ← Click to open modal
                                          ├──────────┤
                                          │ 📁 Files  │
                                          ├──────────┤
                                          │ 🔍 Search │
                                          └──────────┘
```

**Benefits:**
- Graph loaded only when needed (lazy loading)
- Cleaner, more spacious layout
- Consistent with item view
- Modal supports drag, resize, reposition
- More screen space for task information

---

## 🗂️ Files Modal Structure

### Empty State
```
┌─────────────────────────────────────────┐
│  📁 Files                          [X]   │
├─────────────────────────────────────────┤
│                                         │
│           📁                            │
│     Keine Dateien vorhanden             │
│                                         │
│  [📤 Datei hochladen]                   │
└─────────────────────────────────────────┘
```

### With Files
```
┌─────────────────────────────────────────┐
│  📁 Files                          [X]   │
├─────────────────────────────────────────┤
│  [📤 Datei hochladen]                   │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ 📄 document.pdf                │    │
│  │ 2.5 MB • 28.10.2025 • Upload  [⬇] │
│  └────────────────────────────────┘    │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ 📄 notes.md                    │    │
│  │ 15 KB • 27.10.2025 • Manual   [⬇] │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## 🔍 Global Search Modal Structure

### Initial State
```
┌─────────────────────────────────────────┐
│  🔍 Globale Semantische Suche      [X]  │
├─────────────────────────────────────────┤
│  Durchsuche alle Items, Tasks, Files... │
│                                         │
│  ┌──────────────────────────────┐      │
│  │ Suchbegriff...           [🔍] │      │
│  └──────────────────────────────┘      │
│                                         │
│              🔍                         │
│   Geben Sie einen Suchbegriff ein      │
└─────────────────────────────────────────┘
```

### With Results
```
┌─────────────────────────────────────────┐
│  🔍 Globale Semantische Suche      [X]  │
├─────────────────────────────────────────┤
│  ┌──────────────────────────────┐      │
│  │ docker kubernetes        [🔍] │      │
│  └──────────────────────────────┘      │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ [task] Kubernetes Setup   [95%]│    │
│  │ Configure K8s cluster...       │    │
│  │ [Öffnen]                       │    │
│  └────────────────────────────────┘    │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ [item] Docker Migration   [87%]│    │
│  │ Plan migration to Docker...    │    │
│  │ [Öffnen]                       │    │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## 📱 Responsive Behavior

### Desktop (> 1024px)
```
┌──────────────────────────────────────┐
│  Content Area                        │
│                                      │
│                                      │  ┌──────────┐
│                                      │  │   💬     │
│                                      │  ├──────────┤
│                                      │  │   🕸️     │
│                                      │  ├──────────┤
│                                      │  │   📁     │
│                                      │  ├──────────┤
│                                      │  │   🔍     │
│                                      │  └──────────┘
└──────────────────────────────────────┘
```
- Fixed position, right side
- Vertical stack
- 56px × 56px buttons

### Tablet (768px - 1024px)
```
┌────────────────────────────────┐
│  Content Area                  │
│                                │
│                                │  ┌────────┐
│                                │  │   💬   │
│                                │  ├────────┤
│                                │  │   🕸️   │
│                                │  ├────────┤
│                                │  │   📁   │
│                                │  ├────────┤
│                                │  │   🔍   │
└────────────────────────────────┘  └────────┘
```
- Fixed position, right side
- Vertical stack
- 48px × 48px buttons

### Mobile (< 768px)
```
┌────────────────────────────────┐
│  Content Area                  │
│                                │
│                                │
│                                │
│                                │
└────────────────────────────────┘
 ┌──┬──┬──┬──┐
 │💬│🕸️│📁│🔍│
 └──┴──┴──┴──┘
```
- Fixed position, bottom
- Horizontal row
- 52px × 52px buttons

---

## 🎭 Modal Interaction States

### Closed
- Modal hidden
- No performance impact
- Content not loaded

### Opening
```
[Button Click]
    ↓
[Modal Fade In]
    ↓
[Show Loading Spinner]
    ↓
[Fetch Content via API]
    ↓
[Render Content]
    ↓
[Hide Loading Spinner]
```

### Open
- Modal visible and interactive
- Draggable by header
- Resizable by bottom-right handle
- Position/size saved to localStorage

### Closing
- Modal fades out
- Position/size persisted
- Content remains loaded (cached)
- Next open is instant

---

## 🎨 Animation & Transitions

### Button Hover
```css
transform: scale(1.1);
transition: all 0.2s ease-in-out;
box-shadow: enhanced;
```

### Button Active/Click
```css
transform: scale(0.95);
```

### Modal Appearance
```css
opacity: 0 → 1;
transition: fade 0.3s;
```

### Loading States
```css
spinner-border rotating
opacity transitions
```

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  Item/Task Detail View                               │
│  ┌──────────────────────────────────────────────┐  │
│  │  {% include '_floating_action_dock.html' %}  │  │
│  │  with dock_context='item'|'task'             │  │
│  │       object_type='item'|'task'              │  │
│  │       object_id=item.id|task.id              │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  _floating_action_dock.html                          │
│  ┌─────────────┬──────────────┬─────────────────┐  │
│  │ Dock Div    │  Modal HTML  │  JavaScript     │  │
│  │ - Buttons   │  - Chat      │  - Lazy Load    │  │
│  │ - Context   │  - Graph     │  - Event        │  │
│  │   Attrs     │  - Files     │    Handlers     │  │
│  │             │  - Search    │  - API Calls    │  │
│  └─────────────┴──────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  CSS Context Rules                                   │
│  .floating-action-dock[data-context="item"]         │
│  .floating-action-dock[data-context="task"]         │
│  → Show/hide buttons based on context               │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  API Endpoints                                       │
│  - /api/items/<id>/files                            │
│  - /api/tasks/<id>/files                            │
│  - /api/search (POST with query)                    │
└─────────────────────────────────────────────────────┘
```

---

**Created**: October 28, 2025  
**Status**: ✅ Implementation Complete
