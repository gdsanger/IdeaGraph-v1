# Support-Analyse Feature - UI Mockup

## Task Detail View - Before Analysis

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Task Details                                                 Weaviate: ✓│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Title:  [___________________________________________________] [✨]      │
│                                                                          │
│  Description (Markdown)                    [✨ Optimize Text]           │
│                                            [🧠 Support-Analyse (Intern)]│
│                                            [🌍 Support-Analyse (Extern)]│
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ # Task Description                                                │  │
│  │                                                                    │  │
│  │ This task requires implementing a new feature...                  │  │
│  │                                                                    │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  [💾 Save]  [🗑️ Delete]  [📁 Move Task]  [✨ AI Enhancer]  [🔧 GitHub] │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Task Detail View - During Analysis (Loading)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Task Details                                                 Weaviate: ✓│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Title:  [___________________________________________________] [✨]      │
│                                                                          │
│  Description (Markdown)                    [✨ Optimize Text]           │
│                                            [🧠 Support-Analyse... ⟳]    │
│                                            [🌍 Support-Analyse (Extern)]│
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ # Task Description                                                │  │
│  │                                                                    │  │
│  │ This task requires implementing a new feature...                  │  │
│  │                                                                    │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ℹ️  Internal support analysis in progress...                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Task Detail View - After Analysis (Result Displayed)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Task Details                                                 Weaviate: ✓│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Title:  [___________________________________________________] [✨]      │
│                                                                          │
│  Description (Markdown)                    [✨ Optimize Text]           │
│                                            [🧠 Support-Analyse (Intern)]│
│                                            [🌍 Support-Analyse (Extern)]│
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ # Task Description                                                │  │
│  │                                                                    │  │
│  │ This task requires implementing a new feature...                  │  │
│  │                                                                    │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ╔═══════════════════════════════════════════════════════════════════╗  │
│  ║ 💡 Support-Analyse Ergebnis                                    ✖ ║  │
│  ╠═══════════════════════════════════════════════════════════════════╣  │
│  ║                                                                   ║  │
│  ║  ### 🧩 Interne Analyse                                          ║  │
│  ║                                                                   ║  │
│  ║  **Mögliche Ursache:**                                           ║  │
│  ║  - Fehlkonfiguration in der SharePoint Graph API                ║  │
│  ║  - Fehlende Berechtigungen im Azure App Registration            ║  │
│  ║                                                                   ║  │
│  ║  **Ähnliche Tasks:**                                             ║  │
│  ║  - "GraphAPI Auth Error" (#112) - Ähnlichkeit: 95%              ║  │
│  ║  - "SharePoint Access Denied" (#087) - Ähnlichkeit: 87%         ║  │
│  ║                                                                   ║  │
│  ║  **Handlungsempfehlungen:**                                      ║  │
│  ║  1. Prüfe Azure App Permissions (Delegated vs. Application)     ║  │
│  ║  2. Verifiziere SharePoint Site Collection Admin Rechte         ║  │
│  ║  3. Teste die Verbindung mit Graph Explorer                      ║  │
│  ║                                                                   ║  │
│  ╚═══════════════════════════════════════════════════════════════════╝  │
│                                                                          │
│  ✅ Internal support analysis completed successfully!                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Button States

### Normal State (Inactive)
```
┌─────────────────────────────────┐
│ 🧠 Support-Analyse (Intern)    │
└─────────────────────────────────┘
```

### Loading State (Active)
```
┌─────────────────────────────────┐
│ 🧠 Support-Analyse (Inte... ⟳ │  (disabled, with spinner)
└─────────────────────────────────┘
```

### Hover State
```
┌─────────────────────────────────┐
│ 🧠 Support-Analyse (Intern)    │  (slightly lighter background)
└─────────────────────────────────┘
```

## Result Card States

### Collapsed (Hidden)
- Not visible in the DOM (display: none)

### Expanded (Visible)
```
╔═══════════════════════════════════════════════════════════════════╗
║ 💡 Support-Analyse Ergebnis                                    ✖ ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [Markdown content rendered here]                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Color Scheme

### Internal Analysis Button
- **Background:** `btn-outline-primary` (Blue)
- **Icon:** 🧠 (Brain emoji)
- **Text:** "Support-Analyse (Intern)"

### External Analysis Button
- **Background:** `btn-outline-info` (Light Blue/Cyan)
- **Icon:** 🌍 (Globe emoji)
- **Text:** "Support-Analyse (Extern)"

### Result Card
- **Background:** `bg-dark border-info` (Dark with info border)
- **Header Icon:** 💡 (Light bulb emoji)
- **Close Button:** White close icon (btn-close-white)

### Success Alert
- **Type:** `alert-success` (Green)
- **Icon:** ✅ (Checkmark)
- **Auto-dismiss:** After 5 seconds

### Error Alert
- **Type:** `alert-danger` (Red)
- **Icon:** ⚠️ (Warning)
- **Auto-dismiss:** After 5 seconds

## Responsive Behavior

### Desktop (>768px)
- Buttons displayed horizontally in a row
- Result card takes full width below editor
- Comfortable padding and spacing

### Tablet (576px - 768px)
- Buttons may wrap to multiple lines
- Result card remains full width
- Reduced padding

### Mobile (<576px)
- Buttons stack vertically
- Text size slightly reduced
- Close button remains visible in top right

## Accessibility

### Keyboard Navigation
- ✅ All buttons are keyboard-accessible
- ✅ Tab order: Description → Optimize Text → Internal Analysis → External Analysis
- ✅ Close button accessible via Tab
- ✅ Enter/Space to activate buttons

### Screen Reader Support
- ✅ `aria-label` on close button
- ✅ Button text describes action
- ✅ Loading state announced
- ✅ Result card has descriptive header

### Visual Indicators
- ✅ Loading spinner during API calls
- ✅ Button disabled state during processing
- ✅ Success/Error alerts with icons
- ✅ Focus outline on interactive elements

## Animation & Transitions

### Button Click
- Spinner fades in (opacity 0 → 1)
- Button slightly dims (opacity 1 → 0.7)

### Result Card Appearance
- Smooth scroll to result (behavior: 'smooth')
- Card slides down (display: none → block)

### Alert Messages
- Fade in from top
- Auto-dismiss with fade out after 5 seconds

## User Flow

1. **User opens task detail page**
   → Both analysis buttons visible and enabled

2. **User clicks "Support-Analyse (Intern)"**
   → Button shows spinner, becomes disabled
   → Toast notification: "Processing..."

3. **API call in progress**
   → User can view other parts of the page
   → Other buttons remain functional

4. **Analysis complete**
   → Spinner disappears, button re-enabled
   → Result card appears below editor
   → Success alert shows at top
   → Page smoothly scrolls to result

5. **User reviews analysis**
   → Can read markdown-formatted recommendations
   → Can click links in new tab
   → Can copy text for documentation

6. **User closes result (optional)**
   → Clicks X button
   → Result card disappears
   → Can run analysis again if needed

7. **User saves task (optional)**
   → Analysis result remains visible
   → Can incorporate recommendations into task description
   → Clicks "Save" to persist changes
