import pytest

from main import run_archiver, manual_entry


@pytest.fixture(autouse=True)
def _silence_sound(mocker):
    """Stop tests from actually playing audio; return the mock for assertions."""
    return mocker.patch("main.play_sound")


def test_run_archiver_flow(mocker):
    # 1. ARRANGE: Create mocks for our three components
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()

    # Start with an empty archive so the scanned book is treated as new
    mock_db.load_isbns.return_value = set()

    # Tell the mock scanner to return exactly one ISBN then stop
    mock_scanner.scan.return_value = ["9780141184852"]

    # Tell the mock API what to return for that ISBN
    mock_api.fetch_by_isbn.return_value = {
        "isbn": "9780141184852",
        "title": "The Great Gatsby",
        "authors": "F. Scott Fitzgerald",
        "language": "en",
    }

    # 2. ACT: Run the logic with our mocks
    # We use a trick to stop the infinite loop:
    # the scanner only yields one item.
    run_archiver(mock_scanner, mock_api, mock_db)

    # 3. ASSERT: Verify the 'Glue' worked
    mock_api.fetch_by_isbn.assert_called_once_with("9780141184852")
    mock_db.save_book.assert_called_once()


def test_run_archiver_skips_known_isbn(mocker):
    # A book already in the archive should not be fetched or saved again.
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()

    isbn = "9780141184852"
    mock_db.load_isbns.return_value = {isbn}
    mock_scanner.scan.return_value = [isbn]

    run_archiver(mock_scanner, mock_api, mock_db)

    mock_api.fetch_by_isbn.assert_not_called()
    mock_db.save_book.assert_not_called()


def test_manual_entry_accepts_book():
    answers = iter(["y", "The Odyssey", "Homer"])
    result = manual_entry("123", input_fn=lambda _: next(answers))

    assert result["isbn"] == "123"
    assert result["title"] == "The Odyssey"
    assert result["authors"] == "Homer"
    assert result["source"] == "manual"


def test_manual_entry_declined_returns_none():
    assert manual_entry("123", input_fn=lambda _: "n") is None


def test_manual_entry_blank_title_returns_none():
    answers = iter(["y", "   "])
    assert manual_entry("123", input_fn=lambda _: next(answers)) is None


def test_manual_entry_defaults_unknown_author():
    answers = iter(["yes", "Some Title", ""])
    result = manual_entry("123", input_fn=lambda _: next(answers))
    assert result["authors"] == "Unknown"


def test_run_archiver_uses_manual_entry_on_api_miss(mocker):
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()

    isbn = "555"
    mock_db.load_isbns.return_value = set()
    mock_scanner.scan.return_value = [isbn]
    mock_api.fetch_by_isbn.return_value = None  # both providers miss

    manual = {"isbn": isbn, "title": "Typed", "language": "unknown"}
    mocker.patch("main.manual_entry", return_value=manual)

    run_archiver(mock_scanner, mock_api, mock_db)

    mock_db.save_book.assert_called_once_with(manual)


def test_plays_ok_sound_on_save(mocker, _silence_sound):
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()
    mock_db.load_isbns.return_value = set()
    mock_scanner.scan.return_value = ["123"]
    mock_api.fetch_by_isbn.return_value = {"title": "T", "language": "en"}

    run_archiver(mock_scanner, mock_api, mock_db)

    _silence_sound.assert_called_with("ok")


def test_plays_error_sound_when_skipped(mocker, _silence_sound):
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()
    mock_db.load_isbns.return_value = set()
    mock_scanner.scan.return_value = ["123"]
    mock_api.fetch_by_isbn.return_value = None
    mocker.patch("main.manual_entry", return_value=None)  # user skips

    run_archiver(mock_scanner, mock_api, mock_db)

    _silence_sound.assert_called_with("error")
