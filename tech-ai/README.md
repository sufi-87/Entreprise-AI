# Technical Manual RAG Assistant

A Databricks-deployable AI web app with a React dashboard UI and a Python Fastapi backend. It provides a Hybrid RAG experience over uploaded technical manuals using local FAISS and Databricks Model Serving.

## 🚀 Features
- **No Extra Dependencies**: Persists files and FAISS indices entirely locally (`./app_data`).
- **Hybrid Retrieval**: Employs Sentence Transformers (offline embedding) + BM25 keyword matching to gather context across PDF, DOCX, CSV/Excel, and TXT files.
- **Demo Fallback Mode**: If the Databricks token is missing, the application remains fully functional for uploading/indexing, only mocking the final LLM string.
- **Beautiful UI**: Modern dark-themed styling without heavy CSS frameworks, supporting analytics and complex knowledge scope querying.

## ⚠️ Configuration Before Deployment

1. Open `backend/config.py`
2. **Crucial Step**: Edit the `DATABRICKS_TOKEN` to your personal access token (or Service Principal token) if you intend to use the AI Endpoint.
3. Edit `LLAMA4_MAVERICKS_ENDPOINT` to point to the actual serving URL of your Databricks workspace model endpoint.

## 🔧 Local Development

1. **Start Backend**:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
2. **Start Frontend (in a separate terminal)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   > The backend is running on `http://localhost:8000` and the frontend Vite proxy directs `/api` traffic seamlessly.

## ☁️ Databricks Apps Deployment


### ✅ Important (Databricks Apps)
- Frontend is already pre-built in `frontend/dist`.
- `start.sh` does **not** run `npm install` / `npm run build` (so it works even if Node is not available in the runtime).

This folder is built to be dragged-and-dropped via the Databricks Apps UI without Unity Catalog volumes or Environment secrets.

### deployment steps
1. **Prepare the bundle**: Ensure you have edited `backend/config.py` with the static token since the requirement enforces 0 environment variables.
2. In your Databricks Workspace, navigate to **Compute > Apps** and **Create App**.
3. Select "Upload Code" and upload this entire folder.
4. Set the **Start Command** to run the start script:rtup script:
   ```bash
   bash start.sh
   ```
5. Click deploy. The App container will automatically build the Javascript frontend, install the Python libraries, and launch Uvicorn hosting both API routes and the UI statically.
