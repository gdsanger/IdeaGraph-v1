# Chat Widget Feature - IdeaGraph Q&A Assistant

## Overview

The Chat Widget provides an AI-powered Q&A interface for IdeaGraph items, enabling users to ask questions and receive contextual answers based on semantic search and AI processing.

## Features

- **Real-time Q&A**: Ask questions about any item and get AI-generated answers
- **Context-Aware**: Uses Weaviate semantic search to find relevant content
- **Source References**: Displays sources used to generate answers
- **Fallback Handling**: Works even when Weaviate is unavailable
- **Dark Theme Compatible**: Matches IdeaGraph's visual design
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

### Frontend (`ChatWidget.js`)

Vanilla JavaScript ES6 class component that provides:
- Message display (user, assistant, error states)
- Input handling with Enter key support
- Loading indicators with typing animation
- Source reference rendering
- Markdown support for formatted responses
- CSRF token handling for secure requests

### Backend API Endpoint

**Endpoint**: `POST /api/items/<item_id>/chat/ask`

**Request Body**:
```json
{
  "question": "What is this item about?"
}
```

**Response**:
```json
{
  "success": true,
  "answer": "Based on the context...",
  "sources": [
    {
      "title": "Related Document",
      "type": "File",
      "score": 0.85,
      "id": "doc-123"
    }
  ],
  "has_context": true
}
```

### Processing Flow

1. **User submits question** via chat widget
2. **API endpoint receives request** and authenticates user
3. **Semantic search** performed in Weaviate (if available)
   - Searches for relevant content related to the item
   - Filters by item_id and relevance score
   - Returns top 5 most relevant results
4. **Context building** from search results
5. **KIGate agent invoked** with question and context
   - Uses `question-answering-agent`
   - Generates answer based on provided context
6. **Response returned** with answer and sources
7. **Widget displays** formatted answer with source references

## UI Integration

The chat widget is integrated into the item detail page as a new tab:

- **Location**: Item Detail View → "Q&A Assistant" tab
- **Position**: After Milestones tab, before Hierarchy tab
- **Initialization**: Lazy-loaded when tab is first opened
- **Height**: 600px (configurable)

## Usage Example

### Initialization in Template

```javascript
const chatWidget = new ChatWidget('chatWidgetContainer', {
    itemId: 'uuid-here',
    apiBaseUrl: '/api/items',
    theme: 'dark',
    height: '600px',
    showHistory: true
});
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `itemId` | string | required | UUID of the item |
| `apiBaseUrl` | string | `/api/items` | Base URL for API requests |
| `theme` | string | `dark` | UI theme (dark/light) |
| `height` | string | `500px` | Container height |
| `showHistory` | boolean | `true` | Show chat history |

## Dependencies

### Backend Services

- **Weaviate**: Semantic search database (optional, graceful fallback)
- **KIGate**: AI agent orchestration platform (required)
- **Django**: Web framework with session/JWT authentication

### Frontend Libraries

- **Marked.js**: Markdown rendering (already in base template)
- **Bootstrap Icons**: UI icons
- **Bootstrap 5**: Styling framework

## Error Handling

The chat widget handles various error scenarios:

| Scenario | Behavior |
|----------|----------|
| Weaviate unavailable | Continues with item description only |
| KIGate service error | Displays error message to user |
| Missing question | Validation error (400) |
| Item not found | 404 error |
| Unauthenticated user | 401 authentication required |
| Invalid JSON | 400 bad request |

## Testing

Comprehensive test suite in `main/test_chat_widget.py`:

- 9 tests covering success and error scenarios
- All tests passing
- Mocked external services (Weaviate, KIGate)
- Session-based authentication testing

Run tests:
```bash
python manage.py test main.test_chat_widget
```

## Security

✅ **CodeQL Scan**: No vulnerabilities detected
- CSRF protection enabled
- Authentication required
- Input validation
- Error message sanitization
- No SQL injection risks

## Performance Considerations

- **Lazy Loading**: Chat widget only initializes when tab is opened
- **API Timeout**: Configurable timeout for KIGate requests
- **Context Limits**: Content truncated to 8000 chars to prevent token overflow
- **Search Limits**: Maximum 10 results from Weaviate, top 5 used

## Future Enhancements

Potential improvements for future versions:

- [ ] Chat history persistence in database
- [ ] Multi-turn conversations with context
- [ ] File upload support for context
- [ ] Export chat transcripts
- [ ] Suggested questions based on item content
- [ ] Real-time streaming responses
- [ ] Support for multiple languages

## Troubleshooting

### Chat widget not loading
- Check browser console for JavaScript errors
- Verify `ChatWidget.js` is loaded correctly
- Ensure item ID is valid UUID

### No answers generated
- Verify KIGate API is configured in settings
- Check KIGate service is running and accessible
- Review Django logs for API errors

### No source references
- This is normal if Weaviate is unavailable
- Check Weaviate connection in settings
- Widget works without sources, using item description

## Related Documentation

- [KIGate Service Integration](../core/services/kigate_service.py)
- [Weaviate Search Service](../core/services/weaviate_search_service.py)
- [Item Detail View](../main/templates/main/items/detail.html)

## Credits

Implementation follows existing IdeaGraph patterns:
- Semantic Graph component architecture
- Dark theme styling conventions
- API authentication patterns
- Test structure and mocking strategies
