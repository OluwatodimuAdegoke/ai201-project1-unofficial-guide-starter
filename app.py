"""
ASU Unofficial Guide — Gradio Web Interface (Milestone 5)
Provides a browser-based UI for querying the RAG system.

Run:  python app.py
Then open http://localhost:7860 in your browser.

Architecture:
    Browser (Gradio UI)
        |  user types question
        v
    handle_query()
        |  calls ask() from query.py
        v
    retrieve -> ground -> generate -> cite
        |
        v
    Display: Answer box + Sources box + Retrieved chunks (debug)
"""

import sys
import gradio as gr
from query import ask

sys.stdout.reconfigure(encoding="utf-8")

# ── Core handler ──────────────────────────────────────────────────────────────

def handle_query(question: str):
    """
    Bridge between the Gradio UI and the RAG pipeline.

    Calls ask() from query.py with the user's question, then formats the
    results for display across three output components:
        1. Answer textbox — the model's grounded response.
        2. Sources textbox — bulleted list of cited PDF filenames.
        3. Debug textbox — top-5 retrieved chunks with distance scores,
           so it's easy to verify the retrieval backing each answer.

    Input:
        question (str): The question typed by the user in the Gradio UI.

    Output:
        tuple(str, str, str): (answer_text, sources_text, debug_text)
            All three are plain strings formatted for display in gr.Textbox.

    Example:
        answer, sources, debug = handle_query("How many hours of Humanities are required?")
    """
    if not question.strip():
        return (
            "Please enter a question.",
            "",
            "",
        )

    result = ask(question)

    # Format answer — strip the Sources section from the answer box
    # (we display it separately and more cleanly below)
    answer_text = result["answer"]
    if "Sources:" in answer_text:
        answer_text = answer_text.split("Sources:")[0].strip()

    # Format sources as a clean bulleted list
    if result["sources"]:
        sources_text = "\n".join(f"  {s}" for s in result["sources"])
    else:
        sources_text = "  No sources identified."

    # Format debug panel: show each retrieved chunk with rank + distance
    debug_lines = []
    for c in result["chunks"]:
        debug_lines.append(
            f"Rank {c['rank']}  |  distance: {c['distance']}  |  {c['source']}  (chunk #{c['chunk_index']})\n"
            f"{c['text'][:400]}{'...' if len(c['text']) > 400 else ''}\n"
        )
    debug_text = "\n---\n".join(debug_lines)

    return answer_text, sources_text, debug_text


# ── Gradio UI ─────────────────────────────────────────────────────────────────

example_questions = [
    "What math courses are required before taking Data Structures and Algorithms in the CS program?",
    "How many credit hours of Humanities and Fine Arts are required in the 42-hour general education core?",
    "How many total credit hours of organic chemistry including labs must a Biology Pre-Health student complete?",
    "Is a senior internship required for the Criminal Justice degree, and how many credits is it worth?",
    "What is the minimum grade required in COBA core courses to graduate?",
]

with gr.Blocks(title="ASU Unofficial Guide") as demo:

    gr.Markdown(
        """
        # ASU Unofficial Guide
        ### AI-powered curriculum assistant for Alabama State University
        Ask questions about degree requirements, course prerequisites, credit hours,
        and academic policies — sourced directly from ASU's official catalogs and curriculum guides.

        > **Note:** Answers are grounded in retrieved ASU documents only.
        > If the documents don't cover your question, the system will say so.
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            question_box = gr.Textbox(
                label="Your Question",
                placeholder="e.g. What math courses are required before Data Structures in the CS program?",
                lines=3,
            )
            with gr.Row():
                submit_btn = gr.Button("Ask", variant="primary")
                clear_btn  = gr.Button("Clear")

            gr.Examples(
                examples=example_questions,
                inputs=question_box,
                label="Example Questions",
            )

    with gr.Row():
        with gr.Column(scale=3):
            answer_box = gr.Textbox(
                label="Answer",
                lines=12,
                interactive=False,
            )
        with gr.Column(scale=1):
            sources_box = gr.Textbox(
                label="Sources (documents cited)",
                lines=12,
                interactive=False,
            )

    with gr.Accordion("Retrieved Chunks (debug view)", open=False):
        debug_box = gr.Textbox(
            label="Top-5 retrieved chunks with distance scores",
            lines=20,
            interactive=False,
        )

    # Wire up interactions
    submit_btn.click(
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box, debug_box],
    )
    question_box.submit(     # also trigger on Enter key
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box, debug_box],
    )
    clear_btn.click(
        fn=lambda: ("", "", "", ""),
        outputs=[question_box, answer_box, sources_box, debug_box],
    )

    gr.Markdown(
        """
        ---
        **How this works:** Your question is embedded with `all-MiniLM-L6-v2`, matched against
        1,283 chunks from 11 ASU PDF documents stored in ChromaDB, and the top 5 chunks are
        passed as context to `llama-3.3-70b-versatile` via Groq. The model is instructed to
        answer only from retrieved context and to decline if the information isn't there.
        """
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
