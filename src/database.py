import pandas as pd
import os


class BookDatabase:
    def __init__(self, file_path="data/library.csv"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save_book(self, book_data: dict, status="collection"):
        """
        Appends book data with a status.
        Uses a comma separator but forces quoting to prevent Excel cell merging.
        """
        book_data["status"] = status
        df = pd.DataFrame([book_data])

        file_exists = os.path.isfile(self.file_path)

        # We use 'utf-8-sig' and quote all strings so Excel separates them correctly
        df.to_csv(
            self.file_path,
            mode="a",
            index=False,
            header=not file_exists,
            encoding="utf-8-sig",
            sep=",",  # Standard comma
            quoting=1,  # Quote All: forces Excel to see separate cells
        )
        return True
