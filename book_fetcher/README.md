# book_fetcher

This folder contains a separate Python script project that fetches book data from Open Library, filters the results, and writes the output to JSON.

## Files

- `book_fetcher.py`: command-line script
- `requirements.txt`: Python dependencies

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python book_fetcher.py --query python --title-keyword python --min-year 2000 --output filtered_books.json
```

## Output

The script prints how many books were fetched and filtered, then writes the final list to the JSON file you specify.