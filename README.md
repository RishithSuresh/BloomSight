# BloomSight

BloomSight is a small visual cryptography demo with a standard-library Python HTTP server and a browser UI.

## Requirements

- Python 3.10 or newer
- `pip`

## Install

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Start the app server:

```bash
python -m app
```

Then open:

- `http://127.0.0.1:8000/` for the main UI
- `http://127.0.0.1:8000/demo` for the run/demo page

You can also choose a different port:

```bash
python -m app 8080
```

## Test

```bash
pytest -q
```
