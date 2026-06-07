# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This system covers course curriculum requirements for select degree programs at Alabama State University (ASU) — including prerequisites, credit hour breakdowns, and general education core rules across multiple catalog years (2017–2023).

This knowledge is valuable because correctly navigating degree requirements is critical to graduating on time and avoiding unnecessary tuition costs. It is hard to find through official channels because the information is buried in massive, fragmented PDF catalogs (some over 400 pages) that require tedious manual cross-referencing across multiple documents to answer a single question.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | ASU 2021–2023 Undergraduate Catalog | PDF | https://www.alasu.edu/_qa/2021-2023%20Undergraduate%20Catalog.pdf |
| 2 | ASU 2019–2021 Undergraduate Catalog | PDF | https://www.alasu.edu/_qa/ASU%202019_2021%20FINAL%20CATALOG_MAIN%202.pdf |
| 3 | ASU Criminal Justice Curriculum Guide | PDF | https://www.alasu.edu/_qa/Curriculum%20Guide%20Approved%202023_0.pdf |
| 4 | ASU Management Curriculum Guide | PDF | https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf |
| 5 | ASU Theatre Arts BA Curriculum Sheet | PDF | https://www.alasu.edu/_qa/Theatre%20BA%20Curriculum%20Sheet.pdf |
| 6 | ASU Graduate Catalog | PDF | https://www.alasu.edu/_qa/Grad_Catalog-1.pdf |
| 7 | ASU 2017–2019 Undergraduate Catalog | PDF | https://www.alasu.edu/_qa/2017-19%20Undergraduate%20Catalog%20%20-1-updated_0.pdf |
| 8 | ASU Computer Science Curriculum Guide | PDF | https://www.alasu.edu/websites/Computer%20Science%20Curriculum.pdf |
| 9 | ASU Mathematics B.S. Curriculum Guide | PDF | https://www.alasu.edu/_qa/CSTEM%20Mathematics%20B.S..pdf |
| 10 | ASU Biology Pre-Health Curriculum Sequence | PDF | https://www.alasu.edu/_qa/Biology%20Pre-Health%20Sequence.pdf |
| 11 | ASU Business/Accounting Curriculum Guide | PDF | https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 800 tokens (~3,200 characters), implemented using LangChain's `RecursiveCharacterTextSplitter` with a character-based limit of 3,200.

**Overlap:** 150 tokens (~600 characters).

**Why these choices fit your documents:** Academic catalogs and curriculum sheets are structured around nested headings and dense lists of course codes, credit hours, and prerequisites. A larger chunk size of 800 tokens ensures that a complete course description — including its prerequisites, credit hours, and department notes — stays intact within a single chunk rather than being split mid-entry. 
**Final chunk count:** 1,283 chunks across 11 documents.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. This model runs fully locally with no API key or rate limits. It was the right choice for a development pipeline where fast iteration matters more than maximum precision.

**Production tradeoff reflection:** For a real deployment serving ASU students, the primary tradeoff to weigh would be retrieval precision vs. cost and latency. `all-MiniLM-L6-v2` has a 384-dimension embedding space that can struggle to distinguish between semantically similar-but-distinct academic terms. Upgrading to `text-embedding-3-large` (OpenAI, API-hosted) would provide a much larger embedding space and significantly better precision on domain-specific course codes, at the cost of per-query API fees and network latency.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** The system prompt explicitly forbids the model from using its training knowledge, even when it believes it knows the answer. The key instruction reads: *"Answer ONLY using information explicitly stated in the provided document excerpts. Do NOT use your general training knowledge, even if you believe you know the answer."* 

**How source attribution is surfaced in the response:** Attribution is enforced inline rather than as a trailing section. The system prompt instructs: *"Cite your source INLINE within the answer every time you state a fact drawn from a document. Place the citation immediately after the fact, in this exact format: (source: filename.pdf)."* This means every factual claim in the response carries its source next to it — for example: *"Students must complete 12 credit hours of Humanities and Fine Arts (source: 01_asu_catalog_2021-2023.pdf)."* 

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What specific math courses are required as prerequisites before taking Data Structures and Algorithms in the CS program? | Specific math course codes (e.g., MAT 265 Calculus I or Discrete Mathematics) required before Data Structures | System correctly stated that no explicit math prerequisites for CSC 212 were found in the retrieved excerpts, though it noted MAT 265 and MAT 266 appear in CS-related chunks | Partially relevant — top chunks contained CS course lists but not the specific prerequisite rule | Partially accurate — honest about the absence; the CS guide chunk didn't surface the prerequisite line explicitly |
| 2 | How many total credit hours of organic chemistry including labs must a Biology Pre-Health student complete? | 8 credit hours (Organic Chemistry I + II with labs) | "A Biology Pre-Health student must complete 8 semester hours of organic chemistry (CHE 211-212) (source: 07_asu_catalog_2017-2019.pdf)" | Relevant — top chunk contained CHE 211-212 credit listing | Accurate |
| 3 | What is the minimum grade requirement for COBA core courses to graduate? | Minimum grade of "C" in all required COBA core courses | System returned "I don't have enough information in the provided documents to answer that question." | Off-target — retrieved chunks did not contain the COBA grade policy | Inaccurate — the information exists in the catalog but was not retrieved |
| 4 | Is a senior internship required for the Criminal Justice degree, and how many credits is it worth? | Internship is mandatory; specific credit hour count (e.g., 3 credits) | System confirmed CRJ 453 Professional Internship I is required and worth 5 credits, with CRJ 459 as an optional follow-on worth 12 credits (source: 07_asu_catalog_2017-2019.pdf) | Relevant — criminal justice internship chunks retrieved correctly | Partially accurate — correctly identified internship as required; credit count (5) may differ from the curriculum guide value |
| 5 | How many total credit hours of Humanities and Fine Arts are required to satisfy the 42-hour general education core? | 12 credit hours of Humanities and Fine Arts | "Students must complete 12 credit hours of Humanities and Fine Arts (source: 01_asu_catalog_2021-2023.pdf)" | Relevant — direct hit on general studies section | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** "What is the minimum grade requirement for COBA core courses to graduate?" (Q3)

**What the system returned:** "I don't have enough information in the provided documents to answer that question." — even though the minimum grade policy does exist in the ASU undergraduate catalogs.

**Root cause (tied to a specific pipeline stage):** The failure occurred at the **retrieval stage**. The query uses the phrase "minimum grade requirement" and "COBA core courses," but the catalog text likely phrases this as something like "must earn a grade of C or better" embedded within a paragraph of program requirements. The `all-MiniLM-L6-v2` embedding model has a 256-token context window, which means our 800-token chunks were being silently truncated to 256 tokens before embedding. As a result, content appearing in the second half of large catalog chunks was never encoded into the chunk's vector, making it effectively invisible to retrieval.

**What you would change to fix it:** Two changes would address this. First, reduce chunk size to 200–250 tokens so that chunks fit within `all-MiniLM-L6-v2`'s actual context window and no content is silently truncated during embedding. Second, add a metadata filter to the retrieval step that prioritizes chunks from major-specific curriculum guide PDFs (e.g., `04_asu_management_guide.pdf`) when the query mentions "COBA" — a hybrid retrieval approach combining semantic search with source-level filtering would help surface departmental policies that are sparse in the larger catalog documents.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** The chunking strategy section of `planning.md` — which specified 800 tokens with 150-token overlap and explained why those numbers fit academic catalog structure — made the implementation of `chunk_documents()` in `document_pipeline.py` straightforward and defensible. Rather than guessing at chunk size, the spec gave a concrete rationale that could be verified by inspecting the output. When the 5 sample chunks were printed during the checkpoint, they were already coherent because the size had been reasoned through in advance, not tuned by trial and error.

**One way your implementation diverged from the spec, and why:** The spec called for a Gradio web UI in Milestone 5, but the final interface is a command-line tool (`cli.py`). This change was made because a CLI is faster to iterate on during development, has no browser dependency, and is easier to test programmatically by piping questions through stdin.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* I gave Claude access to `planning.md` — specifically the Domain, Chunking Strategy, Retrieval Approach, and Architecture sections — along with instructions describing what each pipeline stage needed to do (load PDFs, clean text, chunk, embed, retrieve, generate).
- *What it produced:* Claude produced a working `pipeline.py` script that loaded PDFs with pdfplumber, cleaned text, and chunked with `RecursiveCharacterTextSplitter` using the 800-token / 150-token overlap from the spec. It also produced `embedding.py` wiring `all-MiniLM-L6-v2` into ChromaDB, and `query.py` connecting retrieval to the Groq LLM.
- *What I changed or overrode:* The initial implementation was written as a flat top-level script with no functions. I directed Claude to refactor it into named functions with full docstrings (inputs, outputs, examples) for reusability and readability — the result became `document_pipeline.py`. This made it possible to import individual stages (e.g., `from document_pipeline import chunk_documents`) rather than re-running the entire pipeline every time.

**Instance 2**

- *What I gave the AI:* After the full pipeline was working, I gave Claude the existing `query.py` system prompt and described a specific output format change: I wanted source citations to appear inline within the answer (e.g., "12 credit hours are required (source: 01_asu_catalog_2021-2023.pdf)") rather than as a separate "Sources:" section appended at the end of the response.
- *What it produced:* Claude updated the system prompt in `build_prompt()` to instruct the model to place `(source: filename.pdf)` immediately after every fact, and updated `cli.py`'s `print_result()` to remove the old logic that split and displayed a separate Sources section.
- *What I changed or overrode:* The instruction was followed accurately. The key judgment call I directed was the format itself — the inline citation style — which Claude then enforced through the system prompt wording rather than post-processing, ensuring grounding and attribution remained structurally linked.
