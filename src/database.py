import pandas as pd
import os


class BookDatabase:
    # Canonical column order. New fields are appended here over time; rows
    # written before a field existed are migrated to it on the next save.
    SCHEMA = [
        "isbn",
        "title",
        "authors",
        "publisher",
        "published_date",
        "language",
        "page_count",
        "categories",
        "source",
        "status",
    ]
    DEFAULTS = {
        "isbn": "",
        "title": "N/A",
        "authors": "Unknown",
        "publisher": "N/A",
        "published_date": "N/A",
        "language": "unknown",
        "page_count": 0,
        "categories": "N/A",
        "source": "unknown",
        "status": "collection",
    }

    def __init__(self, file_path="data/library.csv"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def load_isbns(self) -> set:
        """
        Returns the set of ISBNs already stored in the archive.
        Used to seed the in-memory dedup set so duplicates are skipped
        across separate runs. Returns an empty set if the file is missing.
        """
        if not os.path.isfile(self.file_path):
            return set()
        try:
            df = pd.read_csv(self.file_path, encoding="utf-8-sig", dtype={"isbn": str})
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return set()
        if "isbn" not in df.columns:
            return set()
        return set(df["isbn"].dropna().astype(str))

    def exists(self, isbn: str) -> bool:
        """Returns True if the given ISBN is already stored in the archive."""
        return str(isbn) in self.load_isbns()

    def save_book(self, book_data: dict, status="collection"):
        """
        Saves a book row, keeping the file aligned to the canonical SCHEMA.

        Rather than blind-appending (which misaligns columns once the schema
        grows), this reads any existing rows, migrates them to the current
        SCHEMA, appends the new row, and rewrites the whole file. utf-8-sig
        with quote-all keeps Greek text and cell boundaries correct in Excel.
        """
        row = {**self.DEFAULTS, **book_data, "status": status}
        new_row = pd.DataFrame([row], columns=self.SCHEMA)

        if os.path.isfile(self.file_path):
            existing = pd.read_csv(
                self.file_path, encoding="utf-8-sig", dtype={"isbn": str}
            )
            # Add any columns introduced after these rows were written.
            existing = existing.reindex(columns=self.SCHEMA)
            for col, default in self.DEFAULTS.items():
                existing[col] = existing[col].fillna(default)
            combined = pd.concat([existing, new_row], ignore_index=True)
        else:
            combined = new_row

        self._write(combined)
        return True

    def _write(self, df):
        """Writes the full DataFrame to disk in the canonical format."""
        df.to_csv(
            self.file_path,
            index=False,
            encoding="utf-8-sig",
            sep=",",  # Standard comma
            quoting=1,  # Quote All: forces Excel to see separate cells
        )

    def load_all(self):
        """
        Returns the whole archive as a DataFrame aligned to SCHEMA.
        An empty (but correctly-columned) frame is returned if there is
        no data yet.
        """
        if not os.path.isfile(self.file_path):
            return pd.DataFrame(columns=self.SCHEMA)
        try:
            df = pd.read_csv(self.file_path, encoding="utf-8-sig", dtype={"isbn": str})
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=self.SCHEMA)
        df = df.reindex(columns=self.SCHEMA)
        for col, default in self.DEFAULTS.items():
            df[col] = df[col].fillna(default)
        return df

    def export_to(self, path: str, status: str = None) -> int:
        """
        Writes the collection (optionally filtered by status) to `path` as a
        clean UTF-8-sig CSV. Returns the number of rows written.
        """
        df = self.load_all()
        if status:
            df = df[df["status"].astype(str) == status]
        export_dir = os.path.dirname(path)
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig", quoting=1)
        return len(df)

    def search(self, query: str):
        """
        Case-insensitive substring match against isbn, title, and authors.
        Returns a DataFrame of matching rows.
        """
        df = self.load_all()
        if df.empty:
            return df
        q = str(query).lower()
        mask = (
            df["isbn"].astype(str).str.lower().str.contains(q, na=False)
            | df["title"].astype(str).str.lower().str.contains(q, na=False)
            | df["authors"].astype(str).str.lower().str.contains(q, na=False)
        )
        return df[mask]

    def remove(self, isbn: str) -> bool:
        """Removes the row with the given ISBN. Returns True if one was removed."""
        df = self.load_all()
        target = str(isbn)
        keep = df["isbn"].astype(str) != target
        if keep.all():
            return False
        self._write(df[keep])
        return True

    def set_status(self, isbn: str, status: str) -> bool:
        """Updates the status of the given ISBN. Returns True if it was found."""
        df = self.load_all()
        target = str(isbn)
        mask = df["isbn"].astype(str) == target
        if not mask.any():
            return False
        df.loc[mask, "status"] = status
        self._write(df)
        return True
