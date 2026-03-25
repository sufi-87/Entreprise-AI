from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import time

from backend.config import APP_DATA_DIR, DOCS_DIR
from backend.logger import append_log, get_logs
from backend.ingestion import save_uploaded_file, delete_document, get_documents, process_file_into_chunks, SUPPORTED_EXTENSIONS
from backend.indexer import index_document_chunks, remove_document_from_index, get_stats_by_plant, get_documents_count, get_chunks_count
from backend.rag import run_rag_chat
from backend.database import get_db_status, init_db

app = FastAPI(title='Technical Manual RAG Assistant')
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/api/health')
def health_check():
    return {'status': 'ok', 'database': get_db_status()}

@app.get('/api/stats')
def get_stats():
    plant_stats = get_stats_by_plant()
    logs = get_logs(50)
    return {
        'total_documents': get_documents_count(),
        'total_chunks': get_chunks_count(),
        'total_queries': len([l for l in logs if l['action'] == 'chat']),
        'recent_queries': [l for l in logs if l['action'] == 'chat'][:10],
        'top_plants': plant_stats,
        'logs': logs,
        'database': get_db_status(),
    }

@app.post('/api/documents/upload')
async def upload_document(background_tasks: BackgroundTasks, plant: str = Form(...), file: UploadFile = File(...)):
    start_time = time.time()
    if not file.filename:
        raise HTTPException(status_code=400, detail='No filename provided')
    ext = file.filename.lower().split('.')[-1]
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Unsupported file type .{ext}. Supported: {", ".join(sorted(SUPPORTED_EXTENSIONS))}')
    try:
        file_path = save_uploaded_file(file, plant, file.filename)
        chunks = process_file_into_chunks(file_path, plant, file.filename)
        if not chunks:
            raise ValueError('No readable content extracted from file. Please check file quality or OCR availability.')
        index_document_chunks(plant, chunks)
        latency = int((time.time() - start_time) * 1000)
        append_log(plant, file.filename, 'upload', 'success', latency)
        return {'status': 'success', 'message': f'{file.filename} uploaded and indexed successfully.', 'chunks': len(chunks)}
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        append_log(plant, file.filename, 'upload', f'failed: {str(e)}', latency)
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/documents')
def list_documents(plant: str = None):
    return get_documents(plant)

@app.get('/api/documents/source/{plant}/{filename}')
def open_document_source(plant: str, filename: str):
    file_path = os.path.join(DOCS_DIR, plant, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Source document not found')
    return FileResponse(file_path, filename=filename)

@app.delete('/api/documents/{plant}/{filename}')
def delete_doc(plant: str, filename: str):
    start_time = time.time()
    try:
        deleted = delete_document(plant, filename)
        if not deleted:
            raise HTTPException(status_code=404, detail='File not found')
        remove_document_from_index(plant, filename)
        latency = int((time.time() - start_time) * 1000)
        append_log(plant, filename, 'delete', 'success', latency)
        return {'status': 'success', 'message': 'Document deleted'}
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        append_log(plant, filename, 'delete', f'failed: {str(e)}', latency)
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    query: str
    history: list = []
    plant_scope: str = 'All plants'

@app.post('/api/chat')
def chat_endpoint(req: ChatRequest):
    start_time = time.time()
    try:
        result = run_rag_chat(req.query, req.history, req.plant_scope)
        latency = int((time.time() - start_time) * 1000)
        append_log(req.plant_scope, 'chat', 'chat', 'success', latency)
        return result
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        append_log(req.plant_scope, 'chat', 'chat', f'failed: {str(e)}', latency)
        raise HTTPException(status_code=500, detail=str(e))

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if os.path.exists(FRONTEND_DIR):
    app.mount('/assets', StaticFiles(directory=os.path.join(FRONTEND_DIR, 'assets')), name='assets')

    @app.get('/{full_path:path}')
    async def serve_frontend(full_path: str):
        if full_path.startswith('api/'):
            return JSONResponse(status_code=404, content={'message': 'API route not found'})
        path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))
