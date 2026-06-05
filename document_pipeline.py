"""
ASU Unofficial Guide — Document Pipeline
Stages: Load -> Clean -> Chunk -> Inspect
Follows planning.md spec exactly.

Usage:
    Run directly:  python document_pipeline.py
    Import:        from document_pipeline import load_pdfs, clean_text, clean_all, chunk_documents, inspect_chunks, run_pipeline
"""

import sys
import os
import re
import json
import random
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Force UTF-8 output so special chars from PDFs don't crash on Windows
sys.stdout.reconfigure(encoding="utf-8")

# ── Config (from planning.md) ────────────────────────────────────────────────
DOCUMENTS_DIR = "documents"
RAW_OUTPUT    = "raw_texts.json"
CHUNKS_OUTPUT = "chunks.json"

CHUNK_SIZE    = 800     # tokens  (planning.md: 800 tokens ~ 3,000 chars)
CHUNK_OVERLAP = 150     # tokens

# tiktoken encodes ~4 chars/token on average for English text.
# LangChain's RecursiveCharacterTextSplitter uses character counts,
# so we convert our token targets to character equivalents.
CHARS_PER_TOKEN     = 4
CHUNK_SIZE_CHARS    = CHUNK_SIZE    * CHARS_PER_TOKEN   # 3200
CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP * CHARS_PER_TOKEN   # 600


# ── STAGE 1: LOAD ────────────────────────────────────────────────────────────

def load_pdfs(documents_dir: str = DOCUMENTS_DIR, save_path: str = RAW_OUTPUT) -> dict:
    """
    Load all PDF files from a local directory using pdfplumber and return
    their raw extracted text.

    Iterates over every .pdf file in `documents_dir`, extracts text page by
    page (skipping pages that yield no text, e.g. image-only pages), and
    joins pages with double newlines to preserve paragraph boundaries.

    Input:
        documents_dir (str): Path to the folder containing the PDF files.
                             Defaults to the DOCUMENTS_DIR constant ("documents").
        save_path (str):     File path where raw texts will be saved as JSON
                             before any cleaning. Defaults to RAW_OUTPUT ("raw_texts.json").

    Output:
        dict: A dictionary mapping filename (str) -> raw extracted text (str).
              Files that fail to open or parse are skipped with a printed warning.
              The same dictionary is also serialized to `save_path` as JSON
              so the raw state is preserved before cleaning begins.

    Example:
        raw_docs = load_pdfs("documents", "raw_texts.json")
        # raw_docs["08_asu_computer_science_guide.pdf"] -> "Alabama State University\\n\\nCURRICULUM GUIDE..."
    """
    print("=" * 60)
    print("STAGE 1 — LOADING PDFs with pdfplumber")
    print("=" * 60)

    raw_docs = {}

    for fname in sorted(os.listdir(documents_dir)):
        if not fname.endswith(".pdf"):
            continue
        path = os.path.join(documents_dir, fname)
        try:
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() for p in pdf.pages if p.extract_text()]
                text = "\n\n".join(pages)
            raw_docs[fname] = text
            print(f"  [OK]   {fname:<45}  {len(text):>8,} chars  ({len(pages)} pages)")
        except Exception as e:
            print(f"  [FAIL] {fname}: {e}")

    print(f"\nLoaded {len(raw_docs)} documents.")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(raw_docs, f, ensure_ascii=False, indent=2)
    print(f"Raw texts saved to '{save_path}'\n")

    return raw_docs


# ── STAGE 2: CLEAN ───────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Clean a single document's raw text by removing noise that would
    pollute embeddings and retrieval without adding useful meaning.

    Applies the following cleaning steps in order:
        0. Strip invisible/zero-width Unicode characters (common PDF artifacts).
        1. Remove HTML tags (defensive, in case of mixed-source text).
        2. Decode common HTML entities (&amp;, &nbsp;, &#39;, etc.).
        3. Remove URLs (http/https links add no domain knowledge).
        4. Remove email addresses.
        5. Collapse dot/dash leader sequences (e.g., "........ 3 credits").
        6. Drop boilerplate lines: purely numeric lines (page numbers),
           "Page N of M" labels, and lines of 2 characters or fewer.
        7. Collapse 3+ consecutive blank lines into a single blank line.
        8. Strip leading and trailing whitespace.

    Input:
        text (str): Raw text extracted from a single PDF document.

    Output:
        str: Cleaned text with noise removed, ready for chunking.

    Example:
        cleaned = clean_text(raw_text)
    """
    # 0. Strip invisible/zero-width Unicode characters common in PDFs
    text = re.sub(r"[​‌‍﻿­]", "", text)

    # 1. Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # 2. Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&nbsp;", " ") \
               .replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&#39;", "'").replace("&quot;", '"')

    # 3. Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # 4. Remove email addresses
    text = re.sub(r"\S+@\S+\.\S+", "", text)

    # 5. Collapse dot/dash leader sequences (e.g., "Course........ 3")
    text = re.sub(r"[.\-_]{4,}", " ", text)

    # 6. Drop boilerplate lines
    lines = text.split("\n")
    kept = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) <= 2:
            continue
        if re.fullmatch(r"[\d\s\-]+", stripped):
            continue
        if re.match(r"^(page\s+\d+(\s+of\s+\d+)?|p\.\s*\d+)$", stripped, re.I):
            continue
        kept.append(line)
    text = "\n".join(kept)

    # 7. Collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 8. Strip edges
    return text.strip()


def clean_all(raw_docs: dict, sample_key: str = "08_asu_computer_science_guide.pdf") -> dict:
    """
    Apply clean_text() to every document in the raw_docs dictionary and
    print a per-document summary showing how much text was removed.

    After cleaning, prints a preview of one document so the result can
    be visually inspected before chunking begins.

    Input:
        raw_docs (dict):  Dictionary of filename -> raw text, as returned
                          by load_pdfs().
        sample_key (str): Filename of the document to print as a sample
                          after cleaning. Defaults to the CS curriculum guide.

    Output:
        dict: A new dictionary of filename -> cleaned text. The original
              raw_docs dictionary is not modified.

    Example:
        cleaned_docs = clean_all(raw_docs)
        # Prints per-file removal percentages and a sample preview.
    """
    print("=" * 60)
    print("STAGE 2 — CLEANING")
    print("=" * 60)

    cleaned_docs = {}
    for fname, raw in raw_docs.items():
        cleaned = clean_text(raw)
        cleaned_docs[fname] = cleaned
        reduction = 100 * (1 - len(cleaned) / len(raw)) if raw else 0
        print(f"  {fname:<45}  {len(raw):>8,} -> {len(cleaned):>8,} chars  ({reduction:.1f}% removed)")

    if sample_key in cleaned_docs:
        print()
        print("-" * 60)
        print(f"SAMPLE CLEANED DOCUMENT: {sample_key}")
        print("-" * 60)
        print(cleaned_docs[sample_key][:3000])
        print("... [truncated to 3000 chars] ...")

    print()
    return cleaned_docs


# ── STAGE 3: CHUNK ───────────────────────────────────────────────────────────

def chunk_documents(
    cleaned_docs: dict,
    chunk_size_chars: int = CHUNK_SIZE_CHARS,
    chunk_overlap_chars: int = CHUNK_OVERLAP_CHARS,
    save_path: str = CHUNKS_OUTPUT,
) -> list:
    """
    Split each cleaned document into overlapping text chunks using
    LangChain's RecursiveCharacterTextSplitter, then save results to disk.

    The splitter attempts to break on paragraph boundaries first (\n\n),
    then single newlines, then sentences, then words, then characters —
    preserving as much semantic coherence as possible within each chunk.
    Chunks shorter than 50 characters are filtered out as uninformative.

    Each output chunk is a dictionary with three keys:
        - "text"        (str): The chunk's text content.
        - "source"      (str): The filename the chunk came from.
        - "chunk_index" (int): Zero-based position of this chunk within its source document.

    Input:
        cleaned_docs (dict):        filename -> cleaned text, as returned by clean_all().
        chunk_size_chars (int):     Maximum chunk size in characters. Defaults to
                                    CHUNK_SIZE_CHARS (3200 chars ~ 800 tokens).
        chunk_overlap_chars (int):  Overlap between adjacent chunks in characters.
                                    Defaults to CHUNK_OVERLAP_CHARS (600 chars ~ 150 tokens).
        save_path (str):            File path to save the chunk list as JSON.
                                    Defaults to CHUNKS_OUTPUT ("chunks.json").

    Output:
        list[dict]: A flat list of all chunks across all documents, each dict
                    containing "text", "source", and "chunk_index".
                    Also serialized to `save_path` as JSON.

    Example:
        chunks = chunk_documents(cleaned_docs)
        # chunks[0] -> {"text": "Alabama State University...", "source": "01_...", "chunk_index": 0}
    """
    print("=" * 60)
    print("STAGE 3 — CHUNKING")
    print(f"  Chunk size : {chunk_size_chars} chars  (~{chunk_size_chars // CHARS_PER_TOKEN} tokens)")
    print(f"  Overlap    : {chunk_overlap_chars} chars  (~{chunk_overlap_chars // CHARS_PER_TOKEN} tokens)")
    print("=" * 60)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=chunk_overlap_chars,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []

    for fname, text in cleaned_docs.items():
        splits = splitter.split_text(text)
        splits = [s.strip() for s in splits if len(s.strip()) > 50]
        for i, chunk_text in enumerate(splits):
            all_chunks.append({
                "text":        chunk_text,
                "source":      fname,
                "chunk_index": i,
            })
        print(f"  {fname:<45}  {len(splits):>4} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"Chunks saved to '{save_path}'\n")

    return all_chunks


# ── STAGE 4: INSPECT ─────────────────────────────────────────────────────────

def inspect_chunks(all_chunks: list, n: int = 5) -> None:
    """
    Print a random sample of chunks and a summary report to verify
    that chunking produced clean, self-contained, retrievable units.

    For each sampled chunk, prints its source file, chunk index, character
    length, and up to 800 characters of text. After the samples, prints
    aggregate statistics (total count, average/min/max length) and a
    health warning if chunk count falls outside the 50–2,000 range.

    Input:
        all_chunks (list[dict]): The full list of chunk dicts as returned
                                 by chunk_documents(). Each dict must have
                                 keys "text", "source", and "chunk_index".
        n (int):                 Number of random chunks to print for inspection.
                                 Defaults to 5.

    Output:
        None. Prints results to stdout only. Does not modify the chunk list
        or write any files.

    Example:
        inspect_chunks(chunks, n=5)
        # Prints 5 random chunks and a checkpoint summary.
    """
    print("=" * 60)
    print(f"STAGE 4 — INSPECTING {n} REPRESENTATIVE CHUNKS")
    print("=" * 60)

    sample_indices = random.sample(range(len(all_chunks)), min(n, len(all_chunks)))
    for rank, idx in enumerate(sample_indices, 1):
        chunk = all_chunks[idx]
        print(f"\n-- Chunk {rank} (index {idx}) " + "-" * 35)
        print(f"   Source : {chunk['source']}  (chunk #{chunk['chunk_index']})")
        print(f"   Length : {len(chunk['text'])} chars")
        print(f"   Text   :\n")
        print(chunk["text"][:800])
        if len(chunk["text"]) > 800:
            print("   ... [truncated]")

    print("\n" + "=" * 60)
    print("CHECKPOINT SUMMARY")
    print("=" * 60)
    total = len(all_chunks)
    avg   = sum(len(c["text"]) for c in all_chunks) / total if total else 0
    print(f"  Total chunks     : {total}")
    print(f"  Avg chunk length : {avg:.0f} chars  (~{avg / CHARS_PER_TOKEN:.0f} tokens)")
    print(f"  Min chunk length : {min(len(c['text']) for c in all_chunks)} chars")
    print(f"  Max chunk length : {max(len(c['text']) for c in all_chunks)} chars")

    if total < 50:
        print("\n  [WARNING] Fewer than 50 chunks — consider reducing chunk size.")
    elif total > 2000:
        print("\n  [WARNING] More than 2,000 chunks — consider increasing chunk size.")
    else:
        print("\n  [OK] Chunk count is in the healthy 50-2,000 range.")


# ── FULL PIPELINE ─────────────────────────────────────────────────────────────

def run_pipeline(
    documents_dir: str = DOCUMENTS_DIR,
    raw_output: str = RAW_OUTPUT,
    chunks_output: str = CHUNKS_OUTPUT,
    inspect_n: int = 5,
) -> list:
    """
    Run the complete document pipeline end-to-end: Load -> Clean -> Chunk -> Inspect.

    This is the main entry point that chains all four stages together.
    It is equivalent to calling load_pdfs(), clean_all(), chunk_documents(),
    and inspect_chunks() in sequence with their default arguments.

    Input:
        documents_dir  (str): Path to the folder containing PDF source files.
                              Defaults to DOCUMENTS_DIR ("documents").
        raw_output     (str): File path to save raw (pre-cleaning) texts as JSON.
                              Defaults to RAW_OUTPUT ("raw_texts.json").
        chunks_output  (str): File path to save the final chunk list as JSON.
                              Defaults to CHUNKS_OUTPUT ("chunks.json").
        inspect_n      (int): Number of random chunks to print during inspection.
                              Defaults to 5.

    Output:
        list[dict]: The complete list of chunk dicts produced by chunk_documents().
                    Each dict contains "text", "source", and "chunk_index".
                    Side effects: writes raw_texts.json and chunks.json to disk.

    Example:
        chunks = run_pipeline()
        # Runs all four stages and returns 1,283 chunk dicts.

        chunks = run_pipeline(documents_dir="my_pdfs", inspect_n=3)
        # Custom source folder, inspect only 3 chunks.
    """
    raw_docs     = load_pdfs(documents_dir, save_path=raw_output)
    cleaned_docs = clean_all(raw_docs)
    all_chunks   = chunk_documents(cleaned_docs, save_path=chunks_output)
    inspect_chunks(all_chunks, n=inspect_n)
    return all_chunks


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_pipeline()
