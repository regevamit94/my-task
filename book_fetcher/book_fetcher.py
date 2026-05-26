import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


class Book(BaseModel):
	title: str
	authors: List[str] = Field(default_factory=list, alias="author_name")
	first_publish_year: Optional[int] = None


class SearchResponse(BaseModel):
	docs: List[Book] = Field(default_factory=list)


class JsonOutputWriter:
	def write(self, books: List[Book], output_path: Path) -> None:
		payload = [book.dict(by_alias=False) for book in books]
		output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _http_error_with_headers(exc: requests.exceptions.HTTPError) -> RuntimeError:
	response = exc.response
	if response is None:
		return RuntimeError(f"HTTP request failed: {exc}")

	interesting_headers = ["Retry-After", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
	header_details = {
		key: response.headers.get(key)
		for key in interesting_headers
		if response.headers.get(key)
	}

	return RuntimeError(
		f"API request failed with HTTP {response.status_code}. "
		f"URL: {response.url}. "
		f"Response headers: {header_details if header_details else 'none'}"
	)


def fetch_books(query: str) -> SearchResponse:
	try:
		response = requests.get(
			OPEN_LIBRARY_SEARCH_URL,
			params={"q": query},
			headers={"Accept": "application/json", "User-Agent": "book-fetcher/1.0"},
			timeout=30,
		)
		response.raise_for_status()
	except requests.exceptions.HTTPError as exc:
		raise _http_error_with_headers(exc) from exc
	except requests.exceptions.RequestException as exc:
		raise RuntimeError(f"Network error while calling Open Library: {exc}") from exc

	return SearchResponse.parse_obj(response.json())


def filter_books(books: List[Book], title_keyword: str, min_year: int) -> List[Book]:
	keyword = title_keyword.lower()
	filtered: List[Book] = []

	for book in books:
		if keyword not in book.title.lower():
			continue

		if book.first_publish_year is None or book.first_publish_year < min_year:
			continue

		filtered.append(book)

	return filtered


def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Fetch and filter books from Open Library.")
	parser.add_argument("--query", required=True, help="Query sent to Open Library search API.")
	parser.add_argument("--title-keyword", required=True, help="Keep books whose title contains this keyword.")
	parser.add_argument("--min-year", required=True, type=int, help="Keep books with first_publish_year >= this year.")
	parser.add_argument("--output", required=True, help="Output JSON file path.")
	return parser


def main() -> None:
	args = build_argument_parser().parse_args()

	response = fetch_books(args.query)
	filtered_books = filter_books(response.docs, args.title_keyword, args.min_year)

	JsonOutputWriter().write(filtered_books, Path(args.output))

	print(f"Fetched: {len(response.docs)} books")
	print(f"Filtered: {len(filtered_books)} books")
	print(f"Output written to: {args.output}")


if __name__ == "__main__":
	main()
