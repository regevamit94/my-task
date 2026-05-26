from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Protocol

import requests
from pydantic import BaseModel, Field

# Primary provider endpoint.
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
# Secondary provider endpoint used as a fallback.
GOOGLE_BOOKS_SEARCH_URL = "https://www.googleapis.com/books/v1/volumes"
# Network timeout per request (seconds).
REQUEST_TIMEOUT_SECONDS = 30
# Shared request headers for both providers.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


class Book(BaseModel):
    # Map the pieces of book data we care about from the Open Library response.
    title: str
    authors: list[str] = Field(default_factory=list, alias="author_name")
    first_publish_year: int | None = None


class SearchResponse(BaseModel):
    # The API returns matching books inside the "docs" array.
    docs: list[Book] = Field(default_factory=list)


class OutputWriter(Protocol):
    # Define the output contract so different writer implementations are possible.
    def write(self, books: list[Book], output_path: Path) -> None:
        ...


class JsonOutputWriter:
    def write(self, books: list[Book], output_path: Path) -> None:
        # Convert validated Pydantic models into plain dictionaries for JSON output.
        payload = [book.model_dump(by_alias=False) for book in books]

        # Persist the filtered results as pretty-printed UTF-8 JSON.
        output_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8"
        )


def _fetch_open_library_books(query: str) -> SearchResponse:
    # Send the search query to Open Library.
    response = requests.get(
        OPEN_LIBRARY_SEARCH_URL,
        params={"q": query},
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    # Convert non-2xx HTTP responses into exceptions.
    response.raise_for_status()

    # Validate and normalize the provider payload into our shared response model.
    return SearchResponse.model_validate(response.json())


def _extract_year(value: str | None) -> int | None:
    # Return None when provider gives no publish date.
    if not value:
        return None

    # Extract the first four-digit year from values like "2005-09-01".
    match = re.search(r"(\d{4})", value)
    return int(match.group(1)) if match else None


def _fetch_google_books(query: str) -> SearchResponse:
    # Google Books acts as a fallback provider when Open Library is unreachable.
    response = requests.get(
        GOOGLE_BOOKS_SEARCH_URL,
        params={"q": query, "maxResults": 40},
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    # Convert non-2xx HTTP responses into exceptions.
    response.raise_for_status()

    # Read raw JSON payload from Google Books.
    payload = response.json()

    # Build Open-Library-like docs so downstream filtering stays unchanged.
    docs_payload: list[dict[str, object]] = []

    # Iterate through each returned volume and map only fields we use.
    for item in payload.get("items", []):
        volume_info = item.get("volumeInfo", {})
        title = volume_info.get("title")

        # Skip malformed entries that do not contain a title.
        if not title:
            continue

        # Normalize Google Books fields into the same schema used by Book.
        docs_payload.append(
            {
                "title": title,
                "author_name": volume_info.get("authors", []),
                "first_publish_year": _extract_year(volume_info.get("publishedDate")),
            }
        )

    # Validate and return normalized fallback response.
    return SearchResponse.model_validate({"docs": docs_payload})


def fetch_books(query: str) -> SearchResponse:
    # First attempt the primary provider.
    try:
        return _fetch_open_library_books(query)
    except requests.exceptions.RequestException as open_library_error:
        # If primary provider fails, log the reason and continue with fallback.
        print(
            "Open Library request failed; trying Google Books fallback. "
            f"Reason: {open_library_error}"
        )

    # Try the fallback provider before failing the script.
    try:
        return _fetch_google_books(query)
    except requests.exceptions.RequestException as google_books_error:
        # Surface both provider errors to make troubleshooting easier.
        raise RuntimeError(
            "Both Open Library and Google Books requests failed. "
            f"Open Library error: {open_library_error}. "
            f"Google Books error: {google_books_error}"
        ) from google_books_error


def filter_books(
    books: list[Book],
    title_keyword: str,
    min_year: int,
) -> list[Book]:
    # Normalize keyword once for case-insensitive comparison.
    keyword_lower = title_keyword.lower()
    filtered: list[Book] = []

    for book in books:
        # Check if title contains the keyword.
        matches_title = keyword_lower in book.title.lower()

        # Only keep books with a valid year >= min_year.
        matches_year = (
            book.first_publish_year is not None
            and book.first_publish_year >= min_year
        )

        # Include books matching both conditions.
        if matches_title and matches_year:
            filtered.append(book)

    return filtered


def build_argument_parser() -> argparse.ArgumentParser:
    # Define CLI arguments and defaults.
    parser = argparse.ArgumentParser(
        description="Fetch books from Open Library, filter them, and save JSON output."
    )

    # Query sent to the external books API.
    parser.add_argument(
        "--query",
        default="python",
        help="Search query sent to the Open Library API.",
    )

    # Title keyword used by the local filter stage.
    parser.add_argument(
        "--title-keyword",
        default="python",
        help="Only include books whose title contains this keyword.",
    )

    # Publish-year threshold used by the local filter stage.
    parser.add_argument(
        "--min-year",
        type=int,
        default=2000,
        help="Only include books with first_publish_year >= this value.",
    )

    # Output JSON file path.
    parser.add_argument(
        "--output",
        default="filtered_books.json",
        help="Path to output JSON file.",
    )

    return parser


def main() -> None:
    # Parse command-line arguments.
    parser = build_argument_parser()
    args = parser.parse_args()

    # Fetch books from Open Library.
    response = fetch_books(args.query)

    # Apply title/year filtering.
    filtered_books = filter_books(
        books=response.docs,
        title_keyword=args.title_keyword,
        min_year=args.min_year,
    )

    # Write filtered results to JSON.
    writer: OutputWriter = JsonOutputWriter()
    writer.write(filtered_books, Path(args.output))

    # Print summary.
    print(f"Fetched: {len(response.docs)} books")
    print(f"Filtered: {len(filtered_books)} books")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    # Run only when executed directly.
    main()