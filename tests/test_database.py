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


def test_load_isbns_empty_when_no_file(tmp_path):
    db = BookDatabase(file_path=str(tmp_path / "missing.csv"))
    assert db.load_isbns() == set()


def test_load_isbns_and_exists(tmp_path):
    db = BookDatabase(file_path=str(tmp_path / "lib.csv"))
    db.save_book({"isbn": "123", "title": "A"})
    db.save_book({"isbn": "456", "title": "B"})

    assert db.load_isbns() == {"123", "456"}
    assert db.exists("123") is True
    assert db.exists("999") is False


def test_exists_treats_isbn_as_string(tmp_path):
    # ISBNs are long numeric strings; make sure leading-zero / int coercion
    # does not break matching.
    db = BookDatabase(file_path=str(tmp_path / "lib.csv"))
    db.save_book({"isbn": "9780141184852", "title": "Gatsby"})
    assert db.exists(9780141184852) is True
