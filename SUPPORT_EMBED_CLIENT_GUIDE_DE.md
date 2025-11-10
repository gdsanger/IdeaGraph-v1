# Support Embed - Client Integration Guide (Deutsch)

## Überblick

Diese Anleitung zeigt, wie Sie das Support Widget in Ihre Website oder Anwendung einbinden.

**Wichtig:** Sie benötigen **kein zusätzliches JavaScript** auf Ihrer Seite! Alles wird über einen einfachen `<iframe>` eingebunden.

## Schritt-für-Schritt Anleitung

### Schritt 1: API Key generieren

Zunächst müssen Sie einmalig einen API Key in IdeaGraph generieren:

```python
from core.services.support_embed_key_service import SupportEmbedKeyService

key_service = SupportEmbedKeyService()

# API Key für Ihr Item generieren
result = key_service.generate_key(
    item_id="12345678-1234-1234-1234-123456789012",  # Ihre Item UUID
    name="Website Produktionsumgebung",              # Beschreibender Name
    created_by_user=user,                            # Ihr User-Objekt
    expires_in_days=730                              # Gültig für 2 Jahre
)

if result['success']:
    embed_key = result['key']
    print(f"Ihr Embed Key: {embed_key}")
    print(f"Gültig bis: {result['expires_at']}")
    
    # WICHTIG: Speichern Sie diesen Key sicher!
    # Er wird nur einmal angezeigt.
```

**Hinweis:** Der Key wird aus Sicherheitsgründen nur einmal angezeigt. Speichern Sie ihn an einem sicheren Ort.

### Schritt 2: Widget in HTML einbinden

Fügen Sie diesen Code in Ihre HTML-Seite ein:

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Support</title>
</head>
<body>
    <h1>Hilfe & Support</h1>
    
    <!-- Support Widget einbinden -->
    <iframe 
        src="https://ihre-ideagraph-instanz.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&key=IHR_EMBED_KEY"
        width="420"
        height="650"
        frameborder="0"
        style="border: 1px solid #ddd; border-radius: 8px;">
    </iframe>
</body>
</html>
```

**Das war's!** Kein zusätzliches JavaScript erforderlich.

## Vollständiges Beispiel

### Statische HTML-Seite

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hilfe & Support</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .support-container {
            display: flex;
            gap: 40px;
            margin-top: 40px;
        }
        
        .info-section {
            flex: 1;
        }
        
        .widget-section {
            flex: 1;
        }
        
        .support-iframe {
            border: 2px solid #E59A28;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <header>
        <h1>Hilfe & Support</h1>
        <p>Wir sind hier, um Ihnen zu helfen!</p>
    </header>
    
    <div class="support-container">
        <div class="info-section">
            <h2>Häufig gestellte Fragen</h2>
            <ul>
                <li>Wie kann ich ein Konto erstellen?</li>
                <li>Wie ändere ich mein Passwort?</li>
                <li>Wie kontaktiere ich den Support?</li>
            </ul>
            
            <h2>Kontakt</h2>
            <p>E-Mail: support@example.com</p>
            <p>Telefon: +49 123 456789</p>
        </div>
        
        <div class="widget-section">
            <h2>Chat oder Anfrage erstellen</h2>
            <p>Nutzen Sie unser Support-Widget:</p>
            
            <!-- Support Widget -->
            <iframe 
                src="https://ihre-ideagraph-instanz.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&key=IHR_EMBED_KEY_HIER"
                width="420"
                height="650"
                frameborder="0"
                class="support-iframe">
            </iframe>
        </div>
    </div>
</body>
</html>
```

### Als Modal/Popup einbinden

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Meine Anwendung</title>
    <style>
        /* Modal Styling */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            position: relative;
            background-color: #fff;
            margin: 5% auto;
            padding: 20px;
            width: 480px;
            max-width: 90%;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .close-button {
            position: absolute;
            right: 10px;
            top: 10px;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            background: none;
            border: none;
            color: #666;
        }
        
        .close-button:hover {
            color: #000;
        }
        
        .support-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            background-color: #E59A28;
            color: white;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        .support-button:hover {
            background-color: #d48a1f;
        }
    </style>
</head>
<body>
    <h1>Meine Anwendung</h1>
    <p>Hauptinhalt der Seite...</p>
    
    <!-- Support Button -->
    <button class="support-button" onclick="openSupportModal()">
        💬 Support
    </button>
    
    <!-- Support Modal -->
    <div id="supportModal" class="modal">
        <div class="modal-content">
            <button class="close-button" onclick="closeSupportModal()">&times;</button>
            <h2>Support</h2>
            <iframe 
                src="https://ihre-ideagraph-instanz.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&key=IHR_EMBED_KEY_HIER&theme=light"
                width="100%"
                height="650"
                frameborder="0"
                style="border: none;">
            </iframe>
        </div>
    </div>
    
    <script>
        // Nur einfache Modal-Steuerung - kein zusätzliches Widget-JavaScript nötig!
        function openSupportModal() {
            document.getElementById('supportModal').style.display = 'block';
        }
        
        function closeSupportModal() {
            document.getElementById('supportModal').style.display = 'none';
        }
        
        // Modal schließen bei Klick außerhalb
        window.onclick = function(event) {
            const modal = document.getElementById('supportModal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
```

### In WordPress einbinden

```html
<!-- In WordPress Page/Post Editor (HTML-Modus) -->
<div style="max-width: 420px; margin: 40px auto;">
    <h2>Brauchen Sie Hilfe?</h2>
    <p>Chatten Sie mit uns oder erstellen Sie eine Support-Anfrage:</p>
    
    <iframe 
        src="https://ihre-ideagraph-instanz.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&key=IHR_EMBED_KEY_HIER"
        width="100%"
        height="650"
        frameborder="0"
        style="border: 1px solid #ddd; border-radius: 8px;">
    </iframe>
</div>
```

## URL-Parameter

### Erforderliche Parameter

| Parameter | Beschreibung | Beispiel |
|-----------|--------------|----------|
| `itemId` | UUID des Items in IdeaGraph | `12345678-1234-1234-1234-123456789012` |
| `key` | Ihr generierter Embed API Key | `abc123xyz...` |

### Optionale Parameter

| Parameter | Werte | Standard | Beschreibung |
|-----------|-------|----------|--------------|
| `locale` | `de`, `en` | `de` | Sprache des Widgets |
| `theme` | `auto`, `light`, `dark` | `auto` | Farbschema |

### Beispiele mit Parametern

```html
<!-- Deutsches Widget, helles Theme -->
<iframe src="...?itemId=xxx&key=yyy&locale=de&theme=light" ...></iframe>

<!-- Englisches Widget, dunkles Theme -->
<iframe src="...?itemId=xxx&key=yyy&locale=en&theme=dark" ...></iframe>

<!-- Automatisches Theme (folgt System-Einstellung) -->
<iframe src="...?itemId=xxx&key=yyy&theme=auto" ...></iframe>
```

## Responsive Design

### Mobile-optimiert

```html
<style>
    .support-wrapper {
        width: 100%;
        max-width: 420px;
        margin: 0 auto;
    }
    
    @media (max-width: 768px) {
        .support-wrapper iframe {
            width: 100%;
            height: 500px;
        }
    }
</style>

<div class="support-wrapper">
    <iframe 
        src="https://ihre-ideagraph-instanz.com/embed/support?itemId=xxx&key=yyy"
        width="420"
        height="650"
        frameborder="0"
        style="border: 1px solid #ddd; border-radius: 8px; max-width: 100%;">
    </iframe>
</div>
```

## Häufig gestellte Fragen (FAQ)

### Brauche ich zusätzliches JavaScript?

**Nein!** Das Widget funktioniert vollständig über den `<iframe>`. Sie benötigen nur HTML.

Das einzige JavaScript, das Sie eventuell brauchen, ist für:
- Modal öffnen/schließen (wenn Sie es als Popup verwenden)
- Ihre eigene UI-Logik

Das Widget selbst benötigt kein zusätzliches JavaScript auf Ihrer Seite.

### Wie lange ist der API Key gültig?

Standardmäßig **2 Jahre** (730 Tage). Sie können die Gültigkeit bei der Generierung anpassen.

### Was passiert, wenn der Key abläuft?

Das Widget zeigt eine Fehlermeldung an. Generieren Sie einen neuen Key und aktualisieren Sie Ihre HTML-Seite.

### Kann ich den Key widerrufen?

Ja! Sie können Keys jederzeit widerrufen:

```python
from core.services.support_embed_key_service import SupportEmbedKeyService

key_service = SupportEmbedKeyService()
key_service.revoke_key(key_id="key-uuid")
```

### Wie sicher ist das?

- Keys werden gehashed in der Datenbank gespeichert (SHA-256)
- Keys können sofort widerrufen werden
- Kurze Access Tokens (30 Minuten) minimieren Risiko
- Nutzung wird getrackt (Anzahl, letzter Zugriff)

### Kann ich mehrere Keys für dasselbe Item haben?

Ja! Sie können mehrere Keys generieren, z.B.:
- Einen für Produktion
- Einen für Staging
- Einen für Entwicklung

### Funktioniert das Widget offline?

Nein, das Widget benötigt eine Internetverbindung zur IdeaGraph-Instanz.

## Troubleshooting

### Widget wird nicht angezeigt

**Mögliche Ursachen:**
1. Falsche URL zur IdeaGraph-Instanz
2. Ungültige `itemId`
3. Ungültiger oder abgelaufener `key`

**Lösung:**
- Überprüfen Sie die URL
- Überprüfen Sie die Parameter
- Generieren Sie bei Bedarf einen neuen Key

### Fehlermeldung "Invalid key"

Der API Key ist ungültig oder wurde widerrufen.

**Lösung:** Generieren Sie einen neuen Key

### Fehlermeldung "Key expired"

Der API Key ist abgelaufen.

**Lösung:** Generieren Sie einen neuen Key

### Widget zeigt alte Version

**Lösung:** Leeren Sie den Browser-Cache (Strg+F5)

## Best Practices

### 1. Key-Management

- ✅ Speichern Sie Keys sicher
- ✅ Verwenden Sie unterschiedliche Keys für verschiedene Umgebungen
- ✅ Dokumentieren Sie, wo Keys verwendet werden
- ❌ Committen Sie Keys nicht in Git
- ❌ Teilen Sie Keys nicht öffentlich

### 2. Performance

- ✅ Binden Sie das Widget nur ein, wo es benötigt wird
- ✅ Verwenden Sie Lazy Loading für Modals
- ✅ Optimieren Sie die iframe-Größe für Ihre Seite

### 3. User Experience

- ✅ Platzieren Sie das Widget gut sichtbar
- ✅ Verwenden Sie ein konsistentes Theme
- ✅ Testen Sie auf mobilen Geräten
- ✅ Fügen Sie einen Hinweis hinzu, dass Nutzer chatten oder Anfragen erstellen können

### 4. Wartung

- ✅ Dokumentieren Sie verwendete Keys
- ✅ Setzen Sie Ablaufdaten im Kalender
- ✅ Planen Sie Key-Rotation vor Ablauf
- ✅ Testen Sie neue Keys vor der Produktivschaltung

## Checkliste für Go-Live

- [ ] API Key generiert
- [ ] Key sicher gespeichert (z.B. in Passwort-Manager)
- [ ] `itemId` überprüft
- [ ] URL zur IdeaGraph-Instanz korrekt
- [ ] Widget auf Testseite eingebunden
- [ ] Desktop-Browser getestet (Chrome, Firefox, Safari, Edge)
- [ ] Mobile-Browser getestet (iOS Safari, Chrome Mobile)
- [ ] Theme passt zur Website
- [ ] Sprache korrekt (de/en)
- [ ] Ablaufdatum dokumentiert
- [ ] Backup-Key generiert (optional)

## Support

Bei Fragen oder Problemen:

1. Überprüfen Sie diese Dokumentation
2. Testen Sie mit einem neuen API Key
3. Überprüfen Sie die Browser-Konsole auf Fehler
4. Kontaktieren Sie das IdeaGraph-Team

---

**Version:** 2.0 (mit Embed API Keys)  
**Letzte Aktualisierung:** 2025-11-10  
**Autor:** IdeaGraph Platform Team
