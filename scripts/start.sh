#!/bin/sh
set -e
echo "Running migrations..."
alembic upgrade head
echo "Starting Gunicorn with Uvicorn workers..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 60 \
    --graceful-timeout 30
