import argparse
import os
import shutil
import subprocess
import sys

import pandas as pd

from src.api_client import BookAPI
from src.database import BookDatabase

# Short sounds played as scan feedback (macOS system sounds).
_SOUNDS = {
    "ok": "/System/Library/Sounds/Glass.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
}


def play_sound(kind="ok"):
    """
    Plays a short confirmation sound so you know when to move the book away.
    Best-effort and non-blocking: uses macOS `afplay` when available, falls
    back to the terminal bell, and never raises.
    """
    try:
        path = _SOUNDS.get(kind)
        if sys.platform == "darwin" and path and shutil.which("afplay"):
            subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


# On Apple Silicon, pyzbar can't find the Homebrew `zbar` library because
# /opt/homebrew/lib isn't on the dynamic loader's search path.
_ZBAR_LIB_DIR = "/opt/homebrew/lib"


def _ensure_zbar_on_path():
    """
    DYLD_LIBRARY_PATH is read by the loader only at process start, so adding it
    at runtime is not enough: we set it and re-exec the process once. The
    membership check prevents an infinite loop. No-op off macOS or if the
    directory is absent, so Linux and CI are unaffected.
    """
    if sys.platform != "darwin" or not os.path.isdir(_ZBAR_LIB_DIR):
        return
    if _ZBAR_LIB_DIR in os.environ.get("DYLD_LIBRARY_PATH", "").split(":"):
        return
    existing = os.environ.get("DYLD_LIBRARY_PATH", "")
    os.environ["DYLD_LIBRARY_PATH"] = (
        f"{_ZBAR_LIB_DIR}:{existing}" if existing else _ZBAR_LIB_DIR
    )
    os.execv(sys.executable, [sys.executable] + sys.argv)


def manual_entry(isbn, input_fn=input):
    """
    Prompts the user to type book details when no API has the ISBN.
    Returns a metadata dict, or None if the user chooses to skip
    (declines or leaves the title blank).
    """
    answer = input_fn("    Add this book manually? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        return None

    title = input_fn("    Title: ").strip()
    if not title:
        print("    No title entered; skipping.")
        return None

    authors = input_fn("    Author(s): ").strip() or "Unknown"
    return {
        "isbn": isbn,
        "title": title,
        "authors": authors,
        "publisher": "N/A",
        "published_date": "N/A",
        "language": "unknown",
        "page_count": 0,
        "categories": "N/A",
        "source": "manual",
    }


def run_archiver(scanner, api, db):
    """
    The Business Logic: Orchestrates the flow between
    hardware (scanner), web (api), and storage (db).
    """
    # Seed from the existing archive so books scanned in previous runs are
    # recognised as duplicates, not re-added.
    processed_isbns = db.load_isbns()

    print("--- Professional Book Archiver Initialized ---")
    print(f"Archive contains {len(processed_isbns)} book(s).")
    print("Scanner active. Press 'q' in the window or Ctrl+C here to stop.")

    for isbn in scanner.scan():
        if isbn in processed_isbns:
            # Already logged: still confirm so you know to move the book away.
            print(f"\n[=] ISBN {isbn} already in collection. Skipping.")
            play_sound("ok")
            continue

        print(f"\n[+] Found ISBN: {isbn}")

        # 1. Fetch metadata from Google Books
        book_info = api.fetch_by_isbn(isbn)

        if not book_info:
            print(f"[!] Metadata not found for ISBN {isbn}.")
            book_info = manual_entry(isbn)

        if book_info:
            print(f"[*] Title: {book_info['title']} ({book_info['language']})")

            # 2. Save to the CSV database
            db.save_book(book_info)
            processed_isbns.add(isbn)
            print("[✔] Saved to archive.")
            play_sound("ok")
        else:
            print(f"[!] Skipping ISBN {isbn}.")
            play_sound("error")


STATUSES = ["collection", "wishlist", "read", "lent"]

# Columns shown in list/search tables (the full schema is still stored).
DISPLAY_COLUMNS = ["isbn", "title", "authors", "language", "status", "rating"]


def _print_table(df):
    """Prints a DataFrame as a simple table, or a friendly empty message."""
    if df.empty:
        print("No books found.")
        return
    columns = [c for c in DISPLAY_COLUMNS if c in df.columns]
    print(df[columns].to_string(index=False))
    print(f"\n{len(df)} book(s).")


def cmd_scan(db, args):
    """Runs the interactive barcode-scanning archiver."""
    # Make sure the zbar library is loadable, then import lazily so the
    # management commands don't require the camera / zbar stack at all.
    _ensure_zbar_on_path()
    from src.scanner import BarcodeScanner

    scanner = BarcodeScanner()
    api = BookAPI()
    try:
        run_archiver(scanner, api, db)
    except KeyboardInterrupt:
        print("\n[!] User interrupted the process.")
    except Exception as e:
        print(f"\n[X] A critical error occurred: {e}")
    finally:
        print("\nClosing Archive. Happy Reading!")


def cmd_list(db, args):
    """Lists the collection, optionally filtered by status."""
    df = db.load_all()
    if args.status:
        df = df[df["status"].astype(str) == args.status]
    _print_table(df)


def cmd_search(db, args):
    """Searches the collection by ISBN, title, or author."""
    _print_table(db.search(args.query))


def cmd_stats(db, args):
    """Prints summary statistics about the collection."""
    df = db.load_all()
    if df.empty:
        print("Archive is empty.")
        return

    total = len(df)
    pages = pd.to_numeric(df["page_count"], errors="coerce").fillna(0).sum()
    print(f"Total books: {total}")
    print(f"Total pages: {int(pages)}")

    ratings = pd.to_numeric(df["rating"], errors="coerce").dropna()
    if len(ratings):
        print(f"Rated books: {len(ratings)} (avg {ratings.mean():.1f}/10)")

    print("\nBy status:")
    for status, count in df["status"].value_counts().items():
        print(f"  {status}: {count}")

    print("\nBy language:")
    for lang, count in df["language"].value_counts().items():
        print(f"  {lang}: {count}")

    print("\nTop authors:")
    for author, count in df["authors"].value_counts().head(5).items():
        print(f"  {author}: {count}")


def cmd_export(db, args):
    """Exports the collection (optionally filtered) to a CSV file."""
    count = db.export_to(args.output, args.status)
    suffix = f" ({args.status})" if args.status else ""
    print(f"[✔] Exported {count} book(s){suffix} to {args.output}.")


def _parse_selection(raw, count):
    """
    Parses a user selection like "1,3 5" into a sorted list of unique 0-based
    indices within range. Invalid or out-of-range tokens are ignored.
    """
    indices = []
    for token in raw.replace(",", " ").split():
        if token.isdigit():
            n = int(token)
            if 1 <= n <= count:
                indices.append(n - 1)
    return sorted(set(indices))


def cmd_mark_read(db, args, input_fn=None):
    """Interactively pick books from the collection and mark them as read."""
    if input_fn is None:
        input_fn = input

    df = db.load_all().reset_index(drop=True)
    if df.empty:
        print("Archive is empty.")
        return

    for i, row in df.iterrows():
        title = str(row["title"])[:40]
        marker = "✓" if str(row["status"]) == "read" else " "
        print(f"{i + 1:>3}. [{marker}] {row['isbn']:<15} {title:<40}")

    raw = input_fn("\nNumber(s) to mark as read (e.g. 1,3), blank to cancel: ")
    chosen = _parse_selection(raw, len(df))
    if not chosen:
        print("Nothing selected.")
        return

    isbns = [df.iloc[i]["isbn"] for i in chosen]
    updated = db.set_status_many(isbns, "read")
    print(f"[✔] Marked {updated} book(s) as read.")


def cmd_clear(db, args, input_fn=None):
    """Removes all books, or only those with a given status (with confirmation)."""
    if input_fn is None:
        input_fn = input
    target = db.count(args.status)
    if target == 0:
        scope = f" with status '{args.status}'" if args.status else ""
        print(f"No books{scope} to clear.")
        return

    scope = f" book(s) with status '{args.status}'" if args.status else " book(s)"
    if not args.yes:
        answer = input_fn(f"Delete {target}{scope}? This cannot be undone. [y/N]: ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return

    removed = db.clear(args.status)
    print(f"[✔] Cleared {removed}{scope}.")


def cmd_remove(db, args):
    """Removes a book by ISBN."""
    if db.remove(args.isbn):
        print(f"[✔] Removed ISBN {args.isbn}.")
    else:
        print(f"[!] ISBN {args.isbn} not found.")


def cmd_set_status(db, args):
    """Updates the status of a book by ISBN."""
    if db.set_status(args.isbn, args.status):
        print(f"[✔] ISBN {args.isbn} -> {args.status}.")
    else:
        print(f"[!] ISBN {args.isbn} not found.")


def _rating_arg(value):
    """Argparse type: accept only integers in the 1-10 rating range."""
    try:
        rating = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("rating must be an integer from 1 to 10")
    if not (BookDatabase.MIN_RATING <= rating <= BookDatabase.MAX_RATING):
        raise argparse.ArgumentTypeError("rating must be between 1 and 10")
    return rating


def cmd_rate(db, args):
    """Sets a 1-10 rating for a book by ISBN."""
    if db.set_rating(args.isbn, args.rating):
        print(f"[✔] ISBN {args.isbn} rated {args.rating}/10.")
    else:
        print(f"[!] ISBN {args.isbn} not found.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Book Archive Pro - scan and manage your book collection."
    )
    parser.add_argument(
        "--file",
        default="data/library.csv",
        help="Path to the archive CSV (default: data/library.csv).",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan", help="Scan barcodes and archive books (default).")

    p_list = sub.add_parser("list", help="List archived books.")
    p_list.add_argument(
        "--status", choices=STATUSES, help="Only show books with this status."
    )

    p_search = sub.add_parser("search", help="Search by ISBN, title, or author.")
    p_search.add_argument("query", help="Text to search for.")

    sub.add_parser("stats", help="Show collection statistics.")

    p_export = sub.add_parser("export", help="Export the collection to a CSV file.")
    p_export.add_argument("output", help="Path to write the CSV to.")
    p_export.add_argument(
        "--status", choices=STATUSES, help="Only export books with this status."
    )

    p_remove = sub.add_parser("remove", help="Remove a book by ISBN.")
    p_remove.add_argument("isbn", help="ISBN to remove.")

    p_clear = sub.add_parser(
        "clear", help="Remove all books, or all books with a given status."
    )
    p_clear.add_argument(
        "--status", choices=STATUSES, help="Only clear books with this status."
    )
    p_clear.add_argument(
        "--yes", action="store_true", help="Skip the confirmation prompt."
    )

    p_status = sub.add_parser("set-status", help="Set a book's status.")
    p_status.add_argument("isbn", help="ISBN to update.")
    p_status.add_argument("status", choices=STATUSES, help="New status.")

    sub.add_parser("mark-read", help="Interactively pick books to mark as read.")

    p_rate = sub.add_parser("rate", help="Rate a book from 1 to 10.")
    p_rate.add_argument("isbn", help="ISBN to rate.")
    p_rate.add_argument("rating", type=_rating_arg, help="Rating from 1 to 10.")

    return parser


COMMANDS = {
    "scan": cmd_scan,
    "list": cmd_list,
    "search": cmd_search,
    "stats": cmd_stats,
    "export": cmd_export,
    "clear": cmd_clear,
    "remove": cmd_remove,
    "set-status": cmd_set_status,
    "mark-read": cmd_mark_read,
    "rate": cmd_rate,
}


def main(argv=None):
    """The entry point: parses arguments and dispatches to a command."""
    args = build_parser().parse_args(argv)
    db = BookDatabase(args.file)
    # Default to scanning when no subcommand is given.
    handler = COMMANDS[args.command or "scan"]
    handler(db, args)


if __name__ == "__main__":
    main()
