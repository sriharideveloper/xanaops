"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — VECTOR DATABASE ENGINE                        ║
╚══════════════════════════════════════════════════════════════╝
"""

import hashlib
import time
import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
from config import DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL


@st.cache_resource(show_spinner=False)
def load_db():
    """Load ChromaDB collection with sentence transformer embeddings."""
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)


@st.cache_data(ttl=3600, show_spinner=False)
def get_collection_stats(_collection):
    """Get stats about the collection (cached for 1h)."""
    count = _collection.count()
    sample = _collection.peek(limit=5)
    return {"count": count, "sample": sample}


def query_memories(collection, query, n=5, include_distances=False):
    """Fast memory query with deduplication."""
    includes = ["documents", "metadatas"]
    if include_distances:
        includes.append("distances")

    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=includes,
    )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    distances = results.get("distances", [[]])[0] if include_distances else []

    # Deduplicate
    seen = set()
    unique = []
    for i, doc in enumerate(docs):
        sig = hashlib.md5(doc[:200].encode()).hexdigest()
        if sig not in seen:
            seen.add(sig)
            unique.append(i)

    return (
        [docs[i] for i in unique],
        [metas[i] for i in unique],
        [distances[i] for i in unique] if distances else [],
    )


def query_memories_with_embeddings(collection, query, n=20):
    """Query memories and return embeddings too (for visualization)."""
    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    return {
        "docs": results["documents"][0] if results["documents"] else [],
        "metas": results["metadatas"][0] if results["metadatas"] else [],
        "distances": results["distances"][0] if results["distances"] else [],
        "embeddings": results["embeddings"][0] if results.get("embeddings") and results["embeddings"] else None,
    }


def build_context_string(docs, metas, max_chars=4000):
    """Build context string from docs/metas with truncation."""
    blocks = []
    total = 0
    for doc, meta in zip(docs, metas):
        trunc = doc[:1200] + "…" if len(doc) > 1200 else doc
        date = meta.get("date", "Unknown")
        title = meta.get("title", "Unknown")
        block = f"[{date}] (Chat: {title})\n{trunc}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n---\n\n".join(blocks)


def format_uptime(boot_time):
    """Calculate uptime from boot."""
    elapsed = time.time() - boot_time
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
