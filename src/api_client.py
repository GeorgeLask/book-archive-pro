import requests


class BookAPI:
    """Handles communication with the Google Books API."""

    def __init__(self):
        self.base_url = "https://www.googleapis.com/books/v1/volumes"

    def fetch_by_isbn(self, isbn: str):
        """Fetches book metadata using an ISBN string."""
        params = {"q": f"isbn:{isbn}"}
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "items" in data:
                # We take the first result as it's usually the most accurate
                volume_info = data["items"][0]["volumeInfo"]

                return {
                    "isbn": isbn,
                    "title": volume_info.get("title", "N/A"),
                    "authors": ", ".join(volume_info.get("authors", ["Unknown"])),
                    "publisher": volume_info.get("publisher", "N/A"),
                    "published_date": volume_info.get("publishedDate", "N/A"),
                    "language": volume_info.get("language", "unknown"),
                    "page_count": volume_info.get("pageCount", 0),
                    "categories": ", ".join(volume_info.get("categories", ["N/A"]))
                }
            return None
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return None