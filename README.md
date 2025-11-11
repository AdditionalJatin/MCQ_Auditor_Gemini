# 🤖 MCQ Auditor Gemini

This project uses the Google Gemini 2.5-Flash model to audit Multiple Choice Questions (MCQs) for common errors.

It consists of two parts:
1.  **FastAPI Backend (Python):** A server that receives a Google Doc URL, fetches its text, and uses the Gemini API to audit each question for errors (like duplicates, invalid options, etc.).
2.  **Google Apps Script (Frontend):** A script that runs inside a Google Sheet, adding a custom menu. This menu allows you to send a Doc URL from a cell to the FastAPI backend and then writes the audit results back into your sheet.

## How It Works

1.  A user pastes a public Google Doc URL into a cell in Google Sheets.
2.  With the cell selected, the user clicks the "🤖 MCQ Auditor" > "Audit Doc" menu item.
3.  The **Apps Script** sends the URL to your deployed **FastAPI server**.
4.  The FastAPI server fetches the Google Doc, parses the questions, and audits each one using the **Gemini API**.
5.  The server returns a JSON list of the results.
6.  The Apps Script receives this JSON and neatly formats it into the Google Sheet, creating a header row and populating the data. It also color-codes the "Status" column for easy reading.

---

## SETUP: Part 1 - Deploy the FastAPI Backend
`uvicorn main:app --host 0.0.0.0 --port $PORT`

## SETUP: Part 2 - Configure Google Sheets

This is how you connect your Google Sheet to your live backend.

### 1. Create the Script

1.  Create a new [Google Sheet](https://sheets.new).
2.  Click on **Extensions** > **Apps Script**.
3.  This will open a new tab. Delete any placeholder code in the `Code.gs` file.

### 2. Paste the Apps Script Code

🚀 How to Use the Auditor
1. Authorize the Script (One-Time-Only)
Go back to your Google Sheet tab and refresh the page.

A new menu "🤖 MCQ Auditor" will appear.

Click the menu and select "Audit Doc from Active Cell".

A popup "Authorization Required" will appear. Click "Continue".

Choose your Google Account.

You will see a "Google hasn't verified this app" screen. This is normal.

Click "Advanced", then click "Go to (Your script name) (unsafe)".

Click "Allow" on the final screen.

2. Run an Audit
Click any cell (e.g., A2).

Paste a publicly viewable Google Doc URL into that cell.

With the cell still selected, click 🤖 MCQ Auditor > Audit Doc from Active Cell.

A "🚀 Starting audit..." toast will appear. Wait for the audit to complete.
