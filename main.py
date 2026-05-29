from src.scanner import BarcodeScanner
from src.api_client import BookAPI
from src.database import BookDatabase


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

        if book_info:
            print(f"[*] Title: {book_info['title']} ({book_info['language']})")

            # 2. Save to the CSV database
            db.save_book(book_info)
            processed_isbns.add(isbn)
            print("[✔] Saved to archive.")
        else:
            print(f"[!] Metadata not found for ISBN {isbn}. Skipping...")


def main():
    """The entry point: Handles configuration and initialization."""
    # Initialization
    scanner = BarcodeScanner()
    api = BookAPI()
    db = BookDatabase("data/library.csv")

    try:
        run_archiver(scanner, api, db)
    except KeyboardInterrupt:
        print("\n[!] User interrupted the process.")
    except Exception as e:
        print(f"\n[X] A critical error occurred: {e}")
    finally:
        print("\nClosing Archive. Happy Reading!")


if __name__ == "__main__":
    main()
