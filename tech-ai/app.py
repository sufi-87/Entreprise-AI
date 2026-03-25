import uvicorn
import os

if __name__ == "__main__":
    # In Databricks apps, we typically run via a command like 'uvicorn app:app --host 0.0.0.0 --port 8000'
    # or use a Procfile/start.sh. We provide app.py as a convenient wrapper for local dev.
    
    port = int(os.environ.get("PORT", 8000))
    # We reference backend.main:app
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
