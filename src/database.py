import pandas as pd
import os


class BookDatabase:
    def __init__(self, file_path="data/library.csv"):
        self.file_path = file_path
        # Ensure the 'data' directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def save_book(self, book_data: dict):
        """
        Appends a book record to the CSV.
        Uses utf-8-sig for Greek character compatibility in Excel.
        """
        df = pd.DataFrame([book_data])

        # Check if file exists to see if we need to write the header
        file_exists = os.path.isfile(self.file_path)

        # Mode 'a' means Append
        df.to_csv(
            self.file_path,
            mode="a",
            index=False,
            header=not file_exists,
            encoding="utf-8-sig",
        )
        return True
