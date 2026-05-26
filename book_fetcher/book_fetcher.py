from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


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
    # Build a URL-safe query string for the Open Library search endpoint before sending the API request.
    params = urllib.parse.urlencode({"q": query})
    request_url = f"{OPEN_LIBRARY_SEARCH_URL}?{params}"

    # Send the request to the Open Library search endpoint and decode the response body.
    with urllib.request.urlopen(request_url, timeout=30) as response:
        raw_data = response.read().decode("utf-8")

    # Parse the JSON response and validate it against our response model.
    data = json.loads(raw_data)
    return SearchResponse.model_validate(data)


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
    parser.add_argument(
        "--query",
        default="python",
        help="Search query sent to the Open Library API.",
    )
    parser.add_argument(
        "--title-keyword",
        default="python",
        help="Only include books whose title contains this keyword.",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2000,
        help="Only include books with first_publish_year >= this value.",
    )
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
