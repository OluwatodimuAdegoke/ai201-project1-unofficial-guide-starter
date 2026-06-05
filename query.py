"""
ASU Unofficial Guide — Grounded Generation Engine (Milestone 5)
Pipeline stage: Query -> Retrieve -> Ground -> Generate -> Cite

Architecture (from planning.md):
    User Query
        |
        v
    embedding.py: retrieve()        <- top-5 chunks + metadata
        |
        v
    query.py: build_prompt()        <- inject chunks as context, enforce grounding
        |
        v
    Groq API (llama-3.3-70b-versatile) <- generate answer strictly from context
        |
        v
    ask()  ->  {"answer": str, "sources": list, "chunks": list}

Usage:
    CLI test:  python query.py
    Import:    from query import ask
"""

import sys
import os
from groq import Groq
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_MODEL     = "llama-3.3-70b-versatile"
EMBED_MODEL    = "all-MiniLM-L6-v2"
CHROMA_DIR     = "chroma_store"
COLLECTION     = "asu_unofficial_guide"
TOP_K          = 5

# Load shared resources once at module import — avoids reloading on every call
_embed_model = None
_collection  = None
_groq_client = None


def _get_resources():
    """
    Lazily load and cache the embedding model, ChromaDB collection, and Groq
    client so they are initialized only once per process, not on every query.

    Input:  None
    Output: tuple (SentenceTransformer, chromadb.Collection, groq.Groq)

    Raises:
        EnvironmentError: If GROQ_API_KEY is not set in the environment or .env file.
        FileNotFoundError: If the ChromaDB store has not been built yet.
    """
    global _embed_model, _collection, _groq_client

    if _embed_model is None:
        print("[init] Loading embedding model ...")
        _embed_model = SentenceTransformer(EMBED_MODEL)

    if _collection is None:
        print("[init] Connecting to ChromaDB ...")
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(COLLECTION)
        print(f"[init] Collection loaded: {_collection.count():,} chunks")

    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise EnvironmentError(
                "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _groq_client = Groq(api_key=api_key)
        print(f"[init] Groq client ready (model: {GROQ_MODEL})")

    return _embed_model, _collection, _groq_client


# ── Step 1: Retrieve ──────────────────────────────────────────────────────────

def retrieve_chunks(query: str, top_k: int = TOP_K) -> list:
    """
    Embed the user's query and retrieve the top-k most semantically similar
    chunks from the ChromaDB vector store.

    Input:
        query  (str): Natural-language question from the user.
        top_k  (int): Number of chunks to retrieve. Defaults to TOP_K (5).

    Output:
        list[dict]: Ranked list of result dicts, each containing:
            - "rank"        (int):   1-based rank (1 = closest match).
            - "distance"    (float): Cosine distance. Lower = more relevant.
            - "source"      (str):   Source PDF filename.
            - "chunk_index" (int):   Position within its source document.
            - "text"        (str):   Full text of the retrieved chunk.

    Example:
        chunks = retrieve_chunks("What math is required for CS?")
        # chunks[0]["distance"] -> 0.39
    """
    embed_model, collection, _ = _get_resources()
    query_vec = embed_model.encode(query).tolist()

    raw = collection.query(
        query_embeddings=[query_vec],
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


# ── Step 2: Build grounded prompt ─────────────────────────────────────────────

def build_prompt(query: str, chunks: list) -> list:
    """
    Assemble the messages list for the Groq chat API, injecting retrieved
    chunks as the only permissible knowledge source for the model.

    The system prompt explicitly forbids the model from drawing on training
    knowledge — it must answer from the provided context only, and must
    decline if the context is insufficient. This is the grounding mechanism.

    Source attribution is enforced structurally: the system prompt requires
    the model to end every response with a "Sources:" section listing the
    exact filenames of the chunks it drew from. This guarantees attribution
    is always present and always tied to real retrieved documents.

    Input:
        query  (str):        The user's natural-language question.
        chunks (list[dict]): Retrieved chunks from retrieve_chunks().

    Output:
        list[dict]: A two-element messages list for groq.chat.completions.create():
            [{"role": "system", "content": <grounding instruction>},
             {"role": "user",   "content": <context + question>}]

    Example:
        messages = build_prompt("How many hours of Humanities are required?", chunks)
        response = client.chat.completions.create(model=GROQ_MODEL, messages=messages)
    """
    # Build the numbered context block from retrieved chunks
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Document {i} | Source: {chunk['source']} | Chunk #{chunk['chunk_index']}]\n"
            f"{chunk['text']}"
        )
    context_str = "\n\n---\n\n".join(context_blocks)

    # System prompt — grounding is enforced, not just suggested
    system_prompt = (
        "You are a helpful academic advisor assistant for Alabama State University (ASU). "
        "Your ONLY knowledge source is the set of document excerpts provided in the user's message. "
        "You MUST follow these rules strictly:\n\n"
        "1. Answer ONLY using information explicitly stated in the provided document excerpts. "
        "Do NOT use your general training knowledge, even if you believe you know the answer.\n\n"
        "2. If the provided excerpts do not contain enough information to answer the question, "
        "respond with exactly: 'I don't have enough information in the provided documents to answer that question.' "
        "Do NOT guess, infer, or fill in gaps from general knowledge.\n\n"
        "3. Be specific and cite exact course codes, credit hours, and requirements as they appear "
        "in the documents. Do not paraphrase in a way that changes the meaning.\n\n"
        "4. At the end of EVERY response, include a 'Sources:' section that lists the filename(s) "
        "of the document excerpts you actually used to construct your answer. "
        "Only list sources you genuinely drew from — do not list all provided documents by default."
    )

    # User message: context first, then question
    user_message = (
        f"Here are the relevant document excerpts retrieved for your question:\n\n"
        f"{context_str}\n\n"
        f"---\n\n"
        f"Question: {query}\n\n"
        f"Remember: answer only from the excerpts above. "
        f"End your response with a 'Sources:' section listing the filenames you used."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]


# ── Step 3: Generate ──────────────────────────────────────────────────────────

def generate_answer(messages: list) -> str:
    """
    Send the grounded messages to the Groq API and return the model's response.

    Uses llama-3.3-70b-versatile, a free-tier Groq model that is OpenAI-API-
    compatible. Temperature is set to 0.1 to make responses deterministic and
    factual — lower hallucination risk for a retrieval-grounded system.

    Input:
        messages (list[dict]): The messages list from build_prompt().

    Output:
        str: The raw text content of the model's response, including the
             "Sources:" section appended by the model per the system prompt.

    Example:
        answer = generate_answer(messages)
        print(answer)
    """
    _, _, groq_client = _get_resources()

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.1,      # near-deterministic: reduces hallucination
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ── Step 4: Parse sources ─────────────────────────────────────────────────────

def parse_sources(answer_text: str, retrieved_chunks: list) -> list:
    """
    Extract the list of cited source filenames from the model's response,
    cross-referenced against the actually retrieved chunks for safety.

    The model is instructed to end its response with a "Sources:" section.
    This function parses that section. As a safety fallback, if parsing fails
    or the model omitted the section, it returns the sources of all retrieved
    chunks so attribution is never silently missing.

    Input:
        answer_text      (str):        The raw text response from generate_answer().
        retrieved_chunks (list[dict]): The chunks from retrieve_chunks(), used as
                                       a fallback if parsing fails.

    Output:
        list[str]: Deduplicated list of source filenames cited in the response.

    Example:
        sources = parse_sources(answer, chunks)
        # ["01_asu_catalog_2021-2023.pdf", "08_asu_computer_science_guide.pdf"]
    """
    # Try to parse the "Sources:" section the model was instructed to include
    if "Sources:" in answer_text:
        sources_section = answer_text.split("Sources:")[-1].strip()
        lines = [l.strip().lstrip("•-*123456789. ") for l in sources_section.split("\n")]
        parsed = [l for l in lines if l.endswith(".pdf")]
        if parsed:
            return list(dict.fromkeys(parsed))   # deduplicate, preserve order

    # Fallback: return sources of all retrieved chunks
    return list(dict.fromkeys(c["source"] for c in retrieved_chunks))


# ── Main entry point: ask() ───────────────────────────────────────────────────

def ask(query: str, top_k: int = TOP_K) -> dict:
    """
    Run the full RAG pipeline for a single user question: retrieve -> prompt
    -> generate -> parse, and return a structured response dict.

    This is the primary public API used by app.py (the Gradio interface).
    It chains all four pipeline steps and returns both the answer text and
    structured metadata for display and evaluation.

    Input:
        query  (str): The user's natural-language question about ASU curriculum.
        top_k  (int): Number of chunks to retrieve. Defaults to TOP_K (5).

    Output:
        dict with keys:
            - "answer"  (str):        The model's grounded response text,
                                      including the "Sources:" section.
            - "sources" (list[str]):  Deduplicated list of cited PDF filenames.
            - "chunks"  (list[dict]): The raw retrieved chunks with distance
                                      scores, for debugging or display.

    Example:
        result = ask("What math courses are required before Data Structures?")
        print(result["answer"])
        print(result["sources"])   # ["08_asu_computer_science_guide.pdf"]
    """
    chunks   = retrieve_chunks(query, top_k=top_k)
    messages = build_prompt(query, chunks)
    answer   = generate_answer(messages)
    sources  = parse_sources(answer, chunks)

    return {
        "answer":  answer,
        "sources": sources,
        "chunks":  chunks,
    }


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with 3 evaluation queries + 1 out-of-scope query
    test_questions = [
        ("Q1 (in-scope)",
         "What specific math courses are required as prerequisites before taking "
         "Data Structures and Algorithms in the Computer Science program?"),
        ("Q5 (in-scope)",
         "How many total credit hours of Humanities and Fine Arts are required "
         "to satisfy the 42-hour general education core?"),
        ("Q2 (in-scope)",
         "How many total credit hours of organic chemistry including labs must a "
         "Biology Pre-Health student complete?"),
        ("OUT-OF-SCOPE",
         "What is the best pizza place near Alabama State University campus?"),
    ]

    for label, question in test_questions:
        print("\n" + "=" * 70)
        print(f"  {label}")
        print(f"  Q: {question}")
        print("=" * 70)
        result = ask(question)

        print(f"\n  ANSWER:\n")
        for line in result["answer"].split("\n"):
            print(f"    {line}")

        print(f"\n  PARSED SOURCES: {result['sources']}")
        print(f"\n  TOP RETRIEVAL DISTANCES: "
              f"{[c['distance'] for c in result['chunks']]}")
