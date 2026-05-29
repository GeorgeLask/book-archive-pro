import requests

from src.api_client import BookAPI


def _mock_response(mocker, payload):
    resp = mocker.Mock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_by_isbn_google_success(mocker):
    api = BookAPI()
    mock_response = _mock_response(
        mocker,
        {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Zorba the Greek",
                        "authors": ["Nikos Kazantzakis"],
                        "language": "el",
                    }
                }
            ]
        },
    )
    mocker.patch("requests.get", return_value=mock_response)

    result = api.fetch_by_isbn("9780571050803")

    assert result["title"] == "Zorba the Greek"
    assert result["authors"] == "Nikos Kazantzakis"
    assert result["language"] == "el"
    assert result["source"] == "google"


def test_falls_back_to_openlibrary_when_google_empty(mocker):
    api = BookAPI()
    isbn = "9789601678375"

    google_resp = _mock_response(mocker, {})  # no "items"
    ol_resp = _mock_response(
        mocker,
        {
            f"ISBN:{isbn}": {
                "title": "Hē phonissa",
                "authors": [{"name": "Alexandros Papadiamantēs"}],
                "publishers": [{"name": "Hestia"}],
                "publish_date": "2018",
                "number_of_pages": 330,
                "subjects": [{"name": "Greek fiction"}],
            }
        },
    )
    # First call (Google) returns empty, second call (OpenLibrary) returns data.
    mocker.patch("requests.get", side_effect=[google_resp, ol_resp])

    result = api.fetch_by_isbn(isbn)

    assert result["title"] == "Hē phonissa"
    assert result["authors"] == "Alexandros Papadiamantēs"
    assert result["publisher"] == "Hestia"
    assert result["page_count"] == 330
    assert result["source"] == "openlibrary"


def test_fetch_by_isbn_not_found_anywhere(mocker):
    api = BookAPI()
    empty = _mock_response(mocker, {})
    mocker.patch("requests.get", return_value=empty)

    assert api.fetch_by_isbn("0000000000") is None


def test_continues_to_fallback_on_connection_error(mocker):
    api = BookAPI()
    isbn = "123"
    ol_resp = _mock_response(
        mocker,
        {f"ISBN:{isbn}": {"title": "Recovered", "authors": [{"name": "X"}]}},
    )
    # Google raises a network error; the chain should move on to OpenLibrary.
    mocker.patch(
        "requests.get",
        side_effect=[requests.exceptions.ConnectionError("boom"), ol_resp],
    )

    result = api.fetch_by_isbn(isbn)

    assert result["title"] == "Recovered"
    assert result["source"] == "openlibrary"
