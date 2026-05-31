import main


def _seed_file(tmp_path):
    from src.database import BookDatabase

    path = str(tmp_path / "lib.csv")
    db = BookDatabase(file_path=path)
    db.save_book(
        {"isbn": "111", "title": "Zorba", "authors": "Kazantzakis", "language": "el"}
    )
    db.save_book(
        {"isbn": "222", "title": "1984", "authors": "Orwell", "language": "en"},
        status="wishlist",
    )
    return path


def test_list_outputs_books(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "list"])
    out = capsys.readouterr().out
    assert "Zorba" in out
    assert "1984" in out
    assert "2 book(s)." in out


def test_list_filtered_by_status(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "list", "--status", "wishlist"])
    out = capsys.readouterr().out
    assert "1984" in out
    assert "Zorba" not in out


def test_search(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "search", "orwell"])
    out = capsys.readouterr().out
    assert "1984" in out
    assert "Zorba" not in out


def test_stats(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "stats"])
    out = capsys.readouterr().out
    assert "Total books: 2" in out
    assert "wishlist: 1" in out


def test_export(tmp_path, capsys):
    path = _seed_file(tmp_path)
    out = tmp_path / "export.csv"
    main.main(["--file", path, "export", str(out)])
    output = capsys.readouterr().out
    assert "Exported 2 book(s)" in output
    assert out.exists()


def test_export_xlsx(tmp_path, capsys):
    path = _seed_file(tmp_path)
    out = tmp_path / "books.xlsx"
    main.main(["--file", path, "export", str(out)])
    output = capsys.readouterr().out
    assert "Exported 2 book(s)" in output
    assert out.exists()


def test_export_filtered_by_status(tmp_path, capsys):
    path = _seed_file(tmp_path)
    out = tmp_path / "wishlist.csv"
    main.main(["--file", path, "export", str(out), "--status", "wishlist"])
    output = capsys.readouterr().out
    assert "Exported 1 book(s) (wishlist)" in output


def test_clear_with_yes_flag(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "clear", "--yes"])
    out = capsys.readouterr().out
    assert "Cleared 2" in out

    from src.database import BookDatabase

    assert BookDatabase(file_path=path).count() == 0


def test_clear_aborts_when_declined(tmp_path, capsys, monkeypatch):
    path = _seed_file(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    main.main(["--file", path, "clear"])
    out = capsys.readouterr().out
    assert "Aborted." in out

    from src.database import BookDatabase

    assert BookDatabase(file_path=path).count() == 2  # nothing deleted


def test_clear_confirmed_at_prompt(tmp_path, capsys, monkeypatch):
    path = _seed_file(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    main.main(["--file", path, "clear"])
    out = capsys.readouterr().out
    assert "Cleared 2" in out


def test_clear_by_status(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "clear", "--status", "wishlist", "--yes"])
    out = capsys.readouterr().out
    assert "Cleared 1 book(s) with status 'wishlist'" in out


def test_clear_empty_scope(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "clear", "--status", "read", "--yes"])
    out = capsys.readouterr().out
    assert "No books with status 'read' to clear." in out


def test_remove(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "remove", "111"])
    out = capsys.readouterr().out
    assert "Removed ISBN 111" in out

    from src.database import BookDatabase

    assert BookDatabase(file_path=path).exists("111") is False


def test_set_status(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "set-status", "111", "read"])
    out = capsys.readouterr().out
    assert "111 -> read" in out


def test_set_status_unknown_isbn(tmp_path, capsys):
    path = _seed_file(tmp_path)
    main.main(["--file", path, "set-status", "999", "read"])
    out = capsys.readouterr().out
    assert "not found" in out
