import requests

from src.api_client import BookAPI


def _mock_response(mocker, payload):
    resp = mocker.Mock()
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _mock_429(mocker):
    resp = mocker.Mock()
    resp.status_code = 429
    resp.headers = {}
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
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


def test_merges_openlibrary_into_google_gaps(mocker):
    api = BookAPI()
    isbn = "123"

    # Google has core fields but lacks publisher / pages / categories.
    google = _mock_response(
        mocker,
        {
            "items": [
                {
                    "volumeInfo": {
                        "title": "The Book",
                        "authors": ["An Author"],
                        "published_date": "2020",
                        "language": "en",
                    }
                }
            ]
        },
    )
    ol = _mock_response(
        mocker,
        {
            f"ISBN:{isbn}": {
                "title": "The Book",
                "publishers": [{"name": "Faber"}],
                "number_of_pages": 200,
                "subjects": [{"name": "Fiction"}],
            }
        },
    )
    mocker.patch("requests.get", side_effect=[google, ol])

    result = api.fetch_by_isbn(isbn)

    # Google stays the base (source/title/language), OpenLibrary fills the gaps.
    assert result["source"] == "google"
    assert result["language"] == "en"
    assert result["publisher"] == "Faber"
    assert result["page_count"] == 200
    assert result["categories"] == "Fiction"


def test_google_retries_on_429_then_succeeds(mocker):
    api = BookAPI()
    sleep = mocker.patch("time.sleep")

    success = _mock_response(
        mocker, {"items": [{"volumeInfo": {"title": "Recovered", "language": "en"}}]}
    )
    # Google: rate-limited then succeeds; OpenLibrary then queried to fill gaps.
    ol_empty = _mock_response(mocker, {})
    mocker.patch("requests.get", side_effect=[_mock_429(mocker), success, ol_empty])

    result = api.fetch_by_isbn("123")

    assert result["title"] == "Recovered"
    assert result["source"] == "google"
    sleep.assert_called_once()  # backed off before retrying


def test_google_exhausts_retries_then_falls_back(mocker):
    api = BookAPI()
    mocker.patch("time.sleep")
    isbn = "123"

    ol = _mock_response(
        mocker, {f"ISBN:{isbn}": {"title": "From OL", "authors": [{"name": "X"}]}}
    )
    # Google returns 429 for the initial call + every retry, then OpenLibrary.
    google_429s = [_mock_429(mocker) for _ in range(BookAPI.MAX_RETRIES + 1)]
    mocker.patch("requests.get", side_effect=google_429s + [ol])

    result = api.fetch_by_isbn(isbn)

    assert result["source"] == "openlibrary"


def test_api_key_added_when_env_set(mocker, monkeypatch):
    monkeypatch.setenv("GOOGLE_BOOKS_API_KEY", "secret123")
    api = BookAPI()
    get = mocker.patch(
        "requests.get",
        return_value=_mock_response(
            mocker, {"items": [{"volumeInfo": {"title": "T"}}]}
        ),
    )

    api.fetch_by_isbn("123")

    # The Google request (to GOOGLE_URL) should carry the key.
    google_calls = [
        c for c in get.call_args_list if c.args and c.args[0] == BookAPI.GOOGLE_URL
    ]
    assert google_calls
    assert google_calls[0].kwargs["params"].get("key") == "secret123"


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
