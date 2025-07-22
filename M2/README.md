# MetaInspector

MetaInspector is a Flask web application for extracting metadata from legacy codebases (COBOL, Fortran, Pascal, Assembly, Ada, PL/I, RPG, BASIC, JCL, etc.).

## Features
- Upload single files or ZIPs, or paste code directly
- Supports COBOL (sample), extensible to other languages
- Extracts function/procedure names, variables, control structures, external interfaces, entry points
- Output metadata in JSON, YAML, or plain text
- Syntax-highlighted preview and download
- Bootstrap UI

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open [http://localhost:5000](http://localhost:5000) in your browser.

## Directory Structure
- `app.py` - Flask backend
- `templates/` - Jinja2 HTML templates
- `static/` - CSS/JS (optional, uses CDN for Bootstrap/Highlight.js)
- `parsers/` - Language-specific parsers (COBOL sample)
- `utils/` - Format conversion and file processing

## Extending
- Add new parsers in `parsers/` and update `utils/file_processing.py`
- Stubs for GPT-4o and interface mapping included for future enhancements

## License
MIT 