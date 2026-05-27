# book_fetcher

This folder contains a separate Python script project that fetches book data from Open Library, filters the results, and writes the output to JSON.

## Files

- `book_fetcher.py`: command-line script
- `requirements.txt`: Python dependencies

## Setup

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Use `python -m pip` after activation to ensure packages are installed in the virtual environment.

## Run example (Values can be changed)

```bash
python book_fetcher.py --query python --title-keyword python --min-year 2000 --output filtered_books.json
```

## Output

The script prints how many books were fetched and filtered, then writes the final list to the JSON file you specify.
Pay attention that the library has a short rate-limit, so from time to time, depends of requests amount, there is a chance to be denied by the library and recieve HTTP 403 Forbidden error which the script knows how to handle with.