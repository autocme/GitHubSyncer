#!/bin/bash

# GitHub Sync Server - Container Entrypoint
# Handles automatic directory setup and permissions for bind mounts

set -e

echo "Starting GitHub Sync Server..."

# Check if /repos is a bind mount and ensure proper permissions
if mountpoint -q /repos 2>/dev/null; then
    echo "Detected bind mount at /repos"
    
    # Check if we can write to the bind mount directory
    if [ ! -w /repos ]; then
        echo "Warning: /repos is not writable. Repository cloning may fail."
        echo "To fix this, ensure the host directory has proper permissions:"
        echo "  mkdir -p ./host-repos"
        echo "  sudo chown -R 1000:1000 ./host-repos"
        echo "  chmod 755 ./host-repos"
    else
        echo "Bind mount at /repos is properly configured"
    fi
else
    echo "Using container directory at /repos"
    # Ensure directory exists and has proper permissions
    mkdir -p /repos
    chmod 755 /repos
fi

# Verify Git is available
if ! command -v git &> /dev/null; then
    echo "Warning: Git is not available in container"
fi

# Verify Docker socket is accessible (for container management)
if [ -S /var/run/docker.sock ]; then
    echo "Docker socket is accessible"
else
    echo "Warning: Docker socket not found. Container restart functionality may not work."
fi

echo "Environment setup complete"
echo "Repository storage: /repos"
echo "Starting application..."

# Execute the main application
exec python main.py