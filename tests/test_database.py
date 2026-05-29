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


def test_save_migrates_old_rows_to_current_schema(tmp_path):
    import pandas as pd

    # Simulate a legacy file with the original 8-column schema (no
    # status/source) — the shape of the real data/library.csv.
    legacy = tmp_path / "lib.csv"
    pd.DataFrame(
        [
            {
                "isbn": "111",
                "title": "Old Book",
                "authors": "A",
                "publisher": "P",
                "published_date": "2000",
                "language": "el",
                "page_count": 100,
                "categories": "Fiction",
            }
        ]
    ).to_csv(legacy, index=False, encoding="utf-8-sig")

    db = BookDatabase(file_path=str(legacy))
    db.save_book({"isbn": "222", "title": "New Book", "source": "google"})

    df = pd.read_csv(legacy, encoding="utf-8-sig", dtype={"isbn": str})

    # Columns are now the full canonical schema, in order, with no misalignment.
    assert list(df.columns) == BookDatabase.SCHEMA
    old = df[df["isbn"] == "111"].iloc[0]
    assert old["title"] == "Old Book"
    assert old["status"] == "collection"  # backfilled default
    assert old["source"] == "unknown"  # backfilled default
    new = df[df["isbn"] == "222"].iloc[0]
    assert new["source"] == "google"


def _seed(tmp_path):
    db = BookDatabase(file_path=str(tmp_path / "lib.csv"))
    db.save_book(
        {"isbn": "111", "title": "Zorba", "authors": "Kazantzakis", "language": "el"}
    )
    db.save_book(
        {"isbn": "222", "title": "1984", "authors": "Orwell", "language": "en"},
        status="wishlist",
    )
    return db


def test_load_all_empty_has_schema_columns(tmp_path):
    db = BookDatabase(file_path=str(tmp_path / "none.csv"))
    df = db.load_all()
    assert df.empty
    assert list(df.columns) == BookDatabase.SCHEMA


def test_search_matches_title_author_isbn(tmp_path):
    db = _seed(tmp_path)
    assert set(db.search("zorba")["isbn"]) == {"111"}
    assert set(db.search("orwell")["isbn"]) == {"222"}
    assert set(db.search("222")["isbn"]) == {"222"}
    assert db.search("nonexistent").empty


def test_remove(tmp_path):
    db = _seed(tmp_path)
    assert db.remove("111") is True
    assert db.exists("111") is False
    assert db.exists("222") is True
    assert db.remove("999") is False


def test_set_status(tmp_path):
    db = _seed(tmp_path)
    assert db.set_status("111", "read") is True
    df = db.load_all()
    assert df[df["isbn"] == "111"].iloc[0]["status"] == "read"
    assert db.set_status("999", "read") is False


def test_exists_treats_isbn_as_string(tmp_path):
    # ISBNs are long numeric strings; make sure leading-zero / int coercion
    # does not break matching.
    db = BookDatabase(file_path=str(tmp_path / "lib.csv"))
    db.save_book({"isbn": "9780141184852", "title": "Gatsby"})
    assert db.exists(9780141184852) is True
