import os
from src.database import BookDatabase


def test_save_book_creates_file(tmp_path):
    # tmp_path is a built-in pytest fixture for a temporary directory
    temp_file = tmp_path / "test_library.csv"
    db = BookDatabase(file_path=str(temp_file))

    sample_data = {
        "isbn": "123",
        "title": "Το Άξιον Εστί",  # Greek test
        "authors": "Odysseas Elytis",
    }

    # Action
    db.save_book(sample_data)

    # Assert
    assert os.path.exists(temp_file)
    # Check if data was written correctly
    import pandas as pd

    df = pd.read_csv(temp_file, encoding="utf-8-sig")
    assert df.iloc[0]["title"] == "Το Άξιον Εστί"
