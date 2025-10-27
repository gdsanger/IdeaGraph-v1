# Item Q&A Feature - Quick Reference

## 🚀 Schnellstart

### Für Benutzer
1. Öffne ein Item in der Detailansicht
2. Klicke auf Tab **"Frage stellen"**
3. Gebe deine Frage ein (z.B. "Wie funktioniert die Authentifizierung?")
4. Klicke auf **"Antwort generieren"**
5. Prüfe Antwort und Quellenangaben
6. Optional: Klicke auf **"Als Wissensobjekt speichern"**

### Für Entwickler

#### API Endpoints
```bash
# Frage stellen
POST /api/items/<item_id>/ask
Body: {"question": "Deine Frage"}

# Verlauf abrufen
GET /api/items/<item_id>/questions/history?page=1&per_page=10

# Als KnowledgeObject speichern
POST /api/items/questions/<qa_id>/save
```

#### Model
```python
from main.models import ItemQuestionAnswer

# Q&A abrufen
qa = ItemQuestionAnswer.objects.filter(item=item).order_by('-created_at')

# Q&A erstellen
qa = ItemQuestionAnswer.objects.create(
    item=item,
    question="Frage?",
    answer="Antwort",
    sources=[...],
    asked_by=user,
    relevance_score=0.85
)
```

#### Service
```python
from core.services.item_question_answering_service import ItemQuestionAnsweringService

service = ItemQuestionAnsweringService()

# Suche nach relevantem Wissen
results = service.search_related_knowledge(
    item_id=str(item.id),
    question="Deine Frage",
    limit=3
)

# Generiere Antwort
answer = service.generate_answer_with_kigate(
    question="Deine Frage",
    search_results=results['results'],
    item_title=item.title,
    user_id=str(user.id)
)

# Speichere als KnowledgeObject
result = service.save_as_knowledge_object(
    item_id=str(item.id),
    question="Frage",
    answer="Antwort",
    qa_id=str(qa.id)
)

service.close()
```

## 🔧 KIGate Agent Setup

### Minimale Konfiguration
```yaml
# File: <KIGate>/agents/question-answering-agent.yaml
name: question-answering-agent
description: "Q&A Agent für IdeaGraph Items"
provider: openai
model: gpt-4
temperature: 0.3
max_tokens: 2000
```

## 🎯 Tipps & Tricks

### Bessere Fragen stellen
✅ **Gut**: "Wie funktioniert der Token-basierte Login?"
❌ **Schlecht**: "Login?"

✅ **Gut**: "Welche API-Endpunkte gibt es für Benutzer?"
❌ **Schlecht**: "API?"

### Relevanzscores verstehen
- 🟢 **>80%**: Sehr relevant, hohe Vertrauenswürdigkeit
- 🟡 **70-80%**: Relevant, gute Grundlage für Antwort
- 🔴 **<70%**: Weniger relevant, wird nicht angezeigt

### Wissensbasis aufbauen
1. Füge relevante **Dateien** zum Item hinzu
2. Erstelle aussagekräftige **Tasks**
3. Schreibe **Kommentare** mit wichtigen Informationen
4. Speichere wichtige Q&As als **KnowledgeObject**

## 🐛 Häufige Probleme

| Problem | Lösung |
|---------|--------|
| "Keine relevanten Informationen" | Füge mehr Dateien/Tasks zum Item hinzu |
| "KiGate API not enabled" | Aktiviere KIGate in Settings |
| "Question is required" | Frage darf nicht leer sein |
| "Authentication required" | Melde dich an |

## 📊 Datenbank-Felder

```python
ItemQuestionAnswer:
- id: UUID
- item: ForeignKey(Item)
- question: Text
- answer: Text (Markdown)
- sources: JSON [{"type": "Task", "title": "...", "url": "...", "relevance": 0.85}]
- asked_by: ForeignKey(User)
- relevance_score: Float (0-1)
- saved_as_knowledge_object: Boolean
- weaviate_uuid: String
- created_at: DateTime
- updated_at: DateTime
```

## 🔗 Weiterführende Links

- [Vollständige Dokumentation](ITEM_QA_FEATURE.md)
- [KIGate Dokumentation](KIGate_Documentation.md)
- [Weaviate Sync](WEAVIATE_SYNC.md)

## 📝 Beispiele

### Frage-Beispiele
```
1. "Wie funktioniert die Authentifizierung in diesem System?"
2. "Welche API-Endpunkte sind für Aufgabenverwaltung verfügbar?"
3. "Was sind die Hauptkomponenten dieser Architektur?"
4. "Wie werden Dateien in SharePoint hochgeladen?"
5. "Welche Tests gibt es für die Benutzerverwaltung?"
```

### Response-Beispiel
```markdown
## Antwort auf deine Frage:
Das Token-basierte Login-System erzeugt 256-Bit-Tokens, die für 4 Stunden 
gültig sind. Der Benutzer fordert sie über das Portal an und erhält per 
E-Mail einen Einmal-Link.

## Quellen:
1. 🧩 Task: Einmal-Token-Login umsetzen (92%)
2. 📘 File: token_login_spec.md (88%)
3. 💬 Comment: Token-Länge validiert (85%)
```

## ⚡ Performance

- **Durchschnittliche Response-Zeit**: 3-5 Sekunden
- **Weaviate Search**: ~500ms
- **KIGate AI Generation**: 2-4 Sekunden
- **Database Save**: ~100ms

## 🔒 Sicherheit

- ✅ Authentifizierung erforderlich (JWT/Session)
- ✅ CSRF-Protection aktiv
- ✅ User-spezifische Daten (asked_by)
- ✅ Item-Zugriffskontrolle

## 📈 Monitoring

```python
# Anzahl Q&As pro Item
ItemQuestionAnswer.objects.filter(item=item).count()

# Durchschnittliche Relevanz
ItemQuestionAnswer.objects.filter(item=item).aggregate(Avg('relevance_score'))

# Gespeicherte KnowledgeObjects
ItemQuestionAnswer.objects.filter(saved_as_knowledge_object=True).count()
```
