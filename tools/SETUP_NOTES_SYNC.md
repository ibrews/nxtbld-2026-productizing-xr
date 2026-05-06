# Setting up `?notes` Cloud Sync

The `?notes` view (phone speaker-notes companion) syncs script edits, bullet overrides, target finish time, and clicker state to a Google Sheet via a small Apps Script Web App. One-time setup, ~10 minutes.

## 1. Open your sheet

The current FMX sheet:
https://docs.google.com/spreadsheets/d/1i2uKrT4UpslV8hWOetBZy4IW4ORWKidUnpwjigtzVP4/edit

It must be shared with `reminders-sync@agile-lens-reminders.iam.gserviceaccount.com` (Editor) — but the Apps Script below runs **as your own Google account** so the SA share is only needed for MCP-side ops, not for `?notes` runtime.

## 2. Open Apps Script editor

In the sheet → **Extensions → Apps Script**. A new tab opens with `Code.gs`.

## 3. Paste the script

Replace the contents of `Code.gs` with the contents of [`tools/notes-sync.gs`](notes-sync.gs).

If you're binding to a different sheet, update the `SHEET_ID` constant at the top.

Save (`⌘S`). Name the project something like "Spatial Deck Notes Sync".

## 4. Deploy as a Web App

- Top-right **Deploy → New deployment**
- Gear icon → **Web app**
- Description: `Spatial Deck notes sync v1`
- **Execute as:** Me (your Google account)
- **Who has access:** Anyone with the link
- Click **Deploy**
- First time: Google asks you to authorize. Click through "Advanced → Go to project (unsafe)" if it warns — that's the standard Apps Script flow when no review has been done.
- Copy the **Web app URL**. Looks like:
  `https://script.google.com/macros/s/AKfycb…/exec`

## 5. Save the URL locally

Create `notes-config.json` in the repo root:

```json
{
  "gasUrl": "https://script.google.com/macros/s/AKfycb.../exec",
  "deckId": "fmx-2026"
}
```

This file is gitignored. Use a different `deckId` per fork (`harvardxr-2026`, `fmx-2026`, etc.) so multiple decks can share the same sheet.

## 6. Test from the command line

```bash
curl -L -X POST "https://script.google.com/macros/s/AKfycb.../exec" \
  -H "Content-Type: text/plain;charset=utf-8" \
  --data '{"action":"ping","deckId":"fmx-2026"}'
```

Expected: `{"ok":true,"result":{"pong":true,"ts":...}}`

## 7. Open the deck

Open `index.html?notes` in your phone browser. First load:
- Reads `notes-config.json`
- Calls `seedNotes` with the current `SECTIONS` notes (only seeds if the sheet is empty for this deckId)
- Renders the phone view

If you ever change `SECTIONS` notes in `index.html` and want to push them to the sheet (overwriting), use the "Reseed from SECTIONS" button on the settings slide.

## Re-deploying after edits

Apps Script web apps have versioned deployments. After you edit `Code.gs`:

- **Deploy → Manage deployments → ✏ edit the active deployment → Version: New version → Deploy**
- The URL stays the same.

If you create a *new deployment* instead, you get a new URL — update `notes-config.json` accordingly.

## Sheet schema (for reference)

The script auto-creates two tabs:

**`slides`**

| deckId | idx | type | title | script | bullets | video_seconds |
|---|---|---|---|---|---|---|
| fmx-2026 | 0 | cover | Welcome | Hi everyone... | (newline-separated bullets) | (empty or number) |

**`meta`**

| deckId | key | value |
|---|---|---|
| fmx-2026 | target_finish | 2026-09-25T18:30:00 |
| fmx-2026 | default_view | bullets |
| fmx-2026 | calibration | `{"videoDurations":{...},"thumbnails":{...}}` |
| fmx-2026 | state | `{"currentSlide":3,"locked":true,...}` |

Edit cells directly in the sheet and they'll show up in the deck on next load (or every 1s while padlock-locked).
