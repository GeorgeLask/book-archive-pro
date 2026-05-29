import requests


class BookAPI:
    """
    Fetches book metadata by ISBN, trying providers in order until one
    returns a result: Google Books first, then OpenLibrary as a fallback.
    Both providers are normalised to the same metadata dict.
    """

    GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"
    OPENLIBRARY_URL = "https://openlibrary.org/api/books"

    def __init__(self):
        # The provider chain; order is the fallback priority.
        self.providers = [self._fetch_google, self._fetch_openlibrary]

    def fetch_by_isbn(self, isbn: str):
        """Returns a normalised metadata dict, or None if no provider has it."""
        for provider in self.providers:
            try:
                result = provider(isbn)
            except requests.exceptions.RequestException as e:
                print(f"Connection error ({provider.__name__}): {e}")
                continue
            if result:
                return result
        return None

    def _fetch_google(self, isbn: str):
        """Queries the Google Books API."""
        params = {"q": f"isbn:{isbn}"}
        response = requests.get(self.GOOGLE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

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
        response = requests.get(self.OPENLIBRARY_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

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
