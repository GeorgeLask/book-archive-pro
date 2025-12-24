from src.api_client import BookAPI


def test_fetch_by_isbn_success(mocker):
    # 1. Setup: Create the API client
    api = BookAPI()

    # 2. Mock: Simulate a successful response from Google
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "volumeInfo": {
                    "title": "Zorba the Greek",
                    "authors": ["Nikos Kazantzakis"],
                    "language": "el",
                }
            }
        ]
    }
    mocker.patch("requests.get", return_value=mock_response)

    # 3. Action: Call the function
    result = api.fetch_by_isbn("9780571050803")

    # 4. Assert: Check if the data was parsed correctly
    assert result["title"] == "Zorba the Greek"
    assert result["authors"] == "Nikos Kazantzakis"
    assert result["language"] == "el"


def test_fetch_by_isbn_not_found(mocker):
    api = BookAPI()

    # Mock an empty result
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # No "items" key
    mocker.patch("requests.get", return_value=mock_response)

    result = api.fetch_by_isbn("0000000000")

    assert result is None
