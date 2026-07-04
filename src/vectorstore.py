import os
import faiss
import numpy as np
import pickle
import logging
from typing import List, Any
from sentence_transformers import SentenceTransformer
from embedding import EmbeddingPipeline


logger = logging.getLogger(__name__)


class FaissVectorStore:
    def __init__(self, persist_dir: str = "faiss_store", embedding_model: str = "all-MiniLM-L6-v2", chunk_size: int = 1000, chunk_overlap: int = 200):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.index = None
        self.metadata = []
        self.embedding_model = embedding_model
        self.model = SentenceTransformer(embedding_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info("Loaded embedding model: %s", embedding_model)

    def build_from_documents(self, documents: List[Any]):
        logger.info("Building vector store from %s raw documents", len(documents))
        emb_pipe = EmbeddingPipeline(model_name=self.embedding_model, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = emb_pipe.chunk_documents(documents)
        if not chunks:
            raise ValueError("No chunks were created from the provided documents.")
        embeddings = emb_pipe.embed_chunks(chunks)
        metadatas = [
            {
                "text": chunk.page_content,
                "source": chunk.metadata.get("source") or chunk.metadata.get("file_path"),
                "page": chunk.metadata.get("page"),
            }
            for chunk in chunks
        ]
        self.add_embeddings(np.array(embeddings).astype('float32'), metadatas)
        self.save()
        logger.info("Vector store built and saved to %s", self.persist_dir)

    def add_embeddings(self, embeddings: np.ndarray, metadatas: List[Any] = None):
        if embeddings.size == 0:
            raise ValueError("Cannot add empty embeddings to FAISS.")
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)
        if metadatas:
            self.metadata.extend(metadatas)
        logger.info("Added %s vectors to FAISS index", embeddings.shape[0])

    def save(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        faiss.write_index(self.index, faiss_path)
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info("Saved FAISS index and metadata to %s", self.persist_dir)

    def load(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        self.index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        logger.info("Loaded FAISS index and metadata from %s", self.persist_dir)

    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        if self.index is None:
            raise ValueError("FAISS index is not loaded.")
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        result_count = min(top_k, self.index.ntotal)
        if result_count == 0:
            return []
        D, I = self.index.search(query_embedding, result_count)
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < 0:
                continue
            meta = self.metadata[idx] if idx < len(self.metadata) else None
            results.append({"index": int(idx), "distance": float(dist), "metadata": meta})
        return results

    def query(self, query_text: str, top_k: int = 5):
        logger.info("Querying vector store")
        query_emb = self.model.encode([query_text]).astype('float32')
        return self.search(query_emb, top_k=top_k)

# Example usage
if __name__ == "__main__":
    from src.data_loader import load_all_documents
    docs = load_all_documents("data")
    store = FaissVectorStore("faiss_store")
    store.build_from_documents(docs)
    store.load()
    print(store.query("What is attention mechanism?", top_k=3))
