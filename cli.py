"""
ASU Unofficial Guide — Command Line Interface (Milestone 5)
Interactive CLI for querying the RAG system from the terminal.

Run:
    python cli.py

Commands during session:
    Type any question and press Enter to get an answer.
    Type 'quit' or 'exit' to end the session.
    Type 'debug' to toggle the retrieved chunks panel on/off.
    Type 'help' to see these commands again.
"""

import sys
from query import ask

sys.stdout.reconfigure(encoding="utf-8")

DIVIDER      = "=" * 70
THIN_DIVIDER = "-" * 70


def print_help():
    """Print available CLI commands."""
    print(f"""
  Commands:
    <question>   Ask anything about ASU curriculum and requirements
    debug        Toggle display of retrieved chunks and distance scores
    help         Show this message
    quit / exit  End the session
""")


def print_result(result: dict, show_debug: bool) -> None:
    """
    Print a formatted RAG result to the terminal.

    Displays the answer with the Sources section separated out cleanly,
    and optionally prints the retrieved chunks with distance scores.

    Input:
        result     (dict): Return value from ask() — contains "answer",
                           "sources", and "chunks" keys.
        show_debug (bool): If True, print retrieved chunks below the answer.

    Output:
        None. Prints to stdout only.
    """
    answer_text = result["answer"]

    # Separate the answer body from the Sources section for cleaner display
    if "Sources:" in answer_text:
        body, _, sources_section = answer_text.partition("Sources:")
        body = body.strip()
        sources_section = sources_section.strip()
    else:
        body = answer_text.strip()
        sources_section = None

    print(f"\n  ANSWER\n  {THIN_DIVIDER}")
    for line in body.split("\n"):
        print(f"  {line}")

    print(f"\n  SOURCES")
    if result["sources"]:
        for s in result["sources"]:
            print(f"    * {s}")
    else:
        print("    (none identified)")

    if show_debug:
        print(f"\n  RETRIEVED CHUNKS  {THIN_DIVIDER}")
        for c in result["chunks"]:
            print(f"\n  Rank {c['rank']}  |  distance: {c['distance']}  |  "
                  f"{c['source']}  (chunk #{c['chunk_index']})")
            preview = c["text"][:400]
            if len(c["text"]) > 400:
                preview += " ..."
            for line in preview.split("\n"):
                print(f"    {line}")


def run_cli() -> None:
    """
    Start the interactive CLI session.

    Loads the embedding model, ChromaDB collection, and Groq client once
    on startup (via the first call to ask()), then loops accepting user
    questions until the user types 'quit' or 'exit'.

    Input:  None
    Output: None. All interaction is through stdin/stdout.
    """
    print(DIVIDER)
    print("  ASU Unofficial Guide — AI Curriculum Assistant")
    print("  Powered by: all-MiniLM-L6-v2 + ChromaDB + llama-3.3-70b-versatile")
    print(DIVIDER)
    print("  Ask questions about ASU degree requirements, prerequisites,")
    print("  credit hours, and academic policies.")
    print_help()

    show_debug = False

    while True:
        try:
            raw = input("  Ask > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Goodbye!")
            break

        if not raw:
            continue

        cmd = raw.lower()

        if cmd in ("quit", "exit"):
            print("\n  Goodbye!")
            break
        elif cmd == "help":
            print_help()
            continue
        elif cmd == "debug":
            show_debug = not show_debug
            state = "ON" if show_debug else "OFF"
            print(f"\n  Debug mode {state} — retrieved chunks will "
                  f"{'now' if show_debug else 'no longer'} be shown.\n")
            continue

        # It's a question — run the full RAG pipeline
        print(f"\n  {THIN_DIVIDER}")
        print(f"  Retrieving and generating answer ...")
        print(f"  {THIN_DIVIDER}")

        result = ask(raw)
        print_result(result, show_debug)
        print(f"\n{DIVIDER}\n")


if __name__ == "__main__":
    run_cli()
