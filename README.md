# QSOMapper

Simple tool to parse ADIF logs and create a quick HTML map (`map.html`) of QSOs using OpenLayers.

Prerequisites
- Python 3.8+ recommended
- A virtual environment (optional but recommended)

Install

1. Create and activate a virtual environment (optional but recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Usage

1. Run the parser with your ADIF file:

```bash
python3 pota-mapper.py /path/to/yourfile.adi
```

2. Open the generated `map.html` in your browser (double-click or use `open` on macOS):

```bash
open map.html
```

Notes and tips

- The script looks for `all_parks_ext.csv` in the repo to map park references. Make sure that file exists and has `reference`, `latitude`, and `longitude` columns.
	- You can download the CSV from POTA:
		```bash
		# from the project root
		curl -L -o all_parks_ext.csv https://pota.app/all_parks_ext.csv
		# or
		wget -O all_parks_ext.csv https://pota.app/all_parks_ext.csv
		```
- The script attaches a blue marker for the entry with CALL `MY_PARK` so it's easy to spot on the map.
- Popups open on click/tap. Desktop hover behavior was changed to click to avoid flicker and to work better on touch devices.
- If you see warnings about passive event listeners in the browser console, that's expected — the generated `map.html` includes a small workaround to avoid Chrome's intervention warnings.
If you'd like me to add an automated `run.sh`, CI config, or package this as a small web app, tell me which option you prefer.

Troubleshooting
---------------

- Virtualenv not activated / missing packages:
	- Error: "ModuleNotFoundError: No module named 'pandas'" or similar when running the script.
	- Fix: Activate the venv and install requirements:
		```bash
		source .venv/bin/activate
		pip install -r requirements.txt
		```

- `adif_io` import problems:
	- The script imports `adif_io`. If `pip install -r requirements.txt` fails to find `adif-io`, search PyPI for the correct package name or install from the project's source repository. If you know another package provides `adif_io`, replace the entry in `requirements.txt`.

- Browser console warns about passive event listeners:
	- Symptom: Repeated messages like "Unable to preventDefault inside passive event listener" in Chrome's console.
	- Explanation: OpenLayers adds touch/wheel listeners that call `preventDefault`. Modern Chrome treats some listeners as passive by default for scrolling performance.
	- Fix: `map.html` includes a small workaround to force non-passive for touch/wheel listeners and sets `touch-action:none;` on the map. If you prefer not to use the workaround, you can remove it and accept the console warnings.

- Popup flicker or popups closing immediately:
	- Symptom: Popups flicker on hover or close immediately after opening on click.
	- Explanation: Hover handlers and rapid mouse movements between marker and popup can cause show/hide cycles. On touch devices `mouseover` isn't suitable.
	- Fix: The script now opens popups on click/tap and closes them when clicking the map background. If you want popups to persist until explicitly closed, let me know and I can change the behavior.

- Park CSV mapping issues:
	- Symptom: Wrong marker positions for parks or missing park markers.
	- Fix: Ensure `all_parks_ext.csv` exists and contains `reference`, `latitude`, and `longitude` columns. The script prefers CSV park coordinates over lookup results.

If you run into anything else, paste the terminal or console output here and I'll help debug.
