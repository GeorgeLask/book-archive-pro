import argparse

import pandas as pd

from src.api_client import BookAPI
from src.database import BookDatabase


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
            print(f"\n[=] ISBN {isbn} already in collection. Skipping.")
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
        else:
            print(f"[!] Skipping ISBN {isbn}.")


STATUSES = ["collection", "wishlist", "read", "lent"]

# Columns shown in list/search tables (the full schema is still stored).
DISPLAY_COLUMNS = ["isbn", "title", "authors", "language", "status"]


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
    # Imported lazily so the management commands don't require the camera /
    # zbar stack just to list or search the collection.
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

    print("\nBy status:")
    for status, count in df["status"].value_counts().items():
        print(f"  {status}: {count}")

    print("\nBy language:")
    for lang, count in df["language"].value_counts().items():
        print(f"  {lang}: {count}")

    print("\nTop authors:")
    for author, count in df["authors"].value_counts().head(5).items():
        print(f"  {author}: {count}")


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

    p_remove = sub.add_parser("remove", help="Remove a book by ISBN.")
    p_remove.add_argument("isbn", help="ISBN to remove.")

    p_status = sub.add_parser("set-status", help="Set a book's status.")
    p_status.add_argument("isbn", help="ISBN to update.")
    p_status.add_argument("status", choices=STATUSES, help="New status.")

    return parser


COMMANDS = {
    "scan": cmd_scan,
    "list": cmd_list,
    "search": cmd_search,
    "stats": cmd_stats,
    "remove": cmd_remove,
    "set-status": cmd_set_status,
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
