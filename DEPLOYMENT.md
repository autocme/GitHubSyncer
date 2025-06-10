# GitHub Sync Server - Deployment Guide

## Docker Deployment

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <your-repo-url>
cd github-sync-server
```

2. Build and start the services:
```bash
docker-compose up -d
```

3. Access the application:
- Web Interface: http://localhost:5000
- Webhook Endpoint: http://localhost:8200/webhook (maps to internal port 5000)

The application runs on a single internal port (5000) but provides two external access points:
- Port 5000: Direct web interface access
- Port 8200: Alternative access for webhook configuration (both map to the same internal service)

### Using Portainer Custom Templates

Deploy using Portainer's Custom Templates for one-click deployment:

1. In Portainer, go to "App Templates" → "Custom Templates"
2. Add a new template with the contents of `portainer-template.json`
3. Deploy with a single click
4. The template includes:
   - PostgreSQL database with health checks
   - GitHub Sync Server with proper port mapping
   - Persistent volumes for data and repositories
   - Network isolation for security

### Manual Docker Build

```bash
# Build the image
docker build -t github-sync-server .

# Run with PostgreSQL (recommended for production)
docker run -d \
  --name github-sync-server \
  -p 5000:5000 \
  -p 8200:5000 \
  -v repos_data:/app/repos \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DATABASE_URL=postgresql://user:password@postgres:5432/database?sslmode=disable \
  -e MAIN_PATH=/app/repos \
  github-sync-server

# Or run with SQLite (development)
docker run -d \
  --name github-sync-server \
  -p 5000:5000 \
  -p 8200:5000 \
  -v repos_data:/app/repos \
  -v sqlite_data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DATABASE_URL=sqlite:///app/data/app.db \
  -e MAIN_PATH=/app/repos \
  github-sync-server
```

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string
  - PostgreSQL: `postgresql://user:password@host:5432/database?sslmode=disable`
  - SQLite: `sqlite:///app/data/app.db`
- `MAIN_PATH`: Path for repository storage (default: `/app/repos`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: PostgreSQL connection details

### Port Configuration

The application architecture uses a single FastAPI server that handles both web interface and webhook requests:

- **Internal Port**: 5000 (FastAPI server)
- **External Port Mapping**:
  - 5000:5000 → Web interface access
  - 8200:5000 → Webhook endpoint access (same service, different external port)

Both external ports connect to the same internal service. This design allows:
- Flexible firewall configuration
- Separate webhook URL without additional services
- Simplified deployment and maintenance

### GitHub Webhook Setup

Configure your GitHub repository to send webhooks:

1. Go to your GitHub repository settings
2. Navigate to "Webhooks" → "Add webhook"
3. Set payload URL: `http://your-server:8200/webhook`
4. Content type: `application/json`
5. Select events: "Just the push event" or "Send me everything"
6. Active: ✓ (checked)

### Container Restart Configuration

Containers are automatically discovered and can be configured for restart after repository updates:

1. Add label to your containers: `restart_after_pull=repository_name`
2. The system will restart matching containers after successful git pulls
3. Example Docker command:
```bash
docker run -d --label "restart_after_pull=my-app-repo" my-app:latest
```

## Security Notes

### Production Security Checklist

- [ ] Change default PostgreSQL passwords
- [ ] Use HTTPS with proper SSL certificates
- [ ] Implement webhook authentication/secrets
- [ ] Limit Docker socket access with appropriate user permissions
- [ ] Use environment files (.env) for sensitive configuration
- [ ] Enable firewall rules for port access
- [ ] Regular security updates for base images

### Network Security

The Docker Compose setup includes:
- Isolated network (`github-sync-network`)
- Health checks for all services
- Proper service dependencies
- Non-root user execution where possible

## Monitoring and Maintenance

### Health Checks

- PostgreSQL: `pg_isready` command
- GitHub Sync Server: HTTP endpoint `/api/v1/status`
- Container restart policies: `unless-stopped`

### Log Management

View logs for troubleshooting:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f github-sync
docker-compose logs -f postgres

# Follow logs with timestamp
docker-compose logs -f -t
```

### Data Backup

Important data locations:
- PostgreSQL data: `postgres_data` volume
- Repository data: `repos_data` volume  
- SSH keys: `ssh_keys` volume

Backup commands:
```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U github_sync github_sync_db > backup.sql

# Backup volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Troubleshooting

### Common Issues

1. **Docker socket permission denied**
   ```bash
   # Check Docker socket permissions
   ls -la /var/run/docker.sock
   
   # Add user to docker group (requires restart)
   sudo usermod -aG docker $USER
   ```

2. **PostgreSQL SSL connection issues**
   - Ensure `?sslmode=disable` is in DATABASE_URL
   - Check PostgreSQL container logs: `docker-compose logs postgres`

3. **Repository clone failures**
   - Verify SSH keys are properly configured in Settings
   - Check network connectivity: `docker-compose exec github-sync ping github.com`
   - Review repository URL format (HTTPS vs SSH)

4. **Container restart failures**
   - Verify Docker socket access: `docker-compose exec github-sync docker ps`
   - Check container labels: `docker inspect <container_name>`
   - Review operation logs in the web interface

5. **Webhook not triggering**
   - Test webhook endpoint: `curl -X POST http://localhost:8200/webhook/test`
   - Check GitHub webhook delivery logs
   - Verify port 8200 is accessible from GitHub servers

### Performance Optimization

- Use PostgreSQL instead of SQLite for production
- Configure proper resource limits in docker-compose.yml
- Monitor disk usage for repository storage
- Regular cleanup of old operation logs

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# View startup logs
docker-compose logs -f github-sync
```

## Production Deployment with Reverse Proxy

### Nginx Configuration

```nginx
upstream github-sync {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Web Interface
    location / {
        proxy_pass http://github-sync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhook Endpoint (external port 8200 maps to same service)
    location /webhook {
        proxy_pass http://github-sync/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-sync
  namespace: github-sync
spec:
  replicas: 1
  selector:
    matchLabels:
      app: github-sync
  template:
    metadata:
      labels:
        app: github-sync
    spec:
      containers:
      - name: github-sync
        image: github-sync:latest
        env:
        - name: DATABASE_URL
          value: "postgresql://github_sync:$(POSTGRES_PASSWORD)@postgres:5432/github_sync_db?sslmode=disable"
        - name: MAIN_PATH
          value: "/app/repos"
        - name: LOG_LEVEL
          value: "INFO"
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: repos-storage
          mountPath: /app/repos
        - name: docker-socket
          mountPath: /var/run/docker.sock
      volumes:
      - name: repos-storage
        persistentVolumeClaim:
          claimName: repos-pvc
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock

---
apiVersion: v1
kind: Service
metadata:
  name: github-sync
  namespace: github-sync
spec:
  selector:
    app: github-sync
  ports:
  - name: web
    port: 5000
    targetPort: 5000
  - name: webhook
    port: 8200
    targetPort: 5000  # Both ports map to same container port
  type: LoadBalancer
```

This deployment guide covers all aspects of deploying the GitHub Sync Server using Docker, with proper port configuration, security considerations, and production-ready setup options.