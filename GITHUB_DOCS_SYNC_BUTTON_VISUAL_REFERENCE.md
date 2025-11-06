# GitHub Docs Sync Button - Visual Reference

## Button Location

The "Sync GitHub Docs" button is located on the **Item Detail Page** in the action buttons section.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Item Details                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ Title:     [Item Title Field]                                   [AI★]   │
│                                                                          │
│ Description: [Markdown Editor]                                          │
│                                                                          │
│ [Other fields: GitHub Repo, Section, Status, Parent, etc.]             │
│                                                                          │
│ Action Buttons:                                                         │
│ ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐                      │
│ │  Save  │ │ Delete │ │AI Enhance│ │Build Tasks│                      │
│ └────────┘ └────────┘ └──────────┘ └───────────┘                      │
│                                                                          │
│ ┌────────────────┐ ┌──────────────────┐ ┌───────────────┐            │
│ │Check Similarity│ │Sync GitHub Issues│ │Sync GitHub Docs│ ← NEW!    │
│ └────────────────┘ └──────────────────┘ └───────────────┘            │
│                                                                          │
│ ┌──────────────┐                                                       │
│ │Send via Email│                                                       │
│ └──────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Button States

### Enabled State
```
┌───────────────────────────────────────────┐
│ 📄 Sync GitHub Docs                       │ ← Clickable, outline-info style
└───────────────────────────────────────────┘
Tooltip: "Sync GitHub Documentation"
```

### Disabled State (No GitHub Repo)
```
┌───────────────────────────────────────────┐
│ 📄 Sync GitHub Docs                       │ ← Grayed out, not clickable
└───────────────────────────────────────────┘
Tooltip: "No GitHub repository set for this item"
```

### Disabled State (GitHub Not Enabled)
```
┌───────────────────────────────────────────┐
│ 📄 Sync GitHub Docs                       │ ← Grayed out, not clickable
└───────────────────────────────────────────┘
Tooltip: "GitHub is not enabled"
```

### Loading State
```
┌───────────────────────────────────────────┐
│ 📄 Sync GitHub Docs ⟳                     │ ← Spinner visible, disabled
└───────────────────────────────────────────┘
```

## User Interaction Flow

```
User clicks "Sync GitHub Docs"
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Confirmation Dialog                                          │
│                                                               │
│  This will synchronize all markdown documentation files      │
│  (.md) from the GitHub repository to this item.             │
│                                                               │
│  Files will be uploaded to SharePoint and indexed in         │
│  Weaviate for AI-powered search.                            │
│                                                               │
│  Do you want to continue?                                    │
│                                                               │
│           ┌────────┐        ┌────────┐                      │
│           │  OK    │        │ Cancel │                      │
│           └────────┘        └────────┘                      │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
    Button shows spinner
         │
         ▼
    API call to /api/github/sync-docs/{item_id}
         │
         ▼
    GitHubDocSyncService performs sync
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Success Message (Alert)                                      │
│                                                               │
│  GitHub documentation synchronization completed!             │
│                                                               │
│  Files processed: 10                                         │
│  Files synced: 8                                             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
    Files tab refreshes automatically
```

## Button Styling

**CSS Classes Used:**
- `btn` - Bootstrap button base class
- `btn-outline-info` - Light blue outline style (cyan color)
- Button text with icon: `<i class="bi bi-file-earmark-text"></i> Sync GitHub Docs`
- Spinner: `spinner-border spinner-border-sm` (hidden by default)

**Visual Style:**
- Border color: Light cyan (#17a2b8)
- Text color: Cyan
- Hover: Background becomes light cyan with white text
- Icon: File document icon from Bootstrap Icons
- Consistent with other action buttons in size and spacing

## Response Messages

### Success
```
┌──────────────────────────────────────────────────────────────┐
│  ✓ GitHub documentation synchronization completed!           │
│                                                               │
│  Files processed: 15                                         │
│  Files synced: 12                                            │
└──────────────────────────────────────────────────────────────┘
```

### Success with Errors
```
┌──────────────────────────────────────────────────────────────┐
│  ✓ GitHub documentation synchronization completed!           │
│                                                               │
│  Files processed: 15                                         │
│  Files synced: 10                                            │
│  Errors: 5                                                   │
└──────────────────────────────────────────────────────────────┘
```

### Error
```
┌──────────────────────────────────────────────────────────────┐
│  ✗ Failed to sync GitHub documentation                       │
│                                                               │
│  Item has no GitHub repository configured                    │
└──────────────────────────────────────────────────────────────┘
```

## Icon Reference

The button uses the Bootstrap Icon `bi-file-earmark-text`:
- Represents a document/file
- Indicates documentation content
- Consistent with the "file" theme
- Distinguishes from GitHub Issues sync which uses `bi-github`

## Comparison with Sync GitHub Issues Button

| Feature | Sync GitHub Issues | Sync GitHub Docs |
|---------|-------------------|------------------|
| Icon | `bi-github` | `bi-file-earmark-text` |
| Color | `btn-outline-primary` | `btn-outline-info` |
| Function | Creates tasks from issues | Syncs markdown files |
| Result | Tasks tab refresh | Files tab refresh |
| Confirmation | Yes | Yes |

## Keyboard Accessibility

- Button can be focused with Tab key
- Can be activated with Enter or Space key
- Tooltip appears on focus
- Confirmation dialog is keyboard-accessible
