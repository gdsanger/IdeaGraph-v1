# Item Question Answering Feature - Dokumentation

## 🌟 Überblick

Die kontextbezogene Fragestellung im Item („Frage stellen") ermöglicht Benutzern, gezielte Fragen zu einem Item zu stellen. Das System durchsucht automatisch alle zugehörigen KnowledgeObjects (Tasks, Files, Kommentare, Dokumentationen) und generiert eine fundierte, AI-basierte Antwort mit Quellenangaben.

## 🎯 Funktionen

- **Semantische Suche**: Durchsucht alle KnowledgeObjects mit `related_item = current_item.id` in Weaviate
- **AI-Antwort-Generierung**: Nutzt KIGate Agent zur Generierung prägnanter Antworten
- **Quellenangaben**: Zeigt relevante Quellen mit Relevanzscores an
- **Verlauf**: Speichert alle Fragen und Antworten in der Datenbank
- **Wissensobjekt-Speicherung**: Optional können Antworten als KnowledgeObject in Weaviate gespeichert werden
- **Markdown-Rendering**: Antworten werden als formatiertes Markdown dargestellt

## 🏗️ Architektur

### Backend-Komponenten

#### 1. Model: `ItemQuestionAnswer`
```python
# Location: main/models.py
class ItemQuestionAnswer(models.Model):
    item = ForeignKey(Item)
    question = TextField
    answer = TextField
    sources = JSONField  # Liste der genutzten Quellen
    asked_by = ForeignKey(User)
    relevance_score = FloatField
    saved_as_knowledge_object = BooleanField
    weaviate_uuid = CharField
    created_at = DateTimeField
    updated_at = DateTimeField
```

#### 2. Service: `ItemQuestionAnsweringService`
```python
# Location: core/services/item_question_answering_service.py

# Hauptmethoden:
- search_related_knowledge(item_id, question, limit=3)
  → Semantische Suche in Weaviate mit Filter auf related_item
  
- generate_answer_with_kigate(question, search_results, item_title, user_id)
  → Generiert Antwort mit KIGate Agent
  
- save_as_knowledge_object(item_id, question, answer, qa_id)
  → Speichert Q&A als KnowledgeObject in Weaviate
```

#### 3. API Endpoints

**POST `/api/items/<item_id>/ask`**
- Stellt eine Frage zu einem Item
- Body: `{"question": "Deine Frage hier"}`
- Response: Q&A mit Antwort, Quellen und Relevanzscores

**GET `/api/items/<item_id>/questions/history`**
- Ruft Q&A-Verlauf für ein Item ab
- Query params: `page`, `per_page`
- Response: Liste der letzten Fragen mit Pagination

**POST `/api/items/questions/<qa_id>/save`**
- Speichert ein Q&A-Paar als KnowledgeObject in Weaviate
- Response: Weaviate UUID

### Frontend-Komponenten

#### UI Location
```html
<!-- In Item Detail View: main/templates/main/items/detail.html -->
<!-- Tab: "Frage stellen" -->
```

#### JavaScript Funktionen
```javascript
// Hauptfunktionen:
- askQuestion()           // Fragt eine neue Frage
- displaySources()        // Zeigt Quellen mit Relevanzscores
- saveAsKnowledgeObject() // Speichert Q&A in Weaviate
- loadQAHistory()         // Lädt Verlauf der letzten Fragen
```

## 🔧 KIGate Agent Konfiguration

### Agent Name
```
question-answering-agent
```

### Agent Rolle und Aufgabe

**Rolle:**
```
Du bist der IdeaGraph Assistant, ein spezialisierter KI-Assistent für die Beantwortung 
von Fragen zu Projekten und Items in IdeaGraph. Du hast Zugriff auf das gesamte 
Projektwissen aus Tasks, Dateien, Kommentaren und Dokumentationen.
```

**Aufgabe:**
```
Beantworte Benutzerfragen basierend auf den bereitgestellten Informationen aus dem 
Projektkontext. Die Daten stammen aus Tasks, Dateien, Kommentaren und Dokumentationen, 
die alle zum selben Item gehören. Formuliere eine klare, präzise Antwort in 
Markdown-Format mit einer Liste der genutzten Quellen (Titel + Link).
```

### Prompt Template

```yaml
# KIGate Agent Configuration File
# Location: <KIGate-Installation>/agents/question-answering-agent.yaml

name: question-answering-agent
description: "Beantwortet Fragen zu Items basierend auf semantischem Projektwissen"

role: |
  Du bist der IdeaGraph Assistant, ein spezialisierter KI-Assistent für die Beantwortung 
  von Fragen zu Projekten und Items in IdeaGraph. Du hast Zugriff auf das gesamte 
  Projektwissen aus Tasks, Dateien, Kommentaren und Dokumentationen.

task: |
  Beantworte die folgende Frage basierend auf den bereitgestellten Informationen aus 
  dem Projektkontext. Die Daten stammen aus Tasks, Dateien, Kommentaren und 
  Dokumentationen, die alle zum selben Item gehören.
  
  **Wichtige Regeln:**
  1. Formuliere eine klare, präzise Antwort in Markdown-Format
  2. Nutze die bereitgestellten Informationen als Basis
  3. Erstelle eine Liste der genutzten Quellen mit Titel und Link am Ende
  4. Erfinde keine neuen Fakten - bleibe bei den bereitgestellten Informationen
  5. Wenn die Informationen nicht ausreichen, sage das deutlich
  6. Verwende deutsche Sprache für die Antwort
  
  **Antwortformat:**
  ## Antwort auf deine Frage:
  [Deine fundierte Antwort hier, basierend auf den Quellen]
  
  ## Quellen:
  1. 🧩 [Typ] [Titel] - [Link]
  2. 📘 [Typ] [Titel] - [Link]
  3. ...

provider: openai
model: gpt-4
temperature: 0.3
max_tokens: 2000
```

### Provider-Konfigurationen

#### OpenAI (Empfohlen)
```yaml
provider: openai
model: gpt-4  # oder gpt-4-turbo
temperature: 0.3
max_tokens: 2000
```

#### Claude
```yaml
provider: claude
model: claude-3-sonnet-20240229
temperature: 0.3
max_tokens: 2000
```

#### Lokales Modell (z.B. Ollama)
```yaml
provider: ollama
model: llama3:70b
temperature: 0.3
max_tokens: 2000
base_url: http://localhost:11434
```

## 📋 Verwendung

### Als Benutzer

1. **Item öffnen**: Navigiere zum gewünschten Item
2. **Tab wechseln**: Klicke auf den Tab "Frage stellen"
3. **Frage eingeben**: Gebe deine Frage in das Textfeld ein
4. **Antwort generieren**: Klicke auf "Antwort generieren"
5. **Quellen prüfen**: Überprüfe die angezeigten Quellen mit Relevanzscores
6. **Optional speichern**: Klicke auf "Als Wissensobjekt speichern" um die Antwort in Weaviate zu persistieren

### Beispiel-Workflow

```
Benutzer: "Wie funktioniert der Authentifizierungsprozess?"
         ↓
System:   Sucht in Weaviate nach KnowledgeObjects mit related_item = current_item.id
         und semantischer Relevanz zur Frage
         ↓
System:   Findet 3 relevante Quellen:
         - Task: "Token-basiertes Login implementieren" (Relevanz: 92%)
         - File: "auth_specification.md" (Relevanz: 88%)
         - Comment: "Token-Länge validiert" (Relevanz: 85%)
         ↓
KIGate:  Generiert Antwort basierend auf den 3 Quellen
         ↓
System:  Zeigt formatierte Antwort mit Quellenangaben an
         und speichert Q&A in Datenbank
```

## 🔍 Weaviate Query Details

### Filter-Logik
```python
# Suche nach related_item ODER das Item selbst
related_filter = Filter.by_property("related_item").equal(item_uuid)
item_filter = Filter.by_id().equal(item_uuid)
combined_filter = related_filter | item_filter

# Semantische Suche mit Filter
response = collection.query.near_text(
    query=question,
    limit=3,
    filters=combined_filter,
    return_metadata=MetadataQuery(distance=True, certainty=True)
)
```

### Relevanz-Berechnung
```python
# Certainty (0-1, höher ist besser)
if certainty > 0:
    relevance = certainty
else:
    # Fallback: Distance (0-2, niedriger ist besser)
    relevance = max(0.0, 1.0 - (distance / 2.0))

# Nur Ergebnisse mit Relevanz >= 0.7 werden angezeigt
MIN_RELEVANCE_CERTAINTY = 0.7
```

## 🧪 Tests

```bash
# Alle Q&A Tests ausführen
python manage.py test main.test_item_question_answering

# Einzelne Testklassen
python manage.py test main.test_item_question_answering.ItemQuestionAnsweringTest
python manage.py test main.test_item_question_answering.ItemQuestionAnsweringServiceTest
```

### Test-Abdeckung
- ✅ Model Creation und Validierung
- ✅ API Endpoints (Authentifizierung, Validierung, Error Handling)
- ✅ Q&A History mit Pagination
- ✅ Speichern als KnowledgeObject
- ✅ Service Initialization (Local & Cloud)

## 🚀 Deployment

### Voraussetzungen

1. **Weaviate**: Muss konfiguriert und erreichbar sein
2. **KIGate**: Muss installiert und konfiguriert sein
3. **question-answering-agent**: Muss in KIGate konfiguriert sein
4. **Datenbank-Migration**: Muss ausgeführt sein

### Deployment-Schritte

```bash
# 1. Migration ausführen
python manage.py migrate

# 2. KIGate Agent konfigurieren
# Erstelle: <KIGate>/agents/question-answering-agent.yaml
# (siehe Prompt Template oben)

# 3. KIGate neu starten
cd <KIGate-Installation>
./restart.sh  # oder entsprechender Befehl

# 4. Django Server starten
python manage.py runserver

# 5. Testen
# Öffne ein Item und teste die "Frage stellen" Funktion
```

## 🔐 Sicherheit

### Authentifizierung
- Alle API-Endpoints erfordern Authentifizierung (JWT oder Session)
- CSRF-Protection ist aktiv

### Autorisierung
- Benutzer können nur Fragen zu Items stellen, auf die sie Zugriff haben
- Q&A History ist nur für authentifizierte Benutzer sichtbar

## 📊 Monitoring

### Logging
```python
# Relevante Log-Events:
- "Processing question for item {item_id}: {question}"
- "Found {count} relevant results for item {item_id}"
- "Successfully created Q&A {qa_id} for item {item_id}"
- "Saved Q&A {qa_id} as KnowledgeObject: {weaviate_uuid}"
```

### Metriken
- Anzahl gestellter Fragen pro Item
- Durchschnittliche Relevanzscores
- Anzahl gespeicherter KnowledgeObjects
- Response-Zeiten für Q&A-Anfragen

## 🐛 Troubleshooting

### Problem: "KiGate API is not enabled"
**Lösung**: Aktiviere KIGate in den Settings und stelle sicher, dass API Token konfiguriert ist.

### Problem: "Weaviate Cloud enabled but URL or API key not configured"
**Lösung**: Konfiguriere Weaviate URL und API Key in den Settings, oder deaktiviere Cloud-Modus für lokales Weaviate.

### Problem: "Agent 'question-answering-agent' not found"
**Lösung**: Stelle sicher, dass der Agent in KIGate konfiguriert ist und KIGate neu gestartet wurde.

### Problem: Keine relevanten Ergebnisse gefunden
**Lösung**: 
1. Prüfe ob KnowledgeObjects für das Item in Weaviate vorhanden sind
2. Überprüfe das `related_item` Feld in den KnowledgeObjects
3. Versuche verschiedene Frageformulierungen

## 📝 Weitere Informationen

- **KIGate Dokumentation**: `/docs/KIGate_Documentation.md`
- **Weaviate Sync**: `/docs/WEAVIATE_SYNC.md`
- **API Dokumentation**: Inline in `main/api_views.py`

## 🎯 Best Practices

1. **Fragen formulieren**: Stelle konkrete, spezifische Fragen für bessere Ergebnisse
2. **Kontext aufbauen**: Stelle sicher, dass relevante Tasks, Files und Kommentare zum Item gehören
3. **Wissensobjekte speichern**: Speichere wichtige Q&As als KnowledgeObject für zukünftige Referenz
4. **Quellen prüfen**: Überprüfe immer die angegebenen Quellen für Detailinformationen

## 🔄 Zukünftige Erweiterungen

- [ ] Multi-Item Q&A (Fragen über mehrere Items)
- [ ] Q&A Export (PDF, Markdown)
- [ ] Q&A Bewertung (Thumbs Up/Down)
- [ ] Vorschläge für ähnliche Fragen
- [ ] Voice Input für Fragen
- [ ] Automatische Frage-Generierung basierend auf Item-Kontext
