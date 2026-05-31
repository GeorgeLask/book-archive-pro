# 📚 Book Archive Pro

A Python tool for cataloguing your book collection. Scan ISBN barcodes with
your webcam, fetch metadata automatically, and manage everything from the
command line.

## ✨ Features
- **Real-time barcode scanning** — OpenCV + pyzbar.
- **Automated metadata** — Google Books with an OpenLibrary fallback, plus
  manual entry when neither has the book.
- **Duplicate-safe** — books already in the archive are skipped across runs.
- **Collection management** — list, search, stats, remove, and status
  tracking (`collection` / `wishlist` / `read` / `lent`) from the CLI.
- **Greek language support** — UTF-8-sig encoding for clean Excel display.

## 🛠 Installation

### 1. System requirements (macOS)
The barcode engine needs the `zbar` C library, which Poetry cannot install:
```bash
brew install zbar
```

### 2. Python dependencies
```bash
poetry install --no-root
```

### 3. macOS note
On Apple Silicon, pyzbar can't find the Homebrew `zbar` library on the default
loader path. The app handles this automatically — when you run `scan` it adds
`/opt/homebrew/lib` to the loader path and relaunches itself — so no extra
setup or environment variables are needed.

### Google Books API key (optional)
Metadata lookups use Google Books (anonymous), falling back to OpenLibrary.
Anonymous Google requests are rate-limited and can return `429 Too Many
Requests` when scanning several books quickly; the app retries with backoff
and then falls back. To raise the limit, set an API key:
```bash
export GOOGLE_BOOKS_API_KEY=your_key_here
```

## 🚀 Usage

```bash
python main.py <command> [options]
```

| Command | Description |
|---|---|
| `scan` | Scan barcodes and archive books (default if no command given). |
| `list [--status S]` | List archived books, optionally filtered by status. |
| `search <query>` | Search by ISBN, title, or author. |
| `stats` | Show collection statistics. |
| `export <path> [--status S]` | Export the collection (optionally filtered). A `.xlsx` path writes a formatted Excel workbook; any other extension writes a UTF-8 CSV. |
| `remove <isbn>` | Remove a book by ISBN. |
| `clear [--status S] [--yes]` | Remove all books (or all with a status). Asks to confirm unless `--yes`. |
| `set-status <isbn> <status>` | Set a book's status. |

`--status` / `<status>` is one of `collection`, `wishlist`, `read`, `lent`.
Use `--file PATH` to point at a different archive (default `data/library.csv`).

### Examples
```bash
python main.py scan
python main.py list --status wishlist
python main.py search kazantzakis
python main.py stats
python main.py export my_books.xlsx              # formatted Excel workbook
python main.py export wishlist.xlsx --status wishlist
python main.py export my_books.csv               # plain CSV
python main.py set-status 9789601678375 read
python main.py remove 9789601678375
```

## 🧪 Development

```bash
poetry run pytest        # run the test suite
poetry run ruff check .  # lint
poetry run black .       # format
```

The CI pipeline (GitHub Actions) runs ruff, a black formatting check, and the
full test suite on every push and pull request to `main`.
