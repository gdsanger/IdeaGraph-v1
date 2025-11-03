# HTML Rendering and Auto-Linking in Task Comments

## Feature Overview

This feature enables task comments in IdeaGraph to:
1. **Render HTML correctly** - Comments containing HTML tags are now displayed with proper formatting instead of showing raw HTML
2. **Auto-linkify URLs** - Plain text URLs are automatically converted to clickable links, including IP-based URLs

## Implementation Details

### Security
- Uses the `bleach` library (v6.3.0) for HTML sanitization
- Prevents XSS attacks by stripping dangerous tags and attributes
- Only allows safe HTML tags and protocols

### Technical Components

1. **Template Filter**: `main/templatetags/comment_extras.py`
   - Custom Django template filter `render_comment`
   - Sanitizes HTML using bleach
   - Linkifies URLs with custom regex supporting IP addresses

2. **Template Update**: `main/templates/main/tasks/_comments_list.html`
   - Applies the `render_comment` filter to comment text
   - Enhanced CSS for links and HTML elements

3. **Dependencies**: Added `bleach>=6.0.0` to requirements.txt

## Usage Examples

### Example 1: HTML Formatting

**Input (Comment text):**
```html
<h2>Project Update</h2>
<p>We've completed the following tasks:</p>
<ul>
    <li><strong>Bug Fix:</strong> Fixed the login issue</li>
    <li><strong>Feature:</strong> Added new dashboard</li>
</ul>
```

**Output:** The comment displays with proper HTML formatting:
- Heading in h2 style
- Bullet list with bold labels
- Proper paragraph spacing

### Example 2: Auto-Linkified URLs

**Input (Comment text):**
```
Please check the following resources:
- Documentation: https://github.com/gdsanger/IdeaGraph-v1
- Internal Task: http://172.18.248.192:8080/tasks/95af6493-3bca-4544-98ab-7874868d94e0
- API Docs: https://api.example.com/docs
```

**Output:** All URLs are automatically converted to clickable links:
- `https://github.com/gdsanger/IdeaGraph-v1` → Clickable link
- `http://172.18.248.192:8080/tasks/...` → Clickable link (IP-based URL)
- `https://api.example.com/docs` → Clickable link

### Example 3: Mixed Content

**Input (Comment text):**
```html
<h3>Bug Fix Details</h3>
<p>Fixed the issue in <code>render_comment</code> function.</p>
<p>Pull request: https://github.com/example/repo/pull/123</p>
```

**Output:**
- Heading is rendered as h3
- Code is displayed with monospace font and background
- URL is automatically linkified

## Security Features

### Allowed HTML Tags
Safe tags that are preserved:
- Text formatting: `strong`, `em`, `b`, `i`, `code`, `pre`
- Structure: `p`, `div`, `span`, `br`, `hr`
- Headings: `h1`, `h2`, `h3`, `h4`, `h5`, `h6`
- Lists: `ul`, `ol`, `li`
- Quotes: `blockquote`
- Tables: `table`, `thead`, `tbody`, `tr`, `th`, `td`
- Links: `a` (with href, title, target, rel attributes)
- Images: `img` (with src, alt, title, width, height attributes)

### Blocked/Sanitized Elements
Dangerous elements that are removed or escaped:
- Scripts: `<script>` tags and `javascript:` URLs
- Iframes: `<iframe>` tags
- Dangerous attributes: `onclick`, `onerror`, etc.
- Dangerous protocols: `data:`, `vbscript:`, etc.

### Example: XSS Prevention

**Input:**
```html
<script>alert('XSS')</script>
<a href="javascript:alert('XSS')">Click</a>
Normal text
```

**Output:**
```
&lt;script&gt;alert('XSS')&lt;/script&gt;
<a>Click</a>
Normal text
```
The script tag is escaped, and the javascript: protocol is removed from the link.

## Testing

The feature includes comprehensive test coverage:

### Unit Tests (22 tests)
- Plain text preservation
- URL linkification (including IP addresses)
- HTML sanitization (XSS prevention)
- Safe HTML tag preservation
- Edge cases (special characters, empty text, etc.)

### Integration Tests (3 tests)
- Real-world scenarios with mixed HTML and URLs
- IP-based URL handling
- Code blocks and formatting

### Existing Tests (9 tests)
- All existing task comment functionality tests pass
- No regressions introduced

**Total: 34 tests passing ✅**

## Performance Considerations

- HTML sanitization and linkification are performed only during rendering
- Original comment text is stored unchanged in the database
- Minimal performance impact due to efficient bleach library

## Browser Compatibility

- Works with all modern browsers
- CSS styling uses standard properties
- Clickable links work in all browsers

## Future Enhancements

Potential improvements for future versions:
- Support for Markdown syntax
- Image preview/lightbox for img tags
- Video embedding support
- Custom link previews
- Syntax highlighting for code blocks

## Related Documentation

- Original Issue: Tasks / Kommenatre
- Bleach Library: https://github.com/mozilla/bleach
- Django Template Filters: https://docs.djangoproject.com/en/stable/howto/custom-template-tags/
