# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.0.0
import os
import json
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger("myagent.vector_store")

class VectorMemoryStore:
    """Manages persistent company vector memory using ChromaDB."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorMemoryStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes ChromaDB client and collection."""
        try:
            os.makedirs(settings.CHROMA_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Use local SentenceTransformer embeddings
            self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )

            self.collection = self.client.get_or_create_collection(
                name="company_memory",
                embedding_function=self.embed_fn,
                metadata={"description": "Company proprietary documentation and memory store"}
            )
            logger.info("ChromaDB vector memory store initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            # Fallback to default embedding function if sentence-transformer fails
            self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
            self.collection = self.client.get_or_create_collection(
                name="company_memory",
                embedding_function=self.embed_fn
            )

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Adds a list of document chunks to the persistent vector store."""
        if not chunks:
            return 0

        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "doc_id": c["doc_id"],
                "filename": c["filename"],
                "page": int(c.get("page", 1)),
                "chunk_index": int(c.get("chunk_index", 1))
            }
            for c in chunks
        ]

        # Ingest in batches of 100
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )

        logger.info(f"Successfully upserted {len(chunks)} chunks into vector memory.")
        return len(chunks)

    def search_memory(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Performs semantic similarity search against indexed company documents."""
        k = top_k or settings.TOP_K_RESULTS
        if self.collection.count() == 0:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            hits = []
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                dists = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                ids = results["ids"][0] if "ids" in results else [""] * len(docs)

                for doc_id, text, meta, dist in zip(ids, docs, metas, dists):
                    # Chroma returns cosine distance (0 is identical, higher is further)
                    # Convert to similarity score roughly 0 to 1
                    sim_score = max(0.0, 1.0 - (dist / 2.0))
                    hits.append({
                        "id": doc_id,
                        "content": text,
                        "source": meta.get("filename", "unknown"),
                        "page": meta.get("page", 1),
                        "score": round(sim_score, 4),
                        "metadata": meta
                    })

            return hits
        except Exception as e:
            logger.error(f"Error querying vector memory: {e}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Deletes all chunks associated with a specific document ID."""
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted all memory vectors for document ID: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document vectors for {doc_id}: {e}")
            return False

    def add_note(self, title: str, content: str, tags: List[str] = None) -> str:
        """Adds a direct corporate memory note without file upload."""
        import uuid
        note_id = f"note_{uuid.uuid4().hex[:8]}"
        metadata = {
            "doc_id": note_id,
            "filename": f"Note: {title}",
            "page": 1,
            "chunk_index": 1,
            "tags": ",".join(tags) if tags else "manual_note"
        }
        self.collection.upsert(
            ids=[note_id],
            documents=[f"TITLE: {title}\nNOTE:\n{content}"],
            metadatas=[metadata]
        )
        return note_id

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics about indexed memories."""
        total_chunks = self.collection.count()
        return {
            "total_chunks": total_chunks,
            "collection_name": self.collection.name,
            "embedding_model": settings.EMBEDDING_MODEL
        }
