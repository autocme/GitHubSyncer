# GitHub Sync Server

A robust FastAPI-based webhook server for automatic GitHub repository synchronization and Docker container management.

## Features

- **GitHub Webhook Integration**: Automatic repository updates on push events
- **Docker Container Management**: Intelligent restart of containers after code updates
- **Multi-Repository Support**: Handle multiple repositories with individual configurations
- **SSH Key Management**: Secure access to private repositories
- **Web Dashboard**: Comprehensive management interface
- **API Access**: RESTful API with authentication
- **PostgreSQL/SQLite Support**: Flexible database options
- **Container Discovery**: Automatic detection of Docker containers
- **Operation Logging**: Detailed logs of all operations
- **Health Monitoring**: Built-in health checks and status monitoring

## Quick Start

### Docker Deployment (Recommended)

1. **Clone the repository:**
```bash
git clone git@github.com:autocme/GitHubSyncer.git>
cd github-sync-server
```

2. **Deploy with Docker Compose:**
```bash
docker-compose up -d
```

3. **Access the application:**
- Web Interface: http://localhost:5000
- Webhook Endpoint: http://localhost:8200/webhook

### Portainer Deployment

Use the included `portainer-template.json` for one-click deployment in Portainer's Custom Templates section.

## Configuration

### Port Configuration

The application uses a single FastAPI server with dual port mapping:
- **Internal Port**: 5000 (single service)
- **External Ports**: 
  - 5000 → Web interface access
  - 8200 → Webhook endpoint (maps to same service)

This design provides flexible access while maintaining a simple architecture.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | SQLite |
| `MAIN_PATH` | Repository storage path | `/app/repos` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `POSTGRES_*` | PostgreSQL connection details | - |

### GitHub Webhook Setup

1. Go to your repository Settings → Webhooks
2. Add webhook URL: `http://your-server:8200/webhook`
3. Content type: `application/json`
4. Events: Push events (or all events)
5. Active: ✓

### Container Labels and Auto-Restart

The system automatically restarts Docker containers after repository updates using container labels. Multiple label formats are supported for flexibility:

**Label Format:**
```yaml
restart-after: "repository-name"
```

**Docker Compose Example:**
```yaml
version: '3.8'
services:
  web-app:
    image: my-web-app:latest
    labels:
      restart-after: "my-web-repo"
    ports:
      - "3000:3000"
  
  api-service:
    image: my-api:latest
    labels:
      restart-after: "my-backend-api"
    ports:
      - "8080:8080"
```

**Docker Run Examples:**
```bash
# Simple container with restart label
docker run -d \
  --name my-app \
  --label "restart-after=my-repo-name" \
  my-image:latest

# Multiple labels (only restart-after is used)
docker run -d \
  --name api-server \
  --label "restart-after=backend-repo" \
  --label "environment=production" \
  api:latest
```

**How It Works:**
1. **Add Repository**: Create repository "my-repo-name" in the web interface
2. **Label Containers**: Add `restart-after: "my-repo-name"` label to containers
3. **Automatic Discovery**: System discovers labeled containers when you click "Discover Containers"
4. **Webhook Processing**: When GitHub webhook triggers for "my-repo-name":
   - Repository code is automatically pulled
   - All containers with matching labels are restarted in sequence
   - Success/failure status is logged for monitoring

**Container Discovery Process:**
- Navigate to **Containers** section in web interface
- Click **"Discover Containers"** button
- System scans all Docker containers and parses their labels
- Containers with restart labels are automatically tracked
- View which containers will restart for each repository

## Initial Setup

1. **First Access**: Navigate to http://localhost:5000
2. **Setup Wizard**: Complete the initial configuration
3. **Create Admin**: Set up administrator credentials
4. **Configure Repositories**: Add your Git repositories
5. **Setup SSH Keys**: Configure authentication for private repos
6. **Test Webhooks**: Verify GitHub integration

## API Documentation

### Authentication

The API supports multiple authentication methods:
- Session-based (web interface)
- API key authentication
- JWT tokens

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/repositories` | GET/POST | Repository management |
| `/api/v1/containers` | GET | Container listing |
| `/api/v1/logs` | GET | Operation logs |
| `/api/v1/status` | GET | System status |
| `/webhook/github` | POST | GitHub webhook |

## Docker Configuration

### Development

```yaml
version: '3.8'
services:
  github-sync:
    build: .
    ports:
      - "5000:5000"
      - "8200:5000"
    volumes:
      - ./repos:/app/repos
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DATABASE_URL=sqlite:///app/data/app.db
```

### Production

```yaml
version: '3.8'
services:
  github-sync:
    build: .
    ports:
      - "5000:5000"
      - "8200:5000"
    volumes:
      - repos_data:/app/repos
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db?sslmode=disable
    depends_on:
      postgres:
        condition: service_healthy
    
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=github_sync_db
      - POSTGRES_USER=github_sync
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U github_sync"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Security

### Production Checklist

- [ ] Change default PostgreSQL passwords
- [ ] Use HTTPS with SSL certificates
- [ ] Configure webhook secrets
- [ ] Set up proper firewall rules
- [ ] Use environment files for secrets
- [ ] Regular security updates
- [ ] Limit Docker socket access

### Network Security

- Isolated Docker networks
- Health checks for all services
- Service dependencies properly configured
- Non-root user execution where possible

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:5000/api/v1/status

# Database health (PostgreSQL)
docker exec postgres pg_isready -U github_sync

# Container status
docker-compose ps
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f github-sync

# Application logs in web interface
# Navigate to Logs section in dashboard
```

## Troubleshooting

### Common Issues

1. **Port 8200 not accessible**
   - This is expected when not running in Docker
   - The dual port mapping only works with Docker deployment

2. **Docker socket permission denied**
   - Add user to docker group: `sudo usermod -aG docker $USER`
   - Restart the session

3. **Database connection issues**
   - Check DATABASE_URL format
   - Verify PostgreSQL container is running
   - Ensure `?sslmode=disable` for PostgreSQL

4. **Repository clone failures**
   - Configure SSH keys in Settings
   - Check repository URL format
   - Verify network connectivity

5. **Webhook not triggering**
   - Check GitHub webhook delivery logs
   - Verify external access to port 8200
   - Test with curl: `curl -X POST http://your-server:8200/webhook/test`

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./app.db
export MAIN_PATH=./repos

# Run development server
python main.py
```

### Testing

```bash
# Run deployment tests
python test_deployment.py

# Test webhook endpoint
curl -X POST http://localhost:5000/webhook/github \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main","repository":{"name":"test"}}'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in the web interface
3. Create an issue on GitHub with detailed information
