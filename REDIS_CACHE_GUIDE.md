# Redis Cache Integration Guide

## Übersicht

IdeaGraph unterstützt jetzt Redis als Cache-System für verbesserte Performance und Skalierbarkeit. Das System bietet flexible Cache-Backend-Unterstützung mit der Möglichkeit, zwischen verschiedenen Cache-Backends zu wechseln.

## Unterstützte Cache-Backends

1. **Redis** (empfohlen für Produktion)
   - Persistent, schnell und skalierbar
   - Unterstützt verteilte Systeme
   - Benötigt Redis-Server

2. **Local Memory** (Standard für Entwicklung)
   - In-Memory Cache innerhalb des Django-Prozesses
   - Keine externe Abhängigkeit
   - Geeignet für Entwicklung und Tests

3. **Dummy Cache** (für Tests)
   - Deaktiviert das Caching vollständig
   - Nützlich für Tests ohne Cache-Interferenz

## Installation

### 1. Redis installieren

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Docker
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

### 2. Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Die Datei `requirements.txt` enthält bereits die Redis-Abhängigkeit:
```
redis>=5.0.0
```

## Konfiguration

### Umgebungsvariablen (.env)

Erstellen Sie eine `.env`-Datei basierend auf `.env.example`:

```bash
# Cache Backend auswählen: 'redis', 'locmem', 'dummy'
CACHE_BACKEND=redis

# Redis-Konfiguration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Standard-Cache-Timeout in Sekunden (5 Minuten)
CACHE_DEFAULT_TIMEOUT=300
```

### Konfigurationsparameter

| Parameter | Beschreibung | Standard | Beispiel |
|-----------|--------------|----------|----------|
| `CACHE_BACKEND` | Cache-Backend-Typ | `locmem` | `redis`, `locmem`, `dummy` |
| `REDIS_HOST` | Redis-Server-Hostname | `localhost` | `redis.example.com` |
| `REDIS_PORT` | Redis-Server-Port | `6379` | `6379` |
| `REDIS_DB` | Redis-Datenbank-Nummer | `0` | `0`, `1`, `2`, ... |
| `REDIS_PASSWORD` | Redis-Passwort | (leer) | `mein-sicheres-passwort` |
| `CACHE_DEFAULT_TIMEOUT` | Standard-Timeout in Sekunden | `300` | `600`, `3600` |

## Verwendung

### Mit Django's Cache Framework

```python
from django.core.cache import cache

# Wert speichern
cache.set('my_key', 'my_value', timeout=300)

# Wert abrufen
value = cache.get('my_key')

# Wert löschen
cache.delete('my_key')
```

### Mit CacheManager (empfohlen)

Der `CacheManager` bietet eine erweiterte Abstraktion mit Fehlerbehandlung und Logging:

```python
from core.cache_manager import CacheManager

cache_manager = CacheManager()

# Wert speichern
cache_manager.set('user_token', token_data, timeout=3600)

# Wert abrufen
token = cache_manager.get('user_token')

# Prüfen ob Wert existiert
if cache_manager.exists('user_token'):
    print("Token found in cache")

# Wert löschen
cache_manager.delete('user_token')

# Mehrere Werte auf einmal
cache_manager.set_many({
    'key1': 'value1',
    'key2': 'value2'
}, timeout=600)

values = cache_manager.get_many(['key1', 'key2'])

# Cache leeren
cache_manager.clear()

# Backend-Informationen
info = cache_manager.get_backend_info()
print(f"Using cache backend: {info['backend']}")
```

## Aktuelle Cache-Nutzung im System

### GraphService Token-Caching

Das System nutzt bereits Caching für Microsoft Graph API Tokens:

```python
# In core/services/graph_service.py
TOKEN_CACHE_KEY = 'graph_token_cache'
TOKEN_CACHE_DURATION = 3300  # 55 Minuten

# Token aus Cache laden
cached_token = self._get_token_from_cache()

# Token im Cache speichern
self._set_token_in_cache(access_token, expires_in)
```

## Performance-Vorteile

### Vorher (In-Memory Cache)
- Cache nur innerhalb eines Prozesses verfügbar
- Bei Neustart gehen alle Cache-Daten verloren
- Nicht geeignet für Multi-Server-Deployment

### Nachher (Redis Cache)
- Cache persistent über Prozess-Neustarts hinweg
- Shared Cache zwischen mehreren Servern/Prozessen
- Schneller Zugriff mit Redis' In-Memory-Performance
- Unterstützt erweiterte Features (TTL, Atomic Operations)

## Überwachung und Debugging

### Redis-CLI verwenden

```bash
# Verbindung zu Redis
redis-cli

# Alle Schlüssel anzeigen
KEYS *

# Spezifischen Wert abrufen
GET :1:graph_token_cache

# TTL eines Schlüssels prüfen
TTL :1:graph_token_cache

# Alle Schlüssel löschen (Vorsicht!)
FLUSHDB
```

### Cache-Status in Django

```python
from core.cache_manager import CacheManager

cache_manager = CacheManager()
info = cache_manager.get_backend_info()
print(info)
# Output:
# {
#     'backend': 'redis',
#     'backend_class': "<class 'django.core.cache.backends.redis.RedisCache'>",
#     'redis_host': 'localhost',
#     'redis_port': 6379,
#     'redis_db': 0
# }
```

## Wechseln zwischen Cache-Backends

### Für Entwicklung (Local Memory)

```bash
# In .env
CACHE_BACKEND=locmem
```

### Für Produktion (Redis)

```bash
# In .env
CACHE_BACKEND=redis
REDIS_HOST=redis.production.com
REDIS_PASSWORD=secure_password
```

### Für Tests (Dummy/No Cache)

```bash
# In .env
CACHE_BACKEND=dummy
```

## Sicherheit

### Redis mit Passwort schützen

1. Bearbeiten Sie die Redis-Konfiguration:
   ```bash
   sudo nano /etc/redis/redis.conf
   ```

2. Setzen Sie ein Passwort:
   ```
   requirepass mein-sicheres-passwort
   ```

3. Redis neu starten:
   ```bash
   sudo systemctl restart redis-server
   ```

4. Passwort in `.env` setzen:
   ```
   REDIS_PASSWORD=mein-sicheres-passwort
   ```

### Redis über Netzwerk absichern

Standardmäßig sollte Redis nur von localhost erreichbar sein:

```bash
# In /etc/redis/redis.conf
bind 127.0.0.1 ::1
```

Für Zugriff von anderen Servern:
```bash
bind 0.0.0.0
```

**Wichtig**: Verwenden Sie immer ein Passwort wenn Redis über Netzwerk erreichbar ist!

## Troubleshooting

### Problem: "Connection refused" bei Redis

**Lösung**: Prüfen Sie ob Redis läuft:
```bash
sudo systemctl status redis-server
# oder
redis-cli ping
```

### Problem: Cache-Daten erscheinen nicht

**Lösung**: Prüfen Sie die Konfiguration:
```bash
# .env prüfen
cat .env | grep CACHE

# Redis-Verbindung testen
redis-cli ping
```

### Problem: Performance-Probleme

**Lösung**: 
1. Erhöhen Sie die maximalen Verbindungen in `settings.py`:
   ```python
   'max_connections': 100,
   ```

2. Überwachen Sie Redis-Nutzung:
   ```bash
   redis-cli INFO
   ```

## Best Practices

1. **Cache-Keys strukturieren**
   ```python
   # Gut
   cache.set('user:123:profile', profile_data)
   cache.set('graph:token:tenant_id', token)
   
   # Vermeiden
   cache.set('data', something)
   ```

2. **Timeouts sinnvoll setzen**
   ```python
   # Kurzlebige Daten (z.B. API Responses)
   cache.set('api:response', data, timeout=60)
   
   # Tokens mit Ablaufzeit
   cache.set('token', token, timeout=3600)
   
   # Langlebige Daten
   cache.set('config', settings, timeout=86400)
   ```

3. **Fehlerbehandlung**
   ```python
   try:
       value = cache.get('key')
       if value is None:
           value = expensive_operation()
           cache.set('key', value)
   except Exception as e:
       logger.error(f"Cache error: {e}")
       value = expensive_operation()
   ```

4. **Cache-Invalidierung**
   ```python
   # Bei Datenänderungen Cache invalidieren
   def update_user_profile(user_id, profile_data):
       # Update database
       user.update(profile_data)
       
       # Invalidate cache
       cache.delete(f'user:{user_id}:profile')
   ```

## Migration von In-Memory zu Redis

Wenn Sie von Local Memory Cache zu Redis wechseln:

1. **Redis installieren und starten** (siehe oben)

2. **Umgebungsvariablen aktualisieren**
   ```bash
   CACHE_BACKEND=redis
   REDIS_HOST=localhost
   ```

3. **Django neu starten**
   ```bash
   python manage.py runserver
   ```

4. **Cache-Funktionalität testen**
   ```python
   from django.core.cache import cache
   cache.set('test', 'value')
   assert cache.get('test') == 'value'
   ```

Die Migration ist nahtlos, da der Code keine Änderungen benötigt!

## Weiterführende Ressourcen

- [Django Cache Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Redis Documentation](https://redis.io/documentation)
- [django-redis](https://github.com/jazzband/django-redis) (alternative Redis-Backend)

## Support

Bei Fragen oder Problemen:
1. Überprüfen Sie die Logs: `logs/ideagraph.log`
2. Testen Sie die Redis-Verbindung: `redis-cli ping`
3. Prüfen Sie die Django-Konfiguration in `ideagraph/settings.py`

---

**Hinweis**: Diese Implementierung verwendet Django's eingebaute Redis-Unterstützung (verfügbar ab Django 4.0). Für ältere Django-Versionen müsste `django-redis` verwendet werden.
