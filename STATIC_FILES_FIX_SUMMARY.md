# Lösung: Ungeplante Login-Anforderung für statische Dateien

## Problem
In der Django-Produktionsumgebung wurden statische Dateien (z.B. `/static/main/js/tag-token.js`) durch das `AuthenticationMiddleware` geschützt, was zu einer HTTP 302-Weiterleitung zur Login-Seite führte. Dies verhinderte den korrekten Zugriff auf CSS, JavaScript und andere statische Ressourcen.

## Ursache
Die `AuthenticationMiddleware` in `/main/middleware.py` überprüfte alle eingehenden Anfragen und leitete nicht authentifizierte Benutzer zur Login-Seite weiter. Die Liste der öffentlichen URLs (`PUBLIC_URLS`) enthielt den Pfad `/static/` nicht, wodurch statische Dateien ebenfalls als geschützte Ressourcen behandelt wurden.

## Lösung
Die Lösung bestand darin, den Pfad `/static/` zur Liste der öffentlichen URLs hinzuzufügen:

```python
PUBLIC_URLS = [
    '/login/',
    '/logout/',
    '/register/',
    '/forgot-password/',
    '/reset-password/',
    '/api/',  # API uses JWT auth
    '/static/',  # Static files should be publicly accessible
]
```

## Änderungen
1. **main/middleware.py**: Hinzufügen von `/static/` zur `PUBLIC_URLS`-Liste
2. **main/test_static_files.py**: Neue Tests zur Überprüfung der Zugänglichkeit statischer Dateien

## Tests
- Alle bestehenden 29 Authentifizierungstests bestehen weiterhin
- 3 neue Tests wurden hinzugefügt:
  - Überprüfung, dass statische Dateien ohne Login zugänglich sind
  - Überprüfung, dass statische Verzeichnisse ohne Login zugänglich sind
  - Überprüfung, dass geschützte Seiten weiterhin Authentifizierung erfordern

## Manuelle Verifikation
```bash
# Vor der Änderung:
curl -I http://127.0.0.1:8077/static/main/js/tag-token.js
# HTTP/1.1 302 Found
# Location: /login/?next=/static/main/js/tag-token.js

# Nach der Änderung:
curl -I http://127.0.0.1:8077/static/main/js/tag-token.js
# HTTP/1.1 200 OK
# Content-Type: text/javascript
```

## Sicherheit
- Keine Sicherheitslücken durch CodeQL-Analyse gefunden
- Geschützte Seiten erfordern weiterhin Authentifizierung
- Nur statische Dateien sind ohne Login zugänglich

## Auswirkungen
- Minimale Änderung: Nur eine Zeile Code geändert
- Keine Beeinträchtigung der bestehenden Funktionalität
- Statische Dateien sind nun korrekt zugänglich
- Alle Tests bestehen erfolgreich
