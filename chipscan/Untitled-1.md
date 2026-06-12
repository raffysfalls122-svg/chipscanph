# 📱 ChipScan PH — Complete Project Handover & Guide

This document is prepared specifically for copy-pasting into another AI assistant. It provides a complete architectural overview, the exact setup and deployment procedures, a summary of past issues/fixes, and details on how the new **Google Gemini-based backend scanning API** is configured and runs.

---

## 🏗️ 1. Project Overview & Tech Stack

**ChipScan PH** is a mobile-responsive smartphone storage chip grading and pricing application designed for repair shop technicians in the Philippines. It evaluates, categorizes, and prices recycled eMMC and UFS memory chips.

### Tech Stack:
*   **Backend**: Python 3.10+ & Django (lightweight server-side database router).
*   **Database**: SQLite (`db.sqlite3`), with automatic data pre-seeding.
*   **Frontend**: Vanilla HTML5, CSS3 (responsive grid optimized for mobile screens up to `430px`), and Vanilla JavaScript.
*   **OCR / Image Analysis Engines**:
    1.  **Primary (New)**: Server-side **Gemini 2.0 Flash API** endpoint (`/api/scan/image/`) that processes uploaded pictures or periodic camera frames to extract chip codes with extreme precision.
    2.  **Secondary (Legacy)**: Client-side **Tesseract.js** (v5) running in the browser for manual crop/rotate retry fallbacks.

---

## 📁 2. Project File Structure

```
├── 📁 chipscan
│   ├── 🐍 __init__.py
│   ├── 🐍 settings.py
│   ├── 🐍 urls.py
│   └── 🐍 wsgi.py
├── 📁 scanner
│   ├── 📁 migrations
│   │   ├── 🐍 0001_initial.py
│   │   ├── 🐍 0002_chip_status_scanhistory_status.py
│   │   ├── 🐍 0003_chip_alias_chip_alternate_codes_chip_ocr_text.py
│   │   └── 🐍 __init__.py
│   ├── 📁 templates
│   │   └── 📁 scanner
│   │       └── 🌐 index.html
│   ├── 🐍 __init__.py
│   ├── 🐍 models.py
│   ├── 🐍 urls.py
│   └── 🐍 views.py
├── ⚙️ .gitignore
├── 📝 MOBILE_TESTING.md
├── 📝 README.md
├── 📝 SYSTEM_OVERVIEW.md
├── 🐍 manage.py
└── 📄 requirements.txt
```

---

## ⚙️ 3. How to Run & Configure the System

The application relies on Django and uses the Python standard library `urllib` to request Gemini API tokens, requiring no heavy external SDK wrappers.

### Step 1: Install Dependencies
Run the following inside the root project directory:
```bash
pip install -r requirements.txt
```
*(Only requires Django >= 4.2.0)*

### Step 2: Configure the Gemini API Key
The server-side image analysis requires a Gemini API key. Set it as an environment variable before starting the server.

*   **Windows (PowerShell)**:
    ```powershell
    $env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```
*   **Windows (CMD)**:
    ```cmd
    set GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
    ```
*   **Linux/Mac**:
    ```bash
    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```

### Step 3: Run Database Migrations
Create and configure the local SQLite database file:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4: Start Django Development Server
To make the site accessible to external devices (like your mobile phone) on the same local network, run:
```bash
python manage.py runserver 0.0.0.0:8000
```

### Step 5: Lazy Pre-seeding (Automatic)
The very first time you load the index page (`http://localhost:8000` or the network IP), `scanner/views.py` will automatically seed the database with:
*   **Default Accounts**:
    *   `admin` (Password: `admin123`, Role: `admin`)
    *   `tech1` (Password: `tech123`, Role: `tech`)
*   **Base Pricing Matrix**: Standard tiers (A1 to A5) for Coded and Non-coded classifications.
*   **Built-in Chips**: 28 prominent Samsung, SK Hynix, and Toshiba/Kioxia flash memory chipsets.

---

## 📱 4. Mobile Hosting & Camera Testing Guide

Mobile web browsers enforce strict security rules that block camera access (`getUserMedia`) on insecure `http` connections. To test the live camera scanner, use one of the following methods:

### Option A: Secure Tunneling (Recommended for iOS/Safari & Android)
Ngrok creates a secure `https://` proxy to your local server, bypassing browser security blocks.
1. Make sure Django is running on port 8000.
2. In a separate terminal, start the tunnel:
   ```bash
   ngrok http 8000
   ```
3. Open the generated `https://<random-id>.ngrok-free.app` URL on your phone's browser. The camera will prompt for permission and function instantly.

### Option B: Local Wi-Fi Insecure Origin Bypass (Android Chrome Only)
1. Find your computer's local IP address (using `ipconfig` on Windows, e.g. `192.168.1.15`).
2. Open Chrome on your Android phone and navigate to:
   ```
   chrome://flags/#unsafely-treat-insecure-origin-as-secure
   ```
3. Enable the flag, paste `http://192.168.1.15:8000` into the text box, and tap **Relaunch**.
4. Access `http://192.168.1.15:8000` on your phone to use the camera.

---

## 🔍 5. Summary of the Last Conversation & Problems Faced

During the last development sessions, the system went through optimization iterations. The following errors and bugs were resolved:

### ⚠️ The Main Bug: Scanner Stuck on Rotated Orientation Retries
*   **The Problem**: When a full-image upload or camera scan failed to detect any text, the OCR engine attempted a fallback rotation loop (`0° -> 90° -> 180° -> 270°`) to read rotated text. On complete failure (after `270°`), the loader spinner did not close, locking the user interface indefinitely on the text:
    `"ALIGNMENT RETRY (270°): Scanning rotated orientation..."`
*   **The Diagnosis**: The asynchronous callback loop of the final Tesseract run returned `false` without executing the layout clean-up block in its final recursion base-case.
*   **The Fix**: Restored clean overlay removal (`overlay.classList.remove('s')`) in the final rotation base-case inside `processOcrResult` (in [index.html](file:///c:/Users/Windows%2011/Desktop/chipscanph/scanner/templates/scanner/index.html)). Now it gracefully dismisses the spinner, displays an actionable failure toast, and suggests the manual crop flow.

### 🚫 The RAM Pollution Bug
*   **The Problem**: Technicians were accidentally scanning CPU markings or volatile DRAM (RAM) chips (which cannot be graded or priced) and seeding them into the storage database.
*   **The Fix**: Implemented a RAM rejection filter in the database check logic (`checkChip()` inside `index.html`) using a regular expression:
    ```javascript
    /^(K4[A-Z]|H9HK|H9HN|H5[A-Z])/i
    ```
    This automatically detects Samsung DDR3/DDR4 (`K4B`/`K4A`) and SK Hynix (`H5...`/`H9HK`) RAM chips, shows a clear warning block, and blocks saving them to prevent database contamination.

### 🐛 Other UI/UX Bugs Fixed:
*   **ADD Page Not Saving**: Fixed issues with the initialization and toggles of `selectedManualStatus` and ensured `initStorage()` correctly refreshes `localDatabase` after saving manual chips.
*   **Result Scan Area Stuck**: Added a reset button that cleans all input fields, results display, confidence indicators, and state variables.
*   **Wrong Code Auto-Typed**: Prevented the engine from executing lookups immediately after scans. Scans now populate an **editable text box** first, requiring the technician to review/correct the text and hit "CHECK" manually.
*   **Align/Adjust Crop Modal Freezing**: Offloaded heavy canvas calculations and Tesseract processing out of the main thread using an asynchronous sequence (`setTimeout`) to display loading indicators correctly.

---

## ⚡ 6. Detailed API Upgrade: Gemini-Powered Backend Scanner

To solve client-side OCR issues (bad angles, shadows, low lighting), the application now passes images to a backend API that utilizes the Google Gemini API.

### How it works:
1.  **Endpoint**: `POST /api/scan/image/`
2.  **Processing**: Receives an uploaded photo (camera frame or file selection), base64 encodes it, and makes a direct HTTP POST request to `generativelanguage.googleapis.com` calling the `gemini-2.0-flash` model.
3.  **Prompt Instruction**:
    > *"You are a phone chip code reader for repair technicians in the Philippines. Look at this motherboard chip image. Find the storage chip model code only. Samsung codes START WITH KM. SK Hynix codes START WITH H9. Toshiba codes START WITH TY. IGNORE lines starting with SEC, B4, B7, B8, B9, PG, MH, JM, MT. Return ONLY the model code, nothing else. If not found return: NONE"*
4.  **Database Mapping**: The view takes the returned code (e.g., `KMRX1000BM`), matches it against the local SQLite database (including aliases/alternate codes), and returns a JSON payload containing the classification status, grade, storage size, maker, and prices.
5.  **Camera Integration**: The front-end viewfinder runs a 6-second countdown timer. Once the timer hits 0, it takes a canvas snap of the camera viewfinder stream and sends it to `/api/scan/image/` for identification. If the scan is successful, the camera turns off, and the results display. If not, it begins another 6-second countdown.