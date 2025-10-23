# Google PSE Integration - Schnellanleitung

## Überblick
Die Google PSE (Programmable Search Engine) Integration wurde in die Entitäts-Einstellungen verschoben. Dies ermöglicht eine einfachere Konfiguration ohne Änderungen an Umgebungsvariablen.

## Konfiguration

### Schritt 1: Einstellungen öffnen
1. Als Administrator anmelden
2. Zu "Settings" navigieren
3. Einstellungs-Formular öffnen

### Schritt 2: Google PSE konfigurieren
Im Abschnitt "Google PSE Configuration":

1. **Google PSE aktivieren**
   - Toggle-Schalter aktivieren
   - Dies aktiviert die externe Support-Analyse

2. **Google Search API Key eingeben**
   - Den API-Schlüssel von Google Custom Search eintragen
   - Feld: "Google Search API Key"

3. **Google Search CX eingeben**
   - Die Search Engine ID (CX) eintragen
   - Feld: "Google Search CX"

4. **Speichern**
   - "Update Settings" oder "Create Settings" klicken

## Funktionsweise

### Wenn Google PSE aktiviert ist:
- Die Schaltfläche "Support-Analyse (Extern)" wird in der Task-Detail-Ansicht angezeigt
- Externe Websuche ist für Support-Analysen verfügbar
- Nutzt die konfigurierten API-Credentials

### Wenn Google PSE deaktiviert ist:
- Die Schaltfläche "Support-Analyse (Extern)" wird ausgeblendet
- Nur interne Support-Analyse (über Weaviate) ist verfügbar

## API-Schlüssel erhalten

### Google Custom Search API Key:
1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt oder wähle ein bestehendes
3. Aktiviere die "Custom Search API"
4. Erstelle API-Credentials (API Key)
5. Kopiere den API-Schlüssel

### Google Search CX (Engine ID):
1. Gehe zu [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Erstelle eine neue Suchmaschine
3. Konfiguriere die Sucheinstellungen
4. Kopiere die "Search engine ID" (CX)

## Fehlerbehebung

### Problem: "Support-Analyse (Extern)" Schaltfläche wird nicht angezeigt
**Lösung:**
- Prüfe, ob `google_pse_enabled` in den Einstellungen aktiviert ist
- Stelle sicher, dass die Einstellungen gespeichert wurden

### Problem: Websuche schlägt fehl
**Lösungen:**
- Überprüfe die API-Key-Gültigkeit
- Stelle sicher, dass die CX korrekt ist
- Prüfe API-Quotas in Google Cloud Console
- Verifiziere, dass Custom Search API aktiviert ist

### Problem: Umgebungsvariablen werden nicht mehr verwendet
**Hinweis:**
- Settings-Werte haben Vorrang vor Umgebungsvariablen
- Wenn Settings leer sind, werden Umgebungsvariablen als Fallback verwendet
- Dies gewährleistet Rückwärtskompatibilität

## Sicherheitshinweise

1. **API-Schlüssel schützen**
   - API-Keys werden als Passwort-Felder behandelt
   - Nur Administratoren haben Zugriff auf Settings

2. **Zugriffskontrolle**
   - Nur Benutzer mit Admin-Rolle können Settings ändern
   - API-Credentials werden in der Datenbank gespeichert

3. **Best Practices**
   - Regelmäßig API-Keys rotieren
   - API-Quotas in Google Cloud überwachen
   - Zugriff auf Settings-Seite beschränken

## Vorteile der neuen Lösung

✅ **Keine Server-Neustarts erforderlich**
- Änderungen sofort wirksam

✅ **Einfache Aktivierung/Deaktivierung**
- Mit einem Toggle-Schalter

✅ **Zentrale Verwaltung**
- Alle API-Credentials an einem Ort

✅ **UI-Integration**
- Automatische Anzeige/Verstecken von Features

✅ **Rückwärtskompatibel**
- Bestehende Umgebungsvariablen funktionieren weiterhin

## Support

Bei Problemen oder Fragen:
1. Prüfe die Logs auf Fehlermeldungen
2. Verifiziere die API-Konfiguration in Google Cloud
3. Kontaktiere den System-Administrator

## Technische Details

### Felder in Settings:
- `google_pse_enabled`: Boolean (Standard: False)
- `google_search_api_key`: String (max. 255 Zeichen)
- `google_search_cx`: String (max. 255 Zeichen)

### Datenbank-Migration:
- Migration: `0027_add_google_pse_settings`
- Automatisch beim nächsten Deployment ausgeführt
