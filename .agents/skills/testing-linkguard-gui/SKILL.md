---
name: testing-linkguard-gui
description: How to run and GUI-test the LinkGuard CustomTkinter desktop app (launch, file dialogs, deterministic scan targets, verifying URL-safety/export behaviour).
---

# Testing the LinkGuard desktop GUI

## Environment setup
- `tkinter` is NOT in `requirements.txt` and is not provided by the venv. Without it `src/main.py`
  dies with `ModuleNotFoundError: No module named 'tkinter'` on the `import customtkinter` line.
  Install the system package first: `sudo apt-get install -y python3-tk`, then create the venv
  (a venv created *before* installing python3-tk may still work, but recreating it is the safe move).
- `python3 -m venv venv && venv/bin/pip install -r requirements.txt` (add `pytest`; it is not pinned
  in requirements but `tests/` exists).
- Launch on the X display: `cd <repo> && DISPLAY=:0 venv/bin/python src/main.py`.
  Run it detached (`nohup ... &`) so the shell stays usable.
- Maximize before recording: `DISPLAY=:0 wmctrl -r LinkGuard -b add,maximized_vert,maximized_horz`
  then `DISPLAY=:0 wmctrl -a LinkGuard`. Never use xdotool Super+key (it half-tiles).
- The window title is exactly `LinkGuard`, so `wmctrl -l | grep LinkGuard` is a reliable readiness
  check; if the window is missing, `cat` the redirected stdout log for the traceback.
- A `pkill -f src/main.py` immediately followed by a relaunch in the same command sometimes leaves no
  window; relaunch as a separate command and re-check `wmctrl -l`.

## Driving the UI
- Toolbar (maximized, 1024-wide screen coords): `Load File` ~(42,33), `Start Scan` ~(118,33),
  `Pause` ~(187,33), `Errors Only` ~(904,33), `Export CSV` ~(980,33). Status bar is the bottom strip
  (~y=730) — zoom into `[0,715,600,740]` to read it.
- `Load File`/`Export CSV` open Tk's **non-native** dialog: click the "File name" entry (~506,447),
  type an **absolute path**, then press Enter or click Save/Open (~608,447). This is the reliable way
  to pick fixtures; there is no need to navigate the file list. Use `triple_click` on the entry to
  replace a pre-filled name.
- Error/warning dialogs are `tkinter.messagebox` modals with an `OK` button (~511,416).

## Deterministic scan targets (avoid depending on public sites)
- Serve fixtures locally: `python3 -m http.server 8000` in a dir with a file `home`, a file `about`,
  and a dir `redir/` containing `index.html` → gives 200, 200, 301→200, and 404 for `/missing`.
- Redirect the server's stdout/stderr to a log file: the access log is the best proof of **which URLs
  were actually requested**. To prove a URL was never fetched, put a unique marker in its path
  (e.g. `http://user:pass@localhost:8000/CREDENTIAL_LEAK`) and assert
  `grep -c CREDENTIAL /path/to/access.log` is 0.
- To exercise a redirect **cap** (`engine.MAX_REDIRECTS`), a plain http.server is not enough — run a
  tiny `BaseHTTPRequestHandler` that answers `/r/N` with a 302 to `/r/N-1` (and 200 at `/r/0`), and
  implement `do_HEAD` (LinkGuard sends HEAD first, falling back to GET only on 405). A chain longer
  than the cap should render `Error` even though the final response is 200; a short chain renders
  `Healthy`.

## Gotchas when asserting behaviour
- `allow_redirects=True`, so a 301 is *followed* and the row shows the **final** status (200/`Healthy`),
  not `Redirect`. Do not write a test expecting `Redirect` from an ordinary 301 that resolves.
- `normalize_url` prepends `https://` only when no scheme is present, so a bare `example.com` line is
  **kept and scanned** as `https://example.com`. Only `file:`/`javascript:`/`mailto:`/`user:pass@`
  style entries are dropped by `parse_file`.
- URLs starting with `=`/`+`/`-`/`@` cannot reach `exporter._neutralise` through the Load File path
  (the loader normalises/drops them). To test CSV formula neutralisation through real UI code, write a
  throwaway harness that instantiates the real `LinkGuardApp`, puts crafted result dicts on
  `app._scan_queue` and sets `app._total`, then click the real `Export CSV` button and inspect the
  file with `cat -A`. The same harness is the easiest way to render `Invalid` rows on screen.
- `theme.ERROR_STATES` drives both the status-bar error tally and the "Errors Only" filter, so any new
  state added there must be checked in both places.
- Exports and the SQLite history live under the project root (`exports/`, `data/linkguard.db`);
  prefer typing an absolute path into the save dialog so artifacts land in your own test dir.

## Known pre-existing failure
`venv/bin/python -m pytest -q` → `tests/test_parser.py::test_parse_csv_fixture` fails on `main` too
(the fixture lacks `www.google.com`). Expect `1 failed, 38 passed`; do not report it as a regression.

## Devin Secrets Needed
None — the app is a local desktop app with no auth.
