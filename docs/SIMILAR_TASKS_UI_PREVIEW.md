# Similar Tasks UI Preview

## Task Detail Page - "Ähnliche Aufgaben" Section

The "Ähnliche Aufgaben" (Similar Tasks) section appears at the bottom of the task detail page.

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Ähnliche Aufgaben                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  [Task Icon] Implement user authentication         [🔵 Working]  │
│  │  Task · Ähnlichkeit: 92%                                │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  [GitHub Icon] Add OAuth support                   [🔵 Open]     │
│  │  GitHub Issue · Ähnlichkeit: 85%                        │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  [Task Icon] Create login page                     [🟢 Ready]    │
│  │  Task · Ähnlichkeit: 83%                                │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Loading State

```
┌─────────────────────────────────────────────────────────────────┐
│  Ähnliche Aufgaben                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        [Loading Spinner]                        │
│        Suche nach ähnlichen Aufgaben und GitHub-Issues...      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Empty State

```
┌─────────────────────────────────────────────────────────────────┐
│  Ähnliche Aufgaben                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                          [Info Icon]                            │
│     Keine ähnlichen Aufgaben oder GitHub-Issues gefunden.      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Error State

```
┌─────────────────────────────────────────────────────────────────┐
│  Ähnliche Aufgaben                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        [Warning Icon]                           │
│            Fehler beim Laden ähnlicher Aufgaben.               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Visual Elements

### Status Badges

- **⚪ Neu** (New) - Gray badge (bg-secondary)
- **🔵 Working** (Working) - Blue badge (bg-primary)
- **🟡 Review** (Review) - Yellow badge (bg-warning)
- **🟢 Ready** (Ready) - Green badge (bg-success)
- **✅ Erledigt** (Done) - Gray badge (bg-secondary)

### Type Icons

- **Task**: List icon (bi-list-task) - ☰
- **GitHub Issue**: GitHub icon (bi-github) - 🐙

### Interactive Elements

**Task Cards:**
- Hover: Cursor changes to pointer
- Click: Navigates to task detail page

**GitHub Issue Cards:**
- Hover: Cursor changes to pointer
- Click: Opens GitHub issue in new browser tab

### Similarity Display

Format: `Ähnlichkeit: XX%`
- Range: 80% - 100% (only items >= 80% similarity are shown)
- Higher percentages appear first (sorted descending)

## Color Scheme

Following the application's "Autumn" theme:
- Card background: `rgba(31, 41, 55, 0.9)` (dark translucent)
- Text: White/Light gray
- Borders: Bootstrap default border color
- Hover effect: Slightly lighter background

## Responsive Behavior

- **Desktop**: Full width cards with proper padding
- **Mobile**: Cards stack vertically, touch-friendly
- **Tablet**: Same as desktop with adjusted margins

## Accessibility

- Semantic HTML structure
- Proper ARIA labels
- Screen reader friendly
- Keyboard navigation support
- Loading states announced to screen readers

## Animation

- Smooth fade-in when results load
- Subtle hover effect on cards
- Loading spinner animation
- No jarring transitions

## Implementation Details

### CSS Classes Used
- `.card` - Bootstrap card component
- `.similar-task-card` - Custom class with hover cursor
- `.badge` - Bootstrap badge component
- `.spinner-border` - Bootstrap loading spinner
- `.text-muted` - Muted text color
- `.bi-*` - Bootstrap icons

### JavaScript Behavior
- Async fetch on page load
- Dynamic card generation
- Event delegation for clicks
- Error handling and fallbacks
- HTML escaping for security
