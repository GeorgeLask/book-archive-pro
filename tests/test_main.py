from main import run_archiver


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
