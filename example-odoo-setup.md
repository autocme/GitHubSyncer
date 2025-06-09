# GitHub Sync Server - Odoo Integration Example

## Your Docker Compose Configuration ✓

```yaml
version: '3.8'
services:
  odoo:
    image: odoo:17
    ports:
      - "8069:8069"
    depends_on:
      - db
    volumes:
      - odoo_data:/var/lib/odoo
      - odoo_custom_addons:/mnt/extra-addons
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_DB=postgres
      - PGHOST=db
    labels:
      - restart-after=server-backend  # ✓ Perfect format!

  db:
    image: postgres:12
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_DB=postgres
    volumes:
      - odoo_db_data:/var/lib/postgresql/data
    # No restart label = database stays running during updates

volumes:
  odoo_data:
  odoo_custom_addons:
  odoo_db_data:
```

## How It Works

1. **Repository Name**: Create a repository named `server-backend`
2. **Label Matching**: The `restart-after=server-backend` label links your Odoo container to this repository
3. **Selective Restart**: Only Odoo restarts when you push code; PostgreSQL database continues running
4. **Zero Downtime**: Database connections persist while application updates

## Setup Steps

1. Add repository "server-backend" in the GitHub Sync Server web interface
2. Deploy your Docker Compose stack
3. Configure GitHub webhook to point to your server
4. Push code changes to trigger automatic Odoo container restarts

## Benefits

- **Smart Targeting**: Only restarts containers that need updates
- **Database Safety**: PostgreSQL remains untouched during deployments
- **Quick Recovery**: Odoo restarts quickly with persistent data volumes
- **Full Logging**: All operations tracked in the web interface

Your configuration is production-ready!