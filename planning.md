# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

- **Domain:** student reviews of professors at Alabama State University.

- **Why this domain:** it focuses on real student feedback about teaching style, difficulty, grading, workload, and classroom experience, which is harder to find in official course descriptions or catalogs.

---

## Documents

| #  | Source                                                    | Description                                                                              | URL or Location                                                                                                                                                                                |
| -- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Rate My Professors – Alabama State University Directory   | Main directory containing professor ratings and reviews across departments.              | [https://www.ratemyprofessors.com/search/professors/11?did=%2A&q=%2A](https://www.ratemyprofessors.com/search/professors/11?did=%2A&q=%2A)                                                     |
| 2  | Rate My Professors – Alabama State University School Page | Overall ASU professor listings and student ratings.                                      | [https://www.ratemyprofessors.com/school/11](https://www.ratemyprofessors.com/school/11)                                                                                                       |
| 3  | Reddit Search: Alabama State University Professors        | Student discussions and recommendations about ASU professors.                            | [https://www.reddit.com/search/?q=Alabama+State+University+professors](https://www.reddit.com/search/?q=Alabama+State+University+professors)                                                   |
| 4  | Reddit Search: Best ASU Professors                        | Discussions about the easiest, best, and most recommended professors.                    | [https://www.reddit.com/search/?q=Alabama+State+University+best+professors](https://www.reddit.com/search/?q=Alabama+State+University+best+professors)                                         |
| 5  | Reddit Search: Hardest ASU Classes                        | Student experiences regarding difficult courses and instructors.                         | [https://www.reddit.com/search/?q=Alabama+State+University+hardest+classes](https://www.reddit.com/search/?q=Alabama+State+University+hardest+classes)                                         |
| 6  | Reddit Search: Easiest ASU Classes                        | Discussions identifying easier classes and professors.                                   | [https://www.reddit.com/search/?q=Alabama+State+University+easiest+classes](https://www.reddit.com/search/?q=Alabama+State+University+easiest+classes)                                         |
| 7  | r/AlabamaStateUniversity                                  | University specific subreddit containing student discussions and advice.                 | [https://www.reddit.com/r/AlabamaStateUniversity/](https://www.reddit.com/r/AlabamaStateUniversity/)                                                                                           |
| 8  | College Confidential – Alabama State University Forum     | Student and prospective student discussions about courses, professors, and academics.    | [https://talk.collegeconfidential.com/c/colleges-and-universities/alabama-state-university/124](https://talk.collegeconfidential.com/c/colleges-and-universities/alabama-state-university/124) |
| 9  | Alabama State University Course Catalog                   | Official course descriptions for comparing student reviews with course expectations.     | [https://catalog.alasu.edu/](https://catalog.alasu.edu/)                                                                                                                                       |
| 10 | Alabama State University Class Search                     | Official class schedule and instructor listings used to identify professors and courses. | [https://ssb-prod.ec.alasu.edu/StudentRegistrationSsb/ssb/classSearch/classSearch](https://ssb-prod.ec.alasu.edu/StudentRegistrationSsb/ssb/classSearch/classSearch)                           |


---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->
Chunk Size	400–500 tokens
Overlap Size	75–100 tokens
Chunking Method	Paragraph based with overlap
Document Types	Professor reviews, Reddit posts, forum discussions, and course evaluations

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

Embedding model:
all-MiniLM-L6-v2 from the sentence-transformers library. This model generates 384-dimensional embeddings and provides a good balance between retrieval quality, speed, and computational efficiency for a student review dataset.

Top-k:
Top-k = 5

The system will retrieve the 5 most relevant chunks for each query before passing them to the language model. Since professor reviews are relatively short and focused, retrieving five chunks should provide enough evidence to identify consistent patterns without introducing too much irrelevant information.

Production tradeoff reflection:
If cost were not a constraint, I would consider using a more powerful embedding model such as BAAI/bge-large-en-v1.5, intfloat/e5-large-v2, or OpenAI's text embedding models.

---

## Evaluation Plan
| # | Question                                                                                                                         | Expected Answer                                                                                                                                                                                       |
| - | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Which biology professor at Alabama State University is most frequently described as easy to pass and generous with extra credit? | Komal Vig. Multiple reviews mention extra credit opportunities, clear grading criteria, and that students who pay attention can pass the class relatively easily. ([Rate My Professors][1])           |
| 2 | Which biology professor is most often praised for explaining material that appears directly on exams?                            | Shuntele Burns. Students report that her lectures closely match exam content and that consistent studying leads to success in the course. ([Rate My Professors][2])                                   |
| 3 | Which biology professor receives the most complaints about communication and difficult coursework?                               | Ronald Mcmillion. Reviews frequently describe the course as lecture heavy, homework intensive, test heavy, and criticize communication. ([Rate My Professors][3])                                     |
| 4 | What do students say about Professor Phillip Blackmon's English courses?                                                         | Students report that his classes involve many papers rather than traditional exams. Reviews also mention detailed feedback and relatively moderate difficulty. ([Rate My Professors][4])              |
| 5 | Which Alabama State University professors appear among the highest rated on Rate My Professors?                                  | Examples include Margie Thomas (Education), Paris Chisholm (Mathematics), and Lamya Almas, all of whom show high quality ratings and strong "would take again" percentages. ([Rate My Professors][5]) |

[1]: https://www.ratemyprofessors.com/professor/1708865?utm_source=chatgpt.com "Komal Vig at Alabama State University | Rate My Professors"
[2]: https://www.ratemyprofessors.com/professor/1970314?utm_source=chatgpt.com "Shuntele Burns at Alabama State University | Rate My Professors"
[3]: https://www.ratemyprofessors.com/professor/2238290?utm_source=chatgpt.com "Ronald Mcmillion at Alabama State University | Rate My Professors"
[4]: https://www.ratemyprofessors.com/professor/2178392?utm_source=chatgpt.com "Phillip Blackmon at Alabama State University | Rate My Professors"
[5]: https://www.ratemyprofessors.com/search/professors/11?did=%2A&q=%2A&utm_source=chatgpt.com "Search professors at Alabama State University | Rate My Professors"

---

## Anticipated Challenges

Inconsistent or biased student reviews
Professor reviews are subjective and often based on individual experiences. One student may describe a professor as helpful and fair, while another may describe the same professor as difficult or unfair. This can lead the system to generate conclusions that do not accurately represent the overall student experience if the retrieved reviews are not balanced.
Off-topic or incomplete retrieval due to chunking
Important information about a professor may be split across multiple reviews or separated by chunk boundaries. For example, one part of a review may discuss teaching quality while the next discusses grading policies. If only one chunk is retrieved, the system may miss important context and provide an incomplete or misleading answer.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---
┌─────────────────────┐
│ Document Ingestion  │
│ RMP, Reddit, Forums │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Chunking       │
│ 400-500 tokens      │
│ 100 overlap         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Embeddings          │
│ all-MiniLM-L6-v2    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ChromaDB            │
│ Vector Store        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Retrieval           │
│ Similarity Search   │
│ Top-k = 5           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Generation          │
│ GPT + Retrieved     │
│ Review Chunks       │
└─────────────────────┘


## AI Tool Plan

Milestone 3 — Ingestion and chunking:

AI Tool: Claude

Input: I will provide Claude with my domain description, source list (Rate My Professors, Reddit, forums, course evaluations), and chunking strategy specifying a chunk size of 400–500 tokens with a 75–100 token overlap.

Expected Output: Python code that loads text documents, cleans the text, and chunks the documents using a recursive text splitter while preserving paragraph boundaries when possible.

Verification: I will test the code on several source documents and confirm that:

Chunks are approximately 400–500 tokens.
Consecutive chunks contain the specified overlap.
Reviews are not unnecessarily split in the middle of sentences.
The total number of chunks matches expectations.

Milestone 4 — Embedding and retrieval:

AI Tool: Claude

Input: I will provide Claude with my embedding model choice (all-MiniLM-L6-v2), vector database choice (ChromaDB), retrieval requirement (top-k = 5), and pipeline diagram.

Expected Output: Python code that generates embeddings for all chunks, stores them in ChromaDB, and implements a retrieval function that returns the five most relevant chunks for a user query.

Verification: I will test the retrieval system using my five evaluation questions and verify that:

The returned chunks are relevant to the query.
The system consistently returns five results.
Retrieved chunks contain information needed to answer the question.
Similar queries produce similar retrieval results.

Milestone 5 — Generation and interface:

AI Tool: Claude

Input: I will provide Claude with my retrieval function, evaluation questions, expected answers, and requirement to generate answers only from retrieved context.

Expected Output: A Retrieval Augmented Generation (RAG) application that accepts user questions, retrieves relevant chunks, sends them to an LLM, and generates a response with supporting evidence from the retrieved documents.

Verification: I will evaluate the system using the five test questions and compare the generated answers against my expected answers. I will also verify that:

Responses are based on retrieved documents rather than hallucinated information.
Answers reference information found in the source material.
The interface accepts queries and returns responses correctly.
Retrieved context aligns with the final generated answer.