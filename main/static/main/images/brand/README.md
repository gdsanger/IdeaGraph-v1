# IdeaGraph Brand Assets Documentation

## 📁 Directory Structure

```
main/static/main/images/brand/
├── ideagraph_logo_primary.svg      # Primary logo with wordmark and icon
├── ideagraph_logo_icon.svg         # Icon-only variant for favicons
└── ideagraph_logo_monochrome.svg   # Monochrome variant for special uses
```

## 🎨 Color Palette

The IdeaGraph Corporate Identity uses the following color scheme:

| Variable Name | Hex Code | RGB | Usage |
|---------------|----------|-----|-------|
| `--primary-amber` | `#E49A28` | rgb(228, 154, 40) | Primary accent color, buttons, branding |
| `--secondary-cyan` | `#4BD0C7` | rgb(75, 208, 199) | Interactive elements, highlights, links |
| `--tech-blue` | `#2AB3D1` | rgb(42, 179, 209) | Hover effects, secondary actions |
| `--graph-gray` | `#1A1A1A` | rgb(26, 26, 26) | Dark mode background |
| `--soft-white` | `#EAEAEA` | rgb(234, 234, 234) | Text color, high contrast |

## 🔤 Typography

### Font Stack

**Primary Font (Headlines/Headings):**
- Font: Poppins
- Weights: 400 (Regular), 600 (Semibold), 700 (Bold)
- Source: Google Fonts
- Fallback: 'Inter', system-ui, sans-serif

**Secondary Font (Body Text/UI):**
- Font: Inter
- Weights: 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
- Source: Google Fonts
- Fallback: system-ui, sans-serif

### Font Sizes
- H1: 32px / Bold
- H2: 24px / Semibold
- Body: 16px / Regular
- Small text: 14px / Regular

## 🖼️ Logo Usage Guidelines

### Primary Logo (`ideagraph_logo_primary.svg`)
- **Use for:** Website headers, presentations, splash screens
- **Minimum width:** 200px
- **Background:** Dark (#121212 or similar)
- **Clear space:** Minimum 32px on all sides
- **Contains:** Full wordmark "IdeaGraph" + network G icon + tagline

### Icon Only (`ideagraph_logo_icon.svg`)
- **Use for:** Favicons, app icons, social media avatars
- **Minimum size:** 64 × 64 px
- **Recommended sizes:** 64px, 128px, 256px, 512px
- **Format:** Square (1:1 aspect ratio)
- **Contains:** Network G symbol only

### Monochrome (`ideagraph_logo_monochrome.svg`)
- **Use for:** Print materials, watermarks, alternative themes
- **Colors:** White (#FFFFFF) on dark backgrounds
- **Use cases:** Single-color printing, embossing, subtle branding

## 🎯 Brand Elements

### Network G Symbol
The icon represents a knowledge graph with:
- Central node (amber) - represents the core idea/concept
- 5 outer nodes (cyan) - represent connected knowledge points
- Connection lines (tech blue) - represent relationships
- G-shaped arc (amber) - forms the letter "G" for Graph

### Tagline
**"AI-driven Knowledge & Project Intelligence"**
- Always displayed in cyan (#4BD0C7)
- Font: Inter, 10-12px
- Use below logo or in footer

## 🚀 Implementation in Code

### HTML Head Section
```html
<!-- Favicon -->
<link rel="icon" type="image/svg+xml" href="{% static 'main/images/brand/ideagraph_logo_icon.svg' %}">

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
```

### CSS Variables
```css
:root {
    --primary-amber: #E49A28;
    --secondary-cyan: #4BD0C7;
    --tech-blue: #2AB3D1;
    --graph-gray: #1A1A1A;
    --soft-white: #EAEAEA;
}
```

## 📱 Responsive Considerations

- Logo scales proportionally on mobile devices
- Minimum navbar height: 60px on mobile, 80px on desktop
- Icon-only logo recommended for screens < 768px width
- Maintain color contrast ratios for accessibility (WCAG AA compliant)

## ♿ Accessibility

- Primary amber on dark background: Contrast ratio 4.8:1 (AA compliant)
- Secondary cyan on dark background: Contrast ratio 6.2:1 (AA compliant)
- Soft white text on dark background: Contrast ratio 13.5:1 (AAA compliant)

## 📄 File Formats

All brand assets are provided in SVG format for:
- ✅ Infinite scalability
- ✅ Small file size
- ✅ Sharp rendering at any resolution
- ✅ Easy color modifications
- ✅ Web and print compatibility

## 🔗 Related Documentation

- Full Corporate Identity Guide: `ideagraph_styleguide.md`
- Main README: `README.md`
- License Information: `LICENSE_OVERVIEW.md`

---

© 2025 IdeaGraph | Created by Christian Angermeier
