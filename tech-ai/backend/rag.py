import os
import re
import requests
from typing import List, Dict
from backend.config import DATABRICKS_TOKEN, LLAMA4_MAVERICKS_ENDPOINT
from backend.indexer import get_indexer, ALLOWED_PLANTS, embedding_model, EMBEDDING_DIM
from backend.database import get_db_status, search_chunks_by_vector

MAX_CHUNKS = 6


def _safe_slug(value: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]+', '_', value or '')


def build_source_url(plant: str, filename: str) -> str:
    return f"/api/documents/source/{_safe_slug(plant)}/{_safe_slug(filename)}"


def hybrid_retrieve(query: str, plant_scope: str) -> List[Dict]:
    plants_to_search = ALLOWED_PLANTS if plant_scope == 'All plants' else [plant_scope]
    all_results = []
    query_embedding = None
    if embedding_model:
        query_embedding = embedding_model.encode([query], convert_to_numpy=True)
        import faiss
        faiss.normalize_L2(query_embedding)

    db_status = get_db_status()
    if db_status['enabled'] and query_embedding is not None:
        try:
            rows = search_chunks_by_vector(plants_to_search, query_embedding[0].tolist(), MAX_CHUNKS * 2)
            for row in rows:
                meta = dict(row)
                all_results.append({
                    'score': float(meta.get('score') or 0),
                    'text': meta['text'],
                    'filename': meta['filename'],
                    'plant': meta['plant'],
                    'chunk_id': meta['chunk_id'],
                    'page_num': meta.get('page_num'),
                    'source_type': meta.get('source_type', 'text'),
                    'source_url': build_source_url(meta['plant'], meta['filename'])
                })
        except Exception as e:
            print(f'Postgres vector retrieval failed: {e}')

    for p in plants_to_search:
        idx = get_indexer(p)
        if not idx.chunks_metadata:
            continue
        if query_embedding is not None and idx.index.ntotal > 0:
            distances, indices = idx.index.search(query_embedding, MAX_CHUNKS)
            for i, dist in zip(indices[0], distances[0]):
                if i != -1 and i < len(idx.chunks_metadata):
                    meta = idx.chunks_metadata[i]
                    all_results.append({
                        'score': 1 / (1 + float(dist)),
                        'text': meta['text'],
                        'filename': meta['filename'],
                        'plant': meta['plant'],
                        'chunk_id': meta['chunk_id'],
                        'page_num': meta.get('page_num'),
                        'source_type': meta.get('source_type', 'text'),
                        'source_url': build_source_url(meta['plant'], meta['filename'])
                    })
        if idx.bm25:
            tokenized_query = query.split(' ')
            bm_scores = idx.bm25.get_scores(tokenized_query)
            top_n = sorted(range(len(bm_scores)), key=lambda i: bm_scores[i], reverse=True)[:MAX_CHUNKS]
            for i in top_n:
                if bm_scores[i] > 0:
                    meta = idx.chunks_metadata[i]
                    all_results.append({
                        'score': float(bm_scores[i]) * 0.1,
                        'text': meta['text'],
                        'filename': meta['filename'],
                        'plant': meta['plant'],
                        'chunk_id': meta['chunk_id'],
                        'page_num': meta.get('page_num'),
                        'source_type': meta.get('source_type', 'text'),
                        'source_url': build_source_url(meta['plant'], meta['filename'])
                    })

    seen = set()
    unique_results = []
    for r in sorted(all_results, key=lambda x: x['score'], reverse=True):
        key = (r['plant'], r['chunk_id'])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
            if len(unique_results) >= MAX_CHUNKS:
                break
    return unique_results


def build_system_prompt(retrieved_chunks: List[Dict]) -> str:
    context_text = ''
    for c in retrieved_chunks:
        page = f" page {c['page_num']}" if c.get('page_num') else ''
        context_text += f"---\nSource: {c['filename']} (Plant: {c['plant']},{page}, Type: {c.get('source_type','text')})\n{c['text']}\n"

    return (
        'You are the Technical Manual RAG Assistant. '
        'Answer the user ONLY using the provided context below. '
        'If image OCR or engineering drawing OCR exists in the context, interpret labels, tags, notes, annotations and tabulated values carefully. '
        'Always cite the supporting source filename and plant in the answer. '
        "If the context does not contain sufficient info to answer, strictly say 'I do not have enough information to answer that question from the uploaded documents. Please try uploading more relevant manuals.' "
        'Do not invent or hallucinate answers. '\
        '\n\n=== CONTEXT ===\n'
        f'{context_text}\n'
        '===============\n'
    )


def ask_llama(messages: List[Dict]) -> str:
    if DATABRICKS_TOKEN == 'REPLACE_WITH_YOUR_TOKEN' or not DATABRICKS_TOKEN:
        return 'Model not configured. Please paste token in code constant `DATABRICKS_TOKEN` to use inference.'
    headers = {'Authorization': f'Bearer {DATABRICKS_TOKEN}', 'Content-Type': 'application/json'}
    data = {'messages': messages, 'max_tokens': 1024, 'temperature': 0.1}
    try:
        response = requests.post(LLAMA4_MAVERICKS_ENDPOINT, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get('choices', [{}])[0].get('message', {}).get('content', 'Error parsing response')
    except requests.exceptions.RequestException as e:
        print(f'Error querying model endpoint: {e}')
        return f'Error contacting Model Serving endpoint: {str(e)}'


def run_rag_chat(query: str, history: List[Dict], plant_scope: str) -> Dict:
    chunks = hybrid_retrieve(query, plant_scope)
    system_prompt = build_system_prompt(chunks)
    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in history:
        messages.append({'role': msg['role'], 'content': msg['content']})
    messages.append({'role': 'user', 'content': query})
    answer = ask_llama(messages)

    source_links = []
    seen = set()
    for c in chunks:
        key = (c['plant'], c['filename'])
        if key in seen:
            continue
        seen.add(key)
        source_links.append({
            'label': f"{c['filename']} ({c['plant']})",
            'filename': c['filename'],
            'plant': c['plant'],
            'url': c['source_url'],
            'page_num': c.get('page_num'),
            'source_type': c.get('source_type', 'text')
        })

    return {
        'answer': answer,
        'citations': [s['label'] for s in source_links],
        'source_links': source_links,
    }
