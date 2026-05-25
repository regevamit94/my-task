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
    title: str
    authors: list[str] = Field(default_factory=list, alias="author_name")
    first_publish_year: int | None = None


class SearchResponse(BaseModel):
    docs: list[Book] = Field(default_factory=list)


class OutputWriter(Protocol):
    def write(self, books: list[Book], output_path: Path) -> None:
        ...


class JsonOutputWriter:
    def write(self, books: list[Book], output_path: Path) -> None:
        payload = [book.model_dump(by_alias=False) for book in books]
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_books(query: str) -> SearchResponse:
    params = urllib.parse.urlencode({"q": query})
    request_url = f"{OPEN_LIBRARY_SEARCH_URL}?{params}"

    with urllib.request.urlopen(request_url, timeout=30) as response:
        raw_data = response.read().decode("utf-8")

    data = json.loads(raw_data)
    return SearchResponse.model_validate(data)


def filter_books(
    books: list[Book],
    title_keyword: str,
    min_year: int,
) -> list[Book]:
    keyword_lower = title_keyword.lower()
    filtered: list[Book] = []

    for book in books:
        matches_title = keyword_lower in book.title.lower()
        matches_year = (
            book.first_publish_year is not None
            and book.first_publish_year >= min_year
        )

        if matches_title and matches_year:
            filtered.append(book)

    return filtered


def build_argument_parser() -> argparse.ArgumentParser:
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
    parser = build_argument_parser()
    args = parser.parse_args()

    response = fetch_books(args.query)
    filtered_books = filter_books(
        books=response.docs,
        title_keyword=args.title_keyword,
        min_year=args.min_year,
    )

    writer: OutputWriter = JsonOutputWriter()
    writer.write(filtered_books, Path(args.output))

    print(f"Fetched: {len(response.docs)} books")
    print(f"Filtered: {len(filtered_books)} books")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
