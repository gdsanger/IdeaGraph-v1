# Fix: Email Body HTML to Markdown Conversion

## Problem (German Issue Description)

**Original Issue:** "manag.py process-mails Konvertierung Mail Body"

Die Mails wurden als HTML gespeichert, anstatt als Markdown. Dies war falsch.

### Verständnis der Anforderung:

1. **Eingehende Mail:** HTML muss in Markdown umgewandelt werden (mit KIGate API Agent `html-to-markdown-converter`)
2. **Task-Speicherung:** Das Markdown wird im Task als Description gespeichert
3. **Ausgehende Antwort:** Der Inhalt des Description-Feldes wird wieder in HTML-Format konvertiert (mit KIGate API Agent `markdown-to-html-converter`)

## Root Cause

Die Methode `convert_html_to_markdown()` in `core/services/mail_processing_service.py` hat HTML als solches zurückgegeben, wenn der KiGate Service nicht verfügbar war oder fehlgeschlagen ist, anstatt eine grundlegende HTML-zu-Markdown-Konvertierung durchzuführen.

```python
# VORHER (FALSCH):
if not self.kigate_service:
    logger.warning("KiGate service not available, returning HTML as-is")
    return html_content  # ❌ Gibt HTML zurück!
```

## Solution

Eine Fallback-Konvertierung wurde implementiert, die HTML immer in Markdown umwandelt, auch wenn KiGate nicht verfügbar ist.

```python
# NACHHER (RICHTIG):
if not self.kigate_service:
    logger.warning("KiGate service not available, using fallback HTML-to-Markdown conversion")
    return self._basic_html_to_markdown(html_content)  # ✅ Konvertiert zu Markdown!
```

### Neue Methode: `_basic_html_to_markdown()`

Diese Methode verwendet Python's eingebauten `html.parser.HTMLParser` und konvertiert:

- **Headers** (h1-h6) → Markdown-Headers (#, ##, etc.)
- **Bold/Strong** → `**text**`
- **Italic/Emphasis** → `*text*`
- **Links** → `[text](url)`
- **Unordered Lists** (ul) → Markdown-Listen (-)
- **Ordered Lists** (ol) → Nummerierte Listen (1., 2., etc.)
- **Code** (pre, code) → Backticks und Code-Blöcke
- **Blockquotes** → `> text`
- **Absätze und Zeilenumbrüche**

## Changes Made

### Files Modified

1. **`core/services/mail_processing_service.py`**
   - Added `_basic_html_to_markdown()` method (117 lines)
   - Updated `convert_html_to_markdown()` to use fallback
   - Added verification for KiGate output

2. **`main/test_mail_processing_service.py`**
   - Updated `test_convert_html_to_markdown_no_kigate` to expect Markdown
   - Added `test_convert_html_to_markdown_with_fallback_comprehensive`

### Commits

1. `db1f7fb` - Add HTML to Markdown fallback converter
2. `b555a15` - Fix ordered list conversion in HTML to Markdown parser

## Verification

### Automated Tests
✅ `test_convert_html_to_markdown_no_kigate` - PASS
✅ `test_convert_html_to_markdown_with_fallback_comprehensive` - PASS

### Manual Testing
✅ HTML successfully converted to Markdown
✅ No HTML tags remain in output
✅ All formatting preserved (headers, bold, italic, lists, links, code, blockquotes)
✅ Ordered lists properly numbered
✅ Complete email flow works correctly

### Security Scan
✅ CodeQL: No vulnerabilities found

## Email Processing Flow

### BEFORE (Broken)
```
Incoming Email (HTML) 
  → ❌ Stored as HTML in task.description
  → ✅ Converted to HTML for confirmation (but already HTML)
```

### AFTER (Fixed)
```
Incoming Email (HTML)
  → ✅ Converted to Markdown (KiGate or fallback)
  → ✅ Stored as Markdown in task.description
  → ✅ Converted to HTML for confirmation email
```

## Examples

### Example 1: Support Request

**Input (HTML):**
```html
<h2>Login Problem</h2>
<p>I cannot <strong>log in</strong>. Error: <code>Invalid credentials</code>.</p>
```

**Output (Markdown - stored in task):**
```markdown
## Login Problem

I cannot **log in**. Error: `Invalid credentials`.
```

### Example 2: Bug Report

**Input (HTML):**
```html
<h1>Critical Bug</h1>
<p>Found a <strong>critical issue</strong>:</p>
<ul>
    <li>Page crashes</li>
    <li>Users blocked</li>
</ul>
<ol>
    <li>Open page</li>
    <li>Click menu</li>
</ol>
```

**Output (Markdown - stored in task):**
```markdown
# Critical Bug

Found a **critical issue**:

- Page crashes
- Users blocked

1. Open page
2. Click menu
```

## Benefits

✅ **Korrekt:** Mails werden jetzt als Markdown gespeichert
✅ **Robust:** Funktioniert auch ohne KiGate API
✅ **Sicher:** Keine HTML-Injection-Risiken
✅ **Lesbar:** Markdown ist einfacher zu lesen und zu bearbeiten
✅ **Konsistent:** Einheitlich mit dem Rest der Anwendung
✅ **Vollständig:** Alle Formatierungen werden erhalten

## Technical Details

- **No external dependencies added** - Uses Python's built-in `html.parser`
- **Backward compatible** - KiGate still used when available
- **Graceful degradation** - Falls back to basic conversion if parsing fails
- **Comprehensive** - Handles all common HTML elements
- **Tested** - Unit tests and manual verification completed
- **Secure** - CodeQL security scan passed

## Deployment

No special deployment steps required:
- ✅ Code-only changes
- ✅ No database migrations needed
- ✅ No configuration changes required
- ✅ Works immediately upon deployment

## Support

Bei Fragen oder Problemen:
- Logs prüfen: `mail_processing_service` logger
- KiGate Agents verifizieren: `html-to-markdown-converter`, `markdown-to-html-converter`
- Kontakt: idea@angermeier.net
