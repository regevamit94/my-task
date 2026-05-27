import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

import requests
from pydantic import BaseModel, Field

# Open Library search endpoint used by this script.
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
# App identity headers requested by Open Library docs for frequent API usage.
APP_NAME = "book-fetcher"
CONTACT_EMAIL = "regevamit@gmail.com"


class Book(BaseModel):
	# Subset of book fields we care about from the API response.
	title: str
	authors: List[str] = Field(default_factory=list, alias="author_name")
	first_publish_year: Optional[int] = None


class SearchResponse(BaseModel):
	# Open Library search payload contains matched books under "docs".
	docs: List[Book] = Field(default_factory=list)


class JsonOutputWriter:
	def write(self, books: List[Book], output_path: Path) -> None:
		# Convert validated models into plain dicts for JSON serialization.
		payload = [book.dict(by_alias=False) for book in books]
		# Write pretty-printed JSON to the output file path.
		output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _http_error_with_headers(exc: requests.exceptions.HTTPError) -> RuntimeError:
	# Build a user-friendly error message from HTTP failures.
	response = exc.response
	if response is None:
		return RuntimeError(f"HTTP request failed: {exc}")

	interesting_headers = ["Retry-After", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
	header_details = {
		key: response.headers.get(key)
		for key in interesting_headers
		if response.headers.get(key)
	}

	# Provide specific guidance for forbidden requests.
	if response.status_code == 403:
		return RuntimeError(
			"Open Library denied the request (HTTP 403). "
			"This is usually a temporary block or client/IP restriction, not a code bug. "
			f"URL: {response.url}. "
			f"Response headers: {header_details if header_details else 'none'}"
		)

	# Provide specific guidance for explicit rate limiting.
	if response.status_code == 429:
		return RuntimeError(
			"Open Library rate-limited the request (HTTP 429). "
			"Retry later and consider adding delays between runs. "
			f"URL: {response.url}. "
			f"Response headers: {header_details if header_details else 'none'}"
		)

	return RuntimeError(
		f"API request failed with HTTP {response.status_code}. "
		f"URL: {response.url}. "
		f"Response headers: {header_details if header_details else 'none'}"
	)


def fetch_books(query: str) -> SearchResponse:
	try:
		# Send an API request to Open Library with the requested headers as mentioned in the library API documentation.
		response = requests.get(
			OPEN_LIBRARY_SEARCH_URL,
			params={"q": query},
			headers={
				"Accept": "application/json",
				"User-Agent": f"{APP_NAME} ({CONTACT_EMAIL})",
				"From": CONTACT_EMAIL,
			},
			timeout=30,
		)
		# Turn non-2xx responses into exceptions.
		response.raise_for_status()
	except requests.exceptions.HTTPError as exc:
		# Re-raise with normalized, user-facing message.
		raise _http_error_with_headers(exc) from exc
	except requests.exceptions.RequestException as exc:
		# Catch transport-level failures (DNS, timeout, connection, etc.).
		raise RuntimeError(f"Network error while calling Open Library: {exc}") from exc

	# Validate response structure into typed Pydantic models.
	return SearchResponse.parse_obj(response.json())


def filter_books(books: List[Book], title_keyword: str, min_year: int) -> List[Book]:
	# Normalize keyword once for case-insensitive title matching.
	keyword = title_keyword.lower()
	filtered: List[Book] = []

	for book in books:
		# Keep only titles that include the keyword and with known publish year at or above threshold.
		if keyword not in book.title.lower():
			continue

		if book.first_publish_year is None or book.first_publish_year < min_year:
			continue

		# If the book passed all filters, add it to the filtered list.
		filtered.append(book)

	return filtered

# Define command-line interface for query/filter/output settings.
def build_argument_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Fetch and filter books from Open Library.")
	parser.add_argument("--query", required=True, help="Query sent to Open Library search API.")
	parser.add_argument("--title-keyword", required=True, help="Keep books whose title contains this keyword.")
	parser.add_argument("--min-year", required=True, type=int, help="Keep books with first_publish_year >= this year.")
	parser.add_argument("--output", required=True, help="Output JSON file path.")
	return parser


def main() -> None:
	# Parse input values passed when running the script.
	args = build_argument_parser().parse_args()

	try:
		# Fetch and validate raw search results.
		response = fetch_books(args.query)
	except RuntimeError as exc:
		# Print friendly error and exit with non-zero code.
		print(f"Error: {exc}")
		sys.exit(1)

	# Apply local filtering rules.
	filtered_books = filter_books(response.docs, args.title_keyword, args.min_year)

	# Persist filtered result set in JSON format.
	JsonOutputWriter().write(filtered_books, Path(args.output))

	# Print short run summary.
	print(f"Fetched: {len(response.docs)} books")
	print(f"Filtered: {len(filtered_books)} books")
	print(f"Output written to: {args.output}")


if __name__ == "__main__":
	# Entry point when executed as a script.
	main()
