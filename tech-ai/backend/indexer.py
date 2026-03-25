import os
import json
import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from backend.config import INDEX_DIR, ALLOWED_PLANTS
from backend.database import get_db_status, fetch_chunks_for_plant, insert_chunks, delete_document_record, search_chunks_by_vector, count_documents, count_chunks, stats_by_plant
from typing import List, Dict

try:
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    EMBEDDING_DIM = embedding_model.get_sentence_embedding_dimension()
except Exception as e:
    print(f"Warning: Failed to load sentence-transformers. App will run in limited mode. {e}")
    embedding_model = None
    EMBEDDING_DIM = 384


class PlantIndexer:
    def __init__(self, plant: str):
        self.plant = plant
        self.index_path = os.path.join(INDEX_DIR, plant)
        self.faiss_path = os.path.join(self.index_path, 'faiss.index')
        self.metadata_path = os.path.join(self.index_path, 'metadata.json')
        self.chunks_metadata = []
        self.bm25 = None
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        self._load()

    def _load(self):
        db_status = get_db_status()
        if db_status['enabled']:
            try:
                rows = fetch_chunks_for_plant(self.plant)
                self.chunks_metadata = [dict(r) for r in rows]
                self._rebuild_bm25()
                return
            except Exception as e:
                print(f'DB chunk load failed for {self.plant}: {e}')

        if os.path.exists(self.faiss_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.faiss_path)
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.chunks_metadata = json.load(f)
            self._rebuild_bm25()

    def refresh(self):
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        self.chunks_metadata = []
        self._load()
        if get_db_status()['enabled']:
            return
        if self.chunks_metadata and embedding_model:
            texts = [c['text'] for c in self.chunks_metadata]
            embeddings = embedding_model.encode(texts, convert_to_numpy=True)
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)

    def _rebuild_bm25(self):
        if self.chunks_metadata:
            tokenized_corpus = [str(chunk['text']).split(' ') for chunk in self.chunks_metadata]
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None

    def save_local(self):
        os.makedirs(self.index_path, exist_ok=True)
        faiss.write_index(self.index, self.faiss_path)
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks_metadata, f)

    def index_chunks(self, chunks: List[Dict]):
        if not chunks:
            return
        texts = [c['text'] for c in chunks]
        embeddings = None
        if embedding_model:
            embeddings = embedding_model.encode(texts, convert_to_numpy=True)
            faiss.normalize_L2(embeddings)

        db_status = get_db_status()
        if db_status['enabled']:
            rows = []
            for i, c in enumerate(chunks):
                row = dict(c)
                row['embedding'] = embeddings[i].tolist() if embeddings is not None else None
                rows.append(row)
            insert_chunks(rows)
            self.refresh()
            return

        if embeddings is not None:
            self.index.add(embeddings)
        self.chunks_metadata.extend(chunks)
        self._rebuild_bm25()
        self.save_local()

    def remove_document(self, filename: str):
        db_status = get_db_status()
        if db_status['enabled']:
            delete_document_record(self.plant, filename)
            self.refresh()
            return

        filtered_chunks = [c for c in self.chunks_metadata if c['filename'] != filename]
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        self.chunks_metadata = []
        if filtered_chunks:
            self.index_chunks(filtered_chunks)
        else:
            self._rebuild_bm25()
            self.save_local()


indexers = {}


def get_indexer(plant: str) -> PlantIndexer:
    if plant not in indexers:
        indexers[plant] = PlantIndexer(plant)
    return indexers[plant]


def index_document_chunks(plant: str, chunks: List[Dict]):
    get_indexer(plant).index_chunks(chunks)


def remove_document_from_index(plant: str, filename: str):
    get_indexer(plant).remove_document(filename)


def get_documents_count() -> int:
    if get_db_status()['enabled']:
        return count_documents()
    total_docs = set()
    for p in ALLOWED_PLANTS:
        idx = get_indexer(p)
        for m in idx.chunks_metadata:
            total_docs.add(f"{p}_{m['filename']}")
    return len(total_docs)


def get_chunks_count() -> int:
    if get_db_status()['enabled']:
        return count_chunks()
    return sum(len(get_indexer(p).chunks_metadata) for p in ALLOWED_PLANTS)


def get_stats_by_plant() -> Dict[str, int]:
    if get_db_status()['enabled']:
        stats = stats_by_plant()
        for p in ALLOWED_PLANTS:
            stats.setdefault(p, 0)
        return stats
    stats = {}
    for p in ALLOWED_PLANTS:
        idx = get_indexer(p)
        docs = set(m['filename'] for m in idx.chunks_metadata)
        stats[p] = len(docs)
    return stats
