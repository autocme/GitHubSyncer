# Container Restart Labels Guide

This guide explains how to configure Docker containers for automatic restart after repository updates using container labels.

## Overview

The GitHub Sync Server can automatically restart Docker containers when specific repositories are updated via GitHub webhooks. This is accomplished using container labels that specify which repository updates should trigger a restart.

## Label Format

The system uses a single, simple label format:

```yaml
restart-after: "repository-name"
```

## Configuration Examples

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  web-frontend:
    image: my-frontend:latest
    labels:
      restart_after_pull: "frontend-repo"
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
  
  api-backend:
    image: my-api:latest
    labels:
      restart_after_pull: "backend-repo"
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://...
  
  worker-service:
    image: my-worker:latest
    labels:
      github-sync.restart-after: "worker-repo"
    environment:
      - REDIS_URL=redis://redis:6379
```

### Docker Run Commands

#### Simple Container
```bash
docker run -d \
  --name my-app \
  --label "restart_after_pull=my-repo" \
  --port 3000:3000 \
  my-app:latest
```

#### Production Container with Multiple Labels
```bash
docker run -d \
  --name production-api \
  --label "restart_after_pull=api-repository" \
  --label "environment=production" \
  --label "team=backend" \
  --port 8080:8080 \
  --env DATABASE_URL=postgresql://... \
  api:v1.2.3
```

#### Multiple Containers for Same Repository
```bash
# Both containers will restart when "shared-repo" is updated
docker run -d --name app-1 --label "restart_after_pull=shared-repo" app:latest
docker run -d --name app-2 --label "restart_after_pull=shared-repo" app:latest
```

### Kubernetes Deployment (if using Docker-in-Docker)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
        restart_after_pull: "k8s-app-repo"
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
```

## Workflow Process

### 1. Repository Setup
1. Add your repository in the GitHub Sync Server web interface
2. Configure the repository name (this must match your label value)
3. Set up GitHub webhook pointing to your server

### 2. Container Configuration
1. Add the appropriate restart label to your containers
2. Use the exact repository name as configured in step 1
3. Deploy your containers with the labels

### 3. Discovery Process
1. Navigate to **Containers** section in the web interface
2. Click **"Discover Containers"** button
3. System scans all Docker containers and identifies restart labels
4. Labeled containers are automatically tracked in the database

### 4. Automatic Restart Process
When a GitHub webhook is received:
1. Repository code is pulled from GitHub
2. System queries for containers with matching restart labels
3. Each matching container is restarted in sequence
4. Success/failure status is logged for each operation
5. Overall operation status is recorded in the logs

## Best Practices

### Label Naming
- Use lowercase, hyphen-separated repository names
- Keep names descriptive but concise
- Match exactly with repository names in the web interface

```bash
# Good examples
restart_after_pull: "frontend-app"
restart_after_pull: "api-service"
restart_after_pull: "worker-queue"

# Avoid special characters or spaces
restart_after_pull: "my_app"        # underscores work but hyphens preferred
restart_after_pull: "My App Name"   # spaces will cause issues
```

### Container Organization
- Group related containers with the same repository label
- Use separate repositories for different deployment environments
- Consider using different labels for staging vs. production

```yaml
# Production containers
services:
  prod-api:
    labels:
      restart_after_pull: "api-prod"
  
  prod-worker:
    labels:
      restart_after_pull: "api-prod"

# Staging containers  
  staging-api:
    labels:
      restart_after_pull: "api-staging"
```

### Health Checks
Always include health checks in your containers to ensure proper restart behavior:

```yaml
services:
  app:
    image: my-app:latest
    labels:
      restart_after_pull: "my-repo"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Troubleshooting

### Container Not Restarting
1. **Check Discovery**: Ensure container appears in "Discover Containers" results
2. **Verify Labels**: Confirm label format and repository name match exactly
3. **Check Logs**: Review operation logs for error messages
4. **Docker Access**: Verify GitHub Sync Server has Docker socket access

### Partial Restart Failures
1. **Container Health**: Check if containers are healthy before restart
2. **Resource Limits**: Ensure sufficient system resources for restarts
3. **Dependencies**: Verify container dependencies are available
4. **Timing**: Consider adding delays between restarts for heavy containers

### Label Not Detected
1. **Case Sensitivity**: Repository names are case-sensitive
2. **Whitespace**: Avoid leading/trailing spaces in label values
3. **Special Characters**: Use only alphanumeric characters and hyphens
4. **Label Format**: Ensure using supported label format exactly

## Monitoring and Logging

### Web Interface Monitoring
- **Containers Page**: View all discovered containers and their restart labels
- **Logs Page**: Monitor restart operations and their success/failure status
- **Dashboard**: Quick overview of recent operations

### Log Analysis
Check logs for these key messages:
```
INFO - Found 3 containers with restart labels:
INFO -   - frontend-app: will restart after 'frontend-repo' repository updates
INFO -   - api-service: will restart after 'backend-repo' repository updates
INFO - Successfully restarted container frontend-app (abc123...)
ERROR - Failed to restart container api-service: Container not found
```

### Container Status Verification
After repository updates, verify containers restarted properly:

```bash
# Check container restart times
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# View container logs for restart evidence
docker logs my-app --since 5m

# Check container health status
docker inspect my-app --format='{{.State.Health.Status}}'
```

## Security Considerations

### Docker Socket Access
- Ensure GitHub Sync Server container has appropriate Docker socket permissions
- Consider using Docker-in-Docker or rootless Docker for enhanced security
- Limit Docker socket access to only necessary operations

### Repository Access
- Use SSH keys for private repository access
- Regularly rotate API keys and SSH keys
- Monitor webhook delivery logs for unauthorized access attempts

### Container Isolation
- Use appropriate network isolation between containers
- Implement proper resource limits to prevent resource exhaustion
- Consider using separate Docker networks for different environments

## Advanced Configuration

### Multiple Repository Labels
If you need a container to restart for multiple repositories (not recommended), you'll need separate containers:

```bash
# Create separate containers for different repositories
docker run -d --name app-frontend --label "restart_after_pull=frontend-repo" app:latest
docker run -d --name app-backend --label "restart_after_pull=backend-repo" app:latest
```

### Conditional Restarts
Use container health checks and dependencies to create conditional restart behavior:

```yaml
services:
  database:
    image: postgres:15
    # No restart label - database shouldn't auto-restart
    
  api:
    image: my-api:latest
    labels:
      restart_after_pull: "api-repo"
    depends_on:
      database:
        condition: service_healthy
```

### Rolling Updates
For zero-downtime deployments, consider using multiple container instances:

```bash
# Run multiple instances of the same service
docker run -d --name api-1 --label "restart_after_pull=api-repo" api:latest
docker run -d --name api-2 --label "restart_after_pull=api-repo" api:latest

# Load balancer will handle traffic during rolling restarts
```

This comprehensive labeling system provides flexible, reliable container restart automation while maintaining visibility and control over your deployment process.