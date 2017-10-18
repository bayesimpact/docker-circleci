#!/bin/bash
# Stop the Docker containers that are still hanging because of 'run sleep 1000'.

# Find the files containings the container IDs, and then kill the sleep process on them.
docker ps --format '{{.Names}}' | xargs -n 1 -I container-id docker exec -t container-id /bin/sh -c 'if [ -n "$(pidof sleep)" ]; then kill $(pidof sleep) || echo "Could not kill sleep pid $(pidof sleep)"; fi' || echo 'Unknown error'
