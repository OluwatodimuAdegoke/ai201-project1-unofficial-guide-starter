# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

I chose the course curriculum for select courses at Alabama State University (ASU).
This knowledge is highly valuable because correctly navigating degree requirements ensures students graduate on time and avoid unnecessary tuition costs.
However, answers are hard to find officially because the data is buried in massive, fragmented PDF catalogs that require tedious manual cross-referencing.
A RAG system solves this by turning dense, multi-hundred-page documents into a tool where students can instantly query specific prerequisites and pathways.

---

## Documents

| # | Source | Description | URL or location |
| --- | --- | --- | --- |
| 1 | ASU 2021-2023 Undergraduate Catalog (PDF) | The previous catalog iteration. Essential for RAG because many current upperclassmen are still bound by these specific requirements. | [Link](https://www.alasu.edu/_qa/2021-2023%20Undergraduate%20Catalog.pdf) |
| 2 | ASU 2019-2021 Undergraduate Catalog (PDF) | Older catalog edition. Useful for capturing legacy requirements or tracking how course prerequisites have changed over time. | [Link](https://www.alasu.edu/_qa/ASU%202019_2021%20FINAL%20CATALOG_MAIN%202.pdf) |
| 3 | ASU Criminal Justice Curriculum Guide (PDF) | A specific major pathway document breaking down the pre-professional and required major courses for a Criminal Justice degree. | [Link](https://www.alasu.edu/_qa/Curriculum%20Guide%20Approved%202023_0.pdf) |
| 4 | ASU Management Curriculum Guide (PDF) | College of Business Administration (COBA) curriculum sheet showing business core, electives, and specific management requirements. | [Link](https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf) |
| 5 | ASU Theatre Arts BA Curriculum Sheet (PDF) | Department-specific sheet outlining the performance, stagecraft, and history requirements for a Bachelor of Arts in Theatre. | [Link](https://www.alasu.edu/_qa/Theatre%20BA%20Curriculum%20Sheet.pdf) |
| 6 | ASU Graduate Catalog (PDF) | The official bulletin detailing master's and doctoral program requirements, which differ significantly from undergraduate structures. | [Link](https://www.alasu.edu/_qa/Grad_Catalog-1.pdf) |
| 7 | ASU 2017-2019 Undergraduate Catalog (PDF) | A deeply archived catalog useful for testing your RAG system's ability to differentiate between active and deprecated course codes. | [Link](https://www.alasu.edu/_qa/2017-19%20Undergraduate%20Catalog%20%20-1-updated_0.pdf) |
| 8 | ASU Computer Science Curriculum Guide (PDF) | A specific pathway document breaking down core programming, data structures, and math prerequisites for the CS degree. | [Link](https://www.alasu.edu/websites/Computer%20Science%20Curriculum.pdf) |
| 9 | ASU Mathematics B.S. Curriculum Guide (PDF) | Detailed curriculum sheet for Mathematics majors, covering the required calculus sequence, abstract algebra, and STEM electives. | [Link](https://www.alasu.edu/_qa/CSTEM%20Mathematics%20B.S..pdf) |
| 10 | ASU Biology Pre-Health Curriculum Sequence (PDF) | Outlines the required biology core, chemistry prerequisites, and mandatory laboratory hours for Biology majors on a pre-health track. | [Link](https://www.alasu.edu/_qa/Biology%20Pre-Health%20Sequence.pdf) |
| 11 | ASU Business/Accounting Curriculum Guide (PDF) | Details the College of Business Administration (COBA) core requirements alongside specific upper-level business, finance, and accounting coursework. | [Link](https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf) |

---

## Chunking Strategy

Chunk size: 800 tokens (approximately 3,000 characters)

Overlap: 150 tokens

Reasoning: Academic catalogs and curriculum sheets are heavily structured, relying on nested headings (e.g., "College of Science" $\rightarrow$ "Biology Major" $\rightarrow$ "Pre-requisites") and dense lists of course codes. A larger chunk size of 800 tokens ensures that a complete course description—along with its specific prerequisites, credit hours, and department rules—remains intact within a single context window. The generous 150-token overlap is critical for this specific domain; it prevents standalone course codes or table rows from being orphaned from their parent category headings (such as "Required Major Electives") if a split occurs naturally mid-page. For the sparse, tabular curriculum sheets, this sizing allows the retrieval model to capture the broader degree pathway rather than pulling fragmented, out-of-context course abbreviations.

---

## Retrieval Approach

Embedding model: all-MiniLM-L6-v2 (via sentence-transformers)

Top-k: 5 chunks

Production tradeoff reflection: While all-MiniLM-L6-v2 provides excellent latency and ultra-low compute costs for local deployment, its smaller 384-dimension vector space struggles with complex, nested academic catalogs. In a production environment where cost isn't a constraint, upgrading to a larger model like text-embedding-3-large would significantly improve accuracy on domain-specific course codes and prerequisites, trading minor retrieval latency for vastly superior retrieval precision.

---

## Evaluation Plan

| # | Question | Expected answer |
| --- | --- | --- |
| 1 | According to the ASU Computer Science Curriculum Guide, what specific math courses are required as prerequisites before taking Data Structures and Algorithms? | The expected answer should explicitly list the specific math course codes (e.g., MAT 265 Calculus I or Discrete Mathematics) required before a student can enroll in Data Structures. |
| 2 | Based on the ASU Biology Pre-Health Curriculum Sequence, how many total credit hours of organic chemistry (including labs) must a student complete? | The answer should state exactly 8 credit hours, specifically broken down into Organic Chemistry I (with lab) and Organic Chemistry II (with lab). |
| 3 | In the ASU Business/Accounting Curriculum Guide, what is the minimum grade requirement for the College of Business Administration (COBA) core courses to graduate? | The answer should clearly state that a student must earn a minimum grade of "C" in all required COBA core courses. |
| 4 | According to the ASU Criminal Justice Curriculum Guide, is a senior internship or practicum required for the degree, and how many credits is it worth? | The expected answer should confirm whether the internship is mandatory and state the exact number of credit hours (e.g., 3 credits) it contributes to the major requirements. |
| 5 | Looking at the 2021-2023 ASU Undergraduate Catalog, how many total credit hours of Humanities and Fine Arts are required to satisfy the 42-hour general education core? | The answer should state exactly 12 credit hours of Humanities and Fine Arts are required for the general education core. |

---


## Anticipated Challenges
The "Missing Information" Risk (Data Gaps)

 1. Since we are only uploading a few specific curriculum sheets (like Computer Science and Biology), the RAG system won't know the answers if a student asks about a completely different major, like Nursing or Psychology. If the system isn't told how to say "I don't know," it might try to guess and give completely wrong advice based on the wrong major's documents.

2. Also we are giving the system multiple catalogs from different years, the system might easily mix them up. If a course required 3 credits in 2019 but requires 4 credits today, the system might accidentally pull the old text chunk and give the student outdated information that delays their graduation.

---

## Architecture

+-------------------------------------------------------+
  | 1. DOCUMENT INGESTION                                 |
  | Content: ASU PDF Catalogs & Curriculum Sheets         |
  | Tools: PyPDFLoader (LangChain) or PyMuPDF             |
  +-------------------------------------------------------+
                           |
                           v
  +-------------------------------------------------------+
  | 2. CHUNKING                                           |
  | Config: 800 tokens, 150 token overlap                 |
  | Tools: RecursiveCharacterTextSplitter (LangChain)     |
  +-------------------------------------------------------+
                           |
                           v
  +-------------------------------------------------------+
  | 3. EMBEDDING + VECTOR STORE                           |
  | Model: all-MiniLM-L6-v2 (SentenceTransformers)        |
  | Database: ChromaDB, FAISS, or Qdrant                  |
  +-------------------------------------------------------+
                           |
                           v  <-- (User Query Enters Here)
  +-------------------------------------------------------+
  | 4. RETRIEVAL                                          |
  | Strategy: Top-k (k=5) Similarity Search               |
  | Tools: LangChain VectorStoreRetriever                 |
  +-------------------------------------------------------+
                           |
                           v  <-- (Retrieved Chunks + Query)
  +-------------------------------------------------------+
  | 5. GENERATION                                         |
  | Task: Synthesize answer using strictly the context    |
  | Tools: OpenAI (gpt-4o) or Local LLM (e.g., Llama 3)   |
  +-------------------------------------------------------+

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
AI Tool: Claude Code

Plan: I will provide Claude Code with my ASCII pipeline diagram and the chunking strategy specifying an 800-token size with a 150-token overlap. I will instruct it to generate a Python script using LangChain's PyPDFLoader and RecursiveCharacterTextSplitter to download and process the 11 ASU catalog PDFs. To verify, I will print the total chunk count and inspect the character lengths of the first few chunks to ensure the overlap behaves correctly.

**Milestone 4 — Embedding and retrieval:**
AI Tool: Claude Code

Plan: I will give Claude Code the processed chunks from Milestone 3 and ask it to write code initializing a local vector store using FAISS or ChromaDB. The script will be instructed to use the all-MiniLM-L6-v2 embedding model and configure a retriever with a top_k=5 setting. I will verify the system by running Test Question #1 and checking if the top 5 retrieved text snippets successfully contain pages from the Computer Science curriculum.

**Milestone 5 — Generation and interface:**
AI Tool: Claude Code

Plan: I will provide the retrieval function and the 5 specific evaluation questions to Claude Code, asking it to build a simple command-line interface integrated with a generation model. The prompt template will strictly instruct the LLM to reply with a fallback message if the answer is missing from the data. I will verify the output by running all 5 test questions to match against expected answers and submitting an off-topic query to ensure the data-gap safety fallback triggers properly.
