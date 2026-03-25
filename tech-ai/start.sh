#!/bin/bash
set -e

# Databricks Apps will execute this script.
# Frontend is already pre-built in frontend/dist (no npm required at runtime).

pip install -r requirements.txt

exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
