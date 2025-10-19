# Task Cleanup - Quick Reference

## 🚀 Schnellstart

### 1. Vorschau (Empfohlen)
```bash
python cleanup_tasks.py --dry-run
```

### 2. Tasks bereinigen
```bash
python cleanup_tasks.py
```

## 📋 Häufige Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `python cleanup_tasks.py --dry-run` | Vorschau ohne Löschung |
| `python cleanup_tasks.py --verbose` | Detaillierte Ausgabe |
| `python cleanup_tasks.py --no-owner-only` | Nur Tasks ohne Owner |
| `python cleanup_tasks.py --no-item-only` | Nur Tasks ohne Item |
| `python cleanup_tasks.py --help` | Hilfe anzeigen |

## 🧪 Testen

### Test-Daten erstellen
```bash
python create_test_tasks.py
```

### Unit-Tests ausführen
```bash
python manage.py test main.test_task_cleanup
```

## 📊 Was wird gelöscht?

✅ Tasks **ohne** assigned_to (Owner)  
✅ Tasks **ohne** item  
✅ Tasks **ohne** assigned_to **UND** item

❌ Tasks **mit** assigned_to **UND** item (bleiben erhalten)

## 🔒 Sicherheit

- ✅ Dry-Run für sichere Vorschau
- ✅ Bestätigungsabfrage vor Löschung
- ✅ Database-Transaktionen
- ✅ 0 Vulnerabilities (CodeQL geprüft)

## 📁 Dateien

| Datei | Zweck |
|-------|-------|
| `cleanup_tasks.py` | Haupt-CLI-Script |
| `create_test_tasks.py` | Test-Daten Generator |
| `main/test_task_cleanup.py` | Unit Tests |
| `TASK_CLEANUP_GUIDE.md` | Detaillierte Dokumentation |
| `TASK_CLEANUP_IMPLEMENTATION.md` | Implementierungs-Zusammenfassung |
| `logs/cleanup_tasks.log` | Log-Datei (automatisch erstellt) |

## ⚠️ Wichtige Hinweise

1. **Immer** zuerst Dry-Run durchführen
2. **Backup** der Datenbank erstellen
3. Gelöschte Tasks können **nicht** wiederhergestellt werden
4. Verwandte Objekte (Users, Items, Tags) bleiben erhalten

## 📖 Weitere Dokumentation

- Detaillierte Anleitung: `TASK_CLEANUP_GUIDE.md`
- Implementation Details: `TASK_CLEANUP_IMPLEMENTATION.md`

## 🆘 Support

Bei Problemen:
1. Log-Datei prüfen: `logs/cleanup_tasks.log`
2. Tests ausführen: `python manage.py test main.test_task_cleanup`
3. Verbose-Modus nutzen: `python cleanup_tasks.py --dry-run --verbose`
