# Redis Cache - Quick Reference

## Schnellstart

### 1. Redis installieren und starten

```bash
# Linux
sudo apt install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 --name redis redis:latest
```

### 2. IdeaGraph für Redis konfigurieren

Bearbeiten Sie `.env`:

```bash
CACHE_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 3. Django neu starten

```bash
python manage.py runserver
```

## Verwendung im Code

### Mit CacheManager (empfohlen)

```python
from core.cache_manager import CacheManager

cache = CacheManager()

# Wert speichern
cache.set('my_key', 'my_value', timeout=300)

# Wert abrufen
value = cache.get('my_key')

# Wert löschen
cache.delete('my_key')

# Backend-Info
info = cache.get_backend_info()
```

### Mit Django Cache

```python
from django.core.cache import cache

cache.set('key', 'value', 300)
value = cache.get('key')
cache.delete('key')
```

## Cache-Backends wechseln

| Backend | .env Einstellung | Verwendung |
|---------|------------------|------------|
| Redis | `CACHE_BACKEND=redis` | Produktion |
| Local Memory | `CACHE_BACKEND=locmem` | Entwicklung |
| Dummy (kein Cache) | `CACHE_BACKEND=dummy` | Tests |

## Redis-Befehle

```bash
# Redis-Verbindung testen
redis-cli ping

# Alle Keys anzeigen
redis-cli KEYS "*"

# Wert abrufen
redis-cli GET ":1:my_key"

# Cache leeren
redis-cli FLUSHDB
```

## Tests ausführen

```bash
python manage.py test main.test_cache_manager
```

## Troubleshooting

**Problem**: Connection refused
```bash
# Lösung: Redis Status prüfen
sudo systemctl status redis-server
redis-cli ping
```

**Problem**: Cache funktioniert nicht
```bash
# Lösung: Konfiguration prüfen
cat .env | grep CACHE
```

## Mehr Informationen

Siehe [REDIS_CACHE_GUIDE.md](REDIS_CACHE_GUIDE.md) für die vollständige Dokumentation.
