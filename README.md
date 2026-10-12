# little tasks ♡

A cozy, pastel to-do list for your desktop. *A little progress every day.*

Built with **Python** and **CustomTkinter**, with a soft lavender, blush pink and cream look. Your tasks are saved automatically in a local JSON file, so they are still there the next time you open the app.

## Features

- Add tasks with the **Add Task +** button or by pressing **Enter**
- Tick a task to mark it completed (strikethrough + softer colors), untick to bring it back
- Delete individual tasks with the ✕ button
- Filter by **All**, **Active** or **Completed** (each shows a live count)
- Progress section with completed/remaining counts and a progress bar
- **Clear Completed** button to tidy up in one click
- Friendly messages instead of pop-up errors (for example when you try to add an empty task)
- Cute empty states for every filter
- Today's date and a motivational message that changes every so often
- Scrolling for long lists, and text that re-wraps when you resize the window
- Auto-saves to `tasks.json`, creates it if missing, and recovers safely if the file is ever damaged

## Requirements

- Windows 10/11 (also works on macOS and Linux)
- Python 3.9 or newer
- CustomTkinter (installed from `requirements.txt`)

## Installation

```bash
# 1. Go into the project folder
cd little-tasks

# 2. (Recommended) create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install the dependency
pip install -r requirements.txt
```

## How to run

```bash
python main.py
```

## Project structure

```text
little-tasks/
├── main.py            # the whole application
├── tasks.json         # your saved tasks (created automatically)
├── requirements.txt   # Python dependencies
├── README.md          # this file
└── .gitignore         # files Git should skip
```

## How it works

- `TaskStore` loads, changes and saves the task list (`tasks.json`).
- `LittleTasksApp` builds the window: header, input, filters, task list and progress section.
- Colors and fonts are defined as constants at the top of `main.py`, so you can re-theme the app by changing a few lines.

## Ideas for later

- Edit a task by double-clicking it
- Due dates and reminders
- A dark "midnight lavender" theme
- Package as a `.exe` with PyInstaller

Made with ♡ by Dammoju Harshini
