import os
import time

import requests


class BookAPI:
    """
    Fetches book metadata by ISBN, trying providers in order until one
    returns a result: Google Books first, then OpenLibrary as a fallback.
    Both providers are normalised to the same metadata dict.

    Set the GOOGLE_BOOKS_API_KEY environment variable to use an API key,
    which raises Google's rate limit well above the anonymous quota.
    """

    GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"
    OPENLIBRARY_URL = "https://openlibrary.org/api/books"

    # Retry behaviour for HTTP 429 (Too Many Requests).
    MAX_RETRIES = 2
    INITIAL_BACKOFF = 1.0  # seconds
    MAX_BACKOFF = 10.0  # seconds

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
        # The provider chain; order is the fallback priority.
        self.providers = [self._fetch_google, self._fetch_openlibrary]

    # Metadata fields checked for completeness / gap-filling (isbn and source
    # are excluded; they aren't "missing" in a meaningful sense).
    _METADATA_FIELDS = (
        "title",
        "authors",
        "publisher",
        "published_date",
        "language",
        "page_count",
        "categories",
    )
    # Values that mean "no real data" for a field.
    _PLACEHOLDERS = {"n/a", "unknown", ""}

    def _is_missing(self, value) -> bool:
        if value in (None, 0):
            return True
        return str(value).strip().lower() in self._PLACEHOLDERS

    def _is_complete(self, book: dict) -> bool:
        return not any(self._is_missing(book.get(f)) for f in self._METADATA_FIELDS)

    def _merge(self, base: dict, extra: dict) -> dict:
        """Fills fields that are missing in `base` with values from `extra`."""
        for field in self._METADATA_FIELDS:
            if self._is_missing(base.get(field)) and not self._is_missing(
                extra.get(field)
            ):
                base[field] = extra[field]
        return base

    def fetch_by_isbn(self, isbn: str):
        """
        Returns a normalised metadata dict, or None if no provider has it.

        Providers are queried in order and their results merged so each fills
        gaps the others leave (e.g. OpenLibrary supplying a publisher Google
        lacks). Querying stops early once every field is populated.
        """
        merged = None
        for provider in self.providers:
            try:
                result = provider(isbn)
            except requests.exceptions.RequestException as e:
                print(f"Connection error ({provider.__name__}): {e}")
                continue
            if not result:
                continue
            merged = result if merged is None else self._merge(merged, result)
            if self._is_complete(merged):
                break
        return merged

    def _request(self, url, params):
        """
        GETs a URL, retrying on HTTP 429 with exponential backoff (honoring a
        numeric Retry-After header when present). Raises for other HTTP errors
        and after retries are exhausted.
        """
        delay = self.INITIAL_BACKOFF
        for attempt in range(self.MAX_RETRIES + 1):
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                retry_after = response.headers.get("Retry-After", "")
                wait = float(retry_after) if retry_after.isdigit() else delay
                time.sleep(min(wait, self.MAX_BACKOFF))
                delay *= 2
                continue
            response.raise_for_status()
            return response
        # Retries exhausted on 429: surface the error to trigger fallback.
        response.raise_for_status()
        return response

    def _fetch_google(self, isbn: str):
        """Queries the Google Books API."""
        params = {"q": f"isbn:{isbn}"}
        if self.api_key:
            params["key"] = self.api_key
        data = self._request(self.GOOGLE_URL, params).json()

        items = data.get("items")
        if not items:
            return None

        # The first result is usually the most accurate.
        volume_info = items[0]["volumeInfo"]
        return {
            "isbn": isbn,
            "title": volume_info.get("title", "N/A"),
            "authors": ", ".join(volume_info.get("authors", ["Unknown"])),
            "publisher": volume_info.get("publisher", "N/A"),
            "published_date": volume_info.get("publishedDate", "N/A"),
            "language": volume_info.get("language", "unknown"),
            "page_count": volume_info.get("pageCount", 0),
            "categories": ", ".join(volume_info.get("categories", ["N/A"])),
            "source": "google",
        }

    def _fetch_openlibrary(self, isbn: str):
        """Queries the OpenLibrary Books API as a fallback."""
        params = {
            "bibkeys": f"ISBN:{isbn}",
            "format": "json",
            "jscmd": "data",
        }
        data = self._request(self.OPENLIBRARY_URL, params).json()

        info = data.get(f"ISBN:{isbn}")
        if not info:
            return None

        authors = [a.get("name", "Unknown") for a in info.get("authors", [])]
        publishers = [p.get("name", "N/A") for p in info.get("publishers", [])]
        subjects = [s.get("name", "N/A") for s in info.get("subjects", [])]

        return {
            "isbn": isbn,
            "title": info.get("title", "N/A"),
            "authors": ", ".join(authors) if authors else "Unknown",
            "publisher": ", ".join(publishers) if publishers else "N/A",
            "published_date": info.get("publish_date", "N/A"),
            # OpenLibrary's data endpoint does not expose a language code.
            "language": "unknown",
            "page_count": info.get("number_of_pages", 0),
            "categories": ", ".join(subjects) if subjects else "N/A",
            "source": "openlibrary",
        }
