# Docker Volumes Configuration Guide for GitHub Sync Server

## Problem Analysis
The GitHub Sync Server is experiencing changing repository paths due to Docker Compose recreating containers with new volume paths:
- `/data/compose/206/host-repos/server-backend` 
- `/data/compose/208/host-repos/server-backend`
- `/data/compose/209/host-repos/server-backend`

## Root Cause
Using anonymous or auto-generated bind mounts causes Docker Compose to create new volume paths on each container recreation.

## Recommended Solutions

### Solution 1: Named Volumes (Recommended)
Configure your `docker-compose.yml` to use named volumes:

```yaml
version: '3.8'
services:
  github-sync:
    image: your-github-sync-image
    volumes:
      - repos-data:/repos  # Named volume
    environment:
      - REPOS_PATH=/repos

volumes:
  repos-data:
    driver: local
```

This ensures `/repos` always maps to the same persistent storage location.

### Solution 2: Explicit Bind Mount
Use explicit host path binding:

```yaml
version: '3.8'
services:
  github-sync:
    image: your-github-sync-image
    volumes:
      - /host/path/repos:/repos  # Explicit host path
    environment:
      - REPOS_PATH=/repos
```

Replace `/host/path/repos` with your desired host directory.

### Solution 3: Environment Variable Override
Set a consistent internal path via environment variable:

```yaml
version: '3.8'
services:
  github-sync:
    image: your-github-sync-image
    volumes:
      - repos-data:/app/repos  # Consistent internal path
    environment:
      - REPOS_PATH=/app/repos
```

## Implementation Benefits

1. **Consistent Paths**: Repository paths remain the same across container restarts
2. **Data Persistence**: Repository data survives container recreation
3. **Predictable Behavior**: No need for dynamic path detection
4. **Simpler Configuration**: Clear, explicit volume mappings

## Current Workaround
The GitHub Sync Server now includes automatic Docker volume path detection that adapts to changing container paths, but implementing proper Docker volumes is the permanent solution.

## Migration Steps

1. Stop current containers
2. Update `docker-compose.yml` with named volumes
3. Restart containers
4. Verify repositories use consistent `/repos` path
5. Remove automatic path detection if desired

This ensures the GitHub Sync Server repository paths remain stable regardless of container lifecycle events.