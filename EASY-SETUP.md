# EASY SETUP — Aesthetic AI Studio v1

**For Windows beginners. No technical knowledge needed.**
This guide walks you through every click. If you can install a normal
program, you can do this.

**Created by Dr. Asif Ahmad**

---

## Part 1 — Install Python (one time, ~5 minutes)

The app needs Python, a free tool that runs the program.

1. Open your browser and go to **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python 3.x"** button.
3. Run the downloaded file.
4. ⚠️ **VERY IMPORTANT:** on the *first* screen of the installer, tick the
   checkbox **"Add python.exe to PATH"** at the bottom — then click
   **Install Now**.
5. When it says "Setup was successful", click **Close**.

> If you skipped the checkbox, uninstall Python and reinstall with the box
> ticked. Everything else in this guide will fail without it.

## Part 2 — Get the app files (one time, ~2 minutes)

1. You received the app as a **ZIP file** (e.g. `aesthetic-ai-studio.zip`).
2. **Right-click** the ZIP → **Extract All…** → **Extract**.
3. Open the extracted folder. You should see files including
   `Start-Windows.cmd`, `app.py`, and `requirements.txt`.

> Tip: move the extracted folder somewhere permanent, like
> `Documents\Aesthetic-AI-Studio`. Don't run it from inside the ZIP.

## Part 3 — Start the app (every time you use it)

1. **Double-click `Start-Windows.cmd`** (it has a little gear icon).
2. A black window opens and does the setup automatically:
   - First run only: it creates a private environment and installs the
     needed packages. This takes 1–3 minutes and needs internet.
     **Don't close the window** — wait for it.
   - Your browser opens by itself to **http://127.0.0.1:4321**.
3. If the browser doesn't open, type `http://127.0.0.1:4321` into your
   browser's address bar manually.

> **Keep the black window open** while you use the app. Closing it stops
> the app. To stop properly, press `Ctrl+C` in the black window or just
> close it.

## Part 4 — Make your first presentation (~5 minutes)

1. Click **New Presentation**.
2. Fill in:
   - **Title** — e.g. "Food Safety & Hygiene Workshop"
   - **Audience** — e.g. "Hospital canteen staff"
   - **Slides** — how many you want (start with 8–10)
   - **Theme** — pick one you like, e.g. *dark-green-gold*
3. Click **Generate Outline**. Read the outline — it starts with a cover
   slide and ends with a thank-you slide. Edit any line you don't like.
4. Click **Build Slides**. The app writes every slide for you.
5. Click any slide to **edit text**, then **Save**.
6. Click **Export** → **PowerPoint (.pptx)**. You'll see a validation
   report (green checks = the file was verified). Click **Download**.
7. Open the `.pptx` in PowerPoint — every text box, shape, and table is
   fully editable.

**Try the sample deck first:** open the built-in 30-slide food-safety
workshop deck to see all 13 layouts, tables, checklists, and speaker
notes in action before making your own.

## Part 5 — Using AI providers (optional)

The app works fully **offline** out of the box. If you want smarter
drafting with an online AI:

1. Get an API key from your provider (OpenAI, Anthropic, Google, …).
2. In the app, open **Settings** → paste the key → **Save**.
3. Keys are stored only on your computer, in your `data/` folder.

> The app never sends anything anywhere unless you add a key and choose
> an online provider. Offline mode sends nothing, ever.

## Troubleshooting

| Problem | What to do |
|---|---|
| Double-clicking `Start-Windows.cmd` flashes and closes | Python isn't installed or PATH wasn't ticked. Redo Part 1, ticking **"Add python.exe to PATH"**. |
| `Python was not found` message | Same as above — reinstall Python with the PATH checkbox. |
| Stuck on "Installing required packages" | Needs internet. Check your connection, close the window, and double-click `Start-Windows.cmd` again — it resumes where it stopped. |
| Browser shows "can't reach this site" | The black window may have closed or errored. Scroll up in the black window for a red error message; make sure port 4321 isn't used by another program. |
| `pip install` fails with SSL / network errors | Office/hotel Wi-Fi sometimes blocks it. Try a mobile hotspot, then rerun. |
| Export validation shows a red ✗ | Read the check details — it tells you exactly what failed (e.g. a slide with no content). Fix that slide and export again. |
| I want to start fresh | Close the app, delete the `data/` folder inside the app folder, and restart. All projects will be gone — back up first if needed. |
| Antivirus warns about the `.cmd` file | It's a plain text script (right-click → Edit to read it). Allow it or ask your IT admin. |

## Uninstall

Delete the app folder and the Python program (Settings → Apps). Nothing
else was installed on your system — the app's Python environment lives
inside the app's own `venv/` folder.
