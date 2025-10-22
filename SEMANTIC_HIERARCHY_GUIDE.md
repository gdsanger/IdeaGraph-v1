# Semantic Context Propagation for Hierarchical Items

## Overview

This feature extends IdeaGraph's semantic network with hierarchical context inheritance between parent and child Items. It enables the system to represent both semantic similarity and structural parent-child relationships, making complex project hierarchies more transparent and manageable.

## Features

### 1. Hierarchical Item Relationships

Items can now be organized in parent-child hierarchies:

```
Item (Parent): University Portal (Base)
 ├── Item (Child): Portal University A
 ├── Item (Child): Portal University B
 └── Item (Child): Portal University C
```

### 2. Context Inheritance

Child items can inherit context from their parents:

- **Description**: Combined parent and child descriptions
- **Tags**: Deduplicated union of parent and child tags
- **Semantic Embedding**: Combined context used for Weaviate vectorization

### 3. Template Items

Items can be marked as templates (`is_template=True`) to serve as blueprints for child items.

## Database Schema

### New Fields on Item Model

| Field | Type | Description |
|-------|------|-------------|
| `parent` | ForeignKey (Item, nullable) | Reference to parent item |
| `is_template` | Boolean | Marks item as template |
| `inherit_context` | Boolean | Enables context inheritance from parent |

## API Usage

### Semantic Network with Hierarchy

```http
GET /api/semantic-network/item/<item_id>?include_hierarchy=true
```

**Query Parameters:**
- `include_hierarchy` (boolean, default: false): Include parent-child relationships
- `depth` (int, 1-3): Network depth for similarity search
- `summaries` (boolean): Generate AI summaries

**Response includes:**
```json
{
  "success": true,
  "nodes": [
    {
      "id": "...",
      "type": "item",
      "isSource": true,
      "isParent": false,
      "isChild": false,
      "inheritsContext": false,
      "properties": {...}
    }
  ],
  "edges": [
    {
      "source": "...",
      "target": "...",
      "weight": 1.0,
      "type": "hierarchy",
      "relationship": "parent"
    },
    {
      "source": "...",
      "target": "...",
      "weight": 0.85,
      "type": "similarity"
    }
  ],
  "hierarchy": {
    "has_parent": true,
    "has_children": true,
    "parent_count": 1,
    "children_count": 3
  }
}
```

## UI Components

### Item Form

New fields in item creation/edit form:

1. **Parent Item** dropdown - Select parent item for hierarchy
2. **Template** checkbox - Mark as template item
3. **Context Inheritance** checkbox - Enable context inheritance

### Item Detail View

**Hierarchical Context Card** displays:
- Link to parent item (if exists)
- Context inheritance status badge
- List of child items with their inheritance status

### Semantic Network Visualization

**Controls:**
- 🔁 **Hierarchie** toggle button - Show/hide hierarchical relationships

**Visual Elements:**
- **Green nodes**: Source item
- **Blue nodes**: Parent items  
- **Orange nodes**: Child items
- **Dashed lines**: Parent-child relationships (weight 1.0)
- **Solid lines**: Semantic similarity relationships (weight 0.6-1.0)

**Tooltips show:**
- Item title, type, and similarity
- Role (Parent/Child) if applicable
- Context inheritance status

## Backend Implementation

### Context Inheritance Logic

```python
# Item model method
def get_inherited_context(self):
    if not self.inherit_context or not self.parent:
        return {
            'description': self.description,
            'tags': list(self.tags.all()),
            'has_parent': False
        }
    
    # Combine parent and child context
    combined_description = f"{parent.description}\n\n{self.description}".strip()
    combined_tags = list(set(parent.tags.all()) | set(self.tags.all()))
    
    return {
        'description': combined_description,
        'tags': combined_tags,
        'has_parent': True,
        'parent_id': str(self.parent.id),
        'parent_title': self.parent.title
    }
```

### Weaviate Integration

When syncing items to Weaviate:

```python
context = item.get_inherited_context()

properties = {
    'type': 'Item',
    'title': item.title,
    'description': context['description'],  # Uses inherited context
    'tags': [tag.name for tag in context['tags']],
    'parent_id': context.get('parent_id', ''),
    'context_inherited': context['has_parent']
}
```

### Semantic Network Service

The service provides:

1. **Hierarchical Relationship Detection**
   ```python
   relations = service._find_hierarchical_relations('Item', item_id)
   # Returns: {'parent': [...], 'children': [...]}
   ```

2. **Combined Network Generation**
   - Semantic similarity edges (weight based on vector distance)
   - Hierarchical edges (weight 1.0 for direct relationships)
   - Proper node flagging (isParent, isChild, inheritsContext)

## Use Cases

### 1. Multi-Tenant Project Templates

**Parent**: Base Portal Application (Template)
- Contains core features, authentication, API structure

**Children**: Customer-Specific Portals
- Inherit base description and tags
- Add customer-specific customizations
- Maintain relationship to base template

### 2. Product Line Management

**Parent**: Product Family
- High-level product concept and strategy

**Children**: Product Variants
- Specific implementations for different markets
- Inherit product vision and core features

### 3. Project Hierarchies

**Grandparent**: Organization Strategy
**Parent**: Department Initiative  
**Child**: Specific Project
- Full context chain preserved through hierarchy
- Semantic relationships show related work across hierarchy

## Testing

The feature includes comprehensive test coverage:

### Unit Tests (9 tests)
- Parent-child relationship creation
- Context inheritance logic
- Template and inheritance flags
- Hierarchical traversal methods

### Integration Tests (6 tests)
- Semantic network with hierarchy
- Hierarchical edge types and weights
- Node flag correctness
- API parameter handling

Run tests:
```bash
python manage.py test main.test_hierarchical_items
python manage.py test main.test_semantic_network_hierarchy
```

## Future Enhancements

Potential improvements for future iterations:

1. **KiGate Integration**
   - Hierarchy-aware AI summaries
   - Parent context in child item analysis
   - Template-based auto-generation

2. **Advanced Hierarchy Features**
   - Maximum hierarchy depth enforcement
   - Circular reference prevention
   - Bulk operations on hierarchies

3. **Visualization Enhancements**
   - Collapsible hierarchy trees
   - Hierarchical layout algorithm
   - Filter by hierarchy level

4. **Performance Optimization**
   - Cached hierarchy paths
   - Optimized vector combination
   - Lazy loading for large hierarchies

## Migration

The feature includes a Django migration:

```bash
python manage.py migrate
```

This adds the three new fields to the Item model with appropriate defaults and constraints.

## Backward Compatibility

- All new features are **opt-in** via UI checkboxes or API parameters
- Existing items work without any changes
- Semantic network API maintains backward compatibility
- `include_hierarchy` defaults to `false` to preserve existing behavior

## Performance Considerations

- Context inheritance computed on-demand (not cached)
- Hierarchical relationship queries optimized with `select_related`
- Weaviate vectorization happens asynchronously
- Large hierarchies (>100 items) may need additional optimization

## Security

- Parent selection restricted to same user's items (or admin)
- Circular references prevented at UI level
- Hierarchy traversal depth limited to prevent DoS
- Context inheritance respects item permissions

---

**Author**: GitHub Copilot  
**Version**: 1.0  
**Date**: October 2025
