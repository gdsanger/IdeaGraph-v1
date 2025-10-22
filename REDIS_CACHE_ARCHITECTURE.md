# Redis Cache Architecture

## Architekturübersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                      IdeaGraph Application                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Application Layer                             │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  Views       │  │  Services    │  │  Models      │   │  │
│  │  │              │  │              │  │              │   │  │
│  │  │  - Item      │  │  - Graph     │  │  - User      │   │  │
│  │  │  - Task      │  │  - KiGate    │  │  - Item      │   │  │
│  │  │  - Settings  │  │  - OpenAI    │  │  - Task      │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘   │  │
│  └─────────┼──────────────────┼──────────────────────────────┘  │
│            │                  │                                  │
│            └──────────┬───────┘                                  │
│                       │                                          │
│  ┌────────────────────▼──────────────────────────────────────┐  │
│  │              Cache Abstraction Layer                       │  │
│  │                                                            │  │
│  │    ┌──────────────────────────────────────────────────┐  │  │
│  │    │         CacheManager                             │  │  │
│  │    │  (core/cache_manager.py)                        │  │  │
│  │    │                                                  │  │  │
│  │    │  • get(key)                                      │  │  │
│  │    │  • set(key, value, timeout)                     │  │  │
│  │    │  • delete(key)                                   │  │  │
│  │    │  • exists(key)                                   │  │  │
│  │    │  • get_many() / set_many()                      │  │  │
│  │    │  • Error Handling                                │  │  │
│  │    │  • Logging                                       │  │  │
│  │    └──────────────────────────────────────────────────┘  │  │
│  │                       │                                   │  │
│  │                       │ Uses Django Cache Framework       │  │
│  │                       │                                   │  │
│  │    ┌──────────────────▼──────────────────────────────┐  │  │
│  │    │     Django Cache Framework                       │  │  │
│  │    │  (django.core.cache)                            │  │  │
│  │    └──────────────────┬──────────────────────────────┘  │  │
│  └───────────────────────┼─────────────────────────────────┘  │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │   Backend Selection         │
            │   (CACHE_BACKEND env var)   │
            └──────────────┬──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Redis       │  │ Local Memory  │  │  Dummy Cache  │
│   Backend     │  │   Backend     │  │   Backend     │
├───────────────┤  ├───────────────┤  ├───────────────┤
│ Production    │  │ Development   │  │   Testing     │
│               │  │               │  │               │
│ • Persistent  │  │ • In-Memory   │  │ • No Caching  │
│ • Shared      │  │ • Per Process │  │ • Always Miss │
│ • Fast        │  │ • Simple      │  │ • Simple      │
│ • Scalable    │  │ • No Setup    │  │ • No Setup    │
└───────┬───────┘  └───────────────┘  └───────────────┘
        │
        ▼
┌───────────────────────────┐
│   Redis Server            │
│   (localhost:6379)        │
├───────────────────────────┤
│ • In-Memory Store         │
│ • Key-Value Database      │
│ • Connection Pool (50)    │
│ • Retry on Timeout        │
└───────────────────────────┘
```

## Komponenten-Beschreibung

### 1. Application Layer
- **Views**: Django Views die Cache nutzen
- **Services**: Business-Logik-Services (GraphService, KiGate, etc.)
- **Models**: Django ORM Models

### 2. Cache Abstraction Layer

#### CacheManager (`core/cache_manager.py`)
- **Zweck**: Einheitliche API für alle Cache-Backends
- **Features**:
  - Error Handling mit Try-Catch
  - Comprehensive Logging
  - Backend-unabhängig
  - Erweiterte Operationen

#### Django Cache Framework
- **Standard**: Django's integriertes Cache-System
- **Backends**: Redis, LocMem, Dummy
- **API**: get, set, delete, get_many, set_many

### 3. Backend Selection

Automatische Auswahl basierend auf `CACHE_BACKEND` Umgebungsvariable:

```python
if CACHE_BACKEND == 'redis':
    # Redis Backend
elif CACHE_BACKEND == 'dummy':
    # Dummy Backend
else:
    # Local Memory Backend (default)
```

### 4. Cache Backends

#### Redis Backend (Produktion)
- **Vorteile**:
  - Persistent über Neustarts
  - Shared zwischen Prozessen/Servern
  - Schnell (In-Memory)
  - Skalierbar
- **Nachteile**:
  - Benötigt Redis-Server
  - Zusätzliche Konfiguration

#### Local Memory Backend (Entwicklung)
- **Vorteile**:
  - Keine externe Abhängigkeit
  - Einfach zu nutzen
  - Schnell
- **Nachteile**:
  - Nur innerhalb eines Prozesses
  - Verloren bei Neustart
  - Nicht skalierbar

#### Dummy Backend (Testing)
- **Vorteile**:
  - Kein Caching = deterministisch
  - Keine Seiteneffekte in Tests
- **Nachteile**:
  - Keine Performance-Vorteile

## Datenfluss

### Cache-Hit (Optimaler Fall)

```
Request
   │
   ├─> CacheManager.get('key')
   │      │
   │      ├─> Django Cache Framework
   │      │      │
   │      │      ├─> Redis Server
   │      │      │      │
   │      │      │      └─> Key Found! ✓
   │      │      │
   │      │      └─> Return Value
   │      │
   │      └─> Return to Application
   │
   └─> Response (Fast! ~1ms)
```

### Cache-Miss (Fallback)

```
Request
   │
   ├─> CacheManager.get('key')
   │      │
   │      ├─> Django Cache Framework
   │      │      │
   │      │      ├─> Redis Server
   │      │      │      │
   │      │      │      └─> Key Not Found ✗
   │      │      │
   │      │      └─> Return None
   │      │
   │      └─> Return None to Application
   │
   ├─> Application fetches from DB/API (~500ms)
   │
   ├─> CacheManager.set('key', value)
   │      │
   │      ├─> Django Cache Framework
   │      │      │
   │      │      └─> Redis Server (Cached for next time)
   │      │
   │      └─> Success
   │
   └─> Response (Slower first time, then fast)
```

## Cache-Keys-Struktur

Empfohlene Key-Struktur für bessere Organisation:

```
user:<user_id>:<attribute>
  ├─> user:123:profile
  ├─> user:123:settings
  └─> user:123:permissions

graph:token:<tenant_id>
  └─> graph:token:tenant_xyz

api:<resource>:<id>
  ├─> api:items:list
  └─> api:items:123

config:<setting>
  ├─> config:app_name
  └─> config:version
```

## Konfiguration

### Environment Variables (.env)

```bash
# Backend Selection
CACHE_BACKEND=redis          # 'redis', 'locmem', 'dummy'

# Redis Configuration
REDIS_HOST=localhost         # Redis server hostname
REDIS_PORT=6379             # Redis server port
REDIS_DB=0                  # Redis database number
REDIS_PASSWORD=             # Redis password (optional)

# Cache Settings
CACHE_DEFAULT_TIMEOUT=300   # Default timeout in seconds
```

### Django Settings (ideagraph/settings.py)

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django.core.cache.backends.redis.RedisClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'TIMEOUT': 300,
    }
}
```

## Use Cases

### 1. Token Caching (GraphService)

```python
# Before: Every request = API call (~500ms)
# After: Cached token (~1ms)

TOKEN_CACHE_KEY = 'graph_token_cache'
cached_token = cache.get(TOKEN_CACHE_KEY)
if cached_token:
    return cached_token  # Fast! ~1ms

# Acquire new token
token = acquire_from_api()  # Slow ~500ms
cache.set(TOKEN_CACHE_KEY, token, timeout=3300)
```

### 2. User Profile Caching

```python
user_key = f'user:{user_id}:profile'
profile = cache.get(user_key)
if not profile:
    profile = User.objects.get(id=user_id)
    cache.set(user_key, profile, timeout=600)
```

### 3. API Response Caching

```python
cache_key = f'api:items:list?page={page}'
items = cache.get(cache_key)
if not items:
    items = fetch_from_database()
    cache.set(cache_key, items, timeout=60)
```

## Performance Metriken

| Operation | Redis Cache | Local Memory | No Cache |
|-----------|-------------|--------------|----------|
| Token Fetch | ~1 ms | ~0.5 ms | ~500 ms |
| Profile Load | ~1 ms | ~0.5 ms | ~50 ms |
| API Response | ~1 ms | ~0.5 ms | ~200 ms |
| Memory Usage | Low | Medium | N/A |
| Scalability | ✅ Excellent | ❌ Poor | N/A |
| Persistence | ✅ Yes | ❌ No | N/A |

## Best Practices

### 1. Key Naming
```python
# Good
cache.set('user:123:profile', data)
cache.set('graph:token:tenant_xyz', token)

# Bad
cache.set('data', something)
cache.set('x', value)
```

### 2. Timeouts
```python
# Short-lived (API responses)
cache.set('api:response', data, timeout=60)

# Medium (User data)
cache.set('user:profile', data, timeout=600)

# Long-lived (Tokens)
cache.set('token', token, timeout=3600)
```

### 3. Invalidation
```python
def update_user(user_id, data):
    # Update DB
    user.update(data)
    
    # Invalidate cache
    cache.delete(f'user:{user_id}:profile')
```

### 4. Error Handling
```python
try:
    value = cache.get('key')
except Exception as e:
    logger.error(f"Cache error: {e}")
    value = None  # Fallback
```

## Monitoring

### Redis CLI Commands

```bash
# Connect to Redis
redis-cli

# Check status
PING

# List all keys
KEYS *

# Get value
GET :1:graph_token_cache

# Check TTL
TTL :1:graph_token_cache

# Memory usage
INFO memory

# Stats
INFO stats
```

### Python Monitoring

```python
from core.cache_manager import CacheManager

cache_manager = CacheManager()

# Get backend info
info = cache_manager.get_backend_info()
print(f"Backend: {info['backend']}")
print(f"Class: {info['backend_class']}")
```

## Troubleshooting

### Problem: Connection Refused

**Symptom**: Can't connect to Redis
```
ConnectionError: Error connecting to localhost:6379
```

**Solution**:
```bash
# Check if Redis is running
sudo systemctl status redis-server

# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping
```

### Problem: Cache Not Working

**Symptom**: Values not cached

**Solution**:
```bash
# Check configuration
cat .env | grep CACHE

# Verify backend
python manage.py shell
>>> from core.cache_manager import CacheManager
>>> cm = CacheManager()
>>> print(cm.get_backend_info())
```

### Problem: Memory Issues

**Symptom**: Redis using too much memory

**Solution**:
```bash
# Check memory usage
redis-cli INFO memory

# Set max memory in redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis-server
```

## Security

### 1. Password Protection

```bash
# Set password in redis.conf
requirepass your_secure_password

# Update .env
REDIS_PASSWORD=your_secure_password
```

### 2. Network Security

```bash
# Bind to localhost only (default)
bind 127.0.0.1 ::1

# For remote access (use with password!)
bind 0.0.0.0
```

### 3. Sensitive Data

```python
# Don't cache sensitive data without encryption
# Bad
cache.set('user:password', password)

# Good
cache.set('user:session_id', encrypted_session_id)
```

## Zusammenfassung

Die Redis-Cache-Architektur bietet:

✅ **Flexibilität**: Einfacher Wechsel zwischen Backends  
✅ **Performance**: Bis zu 500x schneller als ohne Cache  
✅ **Skalierbarkeit**: Unterstützt Multi-Server-Deployments  
✅ **Wartbarkeit**: Klare Abstraktion und Fehlerbehandlung  
✅ **Sicherheit**: Best Practices implementiert  
✅ **Monitoring**: Einfache Überwachung und Debugging  

---

**Siehe auch**:
- [REDIS_CACHE_GUIDE.md](REDIS_CACHE_GUIDE.md) - Vollständige Anleitung
- [REDIS_CACHE_QUICKREF.md](REDIS_CACHE_QUICKREF.md) - Schnellreferenz
- [REDIS_CACHE_IMPLEMENTATION_SUMMARY.md](REDIS_CACHE_IMPLEMENTATION_SUMMARY.md) - Implementierungsdetails
