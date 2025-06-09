# Deployment Guide

## Docker Deployment with Portainer

### Option 1: Portainer Custom Templates (Recommended)

1. **Add Template to Portainer:**
   - Navigate to **App Templates** → **Custom Templates**
   - Add template URL: `https://raw.githubusercontent.com/ahmedkhamis12/GitHub-Sync-Webhook-Service/main/portainer-template.json`
   - Click **Add custom template**

2. **Deploy the Stack:**
   - Select **GitHub Sync Webhook Service** from templates
   - Configure environment variables:
     - `POSTGRES_PASSWORD`: Strong database password
     - `GITHUB_SYNC_PORT`: Web interface port (default: 5000)
     - `WEBHOOK_PORT`: GitHub webhook port (default: 8200)
   - Deploy the stack

3. **Access the Application:**
   - Web Interface: `http://your-server:5000`
   - Webhook Endpoint: `http://your-server:8200/api/v1/webhook/github`

### Option 2: Manual Docker Compose

1. **Clone Repository:**
```bash
git clone https://github.com/ahmedkhamis12/GitHub-Sync-Webhook-Service.git
cd GitHub-Sync-Webhook-Service
```

2. **Configure Environment:**
```bash
cp docker-compose.yml docker-compose.local.yml
# Edit environment variables in docker-compose.local.yml
```

3. **Deploy:**
```bash
docker-compose -f docker-compose.local.yml up -d
```

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: github-sync

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: github-sync-config
  namespace: github-sync
data:
  MAIN_PATH: "/app/repos"
  LOG_LEVEL: "INFO"
```

### PostgreSQL Database

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: github-sync
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: "github_sync_db"
        - name: POSTGRES_USER
          value: "github_sync"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: github-sync
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### GitHub Sync Application

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
          value: "postgresql://github_sync:$(POSTGRES_PASSWORD)@postgres:5432/github_sync_db"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        envFrom:
        - configMapRef:
            name: github-sync-config
        ports:
        - containerPort: 5000
        - containerPort: 8200
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
    targetPort: 8200
  type: LoadBalancer
```

## Production Configuration

### Security Considerations

1. **Database Security:**
   - Use strong passwords
   - Enable SSL connections
   - Regular backups
   - Network isolation

2. **Application Security:**
   - Change default admin credentials
   - Use HTTPS with reverse proxy
   - API key rotation
   - Rate limiting

3. **Container Security:**
   - Non-root user execution
   - Read-only root filesystem
   - Resource limits
   - Security scanning

### Reverse Proxy Configuration

#### Nginx Configuration

```nginx
upstream github-sync-web {
    server 127.0.0.1:5000;
}

upstream github-sync-webhook {
    server 127.0.0.1:8200;
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
        proxy_pass http://github-sync-web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhook Endpoint
    location /webhook {
        proxy_pass http://github-sync-webhook/api/v1/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Traefik Configuration

```yaml
version: '3.8'
services:
  github-sync:
    # ... existing configuration
    labels:
      - "traefik.enable=true"
      # Web Interface
      - "traefik.http.routers.github-sync-web.rule=Host(`your-domain.com`)"
      - "traefik.http.routers.github-sync-web.tls=true"
      - "traefik.http.routers.github-sync-web.tls.certresolver=letsencrypt"
      - "traefik.http.services.github-sync-web.loadbalancer.server.port=5000"
      # Webhook
      - "traefik.http.routers.github-sync-webhook.rule=Host(`your-domain.com`) && PathPrefix(`/webhook`)"
      - "traefik.http.routers.github-sync-webhook.tls=true"
      - "traefik.http.services.github-sync-webhook.loadbalancer.server.port=8200"
```

### Monitoring and Logging

#### Prometheus Metrics

Add to docker-compose.yml:

```yaml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
```

#### Log Aggregation

```yaml
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker exec github-sync-postgres pg_dump -U github_sync github_sync_db > backup.sql

# Restore backup
docker exec -i github-sync-postgres psql -U github_sync github_sync_db < backup.sql
```

### Automated Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/github-sync"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
docker exec github-sync-postgres pg_dump -U github_sync github_sync_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Repository backup
tar -czf $BACKUP_DIR/repos_$DATE.tar.gz /opt/github-sync/repos

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed:**
   - Check DATABASE_URL environment variable
   - Verify PostgreSQL container is running
   - Check network connectivity

2. **Docker Socket Permission Denied:**
   - Ensure user has docker group permissions
   - Check socket mount path: `/var/run/docker.sock`

3. **Repository Clone Failures:**
   - Verify SSH keys for private repositories
   - Check network connectivity to Git repositories
   - Ensure sufficient disk space

4. **Webhook Not Receiving Events:**
   - Verify GitHub webhook URL configuration
   - Check firewall rules for port 8200
   - Test webhook endpoint manually

### Health Checks

```bash
# Application health
curl -f http://localhost:5000/api/v1/status

# Database health
docker exec github-sync-postgres pg_isready -U github_sync

# Container status
docker ps | grep github-sync
```

### Log Analysis

```bash
# Application logs
docker logs github-sync-server

# Database logs
docker logs github-sync-postgres

# Follow live logs
docker logs -f github-sync-server
```