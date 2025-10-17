# 💡 IdeaGraph

**IdeaGraph** ist eine KI-gestützte Plattform zur Erfassung, Verwaltung und Konkretisierung von Ideen.  
Sie verknüpft Kreativität, Struktur und Automatisierung – von der ersten Idee bis zur Umsetzung in GitHub.

---

## 🚀 Features

- **Ideenmanagement**
  - Erfassen, kategorisieren und bewerten von Ideen
  - Automatische Tag-Vergabe durch KI
  - Ähnlichkeitssuche mit *ChromaDB* (Vector Search)

- **Aufgabenmanagement**
  - Aufgaben direkt aus Ideen generieren
  - KI-gestützte Textoptimierung („AI Enhancer“)
  - Automatische Titel- und Tag-Erzeugung
  - Statusflow: Neu → Working → Review → Ready → Erledigt

- **GitHub Integration**
  - Automatische Erstellung von Issues aus Aufgaben
  - Synchronisation von Status & Labels
  - Speicherung der GitHub-Issue-ID in IdeaGraph

- **SharePoint Integration**
  - Datei-Upload (PDF, DOCX, MD, HTML, TXT)
  - Automatische Text-Extraktion und Vektorisierung

- **Künstliche Intelligenz**
  - KI-Agenten über *KIGate* (OpenAI, Gemini, Claude, lokale Modelle)
  - AI Enhancer für Textnormalisierung und Aufgabenaufbereitung
  - Similarity Check zur Erkennung verwandter Ideen

- **Benutzerverwaltung**
  - Login mit bcrypt-gesichertem Passwort
  - Admin-Rollen mit Berechtigung für Settings und User-Management
  - Kennwort-Reset via Microsoft Graph API

- **Logging & Monitoring**
  - System- und Audit-Logs in SQLite
  - JSON-basiertes Fehlertracking und API-Monitoring

---

## 🧩 Architekturüberblick

| Ebene | Technologie | Beschreibung |
|-------|--------------|---------------|
| **Frontend** | Django + HTMX + Bootstrap (Dark Theme) | Moderne, reaktive Weboberfläche |
| **Markdown Editor** | Toast UI Editor | KI-freundliche Textbearbeitung |
| **Backend** | Django ORM + FastAPI (KIGate) | Business-Logik & KI-Kommunikation |
| **Vektor DB** | ChromaDB (Cloud) | Similarity Search & KI-Kontext |
| **Relationale DB** | SQLite | Benutzer, Ideen, Aufgaben, Logs |
| **Integrationen** | GitHub API · Graph API | Issues & SharePoint Uploads |

---

## ⚙️ Installation

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Django Setup
python manage.py migrate
python manage.py runserver
```

---

## 🔐 Konfiguration

Bearbeite `.env` oder Settings in der Datenbank (Adminbereich):

| Schlüssel | Beschreibung |
|-----------|---------------|
| OPENAI_API_KEY | OpenAI API Key |
| GITHUB_TOKEN | GitHub PAT |
| CHROMA_API_KEY | Chroma Cloud Key |
| GRAPH_CLIENT_ID / SECRET / TENANT | Microsoft Graph API |
| KIGATE_URL / TOKEN | Verbindung zu KIGate API |
| MAX_TAGS_PER_IDEA | Anzahl automatisch generierter Tags |

---

## 🧠 Beispiel-Workflow

1. **Idee erfassen**  
   → Text eingeben, KI analysiert und klassifiziert.  
2. **AI Enhancer ausführen**  
   → Text wird bereinigt, formatiert, optimiert.  
3. **Aufgaben generieren**  
   → KI erstellt automatisch konkrete Tasks.  
4. **Issue erstellen**  
   → Task per Knopfdruck an GitHub senden.  
5. **Ergebnisse tracken**  
   → Status und Logs im System nachverfolgen.

---

## 🌐 Roadmap

- [ ] Verschlüsselung aller API Keys (v1.1)
- [ ] Asynchrone KI-Verarbeitung (Job Queue)
- [ ] Multi-Agent-Verarbeitung (LLM Consensus)
- [ ] SaaS-Hosting und Team-Funktionen

---

## 🗾 Lizenz

## Urheberrecht und Schutz
© 2025 Christian Angermeier
Alle Rechte vorbehalten.  
Die Nutzung des Quellcodes unterliegt der MIT-Lizenz.  
Logik, Konzept, Systemarchitektur und KI-Agentendesign sind urheberrechtlich geschützt (§ 2 UrhG).

## Besondere Schutzvermerke
- Der Begriff **„Kigil“** und die zugrundeliegende Prozessarchitektur sind geistiges Eigentum des Autors.  [WHITEPAPER_KIGIL](https://github.com/gdsanger/IdeaGraph-v1/blob/main/WHITEPAPER_KIGIL.md)
- Die KI-Agenten-Architektur („KIGate“) ist integraler Bestandteil des Systems.  
- Eine kommerzielle Nutzung oder Integration außerhalb der MIT-Lizenz bedarf der ausdrücklichen Zustimmung.

[Lizenz](https://github.com/gdsanger/IdeaGraph-v1/blob/main/LICENSE_OVERVIEW.md)

## Verantwortlicher Autor
**Christian Angermeier**  
E-Mail: ca@angermeier.net

---

*Dieses Manifest ist Teil der offiziellen IdeaGraph-Version 1.0.*



**IdeaGraph** – von der Idee zur Umsetzung.  
Eine Plattform, die denkt, strukturiert und handelt.
