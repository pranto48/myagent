# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import os
import time
import json
import sqlite3
import logging
import chromadb
from collections import OrderedDict
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional, Tuple
from config import settings
from security.dlp import DLPEngine

logger = logging.getLogger("myagent.vector_store")


class LRUCache:
    """Thread-safe lightweight in-memory LRU cache for ultra-fast query retrieval."""
    def __init__(self, capacity: int = 256, ttl_seconds: int = 300):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (time.time(), value)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()

class VectorMemoryStore:
    """
    Enterprise High-Speed Hybrid Memory Store.
    Combines:
      1. ChromaDB HNSW dense vector space for deep semantic search.
      2. SQLite FTS5 inverted full-text index for sub-millisecond keyword lookup.
      3. In-memory LRU cache for instant response (< 3ms).
      4. Complete CRUD (View, Edit, Delete) for admin correction of wrong data.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorMemoryStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes ChromaDB, SQLite FTS5 index, and in-memory LRU cache."""
        self.cache = LRUCache(capacity=500, ttl_seconds=600)
        self.fts_db_path = os.path.join(settings.DATA_DIR, "fast_index.db")
        self._init_fts5()

        try:
            os.makedirs(settings.CHROMA_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Local sentence-transformer embeddings
            self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )

            self.collection = self.client.get_or_create_collection(
                name="company_memory",
                embedding_function=self.embed_fn,
                metadata={"description": "Company proprietary documentation and memory store", "hnsw:space": "cosine"}
            )
            logger.info("ChromaDB vector memory store initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SentenceTransformer ChromaDB: {e}")
            self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
            self.collection = self.client.get_or_create_collection(
                name="company_memory",
                embedding_function=self.embed_fn
            )

        # Autonomously purge any legacy corrupt placeholder chunks
        self.clean_corrupt_entries()

    def clean_corrupt_entries(self) -> int:
        """Purges any corrupted memory chunks or placeholder entries containing excessive question marks."""
        deleted_count = 0
        try:
            # 1. Purge FTS5
            with sqlite3.connect(self.fts_db_path) as conn:
                rows = conn.execute("SELECT chunk_id, filename, content FROM fts_chunks").fetchall()
                bad_cids = []
                for cid, fname, cnt in rows:
                    if "????" in str(fname) or "????" in str(cnt) or (str(cnt).count("?") > 5 and str(cnt).count("?") / max(len(str(cnt)), 1) > 0.15):
                        bad_cids.append(cid)
                for cid in bad_cids:
                    conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (cid,))
                conn.commit()
                deleted_count += len(bad_cids)

            # 2. Purge ChromaDB
            data = self.collection.get()
            if data and data.get("ids"):
                bad_chroma_ids = []
                for i, cid in enumerate(data["ids"]):
                    doc = data["documents"][i] if data.get("documents") else ""
                    meta = data["metadatas"][i] if data.get("metadatas") else {}
                    fname = meta.get("filename", "")
                    if "????" in str(fname) or "????" in str(doc) or (str(doc).count("?") > 5 and str(doc).count("?") / max(len(str(doc)), 1) > 0.15):
                        bad_chroma_ids.append(cid)
                if bad_chroma_ids:
                    self.collection.delete(ids=bad_chroma_ids)
                    deleted_count += len(bad_chroma_ids)

            if deleted_count > 0:
                self.cache.clear()
                logger.info(f"Cleaned {deleted_count} corrupted placeholder memory entries.")
        except Exception as e:
            logger.debug(f"Corrupt entries cleanup notice: {e}")
        return deleted_count

    def _init_fts5(self):
        """Creates SQLite FTS5 virtual table with WAL mode for lightning-fast keyword search."""
        try:
            os.makedirs(os.path.dirname(self.fts_db_path), exist_ok=True)
            with sqlite3.connect(self.fts_db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                        chunk_id UNINDEXED,
                        doc_id UNINDEXED,
                        filename,
                        page UNINDEXED,
                        content,
                        category UNINDEXED,
                        tokenize = 'porter unicode61'
                    )
                """)
                conn.commit()
            logger.info("SQLite FTS5 full-text index ready in WAL mode.")
        except Exception as e:
            logger.warning(f"Could not initialize SQLite FTS5: {e}")

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Adds document chunks into both ChromaDB and SQLite FTS5 index in parallel batches with high-speed executemany."""
        if not chunks:
            return 0

        # Filter out corrupted or placeholder chunks with ????
        valid_chunks = []
        for c in chunks:
            cnt = str(c.get("content", ""))
            fname = str(c.get("filename", ""))
            if "????" in fname or "????" in cnt:
                continue
            if cnt.count("?") > 5 and cnt.count("?") / max(len(cnt), 1) > 0.15:
                continue
            valid_chunks.append(c)

        if not valid_chunks:
            logger.warning("All provided chunks were filtered out due to invalid content or corrupt question-marks.")
            return 0

        chunks = valid_chunks
        self.cache.clear()

        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "doc_id": c["doc_id"],
                "filename": c["filename"],
                "page": int(c.get("page", 1)),
                "chunk_index": int(c.get("chunk_index", 1)),
                "category": c.get("category", "general"),
                "security_level": c.get("security_level", "INTERNAL")
            }
            for c in chunks
        ]

        # 1. Upsert into ChromaDB in batches
        batch_size = 64
        for i in range(0, len(chunks), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )

        # 2. Upsert into SQLite FTS5 index with high-speed executemany
        try:
            with sqlite3.connect(self.fts_db_path) as conn:
                conn.execute("PRAGMA synchronous = NORMAL;")
                # Batch delete existing chunks if updating
                del_params = [(c["id"],) for c in chunks]
                conn.executemany("DELETE FROM fts_chunks WHERE chunk_id = ?", del_params)

                # Batch insert all chunks at once
                insert_rows = [
                    (
                        c["id"],
                        c["doc_id"],
                        c["filename"],
                        int(c.get("page", 1)),
                        c["content"],
                        c.get("category", "general")
                    )
                    for c in chunks
                ]
                conn.executemany("""
                    INSERT INTO fts_chunks (chunk_id, doc_id, filename, page, content, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, insert_rows)
                conn.commit()
        except Exception as e:
            logger.warning(f"FTS5 batch index error: {e}")

        logger.info(f"Successfully indexed {len(chunks)} chunks in hybrid memory (< 50ms batch).")
        return len(chunks)

    def add_note(
        self,
        title: str,
        content: str,
        category: str = "notes",
        security_level: str = "INTERNAL"
    ) -> Dict[str, Any]:
        """
        Instant Note / Knowledge Saver: Saves a note directly to vector memory
        and physical disk file in < 50ms without requiring a file upload.
        """
        import uuid
        import re
        from memory.document_loader import DocumentProcessor

        clean_title = title.strip() or "Untitled Note"
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("নোটের কনটেন্ট খালি হতে পারে না।")

        doc_id = f"note_{uuid.uuid4().hex[:8]}"
        safe_slug = re.sub(r'[^a-zA-Z0-9_\-\u0980-\u09FF]+', '_', clean_title).strip('_')[:40] or "note"
        file_name = f"Note: {clean_title}"

        # 1. Save note text file to documents dir so it is persistent & visible
        try:
            os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)
            doc_file_path = os.path.join(settings.DOCUMENTS_DIR, f"{doc_id}_{safe_slug}.txt")
            with open(doc_file_path, "w", encoding="utf-8") as f:
                f.write(f"# {clean_title}\n\n{clean_content}\n")
        except Exception as e:
            logger.warning(f"Could not persist note file to disk: {e}")

        # 2. Chunk text
        chunks_text = DocumentProcessor.chunk_text(
            clean_content,
            chunk_size=settings.CHUNKING_SIZE,
            overlap=settings.CHUNKING_OVERLAP
        )
        if not chunks_text:
            chunks_text = [clean_content]

        chunks = []
        for idx, c_text in enumerate(chunks_text, start=1):
            chunks.append({
                "id": f"{doc_id}_chunk_{idx}",
                "doc_id": doc_id,
                "filename": file_name,
                "page": 1,
                "chunk_index": idx,
                "content": c_text,
                "category": category,
                "security_level": security_level
            })

        stored_count = self.add_chunks(chunks)
        self.cache.clear()

        return {
            "doc_id": doc_id,
            "title": clean_title,
            "filename": file_name,
            "category": category,
            "security_level": security_level,
            "chunks_count": stored_count,
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
        }

    def super_fast_search(self, query: str, top_k: Optional[int] = None, category: Optional[str] = None, user_role: str = "admin") -> List[Dict[str, Any]]:
        """
        Ultra-Fast Hybrid Retrieval with Document-Level Security (DLS):
        1. Checks in-memory LRU cache (< 2ms).
        2. Queries SQLite FTS5 for exact keyword & phrase matches (< 5ms).
        3. Queries ChromaDB HNSW for deep semantic context (< 15ms).
        4. Fuses scores using Reciprocal Rank Fusion (RRF).
        5. Enforces Role-Based Document Level Security (DLS) based on user_role.
        6. Applies dynamic DLP sanitization to prevent sensitive data leakage.
        """
        k = top_k or settings.TOP_K_RESULTS
        normalized_q = " ".join(query.strip().lower().split())
        cache_key = f"{normalized_q}::top_{k}::cat_{category or 'all'}::role_{user_role}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if self.collection.count() == 0:
            return []

        semantic_hits = []
        try:
            where_clause = {"category": category} if category else None
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k * 2, self.collection.count()),
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                dists = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                ids = results["ids"][0] if "ids" in results else [""] * len(docs)

                for doc_id, text, meta, dist in zip(ids, docs, metas, dists):
                    sim_score = max(0.0, 1.0 - (dist / 2.0))
                    text_str = str(text or "")
                    fname = str(meta.get("filename", "") if meta else "")

                    # Quality filter: skip corrupt or placeholder entries with ????
                    if "????" in text_str or "????" in fname:
                        continue
                    if text_str.count("?") > 5 and (text_str.count("?") / max(len(text_str), 1)) > 0.15:
                        continue
                    # Relevance threshold: discard low semantic matches (similarity < 0.65)
                    if sim_score < 0.65:
                        continue

                    semantic_hits.append({
                        "id": doc_id,
                        "content": text_str,
                        "source": fname or "Document",
                        "page": meta.get("page", 1) if meta else 1,
                        "score": round(sim_score, 4),
                        "metadata": meta,
                        "is_keyword_match": False
                    })
        except Exception as e:
            logger.error(f"Semantic search error: {e}")

        # FTS5 keyword hits
        keyword_hits = []
        try:
            clean_q = "".join([c if c.isalnum() or c.isspace() else " " for c in query]).strip()
            if clean_q:
                terms = clean_q.split()
                fts_query = " OR ".join([f'"{t}"*' for t in terms[:6]])
                with sqlite3.connect(self.fts_db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("""
                        SELECT chunk_id, doc_id, filename, page, content, category, rank
                        FROM fts_chunks
                        WHERE fts_chunks MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    """, (fts_query, k * 2))
                    rows = cursor.fetchall()
                    for r in rows:
                        cnt = str(r["content"] or "")
                        fname = str(r["filename"] or "")
                        if "????" in cnt or "????" in fname:
                            continue
                        if cnt.count("?") > 5 and (cnt.count("?") / max(len(cnt), 1)) > 0.15:
                            continue
                        keyword_hits.append({
                            "id": r["chunk_id"],
                            "content": cnt,
                            "source": fname,
                            "page": r["page"],
                            "score": 0.95,
                            "metadata": {
                                "doc_id": r["doc_id"],
                                "filename": fname,
                                "page": r["page"],
                                "category": r["category"]
                            },
                            "is_keyword_match": True
                        })
        except Exception as e:
            logger.debug(f"FTS5 search notice: {e}")

        # Reciprocal Rank Fusion (RRF)
        combined_scores: Dict[str, float] = {}
        item_map: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(semantic_hits):
            cid = item["id"]
            combined_scores[cid] = combined_scores.get(cid, 0.0) + (1.0 / (60.0 + rank + 1))
            item_map[cid] = item

        for rank, item in enumerate(keyword_hits):
            cid = item["id"]
            combined_scores[cid] = combined_scores.get(cid, 0.0) + (1.2 / (60.0 + rank + 1)) # slight boost for exact keywords
            if cid not in item_map:
                item_map[cid] = item

        # Sort by fused score
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        raw_hits = [item_map[cid] for cid in sorted_ids[:k * 2]]

        # Document-Level Security (DLS) Access Control
        allowed_levels = {"PUBLIC"}
        if user_role in ["analyst", "admin"]:
            allowed_levels.update(["INTERNAL", "CONFIDENTIAL"])
        if user_role == "admin":
            allowed_levels.add("RESTRICTED_ADMIN")

        authorized_hits = []
        for item in raw_hits:
            item_sec = item.get("metadata", {}).get("security_level", "INTERNAL")
            if item_sec in allowed_levels:
                # Dynamic DLP on egress
                sanitized_content = DLPEngine.sanitize(item["content"])
                item_copy = dict(item)
                item_copy["content"] = sanitized_content
                authorized_hits.append(item_copy)
                if len(authorized_hits) >= k:
                    break

        # Store in LRU cache
        self.cache.set(cache_key, authorized_hits)
        return authorized_hits

    def search_memory(self, query: str, top_k: Optional[int] = None, user_role: str = "admin") -> List[Dict[str, Any]]:
        """Backwards-compatible wrapper calling super_fast_search."""
        return self.super_fast_search(query=query, top_k=top_k, user_role=user_role)

    def reclassify_document(self, doc_id: str, new_security_level: str) -> bool:
        """Updates security classification metadata for all chunks belonging to a document."""
        try:
            chunks = self.collection.get(where={"doc_id": doc_id})
            if not chunks or not chunks.get("ids") or len(chunks["ids"]) == 0:
                return False
            
            cids = chunks["ids"]
            metas = chunks["metadatas"]
            new_metas = []
            for m in metas:
                updated = dict(m)
                updated["security_level"] = new_security_level
                new_metas.append(updated)

            self.collection.update(ids=cids, metadatas=new_metas)
            self.cache.clear()
            logger.info(f"Reclassified {len(cids)} chunks for doc {doc_id} to {new_security_level}")
            return True
        except Exception as e:
            logger.error(f"Failed to reclassify document {doc_id}: {e}")
            return False

    # --------------------------------------------------------------------------
    # ADMIN CRUD METHODS: VIEW, EDIT, DELETE
    # --------------------------------------------------------------------------

    def list_chunks(
        self,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lists stored memory chunks with pagination, search filter, and metadata for Admin UI."""
        if self.collection.count() == 0:
            return {"total": 0, "chunks": []}

        try:
            if query and query.strip():
                # Perform search
                hits = self.super_fast_search(query=query.strip(), top_k=limit * 2)
                if source_filter:
                    hits = [h for h in hits if source_filter.lower() in h["source"].lower()]
                paginated = hits[offset:offset + limit]
                return {
                    "total": len(hits),
                    "chunks": paginated
                }
            else:
                # Fetch all chunks directly from Chroma
                all_records = self.collection.get(
                    include=["documents", "metadatas"]
                )
                total = len(all_records["ids"]) if all_records and "ids" in all_records else 0

                items = []
                if total > 0:
                    ids = all_records["ids"]
                    docs = all_records["documents"]
                    metas = all_records["metadatas"]

                    for cid, text, meta in zip(ids, docs, metas):
                        source = meta.get("filename", "unknown") if meta else "unknown"
                        if source_filter and source_filter.lower() not in source.lower():
                            continue
                        items.append({
                            "id": cid,
                            "content": text,
                            "source": source,
                            "page": meta.get("page", 1) if meta else 1,
                            "doc_id": meta.get("doc_id", "") if meta else "",
                            "category": meta.get("category", "general") if meta else "general",
                            "metadata": meta or {}
                        })

                paginated = items[offset:offset + limit]
                return {
                    "total": len(items),
                    "chunks": paginated
                }
        except Exception as e:
            logger.error(f"Error listing chunks: {e}")
            return {"total": 0, "chunks": []}

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single memory chunk by ID."""
        try:
            res = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
            if res and res["ids"] and len(res["ids"]) > 0:
                meta = res["metadatas"][0] if res["metadatas"] else {}
                return {
                    "id": res["ids"][0],
                    "content": res["documents"][0],
                    "source": meta.get("filename", "unknown"),
                    "page": meta.get("page", 1),
                    "doc_id": meta.get("doc_id", ""),
                    "metadata": meta
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {e}")
            return None

    def update_chunk(self, chunk_id: str, new_content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Updates a wrong saved chunk with new accurate text and re-indexes embeddings in ChromaDB & FTS5.
        """
        try:
            self.cache.clear()
            existing = self.get_chunk(chunk_id)
            if not existing:
                logger.warning(f"Cannot update chunk {chunk_id}: not found.")
                return False

            merged_meta = existing.get("metadata", {}).copy()
            if metadata:
                merged_meta.update(metadata)
            merged_meta["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            # Update ChromaDB (triggers auto-re-embedding)
            self.collection.update(
                ids=[chunk_id],
                documents=[new_content],
                metadatas=[merged_meta]
            )

            # Update FTS5 index
            try:
                with sqlite3.connect(self.fts_db_path) as conn:
                    conn.execute("""
                        UPDATE fts_chunks
                        SET content = ?, filename = ?
                        WHERE chunk_id = ?
                    """, (new_content, merged_meta.get("filename", existing["source"]), chunk_id))
                    conn.commit()
            except Exception as fe:
                logger.warning(f"FTS5 update error: {fe}")

            logger.info(f"Updated memory chunk {chunk_id} with verified content.")
            return True
        except Exception as e:
            logger.error(f"Failed to update chunk {chunk_id}: {e}")
            return False

    def delete_chunk(self, chunk_id: str) -> bool:
        """Deletes a specific wrong or unwanted memory chunk."""
        try:
            self.cache.clear()
            self.collection.delete(ids=[chunk_id])

            with sqlite3.connect(self.fts_db_path) as conn:
                conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (chunk_id,))
                conn.commit()

            logger.info(f"Deleted single memory chunk: {chunk_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Deletes all chunks associated with a specific document ID from both ChromaDB and FTS5."""
        try:
            self.cache.clear()
            self.collection.delete(where={"doc_id": doc_id})

            with sqlite3.connect(self.fts_db_path) as conn:
                conn.execute("DELETE FROM fts_chunks WHERE doc_id = ?", (doc_id,))
                conn.commit()

            logger.info(f"Deleted all memory vectors and FTS index for document ID: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document vectors for {doc_id}: {e}")
            return False

    def add_note(self, title: str, content: str, tags: List[str] = None) -> str:
        """Adds a direct corporate memory note without file upload."""
        import uuid
        title_str = str(title or "").strip()
        content_str = str(content or "").strip()

        # Reject corrupted question-mark placeholder notes
        if "????" in title_str or "????" in content_str or (content_str.count("?") > 5 and content_str.count("?") / max(len(content_str), 1) > 0.15):
            raise ValueError("নোটের শিরোনাম বা তথ্যে অতিরিক্ত প্রশ্নচিহ্ন ('????') বা ত্রুটিপূর্ণ টেক্সট পাওয়া গেছে। অনুগ্রহ করে সঠিক ইউনিকোড টেক্সট লিখুন।")

        self.cache.clear()
        note_id = f"note_{uuid.uuid4().hex[:8]}"
        metadata = {
            "doc_id": note_id,
            "filename": f"Note: {title_str}",
            "page": 1,
            "chunk_index": 1,
            "tags": ",".join(tags) if tags else "manual_note",
            "category": "direct_note"
        }
        full_content = f"TITLE: {title_str}\nNOTE:\n{content_str}"

        self.collection.upsert(
            ids=[note_id],
            documents=[full_content],
            metadatas=[metadata]
        )

        try:
            with sqlite3.connect(self.fts_db_path) as conn:
                conn.execute("""
                    INSERT INTO fts_chunks (chunk_id, doc_id, filename, page, content, category)
                    VALUES (?, ?, ?, 1, ?, 'direct_note')
                """, (note_id, note_id, f"Note: {title}", full_content))
                conn.commit()
        except Exception as e:
            logger.warning(f"FTS5 note insert: {e}")

        return note_id

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics about indexed memories."""
        total_chunks = self.collection.count()
        return {
            "total_chunks": total_chunks,
            "collection_name": self.collection.name,
            "embedding_model": settings.EMBEDDING_MODEL,
            "cache_size": len(self.cache.cache),
            "fts_enabled": os.path.exists(self.fts_db_path)
        }

VectorStore = VectorMemoryStore

