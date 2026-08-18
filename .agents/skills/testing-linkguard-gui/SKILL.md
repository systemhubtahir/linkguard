---
name: testing-linkguard-gui
description: How to run and end-to-end test the LinkGuard CustomTkinter desktop app (launch, load files, exercise all result states/colors, filter, export, DB checks) on a headless-X box.
---

# Testing the LinkGuard desktop GUI

## Launch
`python3-tk` is installed system-wide (see repo blueprint `initialize`), but the pre-existing
`venv/` in the repo may lack `customtkinter`. Create a venv that can see system tkinter:

```bash
cd /path/to/linkguard
python3 -m venv --system-site-packages venv2
./venv2/bin/pip install customtkinter requests pandas
DISPLAY=:0 nohup ./venv2/bin/python src/main.py >/tmp/lg_app.log 2>&1 &
DISPLAY=:0 wmctrl -r LinkGuard -b add,maximized_vert,maximized_horz   # maximize before recording
```
Watch `/tmp/lg_app.log` for tracebacks (Tk exceptions in callbacks only show up there, not in the UI).

## UI path
Toolbar (top, dark bar): `Load File` | `Start Scan` (green) | `Pause` (amber, disabled until a
scan runs) … right side: `Errors Only` | `Export CSV`. Grid columns: ID, URL, Status Code,
Latency (ms), State. Status bar at the bottom carries every confirmation message
("Loaded N URLs — press Start Scan.", "Scanned: n/N | Errors: e | Active Threads: x",
"Scan complete — N URLs | e errors found.", "Exported N rows → file.csv").
The Tk file dialog has a "File name" entry — type the absolute path there instead of browsing.

## Covering every result state deterministically (don't rely on egress)
Outbound HTTP is often partly blocked (e.g. `httpstat.us` is unreachable → every such URL
becomes `Error`). Serve the status codes locally instead:

```python
# /tmp/states_server.py  (port 9100): /ok=200 /moved=304 /missing=404 /boom=500
# /tmp/blackhole.py      (port 9099): socket that accepts and never replies -> real 10s Timeout
```
Then a URL list file gives all five states: scheme-less domain (tests `normalize_url`
prepending https://) → Healthy, `/moved` → Redirect (304 is NOT auto-followed by requests,
while 301/302 are, so use 304 to see the Redirect state), `/missing` → Broken,
`/boom` → Error, `:9099/hang` → Timeout with latency exactly 10000 ms.
Duplicate a line to prove `dedupe` (loaded count must be lower than the line count).

## Verifying colors
State text colors come from `src/theme.py` STATUS_COLORS. Sample pixels from a full-resolution
screenshot rather than eyeballing (screenshots are 1600x1200 while tool coordinates are 1024x768,
so scale by 1600/1024). Expected: Healthy `#10B981`, Redirect `#F59E0B`,
Broken/Error/Timeout `#EF4444`. Button-label colors are subpixel-antialiased and unreliable to
sample — compare zoomed crops before/after instead (e.g. Errors Only label gray→red).

## Non-UI verification
- DB: `sqlite3 data/linkguard.db "select * from scan_history order by id desc limit 5"` (records are
  written per result by `database.insert_result`).
- Export: header must be exactly `id,url,status_code,latency_ms,state,timestamp`.

## Known pre-existing behavior (not a regression)
Clicking `Pause` sets a stop event that shuts the ThreadPoolExecutor down with
`cancel_futures=True`, so the scan thread ends. `Resume` only relabels the button — the scan does
not continue, and `Start Scan` stays disabled because `_scanned` never reaches `_total`. Restart
the app (or run a fresh scan before pausing) to get a clean state. If pause/resume is ever
reported as broken, this is likely the cause.

## Devin Secrets Needed
None.
