# Milestone Interactive AI Analysis - UI Workflow

## Visual Overview

This document provides a visual representation of the interactive AI analysis workflow in the Milestone Knowledge Hub.

## User Interface Structure

### 1. Milestone Detail Page - Context Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🏁 Milestone: Q4 2025 Launch                                        │
│ Status: In Progress | Due: 31.12.2025                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ [Summary] [Tasks (5)] [Context (3)] ◄─ Active Tab                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 📄 Context Objects                                                   │
│                                                                      │
│  [+ Add Context Object ▼]                                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 📄 Meeting_Protocol_Q4.pdf                                  │    │
│  │ File • 23.10.2025 14:30 • by testuser                      │    │
│  │                                                              │    │
│  │ ✓ Analyzed                                                  │    │
│  │                                                              │    │
│  │ Summary: Discussed Q4 launch strategy and timeline...      │    │
│  │ ⚠ 3 task(s) derived                                        │    │
│  │                                                              │    │
│  │                          [📥 Download]  [👁 Show Results]   │    │
│  │                          [✓ Accept]     [➕ Create Tasks]   │    │
│  │                          [🗑 Delete]                         │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 🗒 Team Meeting Notes                                       │    │
│  │ Note • 22.10.2025 10:15 • by testuser                      │    │
│  │                                                              │    │
│  │ ⏱ Not Analyzed                                              │    │
│  │                                                              │    │
│  │                          [🤖 Analyze]                        │    │
│  │                          [🗑 Delete]                         │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Analysis Results Modal (Show Results)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🤖 AI Analysis Results                                          [✕]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Context Object:                                                     │
│  Meeting_Protocol_Q4.pdf                                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 📝 Summary                       [✨ Enhance Summary]       │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ The meeting covered three main topics:                     │    │
│  │ 1. Launch timeline for Q4 2025                             │    │
│  │ 2. Marketing strategy and channels                         │    │
│  │ 3. Technical requirements and dependencies                 │    │
│  │                                                             │    │
│  │ Key decisions:                                              │    │
│  │ - Launch date set for December 15                          │    │
│  │ - Marketing budget approved                                 │    │
│  │ - Dev team needs 2 additional resources                    │    │
│  └────────────────────────────────────────────────────────────┘    │
│  ℹ You can edit the summary before accepting.                       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ 📋 Derived Tasks                                            │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ ┌────────────────────────────────────────────────────┐ [×] │    │
│  │ │ Title: [Finalize launch date and create timeline ]     │ │    │
│  │ │ Desc:  [Coordinate with team to confirm Dec 15... ]     │ │    │
│  │ └────────────────────────────────────────────────────┘     │    │
│  │                                                             │    │
│  │ ┌────────────────────────────────────────────────────┐ [×] │    │
│  │ │ Title: [Prepare marketing campaign materials      ]     │ │    │
│  │ │ Desc:  [Create content, graphics, and schedule... ]     │ │    │
│  │ └────────────────────────────────────────────────────┘     │    │
│  │                                                             │    │
│  │ ┌────────────────────────────────────────────────────┐ [×] │    │
│  │ │ Title: [Hire additional development resources     ]     │ │    │
│  │ │ Desc:  [Post job listings and conduct interviews..]     │ │    │
│  │ └────────────────────────────────────────────────────┘     │    │
│  │                                                             │    │
│  │ [+ Add Task]                                                │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ ℹ When you accept these results:                            │    │
│  │  • The summary will be added to the milestone with source   │    │
│  │  • Tasks can be created from the derived task list          │    │
│  │  • The context object will be marked as accepted            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  [Cancel]                              [✓ Accept & Apply]           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Summary Tab (After Acceptance)

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Summary] ◄─ Active Tab   [Tasks (8)]  [Context (3)]                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 🤖 AI-Generated Summary              [🔄 Regenerate Summary]         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  The meeting covered three main topics:                              │
│  1. Launch timeline for Q4 2025                                      │
│  2. Marketing strategy and channels                                  │
│  3. Technical requirements and dependencies                          │
│                                                                      │
│  Key decisions:                                                      │
│  - Launch date set for December 15                                   │
│  - Marketing budget approved                                         │
│  - Dev team needs 2 additional resources                             │
│                                                                      │
│  – aus ContextObject [Meeting_Protocol_Q4.pdf]                      │
│                                                                      │
│  ───────────────────────────────────────────────────────────────    │
│                                                                      │
│  Additional context from team discussions and planning sessions.     │
│  Focus on deliverables and resource allocation.                      │
│                                                                      │
│  – aus ContextObject [Team Meeting Notes]                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  [Context Objects: 3]  [Total Tasks: 8]  [Analyzed: 2]              │
└─────────────────────────────────────────────────────────────────────┘
```

## Workflow Diagram

```
User Actions                 System Response
─────────────────           ───────────────────

1. Add Context Object
   │
   ├─> File Upload          → Extract text content
   └─> Text Input           → Store in database
   │
   ↓

2. Auto-Analysis (Optional)
   │
   ├─> text-summary-agent   → Generate summary
   └─> task-derivation      → Derive tasks
   │
   ↓

3. Review Results
   │
   ├─> Click "Show Results" → Load analysis data
   │   │                     → Display in modal
   │   │
   │   ├─> Edit Summary      → Update in UI
   │   ├─> Edit Tasks        → Update in UI
   │   ├─> Add/Remove Tasks  → Update in UI
   │   │
   │   └─> "Enhance Summary" → Call summary-enhancer-agent
   │       │                  → Update summary
   │       │
   │   ↓
   │
   └─> Click "Accept"        → Accept without editing
       │
       ↓

4. Accept & Apply
   │
   ├─> Save edited data      → Update context object
   ├─> Append to milestone   → Add summary with source
   └─> Mark as analyzed      → Set analyzed = true
   │
   ↓

5. Create Tasks
   │
   ├─> Click "Create Tasks"  → Create Task objects
   │                          → Link to milestone/item
   │                          → Mark as AI-generated
   │
   ↓

6. View Results
   │
   ├─> Summary Tab           → Show combined summary
   │                          → Include source references
   │
   └─> Tasks Tab             → Show all tasks
                              → Filter/sort options
```

## Button States & Logic

### Context Object Card Buttons

| Button           | Visible When                    | Action                              |
|------------------|---------------------------------|-------------------------------------|
| 🤖 Analyze       | `analyzed == false`             | Run AI analysis                     |
| 👁 Show Results  | `analyzed == true`              | Open review modal                   |
| ✓ Accept         | `analyzed == true && has_tasks` | Quick accept without editing        |
| ➕ Create Tasks  | `has_derived_tasks == true`     | Create Task objects from list       |
| 📥 Download      | `type == 'file' && has_source`  | Download original file              |
| 🗑 Delete        | Always visible                  | Delete context object               |

### Modal Buttons

| Button              | Action                                    |
|---------------------|-------------------------------------------|
| ✨ Enhance Summary  | Call summary-enhancer-agent               |
| + Add Task          | Add empty task to list                    |
| × (on task)         | Remove task from list                     |
| Cancel              | Close modal without saving                |
| ✓ Accept & Apply    | Save edits and apply to milestone         |

## Color Coding

```
Status Badges:
  ✓ Analyzed         → Green (bg-success)
  ⏱ Not Analyzed     → Gray (bg-secondary)
  ⚠ Tasks Derived    → Yellow (bg-warning)

Buttons:
  Primary Actions    → Blue (btn-primary)
  Success Actions    → Green (btn-success)
  Info Actions       → Cyan (btn-info)
  Danger Actions     → Red (btn-danger)
  Secondary Actions  → Gray (btn-secondary)

Context Type Icons:
  📄 File            → Icon varies by file type
  ✉️ Email           → Envelope emoji
  🎙️ Transcript      → Microphone emoji
  🗒️ Note            → Note emoji
```

## Responsive Behavior

### Desktop (≥992px)
- Modal: Large size (modal-lg)
- Buttons: Full labels visible
- Layout: Side-by-side button groups

### Tablet (768px - 991px)
- Modal: Medium size
- Buttons: Abbreviated labels
- Layout: Stacked button groups

### Mobile (<768px)
- Modal: Full width
- Buttons: Icon only
- Layout: Vertical stacking

## Accessibility Features

- ✅ ARIA labels on all interactive elements
- ✅ Keyboard navigation support
- ✅ Screen reader friendly
- ✅ Color contrast compliance (WCAG AA)
- ✅ Focus indicators
- ✅ Toast notifications for status updates

## Performance Considerations

- **Lazy Loading**: Analysis data loaded only when modal opened
- **Debouncing**: Summary enhancement requests debounced (1s)
- **Caching**: Recent analysis results cached client-side
- **Progressive Enhancement**: Works without JavaScript (basic functionality)
- **Optimistic UI**: Immediate feedback before server response

---

**Note:** All mockups use placeholders. Actual UI follows Bootstrap 5 dark theme with custom autumn color scheme.
