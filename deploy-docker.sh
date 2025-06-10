#!/bin/bash

# GitHub Sync Server - Docker Deployment Script
# Sets up bind mount directories with proper permissions

set -e

echo "Setting up GitHub Sync Server for Docker deployment..."

# Create host directory for repositories
echo "Creating host-repos directory..."
mkdir -p ./host-repos
chmod 755 ./host-repos

# Set ownership to match Docker container user (UID 1000)
echo "Setting proper ownership for bind mount..."
sudo chown -R 1000:1000 ./host-repos

# Verify directory permissions
echo "Verifying directory setup..."
ls -la ./host-repos

echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo "Waiting for services to start..."
sleep 30

echo "Checking container health..."
docker-compose ps

echo "GitHub Sync Server is now running!"
echo "Web interface: http://localhost:5000"
echo "Webhook endpoint: http://localhost:8200"
echo "Repository storage: ./host-repos (bind mounted to /repos in container)"

echo ""
echo "To view logs: docker-compose logs -f github-sync"
echo "To stop: docker-compose down"
echo "To restart: docker-compose restart"