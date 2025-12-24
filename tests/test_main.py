from main import run_archiver


def test_run_archiver_flow(mocker):
    # 1. ARRANGE: Create mocks for our three components
    mock_scanner = mocker.Mock()
    mock_api = mocker.Mock()
    mock_db = mocker.Mock()

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
