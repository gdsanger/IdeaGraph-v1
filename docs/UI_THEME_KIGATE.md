# 🖌️ KIGate UI Theme Documentation

## Overview

KIGate uses a professional, technical dark mode color scheme that distinguishes it from IdeaGraph through emerald green accents. The theme is designed to convey **precision, stability, and security** - core values of an API Gateway platform.

## Design Philosophy

Unlike IdeaGraph's futuristic-creative amber/cyan palette, KIGate adopts:
- **Emerald Green** (#10B981) - Primary accent for precision and technical excellence
- **Indigo** (#6366F1) - Secondary accent maintaining connection to IdeaGraph
- **Dark Mode Only** - Enhanced focus on content and code visibility

## Color Palette

### Base Colors

| Element | Color | HEX | Usage |
|---------|-------|-----|-------|
| **Body Background** | Very Dark Anthracite | `#0C0E13` | Main application background |
| **Surface** | Dark Gray | `#181B22` | Cards, panels, containers |
| **Surface Hover** | Lighter Gray | `#1F232B` | Hover states |
| **Text Primary** | Light Gray/White | `#E5E7EB` | Main text content |
| **Text Muted** | Medium Gray | `#9CA3AF` | Secondary text |

### Accent Colors

| Element | Color | HEX | Purpose |
|---------|-------|-----|---------|
| **Primary** | Emerald Green | `#10B981` | Primary actions, KIGate brand |
| **Secondary** | Indigo | `#6366F1` | Secondary actions, IdeaGraph connection |
| **Success** | Light Green | `#22C55E` | Successful API calls |
| **Warning** | Orange | `#F59E0B` | Timeouts, token limits |
| **Danger** | Red | `#EF4444` | Error states |
| **Info** | Blue | `#3B82F6` | Information, status messages |

### Borders & Dividers

| Element | Color | HEX | Usage |
|---------|-------|-----|-------|
| **Border/Divider** | Dark Gray | `#2A2D34` | Lines, frames, separators |

## Bootstrap Integration

The theme integrates with Bootstrap 5 through CSS custom properties in `/main/static/main/css/kigate-theme.css`:

```css
:root {
  /* Base */
  --bs-body-bg: #0C0E13;
  --bs-body-color: #E5E7EB;
  --bs-border-color: #2A2D34;

  /* Surfaces */
  --bs-dark: #181B22;
  --bs-dark-rgb: 24, 27, 34;

  /* Accents */
  --bs-primary: #10B981;
  --bs-primary-rgb: 16, 185, 129;
  --bs-secondary: #6366F1;
  --bs-secondary-rgb: 99, 102, 241;
  --bs-success: #22C55E;
  --bs-warning: #F59E0B;
  --bs-danger: #EF4444;
  --bs-info: #3B82F6;
}
```

## Component Styling

### 🔘 Buttons

**Primary Button** - Emerald gradient with glow effect:
```css
.btn-primary {
  background: linear-gradient(135deg, #10B981, #34D399);
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}
```

**Secondary Button** - Indigo gradient:
```css
.btn-secondary {
  background: linear-gradient(135deg, #6366F1, #818CF8);
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.3);
}
```

### 🪟 Cards

Dark surface with subtle border and shadow:
```css
.card {
  background-color: #181B22;
  border: 1px solid #2A2D34;
  border-radius: 0.75rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}
```

### 📊 Tables

Dark theme with emerald accents:
```css
.table-dark {
  background-color: #181B22;
  color: #E5E7EB;
}

.table-dark tbody tr:hover {
  background-color: #1F232B;
}

.table-dark thead th {
  background-color: rgba(16, 185, 129, 0.15);
  border-bottom: 2px solid #10B981;
}
```

### 💬 Badges

Color-coded for different states:
```css
.badge-primary { background-color: #10B981; }
.badge-secondary { background-color: #6366F1; }
.badge-success { background-color: #22C55E; }
.badge-warning { background-color: #F59E0B; }
.badge-danger { background-color: #EF4444; }
```

### 📑 Tabs

Active tabs with emerald glow:
```css
.nav-tabs .nav-link.active {
  color: #10B981;
  background: rgba(16, 185, 129, 0.1);
  border-bottom: 2px solid #10B981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}
```

### 🧩 Forms & Inputs

Dark surface with emerald focus state:
```css
.form-control:focus {
  border-color: #10B981;
  box-shadow: 0 0 0 0.2rem rgba(16, 185, 129, 0.25);
}
```

### 🎯 Navbar

Dark with emerald bottom border:
```css
.navbar {
  background: rgba(12, 14, 19, 0.95);
  border-bottom: 2px solid #10B981;
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.2);
}
```

## UI Elements Examples

### Navbar
- **Background**: Dark with emerald border
- **Brand**: Emerald green with glow effect
- **Links**: Gray text with emerald hover
- **Active State**: Light emerald

### Buttons
- **Primary**: Emerald → Mint gradient with glow
- **Secondary**: Indigo gradient
- **Hover**: Enhanced glow and subtle lift
- **Focus**: Stronger glow effect

### Cards & Panels
- **Surface**: Dark gray background
- **Border**: Subtle dark border
- **Header**: Light emerald tint
- **Hover**: Stronger shadow

### Tables
- **Header**: Emerald tinted background with emerald border
- **Rows**: Dark surface with hover effect
- **Borders**: Consistent dark gray

### Icons
Recommended to use Lucide Icons in emerald (#10B981) for consistency.

## Animations & Effects

### Glow Animation (Optional)
For primary buttons and active tabs:
```css
@keyframes glow-primary {
  0%, 100% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
  50% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.7); }
}

.btn-primary.glow {
  animation: glow-primary 2s ease-in-out infinite;
}
```

### Hover Transitions
All interactive elements use smooth transitions:
```css
transition: all 0.3s ease;
```

## Accessibility

### High Contrast
- Text colors meet WCAG AA standards
- Primary text: `#E5E7EB` on `#0C0E13` = 14.7:1 ratio
- Accent colors chosen for visibility

### Focus States
Clear focus indicators for keyboard navigation:
```css
*:focus-visible {
  outline: 2px solid #10B981;
  outline-offset: 2px;
}
```

### Readable Hover States
All interactive elements have clear hover feedback through color changes and visual effects.

## Comparison: IdeaGraph vs KIGate

| Aspect | IdeaGraph | KIGate |
|--------|-----------|--------|
| **Primary Color** | Amber (#E49A28) | Emerald (#10B981) |
| **Secondary Color** | Cyan (#4BD0C7) | Indigo (#6366F1) |
| **Character** | Futuristic, Creative | Technical, Precise |
| **Use Case** | Idea Management | API Gateway |
| **Visual Style** | Warm, Dynamic | Cool, Professional |

## Implementation

### File Location
`/main/static/main/css/kigate-theme.css`

### Integration
Included in base template after Bootstrap CSS:
```html
<!-- Bootstrap 5 CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<!-- KIGate Theme CSS -->
<link rel="stylesheet" href="{% static 'main/css/kigate-theme.css' %}" />
```

### Template Compatibility
The theme uses CSS custom properties to override Bootstrap defaults, ensuring:
- ✅ No template changes required
- ✅ Full Bootstrap component compatibility
- ✅ Easy theme switching via CSS file
- ✅ Consistent styling across all pages

## Utility Classes

### Text Colors
```css
.text-primary    /* Emerald */
.text-secondary  /* Indigo */
.text-success    /* Green */
.text-warning    /* Orange */
.text-danger     /* Red */
.text-info       /* Blue */
.text-muted      /* Gray */
```

### Background Colors
```css
.bg-primary      /* Emerald */
.bg-secondary    /* Indigo */
.bg-surface      /* Dark gray surface */
```

### Border Colors
```css
.border-primary    /* Emerald */
.border-secondary  /* Indigo */
```

### Icon Colors
```css
.icon-primary      /* Emerald */
.icon-secondary    /* Indigo */
.icon-success      /* Green */
.icon-warning      /* Orange */
.icon-danger       /* Red */
.icon-info         /* Blue */
```

## Best Practices

### Do's ✅
- Use emerald (#10B981) for primary actions and success states
- Use indigo (#6366F1) for secondary actions
- Apply consistent hover effects (transform, glow)
- Maintain dark surfaces (#181B22) for cards and panels
- Use proper semantic colors (danger, warning, info)

### Don'ts ❌
- Don't mix IdeaGraph amber/cyan colors with KIGate theme
- Don't use light backgrounds (dark mode only)
- Don't override Bootstrap classes unnecessarily
- Don't reduce contrast below WCAG AA standards

## Future Enhancements

Potential improvements for consideration:
1. Theme toggler (IdeaGraph ↔ KIGate)
2. Custom icons library aligned with KIGate brand
3. Animated loading states with emerald accents
4. Enhanced data visualization color palette
5. Responsive breakpoint-specific styling

## Technical Notes

### CSS Variables
All colors are defined as CSS custom properties for easy theming and maintenance.

### Cascading Order
1. Bootstrap 5 base styles
2. KIGate theme overrides
3. Component-specific styles (site.css, etc.)

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS custom properties required
- CSS Grid and Flexbox used throughout

### Performance
- Minimal CSS overhead (~14KB)
- No JavaScript required for basic theming
- Hardware-accelerated transitions

## Contact

**Created by:** Christian Angermeier  
**Email:** ca@angermeier.net  
**Date:** 2025-10-28  
**Version:** 1.0

---

*This theme represents the technical, professional character of KIGate while maintaining visual harmony with the IdeaGraph ecosystem.*
