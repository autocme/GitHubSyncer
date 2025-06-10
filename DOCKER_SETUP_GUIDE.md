# Docker Setup Guide for Production

## Issue: Docker Command Not Found

If you're seeing "Docker command not found" errors in production, your container doesn't have proper Docker access. Here's how to fix it:

## Solution 1: Fix Docker Socket Permissions

### 1. Check Docker Socket Exists
```bash
ls -la /var/run/docker.sock
```

### 2. Update docker-compose.yml
```yaml
services:
  github-sync:
    build: .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw  # Add :rw for read-write
      - ./host-repos:/repos:rw
    user: "0:$(stat -c '%g' /var/run/docker.sock)"  # Run as docker group
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
```

### 3. Alternative: Use Docker Group
```yaml
services:
  github-sync:
    build: .
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./host-repos:/repos:rw
    group_add:
      - docker  # Add container to docker group
```

## Solution 2: Install Docker in Container

### Update Dockerfile
```dockerfile
FROM python:3.11-slim

# Install Docker CLI
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Rest of your Dockerfile...
```

## Solution 3: Use Docker API with Proper Permissions

### 1. Check Current Setup
Run this inside your container:
```bash
# Check if socket exists
ls -la /var/run/docker.sock

# Check permissions
stat /var/run/docker.sock

# Test Docker access
docker ps
```

### 2. Fix Permissions (on host)
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Set socket permissions
sudo chmod 666 /var/run/docker.sock
```

## Production Docker Compose Example

```yaml
version: '3.8'

services:
  github-sync:
    build: .
    container_name: github-sync-server
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - ./repos:/repos:rw
    user: "root"  # Needed for Docker socket access
    restart: unless-stopped
    depends_on:
      - postgres

  # Your other containers (Odoo, etc.)
  odoo:
    image: odoo:17.0
    container_name: odoo-odoo-1
    labels:
      - "restart-after=server-backend"  # This enables auto-restart
    # ... rest of your Odoo config
```

## Testing Docker Access

After making changes, test with:

```bash
# From inside the github-sync container
docker ps
docker restart odoo-odoo-1
```

## Security Note

Running with `user: "root"` or `chmod 666` on Docker socket reduces security. In production, consider:

1. Using a dedicated Docker API proxy
2. Running containers with minimal required permissions
3. Using Docker Swarm or Kubernetes for better security

## Troubleshooting

### Error: "Permission denied"
- Check Docker socket permissions
- Ensure container user is in docker group
- Try running container as root temporarily

### Error: "No such file or directory"
- Docker socket not mounted correctly
- Check docker-compose.yml volumes section

### Error: "Cannot connect to Docker daemon"
- Docker service not running on host
- Socket path incorrect
- Network connectivity issues

## Quick Fix for Testing

For immediate testing, run:
```bash
# On host machine
sudo chmod 666 /var/run/docker.sock

# Then restart your github-sync container
docker-compose restart github-sync
```

This gives full access to Docker socket (less secure but works for testing).