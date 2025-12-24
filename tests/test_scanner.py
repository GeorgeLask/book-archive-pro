import pytest
import os


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="No camera in CI"
)
def test_camera_initialization():
    from src.scanner import BarcodeScanner

    scanner = BarcodeScanner()
    assert scanner.camera_id == 0
