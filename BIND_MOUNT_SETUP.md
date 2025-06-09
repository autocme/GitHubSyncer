# GitHub Sync Server - Bind Mount Configuration

## Overview
The GitHub Sync Server supports bind mounts for persistent repository storage across container restarts. The default path is configurable:
- **Development (Replit)**: Uses writable workspace directory
- **Production (Docker)**: Uses `/repos` for bind mount compatibility

## Docker Deployment with Bind Mounts

The project includes an automated deployment script and properly configured Docker Compose setup.

### Quick Start

1. **Run the deployment script:**
```bash
chmod +x deploy-docker.sh
./deploy-docker.sh
```

2. **Or manual setup:**
```bash
# Create and set up host directory
mkdir -p ./host-repos
sudo chown -R 1000:1000 ./host-repos
chmod 755 ./host-repos

# Deploy with Docker Compose
docker-compose up -d
```

### Docker Compose Configuration (Current)

The `docker-compose.yml` is already configured with proper bind mounts:

```yaml
volumes:
  - ./host-repos:/repos:rw  # Bind mount with read-write permissions
  - /var/run/docker.sock:/var/run/docker.sock
  - ssh_keys:/home/appuser/.ssh
```

### Alternative Bind Mount Options

#### Option 1: Absolute path bind mount
```yaml
volumes:
  - /path/to/your/repositories:/repos:rw
```

#### Option 2: Named volume (for simple setups)
```yaml
volumes:
  - repos_data:/repos
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