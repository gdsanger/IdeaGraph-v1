# Weaviate Docker Configuration

## Overview

IdeaGraph now supports configurable Weaviate connection settings, making it easy to deploy with Docker containers.

## Environment Variables

Configure Weaviate connection using these environment variables in your `.env` file:

```bash
# Weaviate URL (for local instances, use host:port format, e.g., localhost:8081)
# For Docker deployments, use the container name or service name
WEAVIATE_URL=localhost

# Weaviate HTTP port (default: 8081)
WEAVIATE_PORT=8081

# Weaviate gRPC port (default: 50051)
WEAVIATE_GRPC=50051

# Weaviate timeout in seconds (default: 30)
WEAVIATE_TIMEOUT=30
```

## Configuration Priority

The system uses the following priority order for configuration:

1. **Settings Model** (stored in database) - Highest priority
2. **Environment Variables** (from .env file)
3. **Defaults** - Lowest priority
   - `WEAVIATE_URL`: `localhost`
   - `WEAVIATE_PORT`: `8081`
   - `WEAVIATE_GRPC`: `50051`
   - `WEAVIATE_TIMEOUT`: `30`

## Docker Deployment

### Example docker-compose.yml

```yaml
version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:latest
    ports:
      - "8081:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-transformers'
      ENABLE_MODULES: 'text2vec-transformers'
      TRANSFORMERS_INFERENCE_API: 'http://t2v-transformers:8080'
    volumes:
      - weaviate_data:/var/lib/weaviate

  t2v-transformers:
    image: semitechnologies/transformers-inference:sentence-transformers-multi-qa-MiniLM-L6-cos-v1
    environment:
      ENABLE_CUDA: '0'

  ideagraph:
    build: .
    depends_on:
      - weaviate
    environment:
      WEAVIATE_URL: weaviate
      WEAVIATE_PORT: 8080
      WEAVIATE_GRPC: 50051
      WEAVIATE_TIMEOUT: 30
    ports:
      - "8000:8000"

volumes:
  weaviate_data:
```

### Key Points for Docker

1. **Container Name**: Use the service name from docker-compose as `WEAVIATE_URL` (e.g., `weaviate`)
2. **Internal Ports**: Use internal container ports, not the exposed host ports
   - Weaviate HTTP port inside container is typically `8080`
   - Weaviate gRPC port inside container is typically `50051`
3. **Network**: Ensure both services are on the same Docker network

## Local Development

For local development without Docker:

```bash
WEAVIATE_URL=localhost
WEAVIATE_PORT=8081
WEAVIATE_GRPC=50051
WEAVIATE_TIMEOUT=30
```

## Database Settings

You can also configure Weaviate connection through the admin interface:

1. Log in as an admin user
2. Navigate to Settings
3. Configure Weaviate settings:
   - **WEAVIATE_URL**: Host or container name
   - **WEAVIATE_PORT**: HTTP port
   - **WEAVIATE_GRPC**: gRPC port
   - **WEAVIATE_TIMEOUT**: Timeout in seconds

Settings configured in the database take priority over environment variables.

## Migration

After updating the code, run the migration to add the new database fields:

```bash
python manage.py migrate
```

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. Verify Weaviate is running: `docker ps` or check localhost:8081
2. Check environment variables are set correctly
3. Verify network connectivity between containers
4. Check logs for detailed error messages

### Docker Network Issues

If services can't communicate:

1. Ensure all services are on the same network
2. Use service names (not `localhost`) for inter-container communication
3. Verify ports are correctly mapped

### Timeout Issues

If operations are timing out:

1. Increase `WEAVIATE_TIMEOUT` in your configuration
2. Check Weaviate resource allocation
3. Consider scaling Weaviate resources

## See Also

- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- Main project README.md
