import os

# Centralized configuration

# Dummy token usage strategy
# Replace this token with the real PAT or environment variable token when deploying if allowed.
# For Databricks Apps, if we must not use secrets/env vars, we hardcode here.
LLAMA4_MAVERICKS_ENDPOINT = "https://dbc-b87572be-f8e3.cloud.databricks.com/serving-endpoints/databricks-llama-4-maverick/invocations"
# REPLACE ME BEFORE DEPLOY
DATABRICKS_TOKEN = "dapi0dc683099c4577e510a2421951394fa6"

# Storage Configuration
APP_DATA_DIR = os.path.join(os.getcwd(), "app_data")
DOCS_DIR = os.path.join(APP_DATA_DIR, "docs")
INDEX_DIR = os.path.join(APP_DATA_DIR, "index")
LOG_FILE = os.path.join(APP_DATA_DIR, "logs.jsonl")

# Constants
ALLOWED_PLANTS = ["JEP", "GF1", "M5"]

# Function to ensure directories exist
def init_directories():
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    for plant in ALLOWED_PLANTS:
        os.makedirs(os.path.join(DOCS_DIR, plant), exist_ok=True)
        os.makedirs(os.path.join(INDEX_DIR, plant), exist_ok=True)

# Call to init on load
init_directories()
