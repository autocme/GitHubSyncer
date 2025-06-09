# GitHub Sync Webhook Service

A robust FastAPI-based GitHub webhook server designed for secure and intelligent repository management with advanced deployment capabilities.

## Features

- **FastAPI Backend** with enhanced security protocols
- **Intelligent Docker Container Management** - automatically restart containers based on labels
- **Comprehensive GitHub Webhook Integration** - listen for push events and auto-sync
- **Advanced Error Handling** and logging mechanisms
- **Responsive Web Interface** with dynamic user experience
- **Multi-Repository Support** - manage multiple public/private repositories
- **SSH Key Management** for private repository access
- **API Key Authentication** for secure API access
- **Comprehensive Logging** with pagination and filtering
- **Docker Deployment Ready** with Portainer Custom Templates support

## Quick Start with Docker

### Using Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/ahmedkhamis12/GitHub-Sync-Webhook-Service.git
cd GitHub-Sync-Webhook-Service
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access the web interface at `http://localhost:5000`

### Using Portainer Custom Templates

1. Add the template URL to your Portainer instance:
   - Go to **App Templates** → **Custom Templates**
   - Add template URL: `https://raw.githubusercontent.com/ahmedkhamis12/GitHub-Sync-Webhook-Service/main/portainer-template.json`

2. Deploy the **GitHub Sync Webhook Service** template

3. Configure environment variables as needed

## Manual Installation

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Docker (for container management)
- Git

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/ahmedkhamis12/GitHub-Sync-Webhook-Service.git
cd GitHub-Sync-Webhook-Service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/github_sync"
export MAIN_PATH="/path/to/repositories"
```

4. Run the application:
```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `MAIN_PATH` | Path for repository storage | `/tmp/repos` |
| `LOG_LEVEL` | Logging level | `INFO` |

### GitHub Webhook Setup

1. In your GitHub repository settings, go to **Webhooks**
2. Add webhook URL: `http://your-server:8200/api/v1/webhook/github`
3. Select **Push events**
4. Set content type to `application/json`

## Docker Container Labels

To automatically restart containers when repositories are updated, add this label:

```yaml
labels:
  - "restart_after_pull=repository-name"
```

Example Docker Compose service:
```yaml
services:
  my-app:
    image: my-app:latest
    labels:
      - "restart_after_pull=my-repository"
```

## API Endpoints

### Web Interface
- `GET /` - Dashboard
- `GET /repositories` - Repository management
- `GET /containers` - Container management
- `GET /logs` - Operation logs
- `GET /settings` - System settings

### API Endpoints
- `POST /api/v1/webhook/github` - GitHub webhook endpoint
- `GET /api/v1/repositories` - List repositories
- `POST /api/v1/repositories` - Create repository
- `POST /api/v1/repositories/{id}/sync` - Manual sync
- `GET /api/v1/containers` - List containers
- `POST /api/v1/containers/discover` - Discover containers
- `GET /api/v1/logs` - Get operation logs
- `DELETE /api/v1/logs` - Clear all logs

## Security Features

- **Session-based Authentication** with secure cookies
- **API Key Authentication** for programmatic access
- **Rate Limiting** on login attempts
- **IP-based Security** tracking
- **SSH Key Management** for private repositories
- **Input Validation** and sanitization

## Logging and Monitoring

- **Comprehensive Operation Logs** with timestamps
- **Pagination Support** for large log sets
- **Log Filtering** by operation type and status
- **Real-time Status Updates** for repositories and containers
- **Health Check Endpoints** for monitoring

## Docker Deployment

The project includes production-ready Docker configuration:

- **Dockerfile** - Multi-stage build with security best practices
- **docker-compose.yml** - Complete stack with PostgreSQL
- **portainer-template.json** - Portainer Custom Templates support

### Security Considerations

- Non-root user execution
- Minimal attack surface
- Health checks included
- Volume mounts for data persistence
- Network isolation

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
- Create an issue on GitHub
- Check the logs at `/logs` page
- Review the system status at `/dashboard`