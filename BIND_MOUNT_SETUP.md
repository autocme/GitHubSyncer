# GitHub Sync Server - Bind Mount Configuration

## Overview
The GitHub Sync Server supports bind mounts for persistent repository storage across container restarts. The default path is configurable:
- **Development (Replit)**: Uses writable workspace directory
- **Production (Docker)**: Uses `/repos` for bind mount compatibility

## Docker Compose Configuration with Bind Mounts

### Option 1: Use bind mount to host directory
```yaml
version: '3.8'

services:
  github-sync:
    build: .
    container_name: github-sync-server
    ports:
      - "5000:5000"  # Web interface
      - "8200:5000"  # Webhook port
    environment:
      - DATABASE_URL=postgresql://github_sync:secure_password@postgres:5432/github_sync_db?sslmode=disable
      - MAIN_PATH=/repos
      - LOG_LEVEL=INFO
    volumes:
      - ./host-repos:/repos  # Bind mount host directory to container /repos
      - /var/run/docker.sock:/var/run/docker.sock
      - ssh_keys:/home/appuser/.ssh
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - github-sync-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    container_name: github-sync-postgres
    environment:
      - POSTGRES_DB=github_sync_db
      - POSTGRES_USER=github_sync
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - github-sync-network
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U github_sync -d github_sync_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  postgres_data:
    driver: local
  ssh_keys:
    driver: local

networks:
  github-sync-network:
    driver: bridge
```

### Option 2: Use absolute path bind mount
```yaml
volumes:
  - /path/to/your/repositories:/repos  # Absolute path on host
```

### Option 3: Use named volume (current setup)
```yaml
volumes:
  - repos_data:/repos  # Named Docker volume
```

## Directory Setup

### For bind mounts, create the host directory:
```bash
# Create host directory
mkdir -p ./host-repos
chmod 755 ./host-repos

# Or for absolute path
mkdir -p /path/to/your/repositories
chmod 755 /path/to/your/repositories
```

## Environment Variables

The following environment variables control repository storage:

- `MAIN_PATH=/repos` - Container path for repositories (default)
- Can be overridden via database settings in the web interface

## Benefits of Bind Mounts

1. **Persistence**: Repositories persist across container restarts and updates
2. **Host Access**: Direct access to repository files from the host system
3. **Backup**: Easy backup and restore of repository data
4. **Debugging**: Ability to inspect repository contents directly

## Docker Run Command Example

```bash
docker run -d \
  --name github-sync-server \
  -p 5000:5000 \
  -p 8200:5000 \
  -v ./host-repos:/repos \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MAIN_PATH=/repos \
  -e DATABASE_URL=your_database_url \
  github-sync:latest
```

## Verification

After starting the container with bind mounts:

1. Check the web interface at http://localhost:5000
2. Add a repository and verify it appears in your host directory
3. Repository files should be visible at `./host-repos/repository-name/`

## Troubleshooting

### Permission Issues
If you encounter permission issues:

```bash
# Fix permissions on host directory
sudo chown -R 1000:1000 ./host-repos
chmod -R 755 ./host-repos
```

### Path Configuration
- The default path `/repos` is configured in the application
- Can be changed via Settings page in the web interface
- Changes require container restart to take effect

## Security Considerations

- Ensure proper file permissions on the host directory
- Consider using Docker secrets for sensitive configuration
- Bind mounts expose host filesystem to containers - use with caution in production