from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Protocol

import requests
from pydantic import BaseModel, Field

# Primary provider endpoint.
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_SEARCH_URL = "https://www.googleapis.com/books/v1/volumes"
REQUEST_TIMEOUT_SECONDS = 30
GOOGLE_BOOKS_MAX_ATTEMPTS = 3
REQUEST_HEADERS = {
    # Some public APIs block requests with generic default clients.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
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
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_books(query: str) -> SearchResponse:
    open_library_error_message = "unknown error"

    # Try Open Library first.
    try:
        response = requests.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={"q": query},
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return SearchResponse.model_validate(response.json())
    except requests.exceptions.RequestException as open_library_error:
        open_library_error_message = str(open_library_error)
        print(
            "Open Library request failed; trying Google Books fallback. "
            f"Reason: {open_library_error}"
        )

    # If Open Library is blocked/unreachable, fetch from Google Books instead.
    google_books_error_message = "unknown error"
    for attempt in range(1, GOOGLE_BOOKS_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                GOOGLE_BOOKS_SEARCH_URL,
                params={"q": query, "maxResults": 20},
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            # Handle provider rate limiting with bounded backoff retries.
            if response.status_code == 429 and attempt < GOOGLE_BOOKS_MAX_ATTEMPTS:
                retry_after = response.headers.get("Retry-After")
                delay_seconds = int(retry_after) if retry_after and retry_after.isdigit() else attempt * 2
                print(
                    "Google Books rate-limited the request (HTTP 429). "
                    f"Retrying in {delay_seconds}s (attempt {attempt}/{GOOGLE_BOOKS_MAX_ATTEMPTS})."
                )
                time.sleep(delay_seconds)
                continue

            response.raise_for_status()

            payload = response.json()
            docs_payload: list[dict[str, object]] = []

            for item in payload.get("items", []):
                volume_info = item.get("volumeInfo", {})
                title = volume_info.get("title")
                if not title:
                    continue

                published_date = volume_info.get("publishedDate")
                year_match = re.search(r"(\d{4})", published_date or "")

                docs_payload.append(
                    {
                        "title": title,
                        "author_name": volume_info.get("authors", []),
                        "first_publish_year": int(year_match.group(1)) if year_match else None,
                    }
                )

            return SearchResponse.model_validate({"docs": docs_payload})
        except requests.exceptions.RequestException as google_books_error:
            google_books_error_message = str(google_books_error)
            if attempt < GOOGLE_BOOKS_MAX_ATTEMPTS:
                time.sleep(attempt * 2)
                continue
            break

    raise RuntimeError(
        "Both Open Library and Google Books requests failed. "
        f"Open Library error: {open_library_error_message}. "
        f"Google Books error: {google_books_error_message}"
    )


def filter_books(
    books: list[Book],
    title_keyword: str,
    min_year: int,
) -> list[Book]:
    # Normalize the keyword once so title matching is case-insensitive.
    keyword_lower = title_keyword.lower()
    filtered: list[Book] = []

    for book in books:
        # Keep books whose title contains the keyword.
        matches_title = keyword_lower in book.title.lower()

        # Exclude books with no year and keep only books published on or after min_year.
        matches_year = (
            book.first_publish_year is not None
            and book.first_publish_year >= min_year
        )

        # Only collect books that satisfy both filter conditions.
        if matches_title and matches_year:
            filtered.append(book)

    return filtered


def build_argument_parser() -> argparse.ArgumentParser:
    # Define the command-line interface and defaults for the script.
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
    # Build the parser using command-line options from the user, then use it to read CLI arguments into the args namespace.
    parser = build_argument_parser()
    args = parser.parse_args()

    # Send the search query to the Open Library API using the provided query and get back a list of matching books.
    response = fetch_books(args.query)

    # Apply the local title and publication year filters.
    filtered_books = filter_books(
        books=response.docs,
        title_keyword=args.title_keyword,
        min_year=args.min_year,
    )

    # Write the filtered list to the requested output file.
    writer: OutputWriter = JsonOutputWriter()
    writer.write(filtered_books, Path(args.output))

    # Print a short summary so the user can confirm what happened.
    print(f"Fetched: {len(response.docs)} books")
    print(f"Filtered: {len(filtered_books)} books")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    # Run the script only when this file is executed directly.
    main()