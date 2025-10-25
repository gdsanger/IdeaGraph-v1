# Sigma.js Loading Order Fix - Quick Reference

## Problem
❌ Error when opening milestone semantic network tab:
```
ReferenceError: Sigma is not defined
```

## Root Cause
Script loading order issue - libraries loaded after code that uses them

## Solution
✅ Moved library script tags from `{% block content %}` to `{% block extra_js %}`

## Change Summary
**File:** `main/templates/main/milestones/detail.html`

**Before:**
```html
{% block content %}
    <script>
        // Code using Sigma
    </script>
    <script src="sigma.min.js"></script>  ❌ Too late!
{% endblock %}
```

**After:**
```html
{% block content %}
    <script>
        // Code using Sigma
    </script>
{% endblock %}

{% block extra_js %}
    <script src="sigma.min.js"></script>  ✅ Correct order!
{% endblock %}
```

## Testing
1. Open milestone → Click "Semantic Network" tab
2. Check browser console for errors
3. Verify graph renders and is interactive

## Result
✅ Semantic network graph displays correctly
✅ No JavaScript errors
✅ Consistent with items/tasks templates

## Documentation
See `SIGMA_JS_LOADING_ORDER_FIX.md` for detailed analysis

## Related Fixes
- Different from Weaviate type issue (SIGMA_GRAPH_MILESTONE_FIX.md)
- Different from container width issue (SIGMA_CONTAINER_WIDTH_FIX.md)
- Different from credentials issue (SEMANTIC_NETWORK_FIX.md)
