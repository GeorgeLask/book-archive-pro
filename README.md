# 📚 Book Archive Pro

A professional Python-based book archiving tool that uses computer vision to scan ISBN barcodes and automatically fetch metadata via the Google Books API.

## ✨ Features
- **Real-time Barcode Scanning**: OpenCV + Pyzbar integration.
- **Automated Metadata**: Fetches Title, Author, Publisher, and Categories.
- **Greek Language Support**: UTF-8-sig encoding for perfect Excel compatibility.
- **Automated CI/CD**: GitHub Actions pipeline for code quality.

## 🛠 Installation & Setup

### 1. System Requirements (macOS)
The barcode engine requires the `zbar` system library. This is a C-library that Poetry cannot install directly.
```bash
brew install zbar
poetry install --no-root