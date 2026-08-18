import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os

from database import init_db, insert_result, load_config
from engine import parse_file, run_scan
from exporter import export_csv
from theme import (
    BLUE_100,
    FONT_SMALL,
    FONT_TABLE,
    FONT_TABLE_BOLD,
    GRAY_100,
    GRAY_200,
    GRAY_400,
    GRAY_600,
    GRAY_800,
    RED,
    ROW_EVEN,
    ROW_ODD,
    STATE_UNKNOWN,
    STATUS_COLORS,
    WHITE,
    is_error_state,
)
from ui_components import make_toolbar_button

# ── Theme ──────────────────────────────────────────────────────────────────
ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')


class LinkGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('LinkGuard')
        self.geometry('1100x680')
        self.minsize(900, 580)

        init_db()
        self.config = load_config()

        self._urls = []
        self._results = []
        self._scan_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._scan_thread = None
        self._total = 0
        self._scanned = 0
        self._errors = 0
        self._filter_errors_only = False

        self._build_ui()
        self._poll_queue()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_grid()
        self._build_statusbar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color=GRAY_800)
        bar.grid(row=0, column=0, sticky='ew')
        bar.grid_propagate(False)
        bar.grid_columnconfigure(4, weight=1)

        self.btn_load = make_toolbar_button(bar, 'Load File', self._load_file)
        self.btn_load.grid(row=0, column=0, padx=(12, 4), pady=8)

        self.btn_start = make_toolbar_button(bar, 'Start Scan', self._start_scan, style='start')
        self.btn_start.grid(row=0, column=1, padx=4, pady=8)

        self.btn_pause = make_toolbar_button(bar, 'Pause', self._pause_scan, style='pause',
                                            width=90, state='disabled')
        self.btn_pause.grid(row=0, column=2, padx=4, pady=8)

        # spacer handled by weight=1 on column 4

        self.btn_filter = make_toolbar_button(bar, 'Errors Only', self._toggle_filter,
                                              style='toolbar_muted')
        self.btn_filter.grid(row=0, column=5, padx=4, pady=8)

        self.btn_export = make_toolbar_button(bar, 'Export CSV', self._export)
        self.btn_export.grid(row=0, column=6, padx=(4, 12), pady=8)

    def _build_grid(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color=GRAY_100)
        frame.grid(row=1, column=0, sticky='nsew')
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                        background=WHITE,
                        foreground=GRAY_800,
                        rowheight=26,
                        fieldbackground=WHITE,
                        font=FONT_TABLE)
        style.configure('Treeview.Heading',
                        background=GRAY_200,
                        foreground=GRAY_800,
                        font=FONT_TABLE_BOLD,
                        relief='flat')
        style.map('Treeview', background=[('selected', BLUE_100)])

        self.tree = ttk.Treeview(frame,
                                 columns=('id', 'url', 'status', 'latency', 'state'),
                                 show='headings', selectmode='browse')

        self.tree.heading('id',      text='ID')
        self.tree.heading('url',     text='URL')
        self.tree.heading('status',  text='Status Code')
        self.tree.heading('latency', text='Latency (ms)')
        self.tree.heading('state',   text='State')

        self.tree.column('id',      width=55,  minwidth=40,  anchor='center')
        self.tree.column('url',     width=550, minwidth=200, anchor='w')
        self.tree.column('status',  width=110, minwidth=80,  anchor='center')
        self.tree.column('latency', width=110, minwidth=80,  anchor='center')
        self.tree.column('state',   width=110, minwidth=80,  anchor='center')

        # Zebra + status tags
        self.tree.tag_configure('odd',  background=ROW_ODD)
        self.tree.tag_configure('even', background=ROW_EVEN)
        for state, color in STATUS_COLORS.items():
            self.tree.tag_configure(state, foreground=color)

        sb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')

    def _build_statusbar(self):
        self.statusbar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=GRAY_200)
        self.statusbar.grid(row=2, column=0, sticky='ew')
        self.statusbar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text='Ready — load a file to begin.',
            font=FONT_SMALL,
            text_color=GRAY_600
        )
        self.status_label.pack(side='left', padx=12)

    # ── Actions ────────────────────────────────────────────────────────────

    def _load_file(self):
        path = filedialog.askopenfilename(
            title='Select URL list',
            filetypes=[('CSV / Text files', '*.csv *.txt'), ('All files', '*.*')]
        )
        if not path:
            return
        self._urls = parse_file(path)
        self._total = len(self._urls)
        self._set_status(f'Loaded {self._total} URLs — press Start Scan.')

    def _start_scan(self):
        if not self._urls:
            messagebox.showwarning('No URLs', 'Load a file first.')
            return
        if self._scan_thread and self._scan_thread.is_alive():
            return

        self._clear_grid()
        self._results = []
        self._scanned = 0
        self._errors = 0
        self._pause_event.clear()
        self._cancel_event.clear()

        self.btn_start.configure(state='disabled')
        self.btn_pause.configure(text='Pause', state='normal')

        self._scan_thread = threading.Thread(
            target=run_scan,
            args=(self._urls, self._scan_queue.put, self._pause_event, self._cancel_event),
            daemon=True
        )
        self._scan_thread.start()

    def _pause_scan(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.btn_pause.configure(text='Pause')
            self._set_status(f'Resumed — scanned {self._scanned}/{self._total}.')
        else:
            self._pause_event.set()
            self.btn_pause.configure(text='Resume')
            self._set_status(f'Paused — scanned {self._scanned}/{self._total}.')

    def _on_close(self):
        self._cancel_event.set()
        self._pause_event.clear()
        self.destroy()

    def _toggle_filter(self):
        self._filter_errors_only = not self._filter_errors_only
        self.btn_filter.configure(text_color=RED if self._filter_errors_only else GRAY_400)
        self._redraw_grid()

    def _export(self):
        if not self._results:
            messagebox.showwarning('Nothing to export', 'Run a scan first.')
            return
        path = filedialog.asksaveasfilename(
            title='Save scan report',
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv')]
        )
        if not path:
            return
        try:
            export_csv(self._results, path)
            self._set_status(f'Exported {len(self._results)} rows → {os.path.basename(path)}')
        except Exception as e:
            messagebox.showerror('Export failed', str(e))

    # ── Queue polling (thread-safe UI updates) ─────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                result = self._scan_queue.get_nowait()
                self._handle_result(result)
        except Exception:
            pass
        self.after(150, self._poll_queue)

    def _handle_result(self, result):
        self._results.append(result)
        self._scanned += 1

        state = self._state_of(result)
        if is_error_state(state):
            self._errors += 1

        insert_result(result['url'], result['status_code'], result['latency_ms'], state)

        if self._is_visible(state):
            self._insert_row(result)

        active = self._scan_thread.is_alive() if self._scan_thread else 0
        self._set_status(
            f'Scanned: {self._scanned}/{self._total} | '
            f'Errors: {self._errors} | '
            f'Active Threads: {min(10, self._total - self._scanned) if active else 0}'
        )

        if self._scanned >= self._total:
            self.btn_start.configure(state='normal')
            self.btn_pause.configure(state='disabled')
            self._set_status(
                f'Scan complete — {self._total} URLs | {self._errors} errors found.'
            )

    @staticmethod
    def _state_of(result):
        return result.get('state', STATE_UNKNOWN)

    def _is_visible(self, state):
        """Whether a result passes the current grid filter."""
        return not self._filter_errors_only or is_error_state(state)

    def _insert_row(self, result):
        row_num = self.tree.get_children().__len__() + 1
        zebra = 'odd' if row_num % 2 == 0 else 'even'
        state = self._state_of(result)
        tags = (zebra, state)

        self.tree.insert('', 'end',
                         values=(
                             row_num,
                             result['url'],
                             result['status_code'] or '—',
                             f"{result['latency_ms']:.0f}",
                             state
                         ),
                         tags=tags)
        self.tree.yview_moveto(1)

    def _clear_grid(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _redraw_grid(self):
        self._clear_grid()
        for result in self._results:
            if self._is_visible(self._state_of(result)):
                self._insert_row(result)

    def _set_status(self, text):
        self.status_label.configure(text=text)


if __name__ == '__main__':
    app = LinkGuardApp()
    app.mainloop()
