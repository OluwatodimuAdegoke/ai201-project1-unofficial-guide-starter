"""
ASU Unofficial Guide — Embedding & Retrieval (Milestone 4)
Pipeline stage: Chunks -> Embed -> ChromaDB -> Retrieve

Architecture (from planning.md):
    document_pipeline.py  -->  embedding.py
    [Chunks JSON]         -->  [all-MiniLM-L6-v2]  -->  [ChromaDB]  -->  [Retrieval fn]

Usage:
    Build the store:  python embedding.py
    Import:           from embedding import build_vector_store, load_vector_store, retrieve
"""

import sys
import json
import os
from sentence_transformers import SentenceTransformer
import chromadb

sys.stdout.reconfigure(encoding="utf-8")

# ── Config (from planning.md) ────────────────────────────────────────────────
CHUNKS_FILE    = "chunks.json"
CHROMA_DIR     = "chroma_store"
COLLECTION     = "asu_unofficial_guide"
EMBED_MODEL    = "all-MiniLM-L6-v2"
TOP_K          = 5          # planning.md: retrieve top 5 chunks per query
BATCH_SIZE     = 64         # embed this many chunks at a time to avoid OOM


# ── STAGE 1: LOAD CHUNKS ─────────────────────────────────────────────────────

def load_chunks(chunks_file: str = CHUNKS_FILE) -> list:
    """
    Load the list of text chunks produced by document_pipeline.py from disk.

    Reads the JSON file written by chunk_documents() and returns it as a
    Python list of dicts. Each dict has the keys:
        - "text"        (str): The chunk's text content.
        - "source"      (str): The filename the chunk came from.
        - "chunk_index" (int): Zero-based position within its source document.

    Input:
        chunks_file (str): Path to the JSON file produced by document_pipeline.py.
                           Defaults to CHUNKS_FILE ("chunks.json").

    Output:
        list[dict]: All chunks loaded into memory, ready for embedding.

    Raises:
        FileNotFoundError: If chunks_file does not exist. Run document_pipeline.py first.

    Example:
        chunks = load_chunks("chunks.json")
        # chunks[0] -> {"text": "Alabama State...", "source": "01_...", "chunk_index": 0}
    """
    if not os.path.exists(chunks_file):
        raise FileNotFoundError(
            f"'{chunks_file}' not found. Run document_pipeline.py first."
        )
    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"[load_chunks] Loaded {len(chunks):,} chunks from '{chunks_file}'")
    return chunks


# ── STAGE 2: BUILD VECTOR STORE ──────────────────────────────────────────────

def build_vector_store(
    chunks: list,
    embed_model_name: str = EMBED_MODEL,
    chroma_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION,
    batch_size: int = BATCH_SIZE,
) -> chromadb.Collection:
    """
    Embed all chunks with all-MiniLM-L6-v2 and load them into a persistent
    ChromaDB collection, along with source metadata for later attribution.

    Steps:
        1. Load the SentenceTransformer embedding model locally (no API key needed).
        2. Embed chunks in batches to avoid memory issues with large corpora.
        3. Create (or overwrite) a ChromaDB collection on disk at `chroma_dir`.
        4. Add each chunk's embedding, raw text (as document), and metadata
           (source filename + chunk_index) to the collection.

    ChromaDB stores four things per entry:
        - id        : Unique string ID (e.g., "chunk_0042").
        - embedding : The 384-dim float vector from all-MiniLM-L6-v2.
        - document  : The raw chunk text (returned alongside search results).
        - metadata  : {"source": filename, "chunk_index": int} for attribution.

    Input:
        chunks (list[dict]):       Chunk dicts from load_chunks() or chunk_documents().
        embed_model_name (str):    HuggingFace model name to load via SentenceTransformer.
                                   Defaults to EMBED_MODEL ("all-MiniLM-L6-v2").
        chroma_dir (str):          Directory where ChromaDB persists its data files.
                                   Defaults to CHROMA_DIR ("chroma_store").
        collection_name (str):     Name of the ChromaDB collection to create/overwrite.
                                   Defaults to COLLECTION ("asu_unofficial_guide").
        batch_size (int):          Number of chunks to embed per batch.
                                   Defaults to BATCH_SIZE (64).

    Output:
        chromadb.Collection: The populated ChromaDB collection, ready for querying.
        Side effect: Writes the persistent vector store to `chroma_dir/` on disk.

    Example:
        chunks = load_chunks()
        collection = build_vector_store(chunks)
        # Embeds 1,283 chunks and persists them to ./chroma_store/
    """
    print("\n" + "=" * 60)
    print("STAGE 2 — EMBEDDING + LOADING INTO CHROMADB")
    print("=" * 60)

    # 1. Load embedding model
    print(f"[build_vector_store] Loading embedding model '{embed_model_name}' ...")
    model = SentenceTransformer(embed_model_name)
    print(f"[build_vector_store] Model loaded. Vector dimensions: {model.get_sentence_embedding_dimension()}")

    # 2. Embed all chunks in batches
    texts = [c["text"] for c in chunks]
    print(f"[build_vector_store] Embedding {len(texts):,} chunks in batches of {batch_size} ...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
    ).tolist()
    print(f"[build_vector_store] Embedding complete.")

    # 3. Set up persistent ChromaDB client + collection
    #    delete_collection + create_collection = clean rebuild every run
    client = chromadb.PersistentClient(path=chroma_dir)
    try:
        client.delete_collection(collection_name)
        print(f"[build_vector_store] Existing collection '{collection_name}' cleared.")
    except Exception:
        pass   # Collection didn't exist yet — that's fine
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},   # use cosine distance (0=identical, 1=opposite)
    )

    # 4. Add chunks to ChromaDB in batches
    print(f"[build_vector_store] Loading chunks into ChromaDB collection '{collection_name}' ...")
    for start in range(0, len(chunks), batch_size):
        end   = min(start + batch_size, len(chunks))
        batch = chunks[start:end]
        collection.add(
            ids        = [f"chunk_{i}" for i in range(start, end)],
            embeddings = embeddings[start:end],
            documents  = [c["text"]        for c in batch],
            metadatas  = [{"source": c["source"], "chunk_index": c["chunk_index"]} for c in batch],
        )
    print(f"[build_vector_store] Done. Collection now holds {collection.count():,} entries.\n")
    return collection


# ── STAGE 3: LOAD EXISTING STORE ─────────────────────────────────────────────

def load_vector_store(
    chroma_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION,
) -> chromadb.Collection:
    """
    Load an already-built ChromaDB collection from disk without re-embedding.

    Use this instead of build_vector_store() when the store already exists
    and you just want to run queries — it skips the expensive embedding step.

    Input:
        chroma_dir (str):       Path to the ChromaDB persistence directory.
                                Defaults to CHROMA_DIR ("chroma_store").
        collection_name (str):  Name of the collection to load.
                                Defaults to COLLECTION ("asu_unofficial_guide").

    Output:
        chromadb.Collection: The existing collection, ready for querying.

    Raises:
        Exception: If the collection does not exist (build it first with build_vector_store()).

    Example:
        collection = load_vector_store()
        results = retrieve("What math courses are required for CS?", collection)
    """
    client = chromadb.PersistentClient(path=chroma_dir)
    collection = client.get_collection(collection_name)
    print(f"[load_vector_store] Loaded '{collection_name}' ({collection.count():,} entries) from '{chroma_dir}'")
    return collection


# ── STAGE 4: RETRIEVAL ───────────────────────────────────────────────────────

def retrieve(
    query: str,
    collection: chromadb.Collection,
    embed_model_name: str = EMBED_MODEL,
    top_k: int = TOP_K,
) -> list:
    """
    Embed a natural-language query and return the top-k most semantically
    similar chunks from ChromaDB, along with distance scores and metadata.

    How it works:
        1. Encode the query string into a 384-dim vector using all-MiniLM-L6-v2.
        2. ChromaDB performs an approximate nearest-neighbor search (HNSW index)
           using cosine distance against all stored chunk embeddings.
        3. The top_k closest chunks are returned, ranked by distance (lower = better).

    Distance score interpretation (cosine distance, 0.0 to 2.0):
        0.0 – 0.3  : Strong match — chunk is highly relevant to the query.
        0.3 – 0.5  : Moderate match — likely useful but may include some noise.
        0.5 – 0.7  : Weak match — tangentially related; inspect before trusting.
        > 0.7      : Poor match — retrieval failure; chunk shares few semantics with query.

    Input:
        query (str):                    The user's natural-language question.
        collection (chromadb.Collection): A loaded or freshly built ChromaDB collection.
        embed_model_name (str):         Model used to embed the query. Must match the
                                        model used to build the store. Defaults to EMBED_MODEL.
        top_k (int):                    Number of top results to return.
                                        Defaults to TOP_K (5), per planning.md.

    Output:
        list[dict]: A list of up to top_k result dicts, each containing:
            - "rank"        (int):   1-based rank (1 = closest match).
            - "distance"    (float): Cosine distance (lower is better).
            - "source"      (str):   Source filename the chunk came from.
            - "chunk_index" (int):   Position of the chunk within its source document.
            - "text"        (str):   Full text of the retrieved chunk.

    Example:
        results = retrieve("What math courses are required for CS?", collection)
        for r in results:
            print(r["rank"], r["distance"], r["source"])
            print(r["text"][:300])
    """
    model = SentenceTransformer(embed_model_name)
    query_embedding = model.encode(query).tolist()

    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results = []
    for rank, (doc, meta, dist) in enumerate(
        zip(raw["documents"][0], raw["metadatas"][0], raw["distances"][0]), start=1
    ):
        results.append({
            "rank":        rank,
            "distance":    round(dist, 4),
            "source":      meta["source"],
            "chunk_index": meta["chunk_index"],
            "text":        doc,
        })
    return results


# ── STAGE 5: TEST RETRIEVAL ──────────────────────────────────────────────────

def test_retrieval(collection: chromadb.Collection) -> None:
    """
    Run 3 of the 5 evaluation-plan queries from planning.md through the
    retrieval function and print results so relevance can be visually inspected.

    For each query, prints:
        - The query text
        - Each returned chunk's rank, distance score, source file, and
          the first 500 characters of its text
        - A quick health verdict: GOOD (<0.5), WEAK (0.5-0.7), or POOR (>0.7)
          based on the top result's distance

    Input:
        collection (chromadb.Collection): A loaded ChromaDB collection to query.

    Output:
        None. Prints results to stdout only.

    Example:
        collection = load_vector_store()
        test_retrieval(collection)
    """
    # 3 of the 5 evaluation queries from planning.md
    test_queries = [
        (
            "Q1",
            "What specific math courses are required as prerequisites before taking "
            "Data Structures and Algorithms in the Computer Science program?",
        ),
        (
            "Q2",
            "How many total credit hours of organic chemistry including labs must a "
            "Biology Pre-Health student complete?",
        ),
        (
            "Q5",
            "How many total credit hours of Humanities and Fine Arts are required to "
            "satisfy the 42-hour general education core?",
        ),
    ]

    print("=" * 60)
    print("STAGE 5 — RETRIEVAL TEST (3 evaluation queries)")
    print("=" * 60)

    for label, query in test_queries:
        print(f"\n{'=' * 60}")
        print(f"  {label}: {query}")
        print("=" * 60)

        results = retrieve(query, collection)
        top_dist = results[0]["distance"] if results else 999

        if top_dist < 0.5:
            verdict = "[GOOD]  Top distance < 0.5 — strong retrieval"
        elif top_dist < 0.7:
            verdict = "[WEAK]  Top distance 0.5-0.7 — inspect results"
        else:
            verdict = "[POOR]  Top distance > 0.7 — retrieval likely failing"

        print(f"  Verdict: {verdict}\n")

        for r in results:
            print(f"  Rank {r['rank']}  |  distance: {r['distance']}  |  {r['source']}  (chunk #{r['chunk_index']})")
            print(f"  {r['text'][:500]}")
            print(f"  {'- ' * 30}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    chunks     = load_chunks()
    collection = build_vector_store(chunks)
    test_retrieval(collection)
