# Embed Support Client - UI Benutzerhandbuch

## Überblick

Die Embed Support Client UI ermöglicht es Benutzern, Support-Widgets für Items zu verwalten und auf externen Websites einzubinden. Diese Dokumentation beschreibt die Verwendung der neuen UI-Funktionen.

## Zugriff auf die Embed Support Verwaltung

### Im Item Detail

1. Öffnen Sie ein Item in der Detail-Ansicht
2. Klicken Sie auf den Button **"Embed Support"** in der Button-Leiste (neben "Send via Email")
3. Ein Modal-Dialog öffnet sich mit zwei Tabs:
   - **Neuen Key erstellen**: Erstellen Sie neue Embed Keys
   - **Keys verwalten**: Verwalten Sie existierende Keys

## Neuen Embed Key erstellen

### Schritt-für-Schritt Anleitung

1. **Modal öffnen**: Klicken Sie auf den "Embed Support" Button
2. **Tab auswählen**: Stellen Sie sicher, dass der Tab "Neuen Key erstellen" aktiv ist
3. **Formular ausfüllen**:
   - **Name** (Pflichtfeld): Geben Sie einen beschreibenden Namen ein (z.B. "Produktions-Website", "Staging-Umgebung")
   - **Referenz-URL** (optional): URL der Website, auf der der Support eingebunden wird (nur zur Dokumentation)
   - **Gültigkeitsdauer**: Wählen Sie zwischen 1, 2 oder 3 Jahren (Standard: 2 Jahre)
4. **Key generieren**: Klicken Sie auf "Key generieren"

### Nach der Generierung

Nach erfolgreicher Generierung werden angezeigt:

1. **API Key**: Der vollständige Key (wird nur einmal angezeigt!)
   - Kopieren Sie den Key mit dem "Kopieren" Button
   - Bewahren Sie den Key sicher auf!
   
2. **IFrame Code**: Fertig formatierter HTML-Code zur Einbindung
   - Kopieren Sie den Code mit dem "IFrame Code kopieren" Button
   - Fügen Sie den Code direkt in Ihre Website ein
   
3. **Ablaufdatum**: Zeigt an, bis wann der Key gültig ist

### Beispiel IFrame Code

```html
<iframe 
    src="https://your-ideagraph-instance.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&key=YOUR_EMBED_KEY"
    width="420"
    height="650"
    frameborder="0"
    style="border: 1px solid #ddd; border-radius: 8px;">
</iframe>
```

## Keys verwalten

### Key-Liste anzeigen

1. Wechseln Sie zum Tab **"Keys verwalten"**
2. Die Liste aller Keys für dieses Item wird automatisch geladen
3. Für jeden Key werden angezeigt:
   - **Name**: Der bei der Erstellung vergebene Name
   - **Status**: Aktiv (grün) oder Abgelaufen (rot)
   - **Key-Prefix**: Die ersten 8 Zeichen des Keys zur Identifikation
   - **Erstellt**: Erstellungsdatum
   - **Läuft ab**: Ablaufdatum
   - **Zuletzt verwendet**: Wann der Key zuletzt genutzt wurde
   - **Verwendungen**: Anzahl der Verwendungen

### Key löschen

1. Klicken Sie auf den **"Löschen"** Button beim entsprechenden Key
2. Bestätigen Sie die Löschabfrage
3. Der Key wird sofort widerrufen und kann nicht mehr verwendet werden

⚠️ **Wichtig**: Nach dem Löschen können bereits eingebundene Widgets den Key nicht mehr nutzen!

## Best Practices

### Key-Verwaltung

1. **Beschreibende Namen**: Verwenden Sie klare Namen wie "Produktions-Website v2" statt nur "Website"
2. **Dokumentation**: Nutzen Sie das Referenz-URL Feld, um zu dokumentieren, wo der Key verwendet wird
3. **Regelmäßige Rotation**: Erneuern Sie Keys vor Ablauf der Gültigkeit
4. **Trennung**: Verwenden Sie separate Keys für verschiedene Umgebungen (Produktion, Staging, Entwicklung)

### Sicherheit

1. **Nicht öffentlich teilen**: Keys sollten nur in vertrauenswürdigen Umgebungen eingebunden werden
2. **Sofortiges Widerrufen**: Bei Verdacht auf Kompromittierung sofort löschen und neuen Key erstellen
3. **Regelmäßige Überprüfung**: Prüfen Sie die Key-Liste regelmäßig und löschen Sie ungenutzte Keys

### Monitoring

1. **Verwendungsstatistiken**: Überprüfen Sie die "Zuletzt verwendet" und "Verwendungen" Spalten
2. **Ablaufdaten**: Behalten Sie Ablaufdaten im Blick
3. **Status**: Achten Sie auf abgelaufene Keys (rote Badges)

## Technische Details

### API Key Eigenschaften

- **Format**: URL-sicherer Base64-String (64 Zeichen)
- **Speicherung**: Gehashed (SHA-256) in der Datenbank
- **Gültigkeit**: 1-3 Jahre (konfigurierbar)
- **Verwendung**: Automatischer Austausch gegen kurzlebige Access Tokens (30 Minuten)

### Sicherheitsmerkmale

- Keys werden nur bei Erstellung einmal angezeigt
- Gehashte Speicherung in der Datenbank
- Sofortiges Widerrufen möglich
- Nutzungs-Tracking (Anzahl, letzte Verwendung)
- Automatische Ablaufdaten

## Fehlerbehebung

### Key wird nicht akzeptiert

- **Prüfen Sie das Ablaufdatum**: Ist der Key noch gültig?
- **Prüfen Sie den Status**: Wurde der Key widerrufen?
- **Kopieren Sie den Key erneut**: Möglicherweise wurde der Key nicht vollständig kopiert

### Modal lädt nicht

- **Browser-Cache leeren**: Versuchen Sie Strg+F5
- **Browser-Konsole prüfen**: Öffnen Sie die Entwicklertools und suchen Sie nach Fehlern

### Key-Liste bleibt leer

- **Erstellen Sie einen Key**: Wenn noch keine Keys existieren, ist die Liste leer
- **Prüfen Sie die Berechtigungen**: Stellen Sie sicher, dass Sie eingeloggt sind

## Support und Hilfe

Bei Fragen oder Problemen:

1. Prüfen Sie diese Dokumentation
2. Überprüfen Sie die Browser-Konsole auf Fehler
3. Kontaktieren Sie das IdeaGraph-Team

## Verwandte Dokumentation

- **Für Entwickler**: `SUPPORT_EMBED_DOCUMENTATION.md` - Technische API-Dokumentation
- **Für Kunden**: `SUPPORT_EMBED_CLIENT_GUIDE_DE.md` - Client-Integration Guide
- **Implementierung**: `SUPPORT_EMBED_IMPLEMENTATION_SUMMARY.md` - Implementierungs-Details

---

**Version**: 1.0  
**Letzte Aktualisierung**: 2025-11-10  
**Autor**: IdeaGraph Platform Team
