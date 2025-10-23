# Milestone Summary Optimization - User Flow

## Visual Overview

### 1. Initial State - Milestone Detail Page
```
┌─────────────────────────────────────────────────────────────────┐
│ Milestone: Test Milestone                                        │
├─────────────────────────────────────────────────────────────────┤
│ [Summary] [Tasks] [Context Objects]                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🤖 AI-Generated Summary                                         │
│                                    [🔄 Regenerate] [✨ AI-Optimize]│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ This is the current milestone summary. It may contain some │ │
│  │ redundant information and could be better structured.      │ │
│  │ This is the current milestone summary text again.          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Statistics: [Context Objects: 3] [Tasks: 5] [Analyzed: 2]     │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Click "AI-Optimize" Button
The button shows a loading state while the AI processes the summary:

```
[✨ AI-Optimize]  →  [✨ AI-Optimize ⟳]  (Button disabled with spinner)
```

### 3. Optimization Modal Opens - Loading State
```
┌───────────────────────────────────────────────────────────────────┐
│ ✨ AI Summary Optimization                                    [×] │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│                          ⟳                                        │
│                    (spinner animation)                            │
│                                                                   │
│              Optimizing summary with AI...                        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 4. Comparison View After Processing
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ✨ AI Summary Optimization                                           [×] │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ℹ️  Review the AI-optimized version below. You can accept it or discard │
│    it and keep your current summary.                                     │
│                                                                          │
│ ┌─────────────────────────────┬────────────────────────────────────────┐│
│ │ 📄 Original Summary         │ ⭐ AI-Optimized Summary              ││
│ │ ─────────────────────────── │ ──────────────────────────────────── ││
│ │                             │                                        ││
│ │ This is the current         │ **Summary**                            ││
│ │ milestone summary. It may   │                                        ││
│ │ contain some redundant      │ This milestone's current progress      ││
│ │ information and could be    │ indicates room for better              ││
│ │ better structured. This is  │ structuring. The following key         ││
│ │ the current milestone       │ points have been identified:           ││
│ │ summary text again.         │                                        ││
│ │                             │ - Progress tracking improvements       ││
│ │ (Gray background)           │ - Enhanced documentation structure     ││
│ │                             │                                        ││
│ │                             │ (Green background)                     ││
│ └─────────────────────────────┴────────────────────────────────────────┘│
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                      [❌ Discard] [✅ Accept & Save]    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5a. User Clicks "Accept & Save"
- Button shows loading state
- API call saves the optimized summary
- Success toast notification appears
- Page reloads showing the new summary
- Version history entry created in database

```
Toast: ✅ Optimized summary saved successfully!

Page reloads with new summary displayed.
```

### 5b. User Clicks "Discard"
- Modal closes immediately
- No changes are made
- Original summary remains unchanged

```
Modal closes. No notification needed.
```

## Component Breakdown

### Button States
1. **Default**: `[✨ AI-Optimize]` - Green button with icon
2. **Loading**: `[✨ AI-Optimize ⟳]` - Button disabled with spinner
3. **Disabled**: Button hidden when no summary exists

### Modal States
1. **Loading**: Shows spinner with message
2. **Comparison**: Side-by-side view with action buttons
3. **Error**: Shows error message with retry option

### API Flow
```
User Click → POST /api/milestones/{id}/optimize-summary
           ↓
        AI Processing (summary-enhancer-agent via KiGate)
           ↓
        Response with optimized_summary
           ↓
        Display in Modal
           ↓
  [User Reviews and Accepts]
           ↓
        POST /api/milestones/{id}/save-optimized-summary
           ↓
        Update Milestone.summary
           ↓
        Create MilestoneSummaryVersion entry
           ↓
        Reload Page
```

## Color Scheme

- **Original Summary Card**: Gray/Secondary background (`bg-secondary`)
- **Optimized Summary Card**: Green background with opacity (`bg-success bg-opacity-10`)
- **Success Elements**: Green (`text-success`, `btn-success`)
- **Modal Background**: Dark theme (`bg-dark`)
- **Buttons**: 
  - AI-Optimize: Green (`btn-success`)
  - Accept & Save: Green (`btn-success`)
  - Discard: Gray (`btn-secondary`)

## Responsive Design

The modal is full-width (`modal-xl`) and scrollable (`modal-dialog-scrollable`), ensuring:
- Side-by-side comparison on desktop
- Scrollable content for long summaries
- Mobile-friendly layout (columns stack on small screens)

## Error Handling

### No Summary Available
```
┌─────────────────────────────────────────────┐
│ ⚠️ Error                                     │
├─────────────────────────────────────────────┤
│ No summary available to optimize.           │
│ Generate a summary first.                   │
└─────────────────────────────────────────────┘

Toast: ⚠️ No summary available to optimize. Generate a summary first.
```

### AI Service Error
```
┌─────────────────────────────────────────────┐
│ ⚠️ Error                                     │
├─────────────────────────────────────────────┤
│ AI summary optimization failed.             │
│ Details: Connection timeout                 │
└─────────────────────────────────────────────┘

Toast: ❌ Error: AI summary optimization failed
```

### Permission Denied
```
Toast: ❌ Permission denied
(Status 403, user redirected or shown error)
```

## Accessibility

- All interactive elements have proper ARIA labels
- Modal can be closed with Escape key
- Focus management when modal opens/closes
- Screen reader friendly content descriptions
- Color contrast meets WCAG standards
- Loading states clearly indicated

## Performance

- Modal loads instantly (no lazy loading needed)
- API calls use proper loading indicators
- Toast notifications auto-dismiss after 5 seconds
- Page reload only after successful save
- No unnecessary re-renders during optimization

## Browser Compatibility

Works with all modern browsers supporting:
- ES6+ JavaScript
- Bootstrap 5 modals and toasts
- Fetch API
- CSS Grid/Flexbox
