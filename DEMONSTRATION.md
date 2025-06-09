# GitHub Sync Server - Complete Demonstration

## Overview

The GitHub Sync Server is a FastAPI-based webhook system that automatically pulls repository changes and restarts Docker containers with simplified label-based configuration.

## Key Features

### 1. Simplified Container Restart Labels
Containers are restarted after repository pulls using a single label format:
```
restart-after: "repository-name"
```

### 2. Complete Workflow
1. **GitHub Webhook** → Triggers repository pull
2. **Repository Pull** → Downloads latest code changes
3. **Container Restart** → Restarts containers with matching `restart-after` labels
4. **Logging** → Records all operations with timestamps and status

## Example Docker Compose Configuration

```yaml
version: '3.8'
services:
  # GitHub Sync Server
  github-sync:
    image: github-sync-server
    ports:
      - "5000:5000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./repos:/repos
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/github_sync
      - MAIN_PATH=/repos
    
  # Example application container
  web-app:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./repos/my-website:/usr/share/nginx/html
    labels:
      restart-after: "my-website"  # Restart when my-website repo is updated
    
  # Another application
  api-server:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./repos/my-api:/app
    command: npm start
    labels:
      restart-after: "my-api"     # Restart when my-api repo is updated
    
  # Multi-restart container
  full-stack:
    image: python:3.11
    volumes:
      - ./repos/frontend:/app/frontend
      - ./repos/backend:/app/backend
    labels:
      restart-after: "frontend,backend"  # Restart for multiple repos
```

## Web Interface Features

### Dashboard
- System status overview
- Recent repository operations
- Container health monitoring
- Quick access to all sections

### Repositories Management
- Add public/private repositories
- Configure SSH keys for private repos
- Manual sync operations
- Repository status tracking

### Container Management
- Automatic container discovery
- Manual container restart
- Label configuration display
- Container status monitoring

### Operation Logs
- Detailed operation history
- Pull/restart status tracking
- Error message logging
- Timestamp tracking

### Settings
- Path configuration
- SSH key management
- API key management
- System preferences

## API Endpoints

### Repository Operations
- `GET /api/v1/repositories` - List repositories
- `POST /api/v1/repositories` - Add repository
- `PUT /api/v1/repositories/{id}` - Update repository
- `DELETE /api/v1/repositories/{id}` - Remove repository
- `POST /api/v1/repositories/{id}/sync` - Manual sync

### Container Operations
- `GET /api/v1/containers` - List containers
- `POST /api/v1/containers/discover` - Discover containers
- `POST /api/v1/containers/{id}/restart` - Restart container

### Webhook Endpoints
- `POST /webhook/github` - GitHub webhook handler
- `POST /webhook/test` - Test webhook functionality

## GitHub Webhook Configuration

1. **Repository Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://your-server.com/webhook/github`
3. **Content type**: `application/json`
4. **Events**: Select "Push events"
5. **Secret**: Optional (recommended for security)

## Container Label Examples

### Single Repository
```yaml
labels:
  restart-after: "my-app"
```

### Multiple Repositories
```yaml
labels:
  restart-after: "frontend,backend,shared-lib"
```

### Development vs Production
```yaml
# Development
labels:
  restart-after: "my-app-dev"

# Production
labels:
  restart-after: "my-app-main"
```

## Deployment Scenarios

### Local Development
- Run directly with Python
- Docker not required for development
- Database: SQLite or PostgreSQL
- Container management: Limited (development mode)

### Docker Deployment
- Full container orchestration
- Docker socket mounting required
- Database: PostgreSQL recommended
- Container management: Full featured

### Production Deployment
- HTTPS with reverse proxy
- Database clustering
- Log aggregation
- Health monitoring
- Backup strategies

## Security Features

### Authentication
- User account system
- Session-based authentication
- API key authentication
- Rate limiting for login attempts

### Repository Access
- SSH key management
- Private repository support
- Secure credential storage
- Key rotation capabilities

### Container Security
- Docker socket permissions
- Container isolation
- Label-based access control
- Restart permission management

## Monitoring & Logging

### Operation Logs
- Repository pull operations
- Container restart operations
- Error tracking and debugging
- Performance metrics

### Health Checks
- Database connectivity
- Docker daemon status
- Repository accessibility
- Container health status

### Alerting
- Failed pull notifications
- Container restart failures
- System health alerts
- Performance degradation warnings

## Troubleshooting

### Common Issues

1. **Docker Socket Permission Denied**
   - Ensure user is in docker group
   - Check socket permissions
   - Verify volume mounting

2. **Repository Clone Failures**
   - Check SSH key configuration
   - Verify repository URL format
   - Test network connectivity

3. **Container Restart Failures**
   - Verify label format
   - Check container status
   - Review Docker daemon logs

4. **Webhook Not Triggering**
   - Verify webhook URL accessibility
   - Check GitHub delivery logs
   - Review server logs

### Debug Commands

```bash
# Check Docker connectivity
docker ps

# Test repository access
git clone <repository-url>

# Check container labels
docker inspect <container-name>

# Review application logs
docker logs github-sync-server
```

## Performance Optimization

### Repository Management
- Use shallow clones for large repositories
- Configure appropriate pull timeouts
- Implement repository cleanup policies
- Monitor disk usage

### Container Operations
- Optimize restart sequences
- Implement graceful shutdowns
- Monitor resource usage
- Configure health checks

### Database Optimization
- Regular log cleanup
- Index optimization
- Connection pooling
- Query performance monitoring

## Best Practices

### Repository Configuration
- Use descriptive repository names
- Implement proper branching strategies
- Configure appropriate webhook filters
- Regular repository maintenance

### Container Management
- Use consistent label naming
- Implement health checks
- Configure resource limits
- Regular image updates

### Security Practices
- Regular credential rotation
- Secure network configuration
- Access logging and monitoring
- Regular security updates

## Integration Examples

### CI/CD Pipeline Integration
```yaml
# GitHub Actions example
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Trigger deployment
        run: |
          # Push triggers webhook automatically
          # GitHub Sync Server handles the rest
```

### Multiple Environment Support
```yaml
# Environment-specific labels
production:
  labels:
    restart-after: "app-prod"
    environment: "production"

staging:
  labels:
    restart-after: "app-staging"
    environment: "staging"
```

## Conclusion

The GitHub Sync Server provides a robust, production-ready solution for automated repository synchronization and container management. The simplified `restart-after` label format makes configuration straightforward while maintaining powerful functionality for complex deployment scenarios.