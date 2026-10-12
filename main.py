"""
little tasks ♡  -  a cozy, pastel to-do list for your desktop.

Built with Python + CustomTkinter. Tasks are saved in a local JSON file
(tasks.json) that sits right next to this script.

Run it with:   python main.py
"""

import json
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

try:
    import customtkinter as ctk
except ImportError:  # friendly hint instead of a scary traceback
    print("CustomTkinter is not installed yet.")
    print("Install it with:  pip install customtkinter")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Settings: colors, fonts, text
# ---------------------------------------------------------------------------

# Soft pastel palette (lavender, blush pink, cream)
BG = "#E9E2F7"            # app background - soft lavender
CREAM = "#FFF9EF"         # cards
CREAM_DONE = "#F4EFF8"    # completed cards (a bit dimmer, lavender-tinted)
BORDER = "#E3D8F2"        # thin card outlines
LAVENDER_SOFT = "#EFE8FA" # pills, hover backgrounds
PURPLE = "#B79CED"        # main accent
PURPLE_HOVER = "#A387E3"
PINK = "#F6BCD0"          # secondary accent (buttons)
PINK_HOVER = "#F1A5C0"
PINK_DEEP = "#EE8FB2"     # error flash / progress bar
TRACK = "#EADFF5"         # empty part of the progress bar
TEXT = "#4B3F66"          # main text
TEXT_ON_PINK = "#5B3A5E"
MUTED = "#9A8FB3"         # secondary text

BODY_FONT = "Segoe UI"    # clean on Windows; other systems pick a fallback
TITLE_FONT = "Georgia"    # elegant serif for the title

MOTIVATION = [
    "You're doing better than you think ♡",
    "Small steps still count ✿",
    "One cozy task at a time ♡",
    "Be gentle with yourself today ✿",
    "Progress, not perfection ♡",
    "Little by little, a lot gets done ✿",
    "You've got this ♡",
    "Done is lovelier than perfect ✿",
]

MAX_TASK_LENGTH = 150
FILTERS = ("All", "Active", "Completed")

# tasks.json lives next to main.py (or next to the .exe if packaged later)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "tasks.json"


def make_font(size, weight="normal", family=BODY_FONT, **extra):
    """Small helper so every font in the app is created the same way."""
    return ctk.CTkFont(family=family, size=size, weight=weight, **extra)


# ---------------------------------------------------------------------------
# 2. Storage: reading and writing tasks.json
# ---------------------------------------------------------------------------

class TaskStore:
    """Keeps the list of tasks in memory and saves it to a JSON file.

    Each task is a dictionary:
        {"id": "...", "text": "Buy milk", "done": False, "created": "2026-10-12T20:30:00"}
    """

    def __init__(self, path):
        self.path = Path(path)
        self.tasks = []
        self.recovered = False  # True if the old file was damaged
        self.load()

    # ----- loading / saving -------------------------------------------------

    def load(self):
        """Load tasks from disk. Creates the file if it doesn't exist."""
        if not self.path.exists():
            self.save()  # creates an empty tasks.json
            return

        try:
            content = self.path.read_text(encoding="utf-8").strip()
            raw = json.loads(content) if content else []
            if not isinstance(raw, list):
                raise ValueError("tasks.json should contain a list")
        except (OSError, ValueError):
            # File is unreadable or damaged: keep a copy and start fresh
            self._set_aside_broken_file()
            self.tasks = []
            self.recovered = True
            self.save()
            return

        # Keep only well-formed entries so one bad row can't break the app
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                self.tasks.append({
                    "id": str(item.get("id") or uuid.uuid4().hex),
                    "text": item["text"].strip(),
                    "done": bool(item.get("done", False)),
                    "created": str(item.get("created") or datetime.now().isoformat(timespec="seconds")),
                })

    def save(self):
        """Write tasks to disk. Returns True on success, False on failure."""
        temp_path = self.path.with_suffix(".tmp")
        try:
            # Write to a temp file first, then swap it in. This way a crash
            # in the middle of saving can never leave a half-written file.
            temp_path.write_text(
                json.dumps(self.tasks, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temp_path.replace(self.path)
            return True
        except OSError:
            return False

    def _set_aside_broken_file(self):
        try:
            self.path.replace(self.path.with_name("tasks.broken.json"))
        except OSError:
            pass

    # ----- changing tasks ---------------------------------------------------

    def add(self, text):
        task = {
            "id": uuid.uuid4().hex,
            "text": text,
            "done": False,
            "created": datetime.now().isoformat(timespec="seconds"),
        }
        self.tasks.insert(0, task)  # newest task goes to the top
        return task

    def toggle(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                return

    def delete(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]

    def clear_completed(self):
        """Remove all completed tasks and return how many were removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t["done"]]
        return before - len(self.tasks)

    # ----- reading ----------------------------------------------------------

    def visible(self, filter_name):
        if filter_name == "Active":
            return [t for t in self.tasks if not t["done"]]
        if filter_name == "Completed":
            return [t for t in self.tasks if t["done"]]
        return list(self.tasks)

    def counts(self):
        """Returns (total, completed, remaining)."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t["done"])
        return total, completed, total - completed


# ---------------------------------------------------------------------------
# 3. The app window
# ---------------------------------------------------------------------------

class LittleTasksApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")

        self.store = TaskStore(DATA_FILE)
        self.current_filter = "All"
        self._status_job = None      # timer that clears the little message
        self._resize_job = None      # timer used to re-wrap text after resizing
        self._last_width = 0

        self._setup_window()
        self._build_header()
        self._build_input_area()
        self._build_filters()
        self._build_task_list()
        self._build_progress_area()

        self.refresh()
        self._tick_clock()
        self._schedule_motivation()
        self.bind("<Configure>", self._on_resize)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.store.recovered:
            self.show_message(
                "Your old task file looked damaged, so we started fresh "
                "(a copy was kept as tasks.broken.json).", seconds=9)

        self.focus()  # keep the placeholder text visible at startup

    # ----- window setup -----------------------------------------------------

    def _setup_window(self):
        self.title("little tasks ♡")
        self.configure(fg_color=BG)

        # Pick a height that fits smaller laptop screens too, then center it
        width = 560
        height = min(860, self.winfo_screenheight() - 120)
        x = (self.winfo_screenwidth() - width) // 2
        y = max(10, (self.winfo_screenheight() - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(460, 560)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # the task list grows/shrinks

    # ----- header -----------------------------------------------------------

    def _build_header(self):
        card = ctk.CTkFrame(self, fg_color=CREAM, corner_radius=28,
                            border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        ctk.CTkLabel(card, text="little tasks ♡", text_color=TEXT,
                     font=make_font(32, "bold", TITLE_FONT)
                     ).pack(anchor="w", padx=26, pady=(18, 0))

        ctk.CTkLabel(card, text="A little progress every day.", text_color=MUTED,
                     font=make_font(14)
                     ).pack(anchor="w", padx=28, pady=(0, 10))

        # A small "pill" holding today's date
        pill = ctk.CTkFrame(card, fg_color=LAVENDER_SOFT, corner_radius=14)
        pill.pack(anchor="w", padx=26, pady=(0, 6))
        self.date_label = ctk.CTkLabel(pill, text="", text_color=TEXT,
                                       font=make_font(13, "bold"))
        self.date_label.pack(padx=14, pady=4)

        self.motivation_label = ctk.CTkLabel(
            card, text=random.choice(MOTIVATION), text_color=PURPLE_HOVER,
            font=make_font(14, slant="italic"), anchor="w", justify="left",
            wraplength=440)
        self.motivation_label.pack(anchor="w", padx=28, pady=(0, 16))

    def _tick_clock(self):
        """Keeps the date correct, even if the app stays open past midnight."""
        self.date_label.configure(text="✿  " + datetime.now().strftime("%A, %B %d, %Y"))
        self.after(60_000, self._tick_clock)

    def _schedule_motivation(self):
        """Swap in a new motivational message every 45 seconds."""
        self.after(45_000, self._change_motivation)

    def _change_motivation(self):
        options = [m for m in MOTIVATION if m != self.motivation_label.cget("text")]
        self.motivation_label.configure(text=random.choice(options))
        self._schedule_motivation()

    # ----- input area -------------------------------------------------------

    def _build_input_area(self):
        card = ctk.CTkFrame(self, fg_color=CREAM, corner_radius=24,
                            border_width=1, border_color=BORDER)
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            card, height=46, corner_radius=23, border_width=2,
            border_color=BORDER, fg_color="white", text_color=TEXT,
            placeholder_text="What do you need to do today?",
            placeholder_text_color=MUTED, font=make_font(15))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(18, 8), pady=(16, 4))
        self.entry.bind("<Return>", lambda event: self.add_task())  # Enter adds the task

        self.add_button = ctk.CTkButton(
            card, text="Add Task +", width=120, height=46, corner_radius=23,
            fg_color=PINK, hover_color=PINK_HOVER, text_color=TEXT_ON_PINK,
            font=make_font(14, "bold"), command=self.add_task)
        self.add_button.grid(row=0, column=1, padx=(0, 18), pady=(16, 4))

        # Friendly message line (e.g. when you try to add an empty task)
        self.message_label = ctk.CTkLabel(
            card, text="", text_color=PINK_DEEP, font=make_font(12),
            anchor="w", justify="left", wraplength=470, height=18)
        self.message_label.grid(row=1, column=0, columnspan=2, sticky="w",
                                padx=24, pady=(0, 10))

    def show_message(self, text, seconds=3):
        """Show a short, gentle message under the input box."""
        self.message_label.configure(text=text)
        if self._status_job:
            self.after_cancel(self._status_job)
        self._status_job = self.after(int(seconds * 1000), self._clear_message)

    def _clear_message(self):
        self.message_label.configure(text="")
        self._status_job = None

    # ----- filters ----------------------------------------------------------

    def _build_filters(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))

        self.filter_buttons = {}
        for column, name in enumerate(FILTERS):
            bar.grid_columnconfigure(column, weight=1)
            button = ctk.CTkButton(
                bar, text=name, height=38, corner_radius=19,
                font=make_font(13, "bold"),
                command=lambda n=name: self.set_filter(n))
            button.grid(row=0, column=column, padx=4, sticky="ew")
            self.filter_buttons[name] = button

    def set_filter(self, name):
        self.current_filter = name
        self.refresh()

    def _style_filters(self):
        """Highlight the selected filter and show a count on each button."""
        total, completed, remaining = self.store.counts()
        numbers = {"All": total, "Active": remaining, "Completed": completed}
        for name, button in self.filter_buttons.items():
            selected = (name == self.current_filter)
            button.configure(
                text=f"{name}  ·  {numbers[name]}",
                fg_color=PURPLE if selected else CREAM,
                hover_color=PURPLE_HOVER if selected else LAVENDER_SOFT,
                text_color="white" if selected else MUTED,
                border_width=0 if selected else 1,
                border_color=BORDER)

    # ----- task list --------------------------------------------------------

    def _build_task_list(self):
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=PURPLE, scrollbar_button_hover_color=PURPLE_HOVER)
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=(18, 12), pady=(0, 4))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _text_wrap_width(self):
        """How wide task text may be before wrapping onto a new line."""
        width = self.winfo_width() if self.winfo_width() > 1 else 560
        return max(180, width - 190)

    def _add_task_card(self, task):
        done = task["done"]
        card = ctk.CTkFrame(
            self.list_frame, corner_radius=20,
            fg_color=CREAM_DONE if done else CREAM,
            border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=6, pady=5)
        card.grid_columnconfigure(1, weight=1)

        # Checkbox: tick = completed
        checkbox = ctk.CTkCheckBox(
            card, text="", width=30, checkbox_width=26, checkbox_height=26,
            corner_radius=13, border_width=2, border_color=PURPLE,
            fg_color=PURPLE, hover_color=PURPLE_HOVER, checkmark_color="white",
            command=lambda task_id=task["id"]: self.toggle_task(task_id))
        if done:
            checkbox.select()
        checkbox.grid(row=0, column=0, padx=(16, 2), pady=14)

        # Task text (struck through + muted when completed)
        label = ctk.CTkLabel(
            card, text=task["text"], anchor="w", justify="left",
            wraplength=self._text_wrap_width(),
            text_color=MUTED if done else TEXT,
            font=make_font(15, overstrike=done))
        label.grid(row=0, column=1, sticky="w", padx=(8, 6), pady=12)

        # Delete button
        delete_button = ctk.CTkButton(
            card, text="✕", width=34, height=34, corner_radius=17,
            fg_color="transparent", hover_color="#FADCE7", text_color=MUTED,
            font=make_font(14, "bold"),
            command=lambda task_id=task["id"]: self.delete_task(task_id))
        delete_button.grid(row=0, column=2, padx=(0, 12))

    def _show_empty_state(self):
        messages = {
            "All": ("Nothing on your list yet.\nEnjoy your little moment ♡",
                    "Add something above whenever you're ready."),
            "Active": ("Everything is done!\nYou're all caught up ♡",
                       "Time for a cup of tea."),
            "Completed": ("No completed tasks yet.\nYou'll get there ✿",
                          "Tick a task and it will show up here."),
        }
        title, hint = messages[self.current_filter]

        box = ctk.CTkFrame(self.list_frame, fg_color=CREAM, corner_radius=28,
                           border_width=1, border_color=BORDER)
        box.pack(fill="x", padx=6, pady=(14, 6))

        ctk.CTkLabel(box, text="✿", text_color=PINK, font=make_font(54)
                     ).pack(pady=(26, 0))
        ctk.CTkLabel(box, text=title, text_color=TEXT, justify="center",
                     font=make_font(17, "bold", TITLE_FONT)
                     ).pack(pady=(4, 4), padx=20)
        ctk.CTkLabel(box, text=hint, text_color=MUTED, font=make_font(13)
                     ).pack(pady=(0, 28), padx=20)

    # ----- progress area ----------------------------------------------------

    def _build_progress_area(self):
        card = ctk.CTkFrame(self, fg_color=CREAM, corner_radius=24,
                            border_width=1, border_color=BORDER)
        card.grid(row=4, column=0, sticky="ew", padx=24, pady=(8, 24))
        card.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(card, text="", text_color=TEXT,
                                        font=make_font(14, "bold"), anchor="w")
        self.stats_label.grid(row=0, column=0, sticky="w", padx=(22, 8), pady=(16, 6))

        self.clear_button = ctk.CTkButton(
            card, text="Clear Completed", width=140, height=34, corner_radius=17,
            fg_color=LAVENDER_SOFT, hover_color="#E2D5F5", text_color=PURPLE_HOVER,
            font=make_font(12, "bold"), command=self.clear_completed)
        self.clear_button.grid(row=0, column=1, padx=(0, 18), pady=(16, 6))

        self.progress_bar = ctk.CTkProgressBar(
            card, height=14, corner_radius=7, fg_color=TRACK,
            progress_color=PINK_DEEP)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=(22, 10), pady=(0, 18))
        self.progress_bar.set(0)

        self.percent_label = ctk.CTkLabel(card, text="0%", text_color=MUTED,
                                          font=make_font(13, "bold"), width=44)
        self.percent_label.grid(row=1, column=1, padx=(0, 18), pady=(0, 18))

    # ----- actions (what the buttons do) -----------------------------------

    def add_task(self):
        text = " ".join(self.entry.get().split())  # trims spaces, tidies gaps

        if not text:
            self.show_message("Oops, type something first ♡")
            self._flash_entry()
            return
        if len(text) > MAX_TASK_LENGTH:
            self.show_message(f"That's a long one! Keep it under {MAX_TASK_LENGTH} characters ♡")
            self._flash_entry()
            return

        self.store.add(text)
        self.entry.delete(0, "end")
        self._save()
        self.refresh()
        self._scroll_to_top()

    def toggle_task(self, task_id):
        self.store.toggle(task_id)
        self._save()
        # Wait a tick before redrawing so the checkbox can finish its own click
        self.after(80, self.refresh)

    def delete_task(self, task_id):
        self.store.delete(task_id)
        self._save()
        # Same idea: let the button finish its click animation first
        self.after(130, self.refresh)

    def clear_completed(self):
        removed = self.store.clear_completed()
        if removed == 0:
            self.show_message("Nothing completed to clear yet ♡")
            return
        self._save()
        self.refresh()
        self.show_message(f"Cleared {removed} completed task{'s' if removed != 1 else ''} ✿")

    # ----- helpers ----------------------------------------------------------

    def _save(self):
        if not self.store.save():
            self.show_message(
                "Couldn't save your tasks. Is the folder read-only? Your list "
                "is still safe while the app is open.", seconds=8)

    def _flash_entry(self):
        """Briefly outline the input box in pink to say 'look here'."""
        self.entry.configure(border_color=PINK_DEEP)
        self.after(700, lambda: self.entry.configure(border_color=BORDER))

    def _scroll_to_top(self):
        try:
            self.list_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass  # scrolling is just a nicety; never let it crash the app

    def refresh(self):
        """Redraw the task list, filter buttons and progress section."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        tasks = self.store.visible(self.current_filter)
        if tasks:
            for task in tasks:
                self._add_task_card(task)
        else:
            self._show_empty_state()

        self._style_filters()
        self._update_progress()

    def _update_progress(self):
        total, completed, remaining = self.store.counts()
        fraction = completed / total if total else 0

        if total == 0:
            self.stats_label.configure(text="No tasks yet ♡")
        elif remaining == 0:
            self.stats_label.configure(text=f"All {total} done, amazing! ♡")
        else:
            self.stats_label.configure(text=f"{completed} completed  ·  {remaining} remaining")

        self.progress_bar.set(fraction)
        self.percent_label.configure(text=f"{round(fraction * 100)}%")

    def _on_resize(self, event):
        """Re-wrap long task text when the window width changes."""
        if event.widget is not self or abs(event.width - self._last_width) < 20:
            return
        self._last_width = event.width
        self.motivation_label.configure(wraplength=max(200, event.width - 120))
        self.message_label.configure(wraplength=max(200, event.width - 90))
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(200, self.refresh)  # wait until resizing stops

    def _on_close(self):
        self.store.save()
        self.destroy()


# ---------------------------------------------------------------------------
# 4. Start the app
# ---------------------------------------------------------------------------

def main():
    app = LittleTasksApp()
    app.mainloop()


if __name__ == "__main__":
    main()
